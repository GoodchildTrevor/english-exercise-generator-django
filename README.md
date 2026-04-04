# English Exercise Generator

A Django web application that automatically generates English language exercises from any input text. Paste a passage, choose a difficulty level, and get a set of grammar and vocabulary tasks ready to complete in the browser.

## Features

- **Three difficulty levels** — Easy, Medium, Hard
- **Multiple exercise types** depending on difficulty:
  - Select the correct sentence from similar alternatives
  - Identify the part of speech of a highlighted word
  - Choose the missing word from options
  - Choose the correct verb form
  - Type in the missing word (open-ended)
  - Identify the syntactic role of a word in the sentence
- **Instant answer checking** — submit answers and get feedback without page reload
- **Session-based isolation** — each user's exercises are stored and checked independently

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Django 5.0 |
| NLP | spaCy 3.5, GloVe (`glove-wiki-gigaword-100`) |
| Morphology | pyinflect |
| Language detection | langdetect |
| Sentence splitting | sentence-splitter |
| Database | SQLite |
| Server | Gunicorn + Uvicorn |
| Containerization | Docker + Docker Compose |

## Project Structure

```
english-exercise-generator-django/
├── docker-compose.yml
└── eng_ex_gen/
    ├── .env.example
    ├── Dockerfile
    ├── entrypoint.sh
    ├── manage.py
    ├── requirements.txt
    ├── eng_ex_gen/          # Django config (settings, urls, wsgi)
    ├── generator/           # Main app (models, views, utils)
    └── templates/
        ├── Application.html
        └── Exercises.html
```

## Getting Started

### With Docker (recommended)

```bash
git clone https://github.com/GoodchildTrevor/english-exercise-generator-django.git
cd english-exercise-generator-django

cp eng_ex_gen/.env.example eng_ex_gen/.env
# Edit .env and set SECRET_KEY

docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000).

> **Note:** The first startup takes a while — the GloVe model (~130 MB) is downloaded and loaded into memory on launch.

### Without Docker (local)

```bash
git clone https://github.com/GoodchildTrevor/english-exercise-generator-django.git
cd english-exercise-generator-django/eng_ex_gen

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

mkdir db
python manage.py migrate
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Environment Variables

Copy `eng_ex_gen/.env.example` to `eng_ex_gen/.env` and fill in the values:

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | insecure fallback (change in production) |
| `DEBUG` | Enable debug mode | `False` |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts | `localhost,127.0.0.1` |

## How It Works

1. User pastes an English text (up to 30 sentences) and selects a difficulty level
2. The app validates the text and stores it in the session
3. Each sentence is processed with spaCy — tokenization, POS tagging, dependency parsing
4. Based on difficulty, an exercise type is assigned to each sentence
5. Distractors (wrong options) are generated using GloVe word embeddings
6. Exercises are rendered in the browser; answers are checked via AJAX against the session
