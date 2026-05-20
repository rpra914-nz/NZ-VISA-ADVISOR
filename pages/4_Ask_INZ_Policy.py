import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
 
import streamlit as st
from agents.rag_agent import retrieve, ask_claude
 
from utils.cache import get_collection
from utils.urls import INZ_URLS
n_results = max(5, len(INZ_URLS))
 
st.set_page_config(
    page_title="Ask INZ Policy",
    page_icon="❓",
    layout="centered"
)
 
if st.button("← Back to Home"):
    st.switch_page("Home.py")
 
st.title("❓ Ask INZ Policy")
st.caption("Questions answered from live INZ documentation")
st.divider()
 
from utils.auth import check_login
if not check_login():
    st.stop()

# Load RAG — already warmed up by Home.py; this call hits the cache instantly
collection, all_chunks = get_collection()
 
if collection is None:
    error_msg = st.session_state.get(
        "rag_error",
        "⚠️ INZ policy database could not be loaded. Check your internet connection and refresh."
    )
    st.error(error_msg)
    st.info("All other features (Eligibility, Document Review, Report) remain available from Home.")
    st.stop()
 
st.success("✅ INZ documents loaded. Ask your question below!")

# ── Coverage assurance — rule-based facts validated independently of RAG ──
# These are hard facts that must be correct regardless of what the scraped
# documents say. If a question matches, the rule is shown as a verified note.
COVERAGE_RULES = {
    "points": "SMC requires a minimum of **6 points**. Points come from one main pillar (qualification, income, or occupational registration) plus up to 3 points from NZ work experience.",
    "age": "SMC applicants must be **55 or under** at time of application.",
    "english": "English requirement: **IELTS 6.5** overall (no band below 6.5), or equivalent PTE Academic 58+, TOEFL 79+, OET Grade B+.",
    "job offer": "A **skilled job offer from an INZ-accredited employer** is required for SMC.",
    "accredited employer": "The employer must hold **INZ accreditation** before a job offer can be used for SMC points.",
    "green list": "The **Green List** offers faster pathways: Tier 1 = Straight to Residence, Tier 2 = Work to Residence via 2-year AEWV.",
    "salary": "Income pillar (2025 NZ median ~$73k/yr): $73k-109k/yr = 3pts | $110k-145k/yr = 4pts | $146k-218k/yr = 5pts | $219k+/yr = 6pts. Divide annual by 2080 to get hourly rate.",
    "qualification": "Qualification pillar: Bachelor's/Honours = 3pts, Masters/Postgrad = 4pts, PhD/Doctorate = 5pts. NZ qualification adds 1pt.",
    "nz experience": "NZ skilled work experience adds **1 point per year**, up to a maximum of 3 points.",
    "processing": "INZ processing times vary. Check the current INZ website for live timeframes — they are not scraped by this tool.",
}

def get_coverage_note(query: str) -> str | None:
    """Return a verified rule-based note if the query matches a known SMC fact."""
    q = query.lower()
    for keyword, rule in COVERAGE_RULES.items():
        if keyword in q:
            return rule
    return None
 
if "messages" not in st.session_state:
    st.session_state.messages = []
 
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
 
if query := st.chat_input("e.g. What documents do I need?"):
    st.session_state.messages.append({
        "role": "user",
        "content": query
    })
    with st.chat_message("user"):
        st.markdown(query)
 
    with st.chat_message("assistant"):
        with st.spinner("Searching INZ documents..."):
            chunks_retrieved, pages, conflicts = retrieve(collection, query, n=n_results, all_chunks=all_chunks)  # set to None to skip conflict detection for now
            answer = ask_claude(query, chunks_retrieved, pages, conflicts)
        
        # ── Conflict warning — shown to LIA before the answer ────────
        if conflicts:
            with st.expander("⚠️ Conflicting information detected in source documents", expanded=True):
                st.warning(
                    "The INZ documents retrieved contain conflicting information on this topic. "
                    "The answer below reflects the most common position, but **LIA must verify "
                    "against the current INZ website before advising the client.**"
                )
                for c in conflicts:
                    st.caption(f"• {c}")

        # ── Coverage assurance note ──────────────────────────────────
        coverage_note = get_coverage_note(query)
        if coverage_note:
            st.info(f"📌 **Verified INZ rule:** {coverage_note}")

        st.markdown(answer)
        with st.expander("📄 Source sections used"):
            for i, chunk in enumerate(chunks_retrieved):
                st.markdown(f"**Section {pages[i]}**")
                st.caption(chunk[:300] + "...")
 
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })