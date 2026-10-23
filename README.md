# Assistant de questions sur des documents locaux

Programme en ligne de commande qui répond à des questions à partir des documents d'un dossier local (PDF et TXT), entièrement en local. Les réponses se basent uniquement sur ces documents et citent leurs sources (fichier et page). Si l'information n'y figure pas, le programme le dit et ne répond pas de mémoire.

Le principe : les documents sont découpés en morceaux qui se recouvrent, transformés en vecteurs (embeddings) et rangés dans une base locale. À chaque question, le programme retrouve les morceaux les plus proches, puis un modèle de langage rédige la réponse à partir d'eux seulement.

L'assistant est généraliste : aucun domaine n'est codé en dur, il vient du contenu du dossier `docs/`. Le corpus de démonstration est composé de normes comptables françaises publiées par l'Autorité des normes comptables (ANC).

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

- [Règlement ANC n° 2024-07, version commentée](https://www.anc.gouv.fr/files/anc/files/1_Normes_fran%C3%A7aises/Reglements/2024/R2024-07/REGLT_2024_07_version-commentee-def.pdf) (`REGLT_2024_07_version-commentee-def.pdf`)
- [Recueil des normes comptables françaises, janvier 2025](https://www.anc.gouv.fr/files/anc/files/1_Normes_fran%C3%A7aises/Reglements/Recueils/PCG_Janvier2025/Recueil-NF-Janvier-2025.pdf) (`Recueil-NF-Janvier-2025.pdf`)

## Utilisation

### Indexer les documents

```
python src/ingest.py
```

Le programme lit les fichiers de `docs/`, les découpe, calcule les embeddings et remplit la base `chroma_db/`. Relancer la commande reconstruit la base entièrement.

Sur la machine de test (processeur i5-8265U, 8 Go de RAM, carte NVIDIA MX250 de 2 Go utilisée par Ollama), l'indexation des 2194 morceaux du corpus prend environ 15 minutes. Ce temps peut différer sans GPU.

### Poser une question

```
python src/query.py "Votre question"
```

Une question par lancement. La réponse est suivie des passages consultés (fichier et page). Si le modèle répond qu'il ne sait pas, la liste n'est pas affichée. Exemple :

```
python src/query.py "Dans quel compte la part du principal ayant les caractéristiques des fonds non remboursables est-elle comptabilisée ?"
```

```
La part du principal ayant les caractéristiques des fonds non remboursables est comptabilisée dans le compte 1671 – Fonds non remboursables montant principal, d'après l'Extrait 3 du fichier REGLT_2024_07_version-commentee-def.pdf, page 3.

Passages consultés :
- REGLT_2024_07_version-commentee-def.pdf, page 3
- Recueil-NF-Janvier-2025.pdf, page 551
```

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

L'évaluation porte sur 25 questions (`eval/questions.json`).

- Questions 1 à 15 : factuelles, reprenant les termes des documents.
- Questions 19 à 25 : factuelles, reformulées avec des mots du quotidien. Elles ont été ajoutées après une première mesure de la recherche et avant toute génération. Les questions d'origine n'ont pas été modifiées.
- Questions 16 à 18 : hors corpus.

### Recherche : la bonne page figure-t-elle parmi les 4 morceaux retrouvés ?

| Questions | Résultat |
|---|---|
| Questions d'origine (15) | 15/15 |
| Questions reformulées (7) | 3/7 |
| Total factuelles (22) | 18/22 |

Avec 8 morceaux au lieu de 4, le résultat est identique (18/22) : les quatre échecs ne sont pas des quasi-réussites.

### Génération : réponses notées

| Questions | Avec documents (juste / partiel / faux) | Sans documents (juste / partiel / faux) |
|---|---|---|
| Origine (15) | 11 / 1 / 3 | 1 / 2 / 12 |
| Reformulées (7) | 1 / 0 / 6 | 1 / 1 / 5 |
| Total factuelles (22) | 12 / 1 / 9 | 2 / 3 / 17 |

- Hors corpus : 3 refus corrects sur 3 avec documents.
- Refus à tort sur des questions factuelles : 7 sur 22. Dans 4 cas la recherche avait manqué la page (questions 19, 23, 24 et 25). Dans 3 cas elle l'avait trouvée (questions 14, 21 et 22).
- Critères de notation : juste si l'information demandée est correcte. Partiel si le fond est juste mais incomplet ou si un détail est faux. Faux si la réponse est incorrecte ou contradictoire ou s'il y a un refus à tort.
- La notation a été établie par Claude à partir des réponses attendues, selon ces critères. Elle n'est donc pas indépendante.

## Limites

- **Jeu de questions réduit.** 22 questions factuelles et 3 hors corpus écrites à partir des documents. Les résultats sont indicatifs.
- **La recherche dépend du vocabulaire.** 15/15 quand la question reprend les mots du texte contre 3/7 quand elle est reformulée. La question 23 (« ce qu'on pourra le revendre ») ne retrouve pas la page sur la valeur résiduelle, même parmi 8 morceaux.
- **Morceaux qui mélangent plusieurs idées.** La règle sur les actifs acquis à titre gratuit est une puce parmi trois autres modes d'acquisition. La question 19 retrouve à la place des pages sur la contribution financière des équipements.
- **Refus à tort.** Le modèle de 3 milliards de paramètres refuse parfois de répondre alors que le bon passage lui est fourni (questions 14, 21 et 22).
- **Réponses fausses données avec assurance.** La question 9 donne une mauvaise année d'homologation. La question 7 commence par affirmer le contraire de la réponse. La question 15 ne détecte pas le conflit entre le règlement et le recueil (compte 1671 au lieu de 1673 et 1674).
- **Citations irrégulières.** Environ la moitié des réponses donnent le fichier et la page. Les passages consultés sont affichés sauf en cas de refus.
- **Découpage.** Le texte est découpé page par page puis en morceaux de 1 200 caractères avec 200 de recouvrement : une phrase à cheval sur deux pages est coupée. Les pages de tableaux de chiffres (page 359 du recueil) attirent des questions sans rapport. Les fichiers TXT sont traités comme une seule page.
- **Hors corpus.** La recherche renvoie toujours 4 morceaux : le refus repose uniquement sur le modèle. Seules 3 questions hors corpus, simples, ont été testées.
- **Comparaison sans documents.** Les questions 12 et 20 sont justes sans documents : le modèle a des connaissances préalables. Le test mesure l'apport du RAG et non l'absence totale de connaissance.

## Pistes d'amélioration (non testées)

- Reranking : un second modèle reclasse une liste plus large de candidats.
- Recherche hybride : combiner les vecteurs avec une recherche par mots exacts (utile pour les numéros d'article et de compte).
- Découpage par structure : couper aux articles plutôt qu'à un nombre de caractères.
- Seuil de distance : refuser sans appeler le modèle quand les morceaux sont trop éloignés de la question.
- Modèle plus grand si la machine le permet.
- Davantage de questions et essai de plusieurs tailles de morceaux.

## Summary in English

A local, command-line RAG pipeline in Python. It indexes PDF and text files with Ollama (bge-m3 embeddings) and ChromaDB and answers questions with qwen2.5:3b while citing file and page. It says it does not know when the documents do not contain the answer. On a 25-question evaluation built on French accounting standards, retrieval finds the right page for 15 of 15 questions that reuse the source wording but only 3 of 7 reformulated ones. With documents the model answers 12 of 22 factual questions correctly against 2 without. Answers were graded by Claude using the criteria above, so the grading is not independent. Main limits are vocabulary-dependent retrieval and refusals despite correct passages. The code was written with Claude Code from the CLAUDE.md specification.
