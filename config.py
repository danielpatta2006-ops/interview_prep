"""Central configuration."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _secret(name, default=""):
    """Read environment variables first, then Streamlit Cloud secrets."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st
        return str(st.secrets.get(name, default))
    except Exception:
        return default

DB_PATH = os.getenv("DB_PATH", "interview_prep.db")
GROQ_MODEL = _secret("GROQ_MODEL", "llama-3.3-70b-versatile")
ENV_API_KEY = _secret("GROQ_API_KEY", "")

JOB_ROLES = ["Software Developer", "Data Analyst", "AI Engineer", "Web Developer",
             "Data Scientist", "Cloud/DevOps Engineer", "Cybersecurity Analyst"]
CATEGORIES = ["Technical", "HR", "Mixed"]
DIFFICULTIES = ["Beginner", "Intermediate", "Advanced"]

# Evaluation rubric weights (sum = 1.0)
WEIGHTS = {"technical_accuracy": 0.30, "relevance": 0.20, "completeness": 0.20,
           "clarity": 0.15, "communication": 0.15}
