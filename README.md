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

Les PDF ne sont pas dans le dépôt. Pour reproduire la démonstration, téléchargez les deux documents suivants et placez-les dans le dossier `docs/` :

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

> **À compléter par l'auteur.**

## Limites

> **À compléter par l'auteur.**

## Pistes d'amélioration

> **À compléter par l'auteur.**

## Summary in English

> **À compléter par l'auteur.**
