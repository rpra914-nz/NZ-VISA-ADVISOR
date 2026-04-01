"""
pages/1_Visa_Eligibility.py
Phase 1: Conversational intake (9 questions via IntakeAgent)
Phase 2: Profile review + Run Assessment button
Phase 3: Results with points breakdown + disclaimer
"""

import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.intake_agent import IntakeAgent
from agents.classification_agent import classify_applicant

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Visa Eligibility — NZ Visa Advisor",
    page_icon="🛂",
    layout="centered",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.chat-bubble-user {
    background: #E8EEF6;
    border-radius: 12px 12px 2px 12px;
    padding: 10px 14px;
    margin: 6px 0;
    max-width: 80%;
    margin-left: auto;
    font-size: 14px;
}
.chat-bubble-bot {
    background: #F4F6F8;
    border-radius: 12px 12px 12px 2px;
    padding: 10px 14px;
    margin: 6px 0;
    max-width: 80%;
    font-size: 14px;
    border-left: 3px solid #003087;
}
.result-card {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.points-big {
    font-size: 48px;
    font-weight: 700;
    color: #003087;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ── Initialise session state ──────────────────────────────────────────────────
if "intake_agent" not in st.session_state:
    st.session_state.intake_agent = IntakeAgent()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    # Seed with first question
    first_q = st.session_state.intake_agent.get_current_question()
    st.session_state.chat_history.append({"role": "bot", "text": f"👋 Welcome! Let's collect your client's details for the SMC assessment.\n\n**{first_q}**"})

if "intake_complete" not in st.session_state:
    st.session_state.intake_complete = False

if "assessment_result" not in st.session_state:
    st.session_state.assessment_result = None

if "client_profile" not in st.session_state:
    st.session_state.client_profile = None

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🛂 Visa Eligibility")
st.markdown("Skilled Migrant Category (SMC) — Client Assessment")
st.divider()

agent: IntakeAgent = st.session_state.intake_agent

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — INTAKE CHAT
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.intake_complete:

    # Progress bar
    progress = agent.get_progress()
    st.progress(progress / 100, text=f"Question {agent.current_question_index} of {13} — {progress}% complete")

    # Chat history
    for msg in st.session_state.chat_history:
        if msg["role"] == "bot":
            st.markdown(f'<div class="chat-bubble-bot">{msg["text"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-bubble-user">{msg["text"]}</div>', unsafe_allow_html=True)

    # Input
    with st.form("intake_form", clear_on_submit=True):
        user_input = st.text_input(
            "Your answer",
            placeholder="Type your answer here…",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Send →", use_container_width=True)

    if submitted and user_input.strip():
        # Store user message
        st.session_state.chat_history.append({"role": "user", "text": user_input})

        # Process answer
        with st.spinner("Processing…"):
            agent.process_answer(user_input)

        if agent.complete:
            # Intake done
            st.session_state.intake_complete = True
            st.session_state.client_profile = agent.profile
            st.session_state.chat_history.append({
                "role": "bot",
                "text": "✅ **All done!** I've collected the client profile. Review the details below and run the assessment."
            })
        else:
            # Next question
            next_q = agent.get_current_question()
            st.session_state.chat_history.append({
                "role": "bot",
                "text": f"**{next_q}**"
            })

        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — PROFILE REVIEW + RUN ASSESSMENT
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.intake_complete and st.session_state.assessment_result is None:

    st.success("✅ Client intake complete!")
    st.subheader("👤 Client Profile")

    profile = st.session_state.client_profile

    # Display profile as a clean table
    field_labels = {
        "nationality": "Nationality",
        "age": "Age",
        "occupation": "Occupation / Job Title",
        "job_offer": "NZ Job Offer",
        "years_experience": "Years of Experience",
        "qualification": "Highest Qualification",
        "english_level": "English Level",
        "family": "Family Members",
        "currently_in_nz": "Currently in NZ",
    }

    for key, label in field_labels.items():
        val = profile.get(key, "—")
        if isinstance(val, bool):
            val = "Yes ✅" if val else "No ❌"
        elif val is None:
            val = "—"
        c1, c2 = st.columns([2, 3])
        c1.markdown(f"**{label}**")
        c2.markdown(str(val))

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 Start Over", use_container_width=True):
            for key in ["intake_agent", "chat_history", "intake_complete",
                        "assessment_result", "client_profile"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    with col_b:
        if st.button("🧠 Run SMC Assessment", type="primary", use_container_width=True):
            with st.spinner("Analysing eligibility against INZ SMC rules…"):
                try:
                    result = classify_applicant(profile)
                    st.session_state.assessment_result = result
                    st.rerun()
                except Exception as e:
                    st.error(f"Assessment failed: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — RESULTS
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.assessment_result is not None:

    result = st.session_state.assessment_result
    parsed = result.get("parsed", {})
    raw = result.get("raw_assessment", "")

    # Read rich sections directly from parsed dict (populated by classification_agent)
    strengths = parsed.get("strengths", [])
    gaps = parsed.get("gaps", [])
    actions = parsed.get("recommended_actions", [])
    risks = parsed.get("risk_flags", [])

    st.subheader("📊 SMC Assessment Results")

    # Status banner
    status = parsed.get("status", "UNKNOWN")
    total_pts = parsed.get("total_points", "—")
    confidence = parsed.get("confidence", "—")

    if status == "ELIGIBLE":
        st.success(f"### ✅ ELIGIBLE — {total_pts} / 6 points")
    elif status == "LIKELY_ELIGIBLE":
        st.warning(f"### ⚠️ LIKELY ELIGIBLE — {total_pts} / 6 points")
    else:
        st.error(f"### ❌ NOT ELIGIBLE — {total_pts} / 6 points")

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Points", f"{total_pts} / 6")
    col2.metric("Pillar Points", parsed.get("pillar_points", "—"))
    col3.metric("NZ Exp. Points", parsed.get("nz_experience_points", "0"))
    col4.metric("Confidence", confidence)

    st.divider()

    # Points breakdown table
    st.subheader("🔢 Points Breakdown")
    c1, c2 = st.columns([2, 3])
    c1.markdown("**Recommended Visa**")
    c2.markdown(parsed.get("visa", "—"))
    c1.markdown("**Pillar Used**")
    c2.markdown(parsed.get("pillar", "—").title())
    c1.markdown("**Pillar Points**")
    c2.markdown(parsed.get("pillar_points", "—"))
    c1.markdown("**NZ Experience Points**")
    c2.markdown(parsed.get("nz_experience_points", "0"))
    c1.markdown("**Total Points**")
    c2.markdown(f"**{total_pts} / 6**")

    st.divider()

    # Strengths & Gaps side by side
    col_s, col_g = st.columns(2)

    with col_s:
        st.subheader("💪 Strengths")
        if strengths:
            for s in strengths:
                st.markdown(f"✅ {s}")
        else:
            st.caption("None identified.")

    with col_g:
        st.subheader("⚠️ Gaps")
        if gaps:
            for g in gaps:
                st.markdown(f"🔴 {g}")
        else:
            st.caption("None identified.")

    st.divider()

    # Recommended actions
    st.subheader("📋 Recommended Actions")
    if actions:
        for i, a in enumerate(actions, 1):
            st.markdown(f"**{i}.** {a}")
    else:
        st.caption("No actions listed.")

    # Risk flags — always show section, filter out literal "None" entries
    non_none_risks = [r for r in risks if r.strip().lower() not in ("none", "none.")]
    st.divider()
    st.subheader("🚩 Risk Flags")
    if non_none_risks:
        for r in non_none_risks:
            st.warning(r)
    else:
        st.success("✅ No significant risk flags identified.")

    st.divider()

    # Raw assessment collapsed
    with st.expander("📄 Full Raw Assessment", expanded=False):
        st.text(raw)

    st.divider()

    # Navigation
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("🔄 New Client", use_container_width=True):
            for key in ["intake_agent", "chat_history", "intake_complete",
                        "assessment_result", "client_profile", "doc_review_results"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    with col_b:
        if st.button("📄 Document Review →", use_container_width=True):
            st.switch_page("pages/2_Document_Review.py")
    with col_c:
        if st.button("📊 Full Report →", type="primary", use_container_width=True):
            st.switch_page("pages/3_Full_Report.py")

    # Disclaimer
    st.divider()
    st.caption(
        "⚖️ **Disclaimer:** This assessment is AI-generated for use by Licensed Immigration Advisers (LIAs) only. "
        "It does not constitute legal or immigration advice. All results must be verified against current INZ "
        "policy before submission to Immigration New Zealand."
    )