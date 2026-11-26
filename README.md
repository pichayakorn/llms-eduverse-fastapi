# LLMs in EduGame API (FastAPI)

The backend for **EduGame**, the web version of the LLMs in Eduverse English word-guessing game, from the paper:

- **[LLMs in EduGame: A Web-Based Interactive English Learning Game](https://doi.org/10.2197/ipsjjip.34.230)**  
  *2026 Journal of Information Processing*

It extends the original Flask API, [llms-eduverse](https://github.com/pichayakorn/llms-eduverse), built for the Roblox game in [LLMs in Eduverse (GCCE 2024)](https://doi.org/10.1109/GCCE62371.2024.10760474).

## What changed from the Flask version

- **FastAPI** with a Pydantic response model, so every response has the same validated shape.
- **GPT-4o** (`gpt-4o-2024-08-06`) instead of `gpt-3.5-turbo`.
- **Workplace English:** 10 categories such as Business and Finance, Travel and Tourism, and Health and Medicine.
- **A quiz:** each round ends with a fill-in-the-blank question and 4 choices (the target word and 3 others from the list).
- **Choosing a category:** an optional `category_index` query parameter.

## How it works

One request to `GET /generate_words` produces a full round of the game. The API picks a category and makes a chain of GPT-4o function calls, each forced to a specific function so the output is structured:

1. **Words:** 10 words from the category. The first is the target word players must guess.
2. **Scores:** a semantic-similarity score (0 to 1) between the target word and each of the 10 words.
3. **Hints:** 5 fill-in-the-blank sentences. The first 4 are in-game hints; the last is the quiz question.

Every step checks the model's output and asks again if it's invalid: a word list with duplicates or the wrong length, a score list that isn't 10 long, or a hint that gives away the target word or has more than one blank.

The prompts are in [`prompts/`](prompts/).

## API

`GET /generate_words`

| Query parameter | Type | Description |
|---|---|---|
| `category_index` | integer, optional | 0–9 picks a category. Leave it out for a random one. Out of range returns `400`. |

### Example response

```json
{
  "hint": [
    { "ID": 1, "question": "…" },
    { "ID": 2, "question": "…" }
  ],
  "words": [
    { "ID": 1, "word": "…", "score": 1.0 },
    { "ID": 2, "word": "…", "score": 0.8 }
  ],
  "quiz": {
    "question": "…",
    "choices": ["…", "…", "…", "…"]
  }
}
```

(Shortened: a real response has 4 hints and 10 words.)

## Setup

### Install Dependencies

1. (optional) Creating conda environment

```
conda create -n metaguesser python=3.11
conda activate metaguesser
```

2. Install required packages

```
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.

### Run FastAPI server

```
fastapi dev main.py
```

Then open `http://127.0.0.1:8000/generate_words`, or the interactive docs at `http://127.0.0.1:8000/docs`.

## Citation

```bibtex
@article{plupattanakit2024llms2,
  title={LLMs in EduGame: A Web-based Interactive English Learning Game},
  author={Kantinan Plupattanakit and Pratch Suntichaikul and Ibrahim Khan and Ruck Thawonmas and Jeremy White and Kingkarn Sookhanaphibarn and Worawat Choensawat},
  journal={Journal of Information Processing},
  volume={34},
  pages={230-238},
  year={2026},
  doi={10.2197/ipsjjip.34.230}
}
```
