# AI-Powered Interview Preparation System (LLM + Prompt Engineering)

## Quick start
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # paste your Groq key from https://console.groq.com/keys
streamlit run app.py
```
No key? The app starts in **Demo mode** (built-in questions + heuristic scoring), so it always runs in a review.
Run tests: `pytest -q`

## Files
| File | Purpose |
|---|---|
| `app.py` | Streamlit UI (login, profile, resume, interview, report, dashboard, history) |
| `prompts.py` | **Prompt templates** (role, zero/few-shot, context, JSON, dynamic, injection guard) |
| `llm.py` | Groq client, JSON extraction, retries |
| `resume.py` | PyPDF extraction + resume analysis |
| `evaluator.py` | Question generation + 5-criterion weighted scoring |
| `recommender.py` | Final report, weak topics, learning plan |
| `database.py` | SQLite (users, profiles, resumes, interviews, answers) |

## Flowchart
```
Login -> Profile -> Upload resume -> PyPDF text -> LLM skill extraction
  -> Choose role/category/difficulty -> Dynamic prompt -> LLM questions (JSON)
  -> Student answers -> Few-shot rubric prompt -> LLM scores (JSON) -> weighted score
  -> Save to SQLite -> (repeat per question) -> Final report + learning plan -> Dashboard/History
```

## Data flow diagram (Level 1)
```
[Student] --credentials--> (1 Auth) <--> [users]
[Student] --PDF--> (2 Resume) --text--> (LLM) --skills--> [resumes]
[Student] --role/category--> (3 Question Gen) <-- [resumes, past weak topics]
(3) --questions--> [Student] --answers--> (4 Evaluation) --> (LLM) --scores--> [answers]
[answers] --> (5 Analytics/Report) --> [interviews] --> [Student dashboard]
```

## Deploy free
Push to GitHub, then deploy on Streamlit Community Cloud and add `GROQ_API_KEY` and `GROQ_MODEL` under Streamlit Secrets.
The app uses Groq for hosted LLM inference. Set `GROQ_MODEL` to a model currently available in your Groq account.
