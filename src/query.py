"""Recherche des morceaux proches d'une question, puis réponse du modèle avec sources."""

import sys

import chromadb
import ollama

import config


def embed_question(question):
    """Transforme la question en vecteur avec le même modèle que les documents.

    Entrée :
        question (str) : question posée par l'utilisateur.
    Sortie :
        list[float] : le vecteur d'embedding de la question.
    """
    return ollama.embed(model=config.EMBED_MODEL, input=question).embeddings[0]


def search_chunks(question, top_k=config.TOP_K):
    """Retrouve dans la base les morceaux les plus proches de la question.

    Entrées :
        question (str) : question posée par l'utilisateur.
        top_k (int) : nombre de morceaux à retrouver.
    Sortie :
        list[dict] : un dictionnaire par morceau, du plus proche au plus éloigné,
        avec les clés "text" (str), "fichier" (str), "page" (int) et "distance" (float).
    """
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    collection = client.get_collection(config.COLLECTION_NAME)
    result = collection.query(
        query_embeddings=[embed_question(question)], n_results=top_k
    )
    return [
        {"text": text, "fichier": meta["fichier"], "page": meta["page"], "distance": dist}
        for text, meta, dist in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0]
        )
    ]


def build_messages(question, chunks):
    """Construit les messages envoyés au modèle : consigne, extraits, puis question.

    Entrées :
        question (str) : question posée par l'utilisateur.
        chunks (list[dict]) : morceaux retrouvés par search_chunks.
    Sortie :
        list[dict] : messages au format d'Ollama (rôles "system" et "user").
    """
    excerpts = [
        f"[Extrait {i} — fichier : {c['fichier']}, page : {c['page']}]\n{c['text']}"
        for i, c in enumerate(chunks, start=1)
    ]
    user_content = "\n\n".join(excerpts) + f"\n\nQuestion : {question}"
    return [
        {"role": "system", "content": config.SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def answer_question(question, chunks):
    """Demande au modèle de répondre à la question d'après les morceaux.

    Entrées :
        question (str) : question posée par l'utilisateur.
        chunks (list[dict]) : morceaux retrouvés par search_chunks.
    Sortie :
        str : le texte de la réponse du modèle.
    """
    response = ollama.chat(
        model=config.LLM_MODEL,
        messages=build_messages(question, chunks),
        options={"num_ctx": config.NUM_CTX, "temperature": config.TEMPERATURE},
    )
    return response.message.content


def is_refusal(answer):
    """Dit si la réponse est la phrase de refus, sans tenir compte de la casse ni des espaces.

    Entrée :
        answer (str) : réponse du modèle.
    Sortie :
        bool : True si la phrase de refus figure dans la réponse.
    """
    def normalize(text):
        # les apostrophes typographiques sont ramenées à l'apostrophe simple
        return " ".join(text.replace("’", "'").lower().split())

    return normalize(config.REFUSAL_PHRASE) in normalize(answer)


def main():
    """Répond à la question donnée en argument et affiche les passages consultés.

    Entrée : aucune (la question est lue dans la ligne de commande).
    Sortie : aucune (None). Affiche la réponse, puis les passages consultés
    sauf si le modèle a répondu qu'il ne sait pas.
    """
    if len(sys.argv) != 2:
        sys.exit('Usage : python src/query.py "Votre question"')
    question = sys.argv[1]

    try:
        chunks = search_chunks(question)
        answer = answer_question(question, chunks)
    except Exception as error:
        sys.exit(
            f"Erreur : {error}\n"
            "Vérifiez qu'Ollama tourne avec les modèles "
            f"{config.LLM_MODEL} et {config.EMBED_MODEL}, "
            "et que les documents sont indexés (python src/ingest.py)."
        )

    print(answer)
    if not is_refusal(answer):
        print("\nPassages consultés :")
        for file_name, page in dict.fromkeys((c["fichier"], c["page"]) for c in chunks):
            print(f"- {file_name}, page {page}")


if __name__ == "__main__":
    main()
