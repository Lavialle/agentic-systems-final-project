import os
import polars as pl
import pandas as pd
from datetime import datetime
import boto3
from dotenv import load_dotenv
import io

from scrap_urls_all import scrap_urls_all
from download_pdfs import download_new_pdfs

load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "db")
PDF_DIR = os.path.join(DB_DIR, "pdf")
LOG_DIR = os.path.join(DB_DIR, "logs")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

BUCKET_NAME = os.getenv("BUCKET_NAME")
s3 = boto3.client(
    's3',
    endpoint_url=os.getenv("R2_ENDPOINT_URL"),
    aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY")
)

logfile = os.path.join(LOG_DIR, f"pipeline_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.log")

def log(message: str):
    timestamp = datetime.now().isoformat()
    line = f"{timestamp} — {message}"
    print(line)
    with open(logfile, "a") as f:
        f.write(line + "\n")
    return line

# ===============================================
#  ÉTAPE 0: RÉCUPÉRATION DB DEPUIS LE CLOUD
# ===============================================
log("\n" + "="*30 + " ÉTAPE 0: SYNC CLOUD " + "="*30)
log("Téléchargement de la DB depuis Scaleway...")

DB_FILENAME = "db_urls.parquet"
local_db_path = os.path.join(DB_DIR, DB_FILENAME)

try:
    s3.download_file(BUCKET_NAME, DB_FILENAME, local_db_path)
    log("✅ DB récupérée avec succès.")
    old_df = pl.read_parquet(local_db_path)
except Exception as e:
    log(f"⚠️ Pas de DB trouvée sur le Cloud ou erreur ({e}). Création d'une nouvelle.")
    old_df = pl.DataFrame(
        {"url": [], "provenance": [], "added_at": [], "downloaded": [], "is_404": [], "pdf_name": []},
        schema={"url": pl.String, "provenance": pl.String, "added_at": pl.String, "downloaded": pl.Boolean, "is_404": pl.Boolean, "pdf_name": pl.String}
    )

old_urls = set(old_df["url"].to_list())
log(f"Base actuelle : {len(old_urls)} URLs")

# ===============================================
#  ÉTAPE 1: SCRAPING 
# ===============================================
log("\n" + "="*30 + " ÉTAPE 1: SCRAPING " + "="*30) 
try:
    df_scraped_pandas = scrap_urls_all()
    log(f"Scraping terminé. {len(df_scraped_pandas)} URLs trouvées.")
    new_df = pl.from_pandas(df_scraped_pandas)
except Exception as e:
    log(f"ERREUR FATALE SCRAPING: {e}")
    exit(1)

# ===============================================
#  ÉTAPE 2 & 3: COMPARAISON
# ===============================================
log("\n" + "="*25 + " ÉTAPE 2/3: COMPARAISON " + "="*25)

# Sécurités colonnes
if "downloaded" not in old_df.columns: old_df = old_df.with_columns(pl.lit(False).alias("downloaded"))
if "is_404" not in old_df.columns: old_df = old_df.with_columns(pl.lit(False).alias("is_404"))

new_urls = set(new_df["url"].to_list())
added_urls = new_urls - old_urls
log(f"Nouveaux liens : {len(added_urls)}")

retry_urls = set(old_df.filter((pl.col("downloaded") == False) & (pl.col("is_404") == False)).get_column("url").to_list())
retry_urls = retry_urls - added_urls
log(f"À réessayer : {len(retry_urls)}")

urls_to_process = added_urls.union(retry_urls)
log(f"Total à traiter : {len(urls_to_process)}")

if not urls_to_process:
    log("Rien à faire. Fin.")

    exit(0)

rows_from_new = new_df.filter(pl.col("url").is_in(added_urls)).select(["url", "provenance"])
rows_from_old = old_df.filter(pl.col("url").is_in(retry_urls)).select(["url", "provenance"])
rows_to_download = pl.concat([rows_from_new, rows_from_old]).to_dicts()

# ===============================================
#  ÉTAPE 4: TÉLÉCHARGEMENT & UPLOAD CLOUD
# ===============================================
log("\n" + "="*25 + " ÉTAPE 4: DL & UPLOAD " + "="*25) 
download_results = download_new_pdfs(rows_to_download, PDF_DIR, log)

count_success = 0
count_404 = 0
success_urls = set()
failed_404_urls = set()

for res in download_results:
    if res["status"] == "success":
        count_success += 1
        success_urls.add(res["url"])
    elif res["status"] == "404":
        count_404 += 1
        failed_404_urls.add(res["url"])

log(f"Résultat : {count_success} succès (sur Cloud), {count_404} erreurs 404.")

# ===============================================
#  ÉTAPE 5: MISE À JOUR DB ET ENVOI CLOUD
# ===============================================

log("\n" + "="*25 + " ÉTAPE 5: SAUVEGARDE CLOUD " + "="*25)
today = datetime.now().date().isoformat()

successful_map = [
    {"url": r["url"], "pdf_name_new": r["filename"]}
    for r in download_results if r["status"] == "success" and r["filename"] is not None
]
df_success_map = pl.DataFrame(successful_map, schema=[("url", pl.String), ("pdf_name_new", pl.String)])

new_entries = (
    new_df.filter(pl.col("url").is_in(added_urls))
          .select(["url", "provenance"])
          .with_columns(
              pl.lit(today).alias("added_at"),
              pl.lit(False).alias("downloaded"),
              pl.lit(False).alias("is_404"),
              pl.lit(None).cast(pl.String).alias("pdf_name") 
          )
)

final_df = pl.concat([old_df, new_entries], how="vertical")

final_df = final_df.join(df_success_map, on="url", how="left")

final_df = final_df.with_columns(
    pl.when(pl.col("url").is_in(success_urls)).then(True).otherwise(pl.col("downloaded")).alias("downloaded"),
    pl.when(pl.col("url").is_in(failed_404_urls)).then(True).otherwise(pl.col("is_404")).alias("is_404"),
    pl.when(pl.col("pdf_name_new").is_not_null())
      .then(pl.col("pdf_name_new"))
      .otherwise(pl.col("pdf_name"))
      .alias("pdf_name")
).drop("pdf_name_new") 

final_df.write_parquet(local_db_path)

log("☁️  Envoi de la DB mise à jour vers Scaleway...")
try:
    s3.upload_file(local_db_path, BUCKET_NAME, DB_FILENAME)
    log("✅ DB synchronisée sur le Cloud.")
    os.remove(local_db_path) 
    log("🗑️ Fichier db_urls.parquet temporaire supprimé localement.")

except Exception as e:
    log(f"❌ ERREUR CRITIQUE: Impossible d'envoyer la DB sur le Cloud: {e}")

try:
    log_name = os.path.basename(logfile)
    s3.upload_file(logfile, BUCKET_NAME, f"logs/{log_name}")
    log("✅ Log envoyé sur le Cloud.")

except:
    pass

log("=== FIN DU PIPELINE ===")