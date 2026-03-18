import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="NZ Visa Advisor",
    page_icon="🛂",
    layout="centered"
)

# ── HEADER ───────────────────────────────────────────────────────────
st.title("🛂 NZ Visa Advisor")
st.subheader("AI-Powered Immigration Guidance for Licensed Advisers")
st.caption("Built for New Zealand Licensed Immigration Advisers (LIAs)")
st.divider()

# ── DISCLAIMER ───────────────────────────────────────────────────────
st.warning("""⚠️ **For Licensed Immigration Advisers Only.**
This tool assists LIAs in assessing client eligibility and preparing
applications. All recommendations must be verified against current
INZ policy before lodging. This is not legal advice.""")

st.divider()

# ── FEATURE CARDS ────────────────────────────────────────────────────
st.subheader("What would you like to do?")
st.write("")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🧠 Visa Eligibility Check")
    st.write(
        "Assess your client's eligibility for the "
        "Skilled Migrant Category visa through a "
        "guided conversation."
    )
    if st.button("Start Eligibility Check →",
                  type="primary",
                  use_container_width=True):
        st.switch_page("pages/1_Visa_Eligibility.py")

    st.write("")

    st.markdown("### 📋 Full Assessment Report")
    st.write(
        "Generate a complete client-ready report "
        "combining eligibility, points breakdown, "
        "and document checklist."
    )
    if st.button("Generate Report →",
                  use_container_width=True,
                  disabled=True):
        st.switch_page("pages/3_Full_Report.py")
    st.caption("🔒 Complete eligibility check first")

with col2:
    st.markdown("### 📄 Document Review")
    st.write(
        "Upload your client's documents and get an "
        "instant checklist showing what's complete, "
        "missing, or needs attention."
    )
    if st.button("Review Documents →",
                  use_container_width=True,
                  disabled=True):
        st.switch_page("pages/2_Document_Review.py")
    st.caption("🔒 Coming in Week 4")

    st.write("")

    st.markdown("### ❓ Ask INZ Policy")
    st.write(
        "Ask any question about NZ immigration policy. "
        "Answers grounded in live INZ documentation "
        "with source citations."
    )
    if st.button("Ask a Question →",
                  use_container_width=True):
        st.switch_page("pages/4_Ask_INZ_Policy.py")

st.divider()

# ── FOOTER ───────────────────────────────────────────────────────────
st.caption(
    "NZ Visa Advisor v0.1 | "
    "Built with Claude AI | "
    "Data sourced from immigration.govt.nz"
)