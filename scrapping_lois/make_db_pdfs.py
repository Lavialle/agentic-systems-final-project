import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import time

BASE_URL = "https://www.assemblee-nationale.fr"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "db") 
OUTPUT_DIR = os.path.join(DB_DIR, "pdf")
os.makedirs(OUTPUT_DIR, exist_ok=True)

unknown_counter = 1


def extract_id(url):
    patterns = {
        "proposition_loi": r"propositions/pion([\w-]+)\.asp",
        "projet_loi": r"projets/pl([\w-]+)\.asp",
        "rapport_legislatif": r"rapports/r([\w-]+)\.asp",
        "texte_adopte": r"/ta/ta([\w-]+)\.asp",
        "dossier_legislatif": r"/textes/l17b(\d+)_",
    }

    for dtype, pat in patterns.items():
        m = re.search(pat, url)
        if m:
            return dtype, m.group(1)

    return "inconnu", None


def download_pdf(doc_type, doc_id, pdf_url):
    """
    Télécharge le PDF et retourne True si succès (ou déjà existant),
    False si échec.
    """
    global unknown_counter

    if not doc_id:
        filename = f"{doc_type}_unknown_{unknown_counter}.pdf"
        unknown_counter += 1
    else:
        filename = f"{doc_type}_{doc_id}.pdf"

    filepath = os.path.join(OUTPUT_DIR, filename)

    if os.path.exists(filepath):
        print(f"✔️ Déjà téléchargé : {filename}")
        return True 

    print(f"⬇️ Téléchargement : {filename}")

    try:
        r = requests.get(pdf_url, timeout=20)
        r.raise_for_status() 
        with open(filepath, "wb") as f:
            f.write(r.content)
        print(f"✅ Fichier sauvegardé : {filename}")
        return True 
    except Exception as e:
        print(f"❌ ERREUR de téléchargement pour {filename}: {e}")
        return False 


def get_pdf_link(page_url):
    try:
        r = requests.get(page_url, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Impossible de charger {page_url} → {e}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    a = soup.find("a", title="Accéder au document au format PDF")

    if not a:
        print("⚠️ Aucun PDF trouvé sur cette page")
        return None

    pdf_rel_path = a.get("href")

    if not pdf_rel_path or not pdf_rel_path.endswith(".pdf"):
        print("⚠️ Lien trouvé, mais ce n'est pas un PDF")
        return None

    return urljoin(BASE_URL, pdf_rel_path)

# -----------------------------------------------
# NOUVEAU: BOUCLE PRINCIPALE AVEC MISE À JOUR DB
# -----------------------------------------------

df_path = os.path.join(DB_DIR, "db_urls.parquet")
print(f"Lecture de {df_path}...")
try:
    df = pd.read_parquet(df_path)
except FileNotFoundError:
    print(f"ERREUR: Le fichier {df_path} n'existe pas.")
    exit()

if "downloaded" not in df.columns:
    print("Création de la colonne 'downloaded', initialisée à False.")
    df["downloaded"] = False
else:
    print("Colonne 'downloaded' existante.")


print(f"\n=== DÉBUT DU TRAITEMENT: {len(df)} URLs à vérifier ===")

for index, row in df.iterrows():
    url = row["url"]
    print(f"\n=== PAGE ({index + 1}/{len(df)}) : {url}")

    doc_type, doc_id = extract_id(url)
    print(f"→ Type détecté : {doc_type}")
    print(f"→ ID détecté : {doc_id if doc_id else 'AUCUN'}")

    pdf_url = get_pdf_link(url)
    if not pdf_url:
        print("⚠️ PDF introuvable → on continue")
        df.at[index, "downloaded"] = False 
        continue


    success = download_pdf(doc_type, doc_id, pdf_url)


    df.at[index, "downloaded"] = success

    time.sleep(0.1)

print("\n=== FIN — Tous les PDF traités ===")
print(f"💾 Sauvegarde du DataFrame mis à jour dans {df_path}...")
df.write_parquet(df_path, index=False)
print("✅ Base de données (db_urls.parquet) mise à jour avec succès.")