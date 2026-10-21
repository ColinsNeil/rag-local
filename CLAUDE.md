# Assistant de questions sur des documents locaux

## Objectif
Programme en ligne de commande qui répond à des questions à partir des documents d'un dossier local. Les réponses se basent uniquement sur ces documents et citent leurs sources (fichier et page). Si l'information n'y figure pas, le programme le dit et ne répond pas de mémoire.

L'assistant est généraliste. Aucun domaine n'est codé en dur. Le domaine vient seulement du contenu du dossier `docs/`. Le corpus de démonstration est composé de normes comptables françaises publiées par l'Autorité des normes comptables (ANC).

## Règles de travail pour Claude Code
- Travailler une étape à la fois, en mode plan. Présenter le plan, attendre la validation, puis écrire.
- Après chaque étape, expliquer en quelques phrases simples ce que fait le code, puis s'arrêter et attendre.
- Rester dans le périmètre décrit plus bas. Ne rien ajouter qui n'est pas demandé.
- Ne pas ajouter de dépendance sans demander d'abord.
- Écrire un code court et lisible, avec des fonctions courtes et des commentaires simples. Pas de sur-ingénierie.
- Un commit par étape, avec un message court en français.
- Ne jamais écrire de secret, de clé ni de donnée personnelle dans le dépôt.
- Toujours activer l'environnement `.venv` avant de lancer du code. Ne jamais utiliser le `python` global.

## Périmètre
Inclus
- ingestion des fichiers PDF et TXT
- découpage en morceaux avec recouvrement
- calcul des embeddings et stockage dans une base vectorielle locale
- recherche des morceaux proches d'une question
- réponse du modèle avec citation des sources
- évaluation chiffrée

Exclus
- Docker
- recherche hybride et reranking
- interface web et API
- LangChain et autres frameworks d'orchestration
- tout appel à un service externe

## Pile technique
- Python 3.10 ou plus récent
- Ollama pour les modèles, tous deux en local sur processeur
- modèle de réponse `qwen2.5:3b`
- modèle d'embeddings `bge-m3`
- ChromaDB pour la base vectorielle
- `pypdf` pour lire les PDF

Dépendances autorisées dans `requirements.txt` : `ollama`, `chromadb`, `pypdf`.

## Structure
```
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .gitignore
├── docs/              documents à indexer (non publiés)
├── src/
│   ├── config.py      tous les réglages, au même endroit
│   ├── ingest.py      lecture, découpage, embeddings, stockage
│   └── query.py       recherche, prompt, réponse avec sources
└── eval/
    ├── questions.json
    └── run_eval.py
```
La base `chroma_db/`, l'environnement `.venv/` et les résultats `eval/results/` sont dans `.gitignore`.

## Réglages de départ
Ce sont des valeurs de départ, à ajuster d'après les résultats de l'évaluation.
- `CHUNK_SIZE` à 1200 caractères
- `CHUNK_OVERLAP` à 200 caractères
- `TOP_K` à 4 morceaux retrouvés par question
- `LLM_MODEL` à `qwen2.5:3b`
- `EMBED_MODEL` à `bge-m3`

Le modèle de réponse lit un texte de taille limitée. Prévoir une fenêtre de contexte suffisante pour la question, la consigne et les 4 morceaux, et expliquer ce réglage.

## Interface
Une question par lancement.
```
python src/query.py "Votre question"
```
La réponse affiche le texte, puis la liste des sources utilisées (fichier et page).

## Consigne envoyée au modèle
Elle est neutre et ne mentionne aucun métier.

> Réponds à la question uniquement à partir des extraits ci-dessous. Si la réponse ne s'y trouve pas, réponds « Je ne sais pas d'après les documents fournis. » Indique pour chaque information le fichier et la page d'où elle vient.

## Évaluation
Fichier `eval/questions.json`, une entrée par question avec les champs suivants.
- `id`
- `question`
- `reponse_attendue`
- `source_attendue` (fichier, ou `null` pour une question hors corpus)
- `page`
- `type` (`factuelle` ou `hors_corpus`)

Deux mesures, qui restent séparées.
1. La recherche seule, sans le modèle de réponse. Pour chaque question, le morceau de la source attendue figure-t-il parmi les `TOP_K` résultats ? La fonction de recherche de `query.py` doit donc être appelable seule.
2. La génération, avec et sans documents. Les réponses sont notées à la main (juste, faux ou partiel), et les questions hors corpus vérifient que le programme répond « je ne sais pas ».

Les scores de chaque essai (taille des morceaux, `TOP_K`) sont conservés pour le tableau du README.

## Commandes
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src/ingest.py
python src/query.py "Votre question"
python eval/run_eval.py
```

## Documents non publiés
Les PDF du corpus ne sont pas dans le dépôt. Le README en donne seulement la liste et les liens de téléchargement.

## Summary in English
Command-line question answering over local documents, fully offline (Ollama, ChromaDB, Python). Answers rely only on the provided documents and cite file and page. The pipeline is domain-agnostic. Retrieval and generation are evaluated separately on a hand-written question set. Out of scope: Docker, hybrid search, reranking, web UI.