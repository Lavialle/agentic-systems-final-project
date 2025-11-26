import os
from dotenv import load_dotenv
from langfuse.langchain import CallbackHandler

# Charger les variables d'environnement depuis le fichier .env
if os.path.exists(".env"):
    load_dotenv()
    print("Environment variables loaded from .env file.")

# Récupérer les clés API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERP_API_KEY = os.getenv("SERP_API_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL")

# Vérifier que les clés API sont définies
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API Key is missing. Please check your .env file.")
if not SERP_API_KEY:
    raise ValueError("SerpAPI Key is missing. Please check your .env file.")
if not all([LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_BASE_URL]):
    raise ValueError("Langfuse configuration is missing. Please check your .env file.")

# Configuration de l'application
MAX_CHARS = 5000  # Nombre maximum de caractères à traiter pour les textes de loi

# Initialiser le handler Langfuse global

langfuse_handler = CallbackHandler()