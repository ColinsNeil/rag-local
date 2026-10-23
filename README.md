# Assistant de questions sur des documents locaux

Programme en ligne de commande qui répond à des questions à partir des documents d'un dossier local (PDF et TXT), entièrement en local. Les réponses se basent uniquement sur ces documents et citent leurs sources (fichier et page). Si l'information n'y figure pas, le programme le dit et ne répond pas de mémoire.

Le principe : les documents sont découpés en morceaux qui se recouvrent, transformés en vecteurs (embeddings) et rangés dans une base locale. À chaque question, le programme retrouve les morceaux les plus proches, puis un modèle de langage rédige la réponse à partir d'eux seulement.

L'assistant est généraliste : aucun domaine n'est codé en dur, il vient du contenu du dossier `docs/`. Le corpus de démonstration est composé de deux documents de l'EIJV sur la spécialité TIPS : sa plaquette et le syllabus du cursus.

Le code a été écrit avec Claude Code à partir de la spécification `CLAUDE.md` du dépôt.

## Prérequis

- Python 3.10 ou plus récent (testé avec Python 3.12).
- [Ollama](https://ollama.com), installé et lancé, avec les deux modèles suivants :
  ```
  ollama pull qwen2.5:3b
  ollama pull bge-m3
  ```
  `qwen2.5:3b` rédige les réponses et `bge-m3` calcule les embeddings.
- Aucun GPU dédié n'est requis. Ollama utilise le GPU s'il est compatible.

Aucun service externe n'est appelé : tout reste sur la machine.

## Installation

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Les dépendances sont `ollama`, `chromadb` et `pypdf`.

## Documents du corpus

Les PDF ne sont pas dans le dépôt. Pour reproduire la démonstration, créez un dossier `docs/` à la racine du dépôt, puis téléchargez les deux documents suivants et placez-les dedans :

- `PLAQUETTE-TIPS.pdf` : plaquette de la spécialité TIPS. [lien de téléchargement](https://eijv.u-picardie.fr/wp-content/uploads/sites/14/2025/12/PLAQUETTE-TIPS.pdf)
- `Syllabus-Numerique-Sante-IA.pdf` : syllabus du cursus. [lien de téléchargement](https://eijv.u-picardie.fr/wp-content/uploads/sites/14/2025/11/Syllabus-Numerique-Sante-IA.pdf)

## Utilisation

### Indexer les documents

```
python src/ingest.py
```

Le programme lit les fichiers de `docs/`, les découpe, calcule les embeddings et remplit la base `chroma_db/`. Relancer la commande reconstruit la base entièrement.

Sur la machine de test (processeur i5-8265U, 8 Go de RAM, carte NVIDIA MX250 de 2 Go utilisée par Ollama), la durée de l'indexation dépend de la taille du corpus. Elle peut différer sans GPU.

### Poser une question

```
python src/query.py "Votre question"
```

Une question par lancement. La réponse est suivie des passages consultés (fichier et page). Si le modèle répond qu'il ne sait pas, la liste n'est pas affichée.

Sur la machine de test, Ollama place environ 42 % de `qwen2.5:3b` sur le GPU et 58 % sur le processeur, et les réponses prennent 30 à 50 secondes. Ces durées varient selon la machine.

Tous les réglages (taille des morceaux, nombre de morceaux retrouvés, modèles, fenêtre de contexte) sont dans `src/config.py`.

### Lancer l'évaluation

```
python eval/run_eval.py
```

Sans option, la commande mesure la recherche seule, sans modèle de réponse : pour chaque question de `eval/questions.json`, le morceau de la page attendue figure-t-il parmi les morceaux retrouvés ?

| Option | Effet |
|---|---|
| `--generation` | génère les réponses, avec et sans documents, pour que vous les notiez à la main |
| `--top-k N` | essaie un autre nombre de morceaux retrouvés |
| `--score FICHIER` | compte les notes `juste`, `faux` et `partiel` d'un fichier de génération noté |

Les résultats sont écrits dans `eval/results/` (ignoré par git).

## Structure des fichiers

```
├── CLAUDE.md          spécification du projet
├── README.md
├── requirements.txt
├── .gitignore
├── docs/              documents à indexer (non publiés)
├── src/
│   ├── config.py      tous les réglages, au même endroit
│   ├── ingest.py      lecture, découpage, embeddings, stockage
│   └── query.py       recherche, prompt, réponse avec sources
└── eval/
    ├── questions.json questions d'évaluation
    └── run_eval.py    mesure de la recherche et de la génération
```

La base `chroma_db/`, l'environnement `.venv/` et les résultats `eval/results/` sont générés et ne sont pas publiés.

## Passer à un autre domaine

Remplacez le contenu de `docs/` par vos propres documents et le fichier `eval/questions.json` par vos propres questions, puis relancez `python src/ingest.py`.

## Résultats

Corpus : deux fichiers, `PLAQUETTE-TIPS.pdf` (4 pages) et `Syllabus-Numerique-Sante-IA.pdf` (44 pages dont 4 sans texte), soit 94 morceaux.

L'évaluation porte sur 17 questions (`eval/questions.json`) : 13 factuelles en langage courant et 4 hors corpus.

### Recherche : la bonne page figure-t-elle parmi les 4 morceaux retrouvés ?

La bonne page figure parmi les 4 morceaux retrouvés pour 13 questions sur 13.

| Rang du bon morceau | Questions |
|---|---|
| 1 | 9 (questions 1, 2, 3, 4, 5, 8, 9, 10 et 11) |
| 2 | 3 (questions 6, 7 et 12) |
| 3 | 1 (question 13) |

### Génération : réponses notées

Les 13 questions factuelles sont notées.

| | Juste | Partiel | Faux |
|---|---|---|---|
| Avec documents | 7 | 2 | 4 |
| Sans documents | 0 | 2 | 11 |

- Hors corpus : 4 refus corrects sur 4 avec documents.
- Refus à tort sur des questions factuelles : 3 sur 13 (questions 1, 8 et 10). Dans les trois cas la bonne page était retrouvée en rang 1.
- Critères de notation : juste si l'information demandée est correcte. Partiel si le fond est juste mais incomplet ou si un détail est faux. Faux si la réponse est incorrecte ou contradictoire ou s'il y a un refus à tort.
- Notation : établie par Claude à partir des réponses attendues. Elle n'est donc pas indépendante. Les questions ont aussi été écrites par Claude après lecture des PDF.

## Limites

- **Jeu de questions réduit et petit corpus.** 13 questions factuelles et 4 hors corpus pour 94 morceaux : les résultats sont indicatifs et la recherche est plus facile que sur un grand corpus.
- **Questions écrites et notées par Claude.** Elles ne sont pas indépendantes.
- **Refus à tort.** Le modèle de 3 milliards de paramètres refuse parfois de répondre alors que le bon passage lui est fourni (questions 1, 8 et 10).
- **Réponses construites à partir de titres (test manuel, non mesuré).** Hors évaluation, à une question vague sur le détail des matières du semestre 7 posée avec `query.py`, le modèle a construit des descriptions à partir des seuls titres (« pourrait couvrir… »), parce que la recherche n'avait retrouvé que des pages de listes de matières.
- **Titre du module séparé de sa liste.** À la question 13, le morceau retrouvé (page 17) contient la liste « V) Hygiène informatique et bonnes pratiques » mais pas le titre du module Introduction à la cybersécurité, qui se trouve dans le morceau précédent. Le modèle a répondu avec un mauvais intitulé. La liste « Passages consultés » montre ce qui a été retrouvé et non la preuve que la réponse s'y trouve.
- **Pages sans texte.** Les pages 3 à 6 du syllabus sont des images de tableaux de structure. Elles sont ignorées car le programme ne fait pas d'OCR (voir l'essai de lecture d'images ci-dessous).
- **Lecture des pages en images (test manuel, non intégré).** Un essai avec le modèle de vision `qwen2.5vl:3b` sur une des pages en images du syllabus (tableau de structure du semestre S5) a décalé plusieurs colonnes, laissé vide la colonne des noms de matières et s'est arrêté après quatre lignes en produisant des lignes vides. La lecture des pages en images n'a donc pas été ajoutée au programme.
- **Citations irrégulières.** Sur les 10 réponses factuelles non refusées 4 donnent le fichier et la page (questions 5, 7, 9 et 13) et 2 donnent le fichier avec un numéro d'extrait à la place de la page (questions 2 et 11). Les 4 autres ne donnent ni l'un ni l'autre (questions 3, 4, 6 et 12). Le nom du fichier est parfois déformé (« Plaquette-Tips.pdf »).
- **Hors corpus.** La recherche renvoie toujours 4 morceaux et les distances ne séparent pas les deux cas : 0,48 à 0,55 hors corpus contre 0,32 à 0,52 dans le corpus (distance du morceau le plus proche). Le refus repose uniquement sur le modèle et n'a été testé que sur 4 questions simples.
- **Réponses coupées.** La réponse à la question 9 sans documents est coupée à 500 tokens au milieu d'une liste qui se répète. Une réponse tronquée n'est pas signalée.
- **Sans documents.** Le modèle donne des réponses génériques et parfois inventées (question 15 : un taux d'insertion de « 80 % selon l'Insee »).

## Pistes d'amélioration (non testées)

- Reranking : un second modèle reclasse une liste plus large de candidats.
- Recherche hybride : combiner les vecteurs avec une recherche par mots exacts (utile pour les noms propres, sigles et codes de matière).
- Découpage par structure : couper aux articles plutôt qu'à un nombre de caractères.
- Seuil de distance : refuser sans appeler le modèle quand les morceaux sont trop éloignés de la question.
- Modèle plus grand si la machine le permet.
- Davantage de questions et essai de plusieurs tailles de morceaux.

## Summary in English

A local, command-line RAG pipeline in Python. It is domain-agnostic: the domain comes only from the documents in the `docs/` folder. It indexes PDF and text files with Ollama (bge-m3 embeddings) and ChromaDB and answers questions with qwen2.5:3b while citing file and page. It says it does not know when the documents do not contain the answer. The demonstration corpus is made of two school documents (a programme brochure and a syllabus). Retrieval and generation are evaluated separately on a question set written and graded with Claude, so the figures are indicative and not independent. Results and limits are reported above. The code was written with Claude Code from the CLAUDE.md specification.
