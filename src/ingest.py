"""Lecture des documents, découpage, embeddings et stockage dans ChromaDB."""

import sys
import time

import chromadb
import ollama
from pypdf import PdfReader

import config

BATCH_SIZE = 32  # morceaux envoyés à Ollama en une fois


def read_documents(docs_dir):
    """Renvoie une liste de (fichier, page, texte). La première page vaut 1."""
    pages = []
    for path in sorted(docs_dir.iterdir()):
        if path.suffix.lower() == ".pdf":
            reader = PdfReader(path)
            texts = [page.extract_text() or "" for page in reader.pages]
        elif path.suffix.lower() == ".txt":
            texts = [path.read_text(encoding="utf-8")]  # un TXT n'a pas de pages : page 1
        else:
            continue
        for number, text in enumerate(texts, start=1):
            if text.strip():
                pages.append((path.name, number, text))
            else:
                print(f"Page vide ignorée : {path.name}, page {number}")
    return pages


def split_text(text, size=config.CHUNK_SIZE, overlap=config.CHUNK_OVERLAP):
    """Découpe un texte en morceaux de `size` caractères qui se recouvrent de `overlap`."""
    step = size - overlap
    chunks = []
    for start in range(0, len(text), step):
        chunks.append(text[start:start + size])
        if start + size >= len(text):  # le dernier morceau atteint la fin du texte
            break
    return chunks


def embed_texts(texts):
    """Calcule les embeddings par lots, avec le modèle d'embeddings."""
    vectors = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        vectors.extend(ollama.embed(model=config.EMBED_MODEL, input=batch).embeddings)
        print(f"  embeddings : {min(i + BATCH_SIZE, len(texts))}/{len(texts)}")
    return vectors


def store_chunks(ids, texts, metadatas, vectors):
    """Recrée la collection puis y range les morceaux (relancer ne crée pas de doublons)."""
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    try:
        client.delete_collection(config.COLLECTION_NAME)
    except Exception:
        pass  # la collection n'existait pas encore
    collection = client.create_collection(
        config.COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )
    collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=vectors)


def main():
    start_time = time.time()

    if not config.DOCS_DIR.exists():
        sys.exit(f"Le dossier {config.DOCS_DIR} n'existe pas.")
    pages = read_documents(config.DOCS_DIR)
    if not pages:
        sys.exit(f"Aucun PDF ni TXT à indexer dans {config.DOCS_DIR}.")

    ids, texts, metadatas = [], [], []
    for file_name, page, text in pages:
        for n, chunk in enumerate(split_text(text)):
            ids.append(f"{file_name}:{page}:{n}")
            texts.append(chunk)
            metadatas.append({"fichier": file_name, "page": page})
    n_files = len({file_name for file_name, _, _ in pages})
    print(f"{n_files} fichier(s), {len(pages)} page(s), {len(texts)} morceaux")

    try:
        vectors = embed_texts(texts)
    except Exception as error:
        sys.exit(
            f"Erreur Ollama : {error}\n"
            f"Vérifiez qu'Ollama tourne et que le modèle est installé "
            f"(ollama pull {config.EMBED_MODEL})."
        )
    store_chunks(ids, texts, metadatas, vectors)

    print(f"Indexation terminée en {time.time() - start_time:.1f} s")


if __name__ == "__main__":
    main()
