import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv

load_dotenv()
BUCKET_NAME = os.getenv("BUCKET_NAME")
s3 = boto3.client(
    's3',
    endpoint_url=os.getenv("R2_ENDPOINT_URL"),
    aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY")
)

BASE_URL = "https://www.assemblee-nationale.fr"

# ----------------------------
#  Extracteur d’ID 
# ----------------------------
def extract_id(url):
    patterns = {
        "proposition_loi": r"propositions/pion([\w-]+)\.asp",
        "projet_loi": r"projets/pl([\w-]+)\.asp",
        "rapport_legislatif": r"rapports/r([\w-]+)\.asp",
        "texte_adopte": r"/ta/ta([\w-]+)\.asp",
        "dossier_legislatif": r"/textes/l17b(\d+)_",
    }
    for dtype, pattern in patterns.items():
        m = re.search(pattern, url)
        if m:
            return dtype, m.group(1)
    return "inconnu", None

# ----------------------------
#  Trouver le lien PDF 
# ----------------------------
def get_pdf_link(page_url):
    try:
        r = requests.get(page_url, timeout=20)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return "404"
        return None
    except Exception as e:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    a = soup.find("a", title="Accéder au document au format PDF")
    if not a:
        return "no_link"
    pdf_rel = a.get("href")
    if not pdf_rel or not pdf_rel.endswith(".pdf"):
        return "no_link"
    return urljoin(BASE_URL, pdf_rel)

# ----------------------------
#  Upload vers Cloud & Nettoyage 
# ----------------------------
def upload_to_cloud_and_clean(local_path, filename, log):
    cloud_key = f"pdfs/{filename}"
    try:
        s3.upload_file(local_path, BUCKET_NAME, cloud_key)
        log(f"[CLOUD] ☁️ Upload réussi : {filename}")
        
        os.remove(local_path)
        return True

    except Exception as e:
        log(f"[ERREUR CLOUD] Impossible d'envoyer {filename}: {e}")
        return False

# ----------------------------
#  Télécharger un PDF
# ----------------------------
def download_pdf(doc_type, doc_id, pdf_url, pdf_dir, log):
    filename = f"{doc_type}_{doc_id}.pdf"
    filepath = os.path.join(pdf_dir, filename)

    try:
        log(f"[DL] {filename}")
        r = requests.get(pdf_url, timeout=20)
        r.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(r.content)

        if upload_to_cloud_and_clean(filepath, filename, log):
            return filename
        else:
            return None

    except Exception as e:
        log(f"[ERREUR] Téléchargement impossible ({pdf_url}) : {e}")
        return None

# ----------------------------
#  Fonction principale 
# ----------------------------
def download_new_pdfs(rows_to_process, pdf_dir, log):
    results = []
    for row in rows_to_process:
        url = row["url"]
        log(f"\n--- Analyse : {url}")

        doc_type, doc_id = extract_id(url)
        pdf_link_or_status = get_pdf_link(url)

        if pdf_link_or_status in ["404", "no_link", None]:
            status = pdf_link_or_status if pdf_link_or_status else "error"
            log(f"[STATUT] {status}")
            results.append({"url": url, "status": status, "filename": None})
            continue

        pdf_url = pdf_link_or_status
        if not doc_id:
            log("[STATUT] Pas d'ID")
            results.append({"url": url, "status": "no_id", "filename": None})
            continue

        filename = download_pdf(doc_type, doc_id, pdf_url, pdf_dir, log)
        
        if filename:
            results.append({"url": url, "status": "success", "filename": filename})
        else:
            results.append({"url": url, "status": "dl_failed", "filename": None})

    return results