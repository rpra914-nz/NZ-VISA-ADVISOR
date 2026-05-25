# pages/0_Client_Cases.py — Client case dashboard: view, search, and reload all saved LIA assessments.

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from utils.auth import check_login
from utils.database import get_all_cases, get_case, search_cases, init_db

st.set_page_config(page_title="Client Cases", page_icon="📁", layout="wide")

if not check_login():
    st.stop()

init_db()

if st.button("← Back to Home"):
    st.switch_page("Home.py")

st.title("📁 Client Cases")
st.caption("All saved assessments — search by Case ID or client name")
st.divider()

# ── Search bar ────────────────────────────────────────────────────────
search_query = st.text_input("🔍 Search by Case ID or Name",
                              placeholder="e.g. CASE-001 or Priya Sharma")

if search_query.strip():
    cases = search_cases(search_query.strip())
else:
    cases = get_all_cases()

# ── Case count ────────────────────────────────────────────────────────
st.caption(f"{len(cases)} case(s) found")
st.divider()

# ── Case list ─────────────────────────────────────────────────────────
if not cases:
    st.info("No cases found. Complete a Visa Eligibility assessment to create the first case.")
else:
    for case in cases:
        status = case["status"]

        # Colour code by status
        if status == "ELIGIBLE":
            badge = "🟢 ELIGIBLE"
        elif status == "LIKELY_ELIGIBLE":
            badge = "🟡 LIKELY ELIGIBLE"
        elif status == "NOT_ELIGIBLE":
            badge = "🔴 NOT ELIGIBLE"
        elif status == "INCOMPLETE":
            badge = "⚫ INCOMPLETE"
        else:
            badge = "⚪ UNKNOWN"

        with st.expander(
            f"**{case['case_id']}** — {case['full_name']} ({case['nationality']}) — {badge} — {case['created_at']}"
        ):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**Case ID:** {case['case_id']}")
                st.markdown(f"**Client:** {case['full_name']}")
                st.markdown(f"**Nationality:** {case['nationality']}")
                st.markdown(f"**Status:** {badge}")
                st.markdown(f"**Created:** {case['created_at']}")

            with col2:
                if st.button("📂 Load Case",
                             key=f"load_{case['case_id']}",
                             use_container_width=True):
                    saved = get_case(case["case_id"])
                    if saved:
                        # Restore session state so page 1 shows results
                        st.session_state["client_profile"] = saved["profile"]
                        st.session_state["assessment_result"] = {
                            "parsed": saved["parsed"],
                            "profile": saved["profile"],
                            "raw_assessment": "",
                            "green_list": {},
                            "lia_interventions": []
                        }
                        st.session_state["intake_complete"] = True
                        st.session_state["active_case_id"] = case["case_id"]
                        st.success(f"Case {case['case_id']} loaded — go to Visa Eligibility to view results.")
                    else:
                        st.error("Could not load case data.")