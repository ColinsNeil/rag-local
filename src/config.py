"""Tous les réglages du projet, au même endroit."""

from pathlib import Path

# Chemins, calculés depuis ce fichier pour marcher quel que soit le dossier de lancement
ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"
CHROMA_DIR = ROOT_DIR / "chroma_db"
COLLECTION_NAME = "documents"

# Découpage des documents (en caractères)
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

# Nombre de morceaux retrouvés par question
TOP_K = 4

# Modèles Ollama (tous deux en local)
LLM_MODEL = "qwen2.5:3b"
EMBED_MODEL = "bge-m3"

# Fenêtre de contexte du modèle de réponse, en tokens.
# Ollama en utilise une petite par défaut (souvent 2048) et coupe le surplus
# sans prévenir : le modèle ne verrait alors qu'une partie des extraits.
# Estimation : 4 morceaux de 1200 caractères ~ 1400 tokens, plus la consigne
# et la question (~150), plus la réponse (300 à 500) ~ 2200 tokens.
# 4096 laisse de la marge. À relever si TOP_K ou CHUNK_SIZE augmentent.
NUM_CTX = 4096
