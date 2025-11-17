import os
import polars as pl
import pandas as pd
from datetime import datetime

from scrap_urls_all import scrap_urls_all
from download_pdfs import download_new_pdfs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "db")
PDF_DIR = os.path.join(DB_DIR, "pdf")
LOG_DIR = os.path.join(DB_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, "db_urls.parquet")

logfile = os.path.join(LOG_DIR, f"pipeline_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.log")

def log(message: str):
    timestamp = datetime.now().isoformat()
    line = f"{timestamp} — {message}"
    print(line)
    with open(logfile, "a") as f:
        f.write(line + "\n")
    return line

# ===============================================
#  ÉTAPE 1: LANCEMENT DU SCRAPING
# ===============================================
log("\n" + "="*30 + " ÉTAPE 1: SCRAPING " + "="*30) 
log("Lancement du scraping (Selenium)...")

try:
    df_scraped_pandas = scrap_urls_all()
    log(f"Scraping terminé. {len(df_scraped_pandas)} URLs trouvées.")
except Exception as e:
    log(f"ERREUR FATALE: Le scraping (scrap_urls_all) a échoué : {e}")
    exit(1)

try:
    new_df = pl.from_pandas(df_scraped_pandas)
    log("Conversion des URLs scrapées en Polars (en mémoire) réussie.")
except Exception as e:
    log(f"ERREUR: Échec de la conversion de Pandas à Polars: {e}")
    exit(1)

# ===============================================
#  ÉTAPE 2: CHARGEMENT DE L'ANCIENNE DB
# ===============================================
log("\n" + "="*25 + " ÉTAPE 2: CHARGEMENT DB " + "="*25) 
log("Chargement de l'ancienne base de données...")
try:
    old_df = pl.read_parquet(DB_PATH)
except FileNotFoundError:
    log("INFO: db_urls.parquet non trouvé. Création d'un DataFrame vide.")
    old_df = pl.DataFrame(
        {
            "url": pl.Series([], dtype=pl.String),
            "provenance": pl.Series([], dtype=pl.String),
            "added_at": pl.Series([], dtype=pl.String),
            "downloaded": pl.Series([], dtype=pl.Boolean),
            "is_404": pl.Series([], dtype=pl.Boolean),
        }
    )

old_urls = set(old_df["url"].to_list())
log(f"Ancienne base : {len(old_urls)} URLs")

if "downloaded" not in old_df.columns:
    log("INFO: Ajout de la colonne 'downloaded'")
    old_df = old_df.with_columns(pl.lit(False).alias("downloaded"))
if "is_404" not in old_df.columns:
    log("INFO: Ajout de la colonne 'is_404'")
    old_df = old_df.with_columns(pl.lit(False).alias("is_404"))

# ===============================================
#  ÉTAPE 3: COMPARAISON DES URLS
# ===============================================
log("\n" + "="*25 + " ÉTAPE 3: COMPARAISON " + "="*25) 
log("Comparaison des URLs (nouvelles vs anciennes)...")
new_urls = set(new_df["url"].to_list())

added_urls = new_urls - old_urls
log(f"Nouveaux liens (added): {len(added_urls)}")

retry_urls = set(
    old_df.filter(
        (pl.col("downloaded") == False) & (pl.col("is_404") == False)
    )
    .get_column("url")
    .to_list()
)
retry_urls = retry_urls - added_urls
log(f"Liens à réessayer (retry): {len(retry_urls)}")

urls_to_process = added_urls.union(retry_urls)
log(f"Total de liens à traiter : {len(urls_to_process)}")

if not urls_to_process:
    log("Aucun nouvel URL ou URL à réessayer → FIN")
    exit(0)

rows_from_new = (
    new_df.filter(pl.col("url").is_in(added_urls))
          .select(["url", "provenance"])
)
rows_from_old = (
    old_df.filter(pl.col("url").is_in(retry_urls))
          .select(["url", "provenance"])
)

rows_to_download = pl.concat([rows_from_new, rows_from_old]).to_dicts()

# ===============================================
#  ÉTAPE 4: TÉLÉCHARGEMENT
# ===============================================
log("\n" + "="*25 + " ÉTAPE 4: TÉLÉCHARGEMENT " + "="*25) 
log(f"⏬ Téléchargement de {len(rows_to_download)} URLs...")

# *** DEBUT DES MODIFICATIONS DU RÉSUMÉ ***
download_results = download_new_pdfs(rows_to_download, PDF_DIR, log)

# Analyser les résultats
count_404 = 0
count_success = 0
success_urls = set()
successful_files = []
failed_404_urls = set()

for res in download_results:
    if res["status"] == "success":
        count_success += 1
        success_urls.add(res["url"])
        successful_files.append(res["filename"])
    elif res["status"] == "404":
        count_404 += 1
        failed_404_urls.add(res["url"])

log("\n" + "-"*30 + " RÉSUMÉ DU TÉLÉCHARGEMENT " + "-"*30)
log(f"Traitement terminé.")
log(f"  > {count_success} succès.")
log(f"  > {count_404} erreurs 404.")

if successful_files:
    log("\n--- Fichiers téléchargés lors de cette session ---")
    for fname in successful_files:
        log(f"  [+] {fname}")

if failed_404_urls:
    log("\n--- URLs marquées comme 404 lors de cette session ---")
    for url in failed_404_urls:
        log(f"  [!] {url}")

# ===============================================
#  ÉTAPE 5: MISE À JOUR DE LA DB
# ===============================================
log("\n" + "="*25 + " ÉTAPE 5: MISE À JOUR DB " + "="*25)
log("Mise à jour de la base de données finale...")
today = datetime.now().date().isoformat()

new_entries = (
    new_df.filter(pl.col("url").is_in(added_urls))
          .select(["url", "provenance"])
          .with_columns(
              pl.lit(today).alias("added_at"),
              pl.lit(False).alias("downloaded"),
              pl.lit(False).alias("is_404")
          )
)

final_df = pl.concat([old_df, new_entries], how="vertical")

final_df = final_df.with_columns(
    pl.when(pl.col("url").is_in(success_urls))
    .then(True)
    .otherwise(pl.col("downloaded"))
    .alias("downloaded"),
    
    pl.when(pl.col("url").is_in(failed_404_urls))
    .then(True)
    .otherwise(pl.col("is_404"))
    .alias("is_404")
)

final_df.write_parquet(DB_PATH)

log(f"✔ DB mise à jour avec succès (Total: {len(final_df)} lignes).")
log("=== FIN DE L’ACTUALISATION ===")