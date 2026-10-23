"""Évaluation chiffrée : recherche seule, génération, et comptage des notes."""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import chromadb
import ollama

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR.parent / "src"))

import config  # noqa: E402
import query  # noqa: E402

QUESTIONS_PATH = EVAL_DIR / "questions.json"
RESULTS_DIR = EVAL_DIR / "results"
GRADES = ("juste", "faux", "partiel")


def load_questions(path=QUESTIONS_PATH):
    """Lit le fichier des questions d'évaluation.

    Entrée :
        path (Path) : chemin du fichier JSON.
    Sortie :
        list[dict] : une entrée par question (id, question, reponse_attendue,
        source_attendue, page, type, et remarque si elle existe).
    """
    return json.loads(path.read_text(encoding="utf-8"))


def check_sources(questions):
    """Vérifie que chaque source attendue est indexée, sinon arrête le programme.

    Entrée :
        questions (list[dict]) : questions d'évaluation.
    Sortie :
        aucune (None). Arrête le programme avec un message clair si la base
        est absente ou vide, ou si une source attendue n'y figure pas.
    """
    try:
        client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
        metadatas = client.get_collection(config.COLLECTION_NAME).get(include=["metadatas"])["metadatas"]
    except Exception:
        metadatas = []
    if not metadatas:
        sys.exit("La base est absente ou vide. Lancez python src/ingest.py.")

    indexed = {meta["fichier"] for meta in metadatas}
    missing = {}
    for q in questions:
        source = q["source_attendue"]
        if source is not None and source not in indexed:
            missing.setdefault(source, []).append(str(q["id"]))
    if missing:
        lines = [f"Source absente de la base : {s} (questions {', '.join(ids)})." for s, ids in missing.items()]
        sys.exit("\n".join(lines) + "\nLancez python src/ingest.py.")


def find_rank(chunks, file_name, page):
    """Cherche le rang du premier morceau qui vient de la page attendue.

    Entrées :
        chunks (list[dict]) : morceaux retrouvés, du plus proche au plus éloigné.
        file_name (str) : fichier attendu.
        page (int) : page attendue (la première page vaut 1).
    Sortie :
        int | None : rang du morceau (1 pour le plus proche), ou None s'il est absent.
    """
    for rank, chunk in enumerate(chunks, start=1):
        if chunk["fichier"] == file_name and chunk["page"] == page:
            return rank
    return None


def save_results(data, path):
    """Écrit les résultats dans un fichier JSON, en remplaçant le contenu précédent.

    Entrées :
        data (dict) : résultats à écrire.
        path (Path) : fichier de destination (le dossier est créé si besoin).
    Sortie :
        aucune (None).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def settings(top_k):
    """Rassemble les réglages de l'essai, à conserver avec les résultats.

    Entrée :
        top_k (int) : nombre de morceaux retrouvés par question.
    Sortie :
        dict : taille et recouvrement des morceaux, top_k et noms des modèles.
    """
    return {
        "chunk_size": config.CHUNK_SIZE,
        "chunk_overlap": config.CHUNK_OVERLAP,
        "top_k": top_k,
        "llm_model": config.LLM_MODEL,
        "embed_model": config.EMBED_MODEL,
    }


def run_retrieval(questions, top_k):
    """Mesure la recherche seule : le morceau de la page attendue est-il dans les top_k ?

    Entrées :
        questions (list[dict]) : questions d'évaluation.
        top_k (int) : nombre de morceaux retrouvés par question.
    Sortie :
        Path : fichier de résultats écrit dans eval/results/. Les questions hors
        corpus sont notées "non applicable" et ne comptent pas dans le score.
    """
    results = []
    for q in questions:
        chunks = query.search_chunks(q["question"], top_k)
        entry = {
            "id": q["id"],
            "question": q["question"],
            "type": q["type"],
            "source_attendue": q["source_attendue"],
            "page": q["page"],
            "succes": None,
            "rang": None,
            "morceaux": [
                {"fichier": c["fichier"], "page": c["page"], "distance": round(c["distance"], 4)}
                for c in chunks
            ],
        }
        if q["source_attendue"] is not None:
            entry["rang"] = find_rank(chunks, q["source_attendue"], q["page"])
            entry["succes"] = entry["rang"] is not None
            print(f"Question {q['id']} : {'OK, rang ' + str(entry['rang']) if entry['succes'] else 'ÉCHEC'}")
        else:
            print(f"Question {q['id']} : non applicable (hors corpus)")
        results.append(entry)

    scored = [r for r in results if r["succes"] is not None]
    hits = sum(r["succes"] for r in scored)
    print(f"\nScore de la recherche : {hits}/{len(scored)} (top_k = {top_k})")

    path = RESULTS_DIR / f"{time.strftime('%Y%m%d_%H%M%S')}_recherche.json"
    save_results({"parametres": settings(top_k), "score": f"{hits}/{len(scored)}", "resultats": results}, path)
    return path


def answer_without_documents(question):
    """Fait répondre le modèle à la question seule, sans consigne ni extraits.

    Entrée :
        question (str) : question posée au modèle.
    Sortie :
        str : la réponse du modèle, donnée de mémoire (coupée à NUM_PREDICT tokens).
    """
    response = ollama.chat(
        model=config.LLM_MODEL,
        messages=[{"role": "user", "content": question}],
        options={
            "num_ctx": config.NUM_CTX,
            "temperature": config.TEMPERATURE,
            "num_predict": config.NUM_PREDICT,
        },
    )
    return response.message.content


def generate_entry(q, top_k):
    """Génère les deux réponses d'une question : avec documents, puis sans.

    Entrées :
        q (dict) : une question d'évaluation.
        top_k (int) : nombre de morceaux retrouvés pour la réponse avec documents.
    Sortie :
        dict : réponses, passages, temps, refus automatique et champs "note" vides.
    """
    start = time.time()
    chunks = query.search_chunks(q["question"], top_k)
    answer = query.answer_question(q["question"], chunks)
    with_docs_time = time.time() - start

    start = time.time()
    answer_no_docs = answer_without_documents(q["question"])
    no_docs_time = time.time() - start

    refusal = query.is_refusal(answer)
    entry = {
        "id": q["id"],
        "question": q["question"],
        "type": q["type"],
        "reponse_attendue": q["reponse_attendue"],
        "avec_documents": {
            "reponse": answer,
            "passages": [{"fichier": f, "page": p} for f, p in dict.fromkeys((c["fichier"], c["page"]) for c in chunks)],
            "refus": refusal,
            "refus_conforme": refusal == (q["type"] == "hors_corpus"),
            "temps_s": round(with_docs_time, 1),
            "note": "",
        },
        "sans_documents": {"reponse": answer_no_docs, "temps_s": round(no_docs_time, 1), "note": ""},
    }
    if q.get("remarque"):
        entry["remarque"] = q["remarque"]
    return entry


def run_generation(questions, top_k):
    """Génère les réponses de toutes les questions et les enregistre au fur et à mesure.

    Le fichier est réécrit après chaque question, pour ne rien perdre en cas d'interruption.
    Entrées :
        questions (list[dict]) : questions d'évaluation.
        top_k (int) : nombre de morceaux retrouvés par question.
    Sortie :
        Path : fichier de résultats écrit dans eval/results/, à noter à la main.
    """
    path = RESULTS_DIR / f"{time.strftime('%Y%m%d_%H%M%S')}_generation.json"
    data = {"parametres": settings(top_k), "resultats": []}
    for i, q in enumerate(questions, start=1):
        entry = generate_entry(q, top_k)
        data["resultats"].append(entry)
        save_results(data, path)
        avec = entry["avec_documents"]
        flag = "" if avec["refus_conforme"] else (" — REFUS À TORT" if avec["refus"] else " — PAS DE REFUS")
        print(f"[{i}/{len(questions)}] question {q['id']} : {avec['temps_s']} s avec documents, "
              f"{entry['sans_documents']['temps_s']} s sans{flag}")

    wrong = sum(1 for r in data["resultats"] if r["type"] == "factuelle" and r["avec_documents"]["refus"])
    correct = sum(1 for r in data["resultats"] if r["type"] == "hors_corpus" and r["avec_documents"]["refus"])
    total_out = sum(1 for r in data["resultats"] if r["type"] == "hors_corpus")
    print(f"\nRefus à tort sur des questions factuelles : {wrong}")
    print(f"Refus corrects sur les questions hors corpus : {correct}/{total_out}")
    return path


def summarize_grades(path):
    """Compte les notes juste, faux et partiel d'un fichier de génération noté.

    Entrée :
        path (Path) : fichier de génération dont les champs "note" ont été remplis.
    Sortie :
        aucune (None). Affiche les totaux avec et sans documents, et signale
        les questions sans note ou avec une note inconnue.
    """
    results = json.loads(path.read_text(encoding="utf-8"))["resultats"]
    for key, title in (("avec_documents", "Avec documents"), ("sans_documents", "Sans documents")):
        counts = Counter()
        problems = []
        for r in results:
            note = r[key]["note"].strip().lower()
            if note in GRADES:
                counts[note] += 1
            else:
                problems.append(f"{r['id']} ({note or 'sans note'})")
        print(f"{title} : " + ", ".join(f"{g} {counts[g]}" for g in GRADES) + f" sur {len(results)} questions")
        if problems:
            print("  À corriger : " + ", ".join(problems))


def main():
    """Lance l'évaluation demandée en ligne de commande.

    Entrée : aucune (options lues dans la ligne de commande : --generation,
    --top-k, --score).
    Sortie : aucune (None). Sans option, mesure la recherche seule ; avec
    --generation, génère les réponses ; avec --score, compte les notes d'un fichier.
    """
    parser = argparse.ArgumentParser(description="Évaluation de l'assistant.")
    parser.add_argument("--generation", action="store_true", help="génère les réponses (au lieu de mesurer la recherche)")
    parser.add_argument("--top-k", type=int, default=config.TOP_K, help="nombre de morceaux retrouvés par question")
    parser.add_argument("--score", type=Path, metavar="FICHIER", help="compte les notes d'un fichier de génération")
    args = parser.parse_args()

    if args.score:
        if not args.score.is_file():
            sys.exit(f"Fichier introuvable : {args.score}")
        summarize_grades(args.score)
        return

    questions = load_questions()
    check_sources(questions)
    try:
        if args.generation:
            path = run_generation(questions, args.top_k)
        else:
            path = run_retrieval(questions, args.top_k)
    except Exception as error:
        sys.exit(f"Erreur : {error}\nVérifiez qu'Ollama tourne avec les modèles {config.LLM_MODEL} et {config.EMBED_MODEL}.")
    print(f"Résultats écrits dans {path}")


if __name__ == "__main__":
    main()
