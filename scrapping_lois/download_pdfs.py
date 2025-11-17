import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from datetime import datetime 

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
#  Télécharger un PDF 
# ----------------------------
def download_pdf(doc_type, doc_id, pdf_url, pdf_dir, log):
    """
    Télécharge le PDF.
    Retourne 'filename' en cas de succès OU s'il existe déjà.
    Retourne None en cas d'échec.
    """
    filename = f"{doc_type}_{doc_id}.pdf"
    filepath = os.path.join(pdf_dir, filename)

    if os.path.exists(filepath):
        log(f"[EXISTE] {filename} (Compté comme succès)")
        return filename

    try:
        log(f"[DL] {filename}")
        r = requests.get(pdf_url, timeout=20)
        r.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(r.content)

        log(f"[OK] PDF sauvegardé → {filepath}")
        return filename # Succès du téléchargement

    except Exception as e:
        log(f"[ERREUR] Téléchargement impossible ({pdf_url}) : {e}")
        return None # Échec du téléchargement

# ----------------------------
#  Fonction principale
# ----------------------------
def download_new_pdfs(rows_to_process, pdf_dir, log):
    """
    Traite les URLs et retourne une liste de résultats structurés.
    CHAQUE dictionnaire retourné DOIT contenir 'status' ET 'filename'.
    """
    results = []

    for row in rows_to_process:
        url = row["url"]
        log(f"\n--- Analyse : {url}")

        doc_type, doc_id = extract_id(url)
        pdf_link_or_status = get_pdf_link(url)

        if pdf_link_or_status == "404":
            log("[STATUT] Page 404 (Introuvable)")
            results.append({"url": url, "status": "404", "filename": None})
            continue
        
        if pdf_link_or_status == "no_link":
            log("[STATUT] Page chargée, mais aucun lien PDF trouvé")
            results.append({"url": url, "status": "no_link", "filename": None})
            continue

        if pdf_link_or_status is None:
            log("[STATUT] Erreur de chargement (timeout, 500, etc.)")
            results.append({"url": url, "status": "error", "filename": None})
            continue

        pdf_url = pdf_link_or_status
        
        if not doc_id:
            log("[STATUT] PDF trouvé, mais ID introuvable (skip)")
            results.append({"url": url, "status": "no_id", "filename": None})
            continue

        filename = download_pdf(doc_type, doc_id, pdf_url, pdf_dir, log)
        
        if filename:
            results.append({"url": url, "status": "success", "filename": filename})
        else:
            results.append({"url": url, "status": "dl_failed", "filename": None})

    return results