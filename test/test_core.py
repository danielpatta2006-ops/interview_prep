import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")
import config; config.DB_PATH = os.environ["DB_PATH"]
import database as db, evaluator as ev, recommender as rec, resume as rs
from llm import LLMClient, extract_json, LLMError
import pytest

db.DB_PATH = config.DB_PATH
db.init_db()
DEMO = LLMClient(api_key="")


def test_T1_T2_register_duplicate():
    assert db.register("alice", "secret1")[0]
    assert not db.register("alice", "secret1")[0]


def test_T3_login():
    db.register("bob", "secret1")
    assert db.login("bob", "secret1")
    assert db.login("bob", "wrong") is None


def test_T7_json_repair():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! {"a": 2} hope it helps') == {"a": 2}
    with pytest.raises(LLMError):
        extract_json("not json")


def test_T11_weighted_score():
    s = dict(technical_accuracy=10, relevance=10, completeness=10, clarity=10, communication=10)
    assert ev.weighted_overall(s) == 10.0
    s = dict(technical_accuracy=7, relevance=9, completeness=4, clarity=6, communication=5)
    assert ev.weighted_overall(s) == 6.4


def test_T13_demo_mode_and_questions():
    assert DEMO.demo
    qs = ev.generate_questions(DEMO, "Software Developer", "Mixed", "Beginner", 4, {}, None, [])
    assert len(qs) == 4 and {q["type"] for q in qs} == {"Technical", "HR"}


def test_T8_T9_heuristic_evaluation():
    q = ev.DEMO_QUESTIONS["Technical"][0]
    q = {"question": q[0], "expected_concepts": q[2]}
    good = ev.evaluate_answer(DEMO, q, "Lists are mutable while tuples are immutable. Tuples are hashable so "
                              "they can be dictionary keys. Use tuples for fixed use cases such as coordinates.")
    bad = ev.evaluate_answer(DEMO, q, "don't know")
    assert good["overall"] > bad["overall"] and bad["overall"] <= 2


def test_report_and_weak_topics():
    items = [{"question": "q", "topic": "SQL", "type": "Technical", "score": 3.0,
              "eval": ev.heuristic_evaluation({"expected_concepts": ["joins"]}, "")}]
    rep = rec.build_report(DEMO, "Data Analyst", items)
    assert rep["overall"] == 3.0 and rep["study_topics"]
    assert rec.weak_topics_from_history([{"topic": "SQL", "score": 3}]) == ["SQL"]


def test_resume_heuristic():
    a = rs.heuristic_analysis("Skills: Python, SQL, Machine Learning\nProject: Chatbot using Streamlit")
    assert "Python" in a["skills"] and a["projects"]
