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
st.caption(
    "⚠️ Answers reflect the most recently scraped INZ policy. "
    "If your client's lodgement date differs from today, verify the policy version "
    "that was in effect at that time, as INZ rules change periodically (e.g. SMC changes effective 24 Aug 2026)."
)

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
    "overseas experience": "Overseas work experience does NOT count for NZ experience top-up points. Only skilled work experience gained IN New Zealand adds points (1pt/year, max 3pts). Overseas experience may support qualification or registration pillar claims but not the NZ experience top-up.",
    "contractor": "Contractor roles can qualify for SMC if the contract is continuous for at least 6 months. Evidence required: income summary or tax statement from Inland Revenue, plus job descriptions and contract history.",
    "ielts expires": "English language test results must be less than 2 years old when you apply. From 24 August 2026, results will be valid for 5 years for applicants with recognised occupational registration.",
}

# Maps multiple search terms to each COVERAGE_RULES key, so e.g. "IELTS" or "PTE"
# both trigger the "english" rule rather than requiring the exact word "english".
COVERAGE_KEYWORD_ALIASES = {
    # Specific rules first — must come before generic ones
    "contractor": ["contractor", "contract role", "fixed-term contract", "contracting"],
    "ielts expires": ["ielts expires", "pte valid", "ielts valid", "score valid", "score expires", "results expire", "test expiry", "how long is my", "valid for how"],
    "overseas experience": ["overseas experience", "overseas work", "international experience", "work experience overseas", "foreign experience"],
    "accredited employer": ["accredited employer", "accreditation"],
    "age": ["age limit", "age requirement", "how old", "maximum age", "55 years"],
    "green list": ["green list"],
    "processing": ["processing time", "how long does"],
    # Generic rules last
    "english": ["english", "ielts", "pte", "toefl", "language"],
    "job offer": ["job offer", "employer"],
    "salary": ["salary", "income", "wage"],
    "qualification": ["qualification", "degree", "bachelor", "masters", "phd"],
    "nz experience": ["nz experience", "new zealand experience", "how much experience", "years of experience in nz", "work experience"],
    "points": ["points", "threshold"],
}

def get_coverage_note(query: str) -> str | None:
    """Return a verified rule-based note if the query matches a known SMC fact."""
    q = query.lower()
    for rule_key, aliases in COVERAGE_KEYWORD_ALIASES.items():
        if any(alias in q for alias in aliases):
            return COVERAGE_RULES.get(rule_key)
    return None
 
if "messages" not in st.session_state:
    st.session_state.messages = []
 
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "confidence" in msg:
            st.caption(f"📊 Retrieval confidence: {msg['confidence']}")
 
if query := st.chat_input("e.g. What documents do I need?"):
    st.session_state.messages.append({
        "role": "user",
        "content": query
    })
    with st.chat_message("user"):
        st.markdown(query)
 
    with st.chat_message("assistant"):
        with st.spinner("Searching INZ documents..."):
            chunks_retrieved, pages, conflicts, confidence = retrieve(collection, query, n=n_results, all_chunks=all_chunks)
            answer = ask_claude(query, chunks_retrieved, pages, conflicts)
    
            # Secondary confidence check
            #cant_answer_phrases = [
            #    "does not contain", "outside the scope", "not covered",
            #    "no information", "cannot find", "not available in"
            #]
            #if any(phrase in answer.lower() for phrase in cant_answer_phrases):
            #    confidence = min(confidence, 25)

        if confidence < 35:
            st.warning(f"⚠️ Low confidence ({confidence}%) — retrieved policy chunks may not directly answer this question. Verify with INZ directly before advising the client.")
            #st.stop()
        
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
            if confidence < 50:
                st.caption("📊 Retrieval confidence: based on verified INZ rule above — RAG retrieval was insufficient for this query.")
                st.session_state.messages.append({"role": "assistant", "content": coverage_note, "confidence": "🔴 Low — answered from verified rule"})
                st.stop()

        st.markdown(answer)

        if confidence >= 70:
            conf_label = "🟢 High confidence"
            conf_reason = "Policy chunks closely match this query."
        elif confidence >= 45:
            conf_label = "🟡 Medium confidence"
            conf_reason = "Partial policy match found — answer may not cover all aspects. Verify with INZ if advising on this point."
        else:
            conf_label = "🔴 Low confidence"
            if conflicts:
                conf_reason = "Conflicting policy information detected — LIA must verify directly with INZ."
            elif any(phrase in answer.lower() for phrase in ["does not contain", "not available", "cannot find", "outside the scope"]):
                conf_reason = "This topic is not covered in the scraped INZ pages. Check immigration.govt.nz directly."
            else:
                conf_reason = "Query did not closely match available policy content. Rephrase or verify directly with INZ."
        st.caption(f"📊 Retrieval confidence: {conf_label} ({confidence}%) — {conf_reason}")

        with st.expander("📄 Source sections used"):
            for i, chunk in enumerate(chunks_retrieved):
                st.markdown(f"**Section {pages[i]}**")
                st.caption(chunk[:300] + "...")

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "confidence": f"{conf_label} ({confidence}%) — {conf_reason}"
    })