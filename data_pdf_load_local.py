import os
import boto3
import polars as pl
from dotenv import load_dotenv
from botocore.exceptions import ClientError
import time 

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PDF_LOCAL = os.path.join(BASE_DIR, "db_local_pdfs") 
DB_TEMP_PATH = os.path.join(BASE_DIR, "db_urls.parquet.tmp") 
DB_FILENAME = "db_urls.parquet"

BUCKET_NAME = os.getenv("BUCKET_NAME")
ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
SECRET_KEY = os.getenv("R2_SECRET_ACCESS_KEY")

s3 = boto3.client(
    's3',
    endpoint_url=ENDPOINT_URL,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)

def download_pdfs_guided_by_db():
    
    if not os.path.exists(DB_PDF_LOCAL):
        os.makedirs(DB_PDF_LOCAL, exist_ok=True)
        print(f"Création du dossier local : {DB_PDF_LOCAL}")

    total_downloaded = 0
    total_skipped = 0
    
    try:
        print("1. 📥 Téléchargement de la DB pour obtenir l'index des fichiers...")
        s3.download_file(BUCKET_NAME, DB_FILENAME, DB_TEMP_PATH)
        df = pl.read_parquet(DB_TEMP_PATH)
        
        print("2. ⚙️ Préparation de l'index des clés cloud...")
        cloud_keys = (
            df.filter(pl.col("downloaded") == True)
              .select(pl.concat_str([pl.lit("pdfs/"), pl.col("pdf_name")]).alias("cloud_key"))
              .get_column("cloud_key")
              .to_list()
        )
        
        print(f"   {len(cloud_keys)} fichiers à télécharger trouvés dans l'index.")
        
        print("\n3. ⬇️ Démarrage du téléchargement")

        for cloud_key in cloud_keys:
            filename = os.path.basename(cloud_key)
            local_path = os.path.join(DB_PDF_LOCAL, filename)
                
            s3.download_file(BUCKET_NAME, cloud_key, local_path)
            print(f"   [OK] {filename}")
            total_downloaded += 1

        print("\n" + "="*50)
        print("✅ TÉLÉCHARGEMENT GUIDÉ RÉUSSI.")
        print(f"   Fichiers téléchargés : {total_downloaded}")
        print(f"   Fichiers sautés : {total_skipped}")
        print("="*50)
        
    except ClientError as e:
        print(f"\n❌ ERREUR CRITIQUE D'ACCÈS : {e}")
        print("Vérifie l'accès au bucket ou la présence de 'db_urls.parquet'.")
    except Exception as e:
        print(f"\n❌ ERREUR INCONNUE : {e}")
    finally:
        if os.path.exists(DB_TEMP_PATH):
            os.remove(DB_TEMP_PATH)

if __name__ == "__main__":
    download_pdfs_guided_by_db()