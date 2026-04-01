"""
pages/3_Full_Report.py
Pulls together intake profile + assessment + document review → generates a PDF report.
"""

import streamlit as st
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.report_agent import generate_report

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Full Report — NZ Visa Advisor",
    page_icon="📊",
    layout="centered",
)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📊 Full Client Report")
st.markdown(
    "Generate a complete, client-ready PDF report combining the visa eligibility "
    "assessment and document review results."
)
st.divider()

# ── Check what data is available in session state ─────────────────────────────
has_profile = "client_profile" in st.session_state
has_assessment = "assessment_result" in st.session_state
has_doc_review = "doc_review_results" in st.session_state

# ── Status checklist ──────────────────────────────────────────────────────────
st.subheader("📋 Report Sections")

col1, col2, col3 = st.columns(3)

with col1:
    if has_profile:
        st.success("✅ Client Profile\n\nCollected")
    else:
        st.error("❌ Client Profile\n\nNot collected")

with col2:
    if has_assessment:
        st.success("✅ SMC Assessment\n\nCompleted")
    else:
        st.warning("⚠️ SMC Assessment\n\nNot run yet")

with col3:
    if has_doc_review:
        st.success("✅ Document Review\n\nCompleted")
    else:
        st.warning("⚠️ Document Review\n\nNot run yet")

st.divider()

# ── If no profile, block report generation ────────────────────────────────────
if not has_profile:
    st.error(
        "**Client profile is required** to generate a report. "
        "Please complete the Visa Eligibility intake first."
    )
    if st.button("← Go to Visa Eligibility", type="primary"):
        st.switch_page("pages/1_Visa_Eligibility.py")
    st.stop()

# ── Prepare data (use empty fallbacks for optional sections) ──────────────────
profile = st.session_state.get("client_profile", {})
assessment = st.session_state.get("assessment_result", {})
doc_review = st.session_state.get("doc_review_results", {
    "reviewed_docs": [],
    "checklist": [],
    "required_missing": [],
    "all_required_present": False,
    "total_uploaded": 0,
})

# ── Report preview ────────────────────────────────────────────────────────────
st.subheader("👤 Report Preview")

name = profile.get("full_name", "Client")
total_pts = assessment.get("total_points", "—")
status = assessment.get("status", "—")
docs_uploaded = doc_review.get("total_uploaded", 0)
missing_count = len(doc_review.get("required_missing", []))

preview_data = {
    "Client Name": name,
    "SMC Points": f"{total_pts} points",
    "Eligibility Status": status.replace("_", " ") if isinstance(status, str) else "—",
    "Documents Uploaded": f"{docs_uploaded} file(s)",
    "Missing Required Docs": f"{missing_count} document(s)" if missing_count else "None ✅",
    "Report Date": datetime.now().strftime("%d %B %Y"),
}

for field, value in preview_data.items():
    c1, c2 = st.columns([2, 3])
    c1.markdown(f"**{field}**")
    c2.markdown(value)

st.divider()

# ── Warnings if sections are missing ─────────────────────────────────────────
if not has_assessment:
    st.warning(
        "⚠️ **No SMC assessment found.** The report will be generated without a points breakdown. "
        "Run the assessment in **Visa Eligibility** first for a complete report."
    )
if not has_doc_review:
    st.warning(
        "⚠️ **No document review found.** The report will include an empty document section. "
        "Upload documents in **Document Review** for a complete report."
    )

# ── Generate & download ───────────────────────────────────────────────────────
st.subheader("⬇️ Download Report")
st.markdown(
    "Click below to generate the PDF. The file will download automatically. "
    "Always review the report before sharing with your client."
)

if st.button("📄 Generate PDF Report", type="primary", use_container_width=True):
    with st.spinner("Generating PDF report…"):
        try:
            pdf_bytes = generate_report(profile, assessment, doc_review)

            client_name_safe = name.replace(" ", "_").replace("/", "-")
            date_safe = datetime.now().strftime("%Y%m%d")
            filename = f"NZ_Visa_Report_{client_name_safe}_{date_safe}.pdf"

            st.download_button(
                label="⬇️ Download Report PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
            )
            st.success(f"✅ Report generated successfully: **{filename}**")
            st.balloons()

        except Exception as e:
            st.error(f"Report generation failed: {e}")
            st.info("Ensure `reportlab` is installed: `pip install reportlab`")

st.divider()

# ── Navigation ────────────────────────────────────────────────────────────────
st.markdown("### 🧭 Navigate")
col_a, col_b, col_c = st.columns(3)

with col_a:
    if st.button("← Visa Eligibility", use_container_width=True):
        st.switch_page("pages/1_Visa_Eligibility.py")
with col_b:
    if st.button("← Document Review", use_container_width=True):
        st.switch_page("pages/2_Document_Review.py")
with col_c:
    if st.button("Ask INZ Policy →", use_container_width=True):
        st.switch_page("pages/4_Ask_INZ_Policy.py")

# ── Disclaimer ────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "⚖️ **Disclaimer:** This report is AI-generated for use by Licensed Immigration Advisers (LIAs) only. "
    "It does not constitute legal or immigration advice. All assessments must be verified against "
    "current INZ policy before submission to Immigration New Zealand."
)