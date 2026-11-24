"""AI-Powered Interview Preparation System - Streamlit frontend.
Run:  streamlit run app.py
"""
import pandas as pd
import streamlit as st
import database as db
import evaluator as ev
import recommender as rec
import resume as rs
from config import JOB_ROLES, CATEGORIES, DIFFICULTIES, ENV_API_KEY
from llm import LLMClient

st.set_page_config(page_title="AI Interview Coach", page_icon="🎯", layout="wide")
db.init_db()
S = st.session_state
for k, v in {"uid": None, "username": None, "iv": None, "api_key": ENV_API_KEY}.items():
    S.setdefault(k, v)


def llm():
    return LLMClient(api_key=S.api_key)


# ---------------------------------------------------------------- auth
def auth_page():
    st.title("🎯 AI Interview Preparation System")
    st.caption("Practice technical and HR interviews with LLM-powered feedback.")
    t1, t2 = st.tabs(["Login", "Register"])
    with t1:
        u = st.text_input("Username", key="lu")
        p = st.text_input("Password", type="password", key="lp")
        if st.button("Login", type="primary"):
            uid = db.login(u, p)
            if uid:
                S.uid, S.username = uid, u.strip().lower()
                st.rerun()
            st.error("Invalid username or password.")
    with t2:
        u = st.text_input("Choose username", key="ru")
        p = st.text_input("Choose password (6+ chars)", type="password", key="rp")
        if st.button("Create account"):
            ok, msg = db.register(u, p)
            (st.success if ok else st.error)(msg)


# ---------------------------------------------------------------- pages
def profile_page():
    st.header("👤 Student Profile")
    p = db.get_profile(S.uid)
    with st.form("profile"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Full name", p.get("full_name") or "")
        email = c2.text_input("Email", p.get("email") or "")
        branch = c1.text_input("Branch / Degree", p.get("branch") or "")
        college = c2.text_input("College", p.get("college") or "")
        year = c1.number_input("Graduation year", 2020, 2035, int(p.get("grad_year") or 2026))
        role = c2.selectbox("Target role", JOB_ROLES,
                            index=JOB_ROLES.index(p["target_role"]) if p.get("target_role") in JOB_ROLES else 0)
        level = st.selectbox("Level", ["Fresher", "0-1 years", "1-3 years"])
        if st.form_submit_button("Save profile", type="primary"):
            db.save_profile(S.uid, full_name=name, email=email, branch=branch, college=college,
                            grad_year=int(year), target_role=role, level=level)
            st.success("Profile saved.")


def resume_page():
    st.header("📄 Resume Upload & Analysis")
    f = st.file_uploader("Upload your resume (PDF)", type=["pdf"])
    if f and st.button("Analyse resume", type="primary"):
        try:
            text = rs.extract_pdf_text(f.read())
        except Exception as e:
            st.error(f"Could not read PDF: {e}")
            return
        with st.spinner("Analysing resume..."):
            a = rs.analyse_resume(text, llm())
        db.save_resume(S.uid, text, a)
        st.success("Resume analysed and saved.")
    r = db.get_resume(S.uid)
    if not r:
        st.info("No resume analysed yet.")
        return
    a = r["analysis"]
    c1, c2 = st.columns([1, 2])
    c1.metric("Resume score", f"{a.get('resume_score', 0)}/10")
    c2.write("**Skills:** " + (", ".join(a.get("skills", [])) or "—"))
    for title, key in [("Qualifications", "qualifications"), ("Experience", "experience"),
                       ("Projects", "projects"), ("Strengths", "strengths"),
                       ("Gaps", "gaps"), ("Suggestions", "suggestions")]:
        if a.get(key):
            with st.expander(title, expanded=key == "suggestions"):
                for x in a[key]:
                    st.write("• " + str(x))


def start_page():
    st.header("🎤 Start a Mock Interview")
    prof = db.get_profile(S.uid)
    c1, c2, c3, c4 = st.columns(4)
    role = c1.selectbox("Job role", JOB_ROLES,
                        index=JOB_ROLES.index(prof["target_role"]) if prof.get("target_role") in JOB_ROLES else 0)
    cat = c2.selectbox("Category", CATEGORIES)
    diff = c3.selectbox("Difficulty", DIFFICULTIES, index=1)
    n = c4.slider("Questions", 3, 10, 5)
    if llm().demo:
        st.warning("Demo mode: no Groq API key set. Built-in questions and a heuristic evaluator are used.")
    if st.button("Generate questions & begin", type="primary"):
        resume = db.get_resume(S.uid)
        weak = rec.weak_topics_from_history(db.all_user_answers(S.uid))
        with st.spinner("Preparing your personalised interview..."):
            qs = ev.generate_questions(llm(), role, cat, diff, n, prof, resume["analysis"] if resume else None, weak)
        S.iv = {"id": db.create_interview(S.uid, role, cat, diff), "role": role, "qs": qs,
                "i": 0, "items": [], "done": False}
        st.rerun()


def interview_page():
    iv = S.iv
    if not iv:
        return start_page()
    if iv["done"]:
        return report_view(iv["report"], iv["items"], iv["role"])
    i, qs = iv["i"], iv["qs"]
    st.header(f"🎤 {iv['role']} interview")
    st.progress(i / len(qs), text=f"Question {i + 1} of {len(qs)}")
    q = qs[i]
    st.subheader(q["question"])
    st.caption(f"{q['type']} · {q['topic']}")
    ans = st.text_area("Your answer", height=180, key=f"ans{i}",
                       placeholder="Type your answer as you would say it in the interview...")
    c1, c2 = st.columns([1, 5])
    if c1.button("Submit answer", type="primary"):
        with st.spinner("Evaluating..."):
            e = ev.evaluate_answer(llm(), q, ans)
        db.save_answer(iv["id"], i, q, ans, e)
        iv["items"].append({"question": q["question"], "topic": q["topic"], "type": q["type"],
                            "score": e["overall"], "eval": e, "answer": ans})
        iv["last"] = e
        iv["submitted"] = i
        st.rerun()
    if iv.get("submitted") == i:  # show instant feedback
        show_eval(iv["last"])
        last = i == len(qs) - 1
        if st.button("Finish & view report" if last else "Next question ➡️"):
            if last:
                with st.spinner("Building your report..."):
                    rep = rec.build_report(llm(), iv["role"], iv["items"])
                db.finish_interview(iv["id"], rep["overall"], rep)
                iv["report"], iv["done"] = rep, True
            else:
                iv["i"] += 1
            st.rerun()
    if st.button("Cancel interview"):
        S.iv = None
        st.rerun()


def show_eval(e):
    st.markdown("---")
    st.metric("Answer score", f"{e['overall']}/10")
    cols = st.columns(5)
    for col, (k, v) in zip(cols, e["scores"].items()):
        col.metric(k.replace("_", " ").title(), v)
    st.write("**Why:** " + e.get("reasoning_summary", ""))
    if e.get("missing_concepts"):
        st.write("**Missing concepts:** " + ", ".join(e["missing_concepts"]))
    for label, key in [("Strengths", "strengths"), ("Weaknesses", "weaknesses")]:
        if e.get(key):
            st.write(f"**{label}:** " + "; ".join(e[key]))
    if e.get("grammar_feedback"):
        st.write("**Grammar & communication:** " + e["grammar_feedback"])
    if e.get("improved_answer"):
        st.info("**Stronger answer:** " + e["improved_answer"])
    if e.get("suggestion"):
        st.success("**Next step:** " + e["suggestion"])


def report_view(rep, items, role):
    st.header(f"📊 Final Interview Report - {role}")
    c1, c2 = st.columns([1, 3])
    c1.metric("Overall score", f"{rep['overall']}/10")
    c2.write(rep.get("summary", ""))
    if rep.get("criteria"):
        st.bar_chart(pd.Series(rep["criteria"]))
    a, b = st.columns(2)
    a.subheader("✅ Strengths")
    for x in rep.get("strengths", []):
        a.write("• " + x)
    b.subheader("⚠️ Weaknesses")
    for x in rep.get("weaknesses", []):
        b.write("• " + x)
    if rep.get("missing_concepts"):
        st.subheader("Missing technical concepts")
        st.write(", ".join(rep["missing_concepts"]))
    st.subheader("📚 Recommended topics")
    for t in rep.get("study_topics", []):
        st.write(f"**{t.get('topic')}** - {t.get('why', '')}  \n_Resources:_ {', '.join(t.get('resources', []))}")
    if rep.get("seven_day_plan"):
        with st.expander("7-day improvement plan"):
            for d in rep["seven_day_plan"]:
                st.write("• " + d)
    st.subheader("Question-wise scores")
    for n, it in enumerate(items, 1):
        with st.expander(f"Q{n}. {it['question']}  -  {it['score']}/10"):
            if it.get("answer"):
                st.write("**Your answer:** " + it["answer"])
            show_eval(it["eval"])
    if st.button("Start another interview"):
        S.iv = None
        st.rerun()


def dashboard_page():
    st.header("📈 Performance Dashboard")
    df = rec.history_frame(db.list_interviews(S.uid))
    if df.empty:
        st.info("Complete an interview to see analytics.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Interviews taken", len(df))
    c2.metric("Average score", round(df["overall_score"].mean(), 1))
    c3.metric("Best score", round(df["overall_score"].max(), 1))
    st.subheader("Score trend")
    st.line_chart(df.set_index("started_at")["overall_score"])
    rows = db.all_user_answers(S.uid)
    topics = pd.DataFrame(rows).groupby("topic")["score"].mean().round(1).sort_values()
    st.subheader("Average score by topic")
    st.bar_chart(topics)
    weak = rec.weak_topics_from_history(rows)
    st.subheader("🎓 Personalised learning recommendations")
    if weak:
        for t in weak:
            st.write(f"• Revise **{t}** (avg {topics[t]}/10) - next interview will focus on it.")
    else:
        st.success("No weak topics detected. Try Advanced difficulty!")


def history_page():
    st.header("🗂️ Mock Interview History")
    items = db.list_interviews(S.uid)
    if not items:
        st.info("No completed interviews yet.")
        return
    st.dataframe(pd.DataFrame(items).rename(columns={"started_at": "date", "overall_score": "score"}),
                 use_container_width=True, hide_index=True)
    pick = st.selectbox("Open report", [x["id"] for x in items],
                        format_func=lambda i: next(f"#{x['id']} · {x['role']} · {x['overall_score']}/10" for x in items if x["id"] == i))
    d = db.get_interview(pick)
    if d:
        report_view(d["report"], [{"question": a["question"], "topic": a["topic"], "type": a["qtype"],
                                   "score": a["score"], "eval": a["eval"], "answer": a["answer"]}
                                  for a in d["answers"]], d["role"])


# ---------------------------------------------------------------- router
if not S.uid:
    auth_page()
    st.stop()

with st.sidebar:
    st.write(f"Signed in as **{S.username}**")
    S.api_key = st.text_input("Groq API key", value=S.api_key, type="password",
                              help="Get a key at console.groq.com/keys. Leave empty for Demo mode.")
    st.caption("Mode: " + ("🟡 Demo (offline)" if llm().demo else "🟢 Groq"))
    page = st.radio("Menu", ["Interview", "Dashboard", "History", "Resume", "Profile"])
    if st.button("Logout"):
        for k in ["uid", "username", "iv"]:
            S[k] = None
        st.rerun()

{"Interview": interview_page, "Dashboard": dashboard_page, "History": history_page,
 "Resume": resume_page, "Profile": profile_page}[page]()
