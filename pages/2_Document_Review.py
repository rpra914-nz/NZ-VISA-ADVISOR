"""
pages/2_Document_Review.py
Upload client PDFs → Claude identifies each doc → checklist of ✅ ⚠️ ❌
"""

import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.document_review_agent import review_documents

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Document Review — NZ Visa Advisor",
    page_icon="📄",
    layout="centered",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.doc-card {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 12px;
}
.doc-card.ok    { border-left: 4px solid #1A7F37; }
.doc-card.warning { border-left: 4px solid #D97706; }
.doc-card.error { border-left: 4px solid #DC2626; }
.status-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
.badge-ok      { background: #DCFCE7; color: #1A7F37; }
.badge-warning { background: #FEF3C7; color: #92400E; }
.badge-error   { background: #FEE2E2; color: #991B1B; }
.checklist-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📄 Document Review")
st.markdown(
    "Upload your client's supporting documents. "
    "The AI will identify each file and check it against INZ SMC requirements."
)
st.divider()

# ── Sidebar: tips ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📋 Required Documents")
    st.markdown("""
**Essential (must have):**
- ✅ Passport
- ✅ Job offer / employment contract
- ✅ Academic qualification(s)
- ✅ Police clearance certificate
- ✅ Medical certificate

**Recommended:**
- 📎 Bank statements (3 months)
- 📎 English language evidence
- 📎 CV / Résumé
- 📎 Reference letters
""")
    st.info("💡 Upload PDFs only. Scanned documents must be legible.")

# ── File uploader ─────────────────────────────────────────────────────────────
uploaded_files = st.file_uploader(
    "Upload client documents (PDF only)",
    type=["pdf"],
    accept_multiple_files=True,
    help="You can upload multiple files at once.",
)

if not uploaded_files:
    st.markdown("""
<div style='text-align:center; color:#8C9099; padding:40px 0;'>
    <div style='font-size:48px;'>📂</div>
    <div style='font-size:16px; margin-top:8px;'>No files uploaded yet</div>
    <div style='font-size:13px;'>Drag and drop PDFs above to get started</div>
</div>
""", unsafe_allow_html=True)
    st.stop()

# ── Analyse button ────────────────────────────────────────────────────────────
st.success(f"**{len(uploaded_files)} file(s) uploaded.** Click below to analyse.")

if st.button("🔍 Analyse Documents", type="primary", use_container_width=True):
    with st.spinner("Reviewing documents with AI… this may take 15–30 seconds."):
        try:
            results = review_documents(uploaded_files)
            st.session_state["doc_review_results"] = results
        except Exception as e:
            st.error(f"Document review failed: {e}")
            st.stop()

# ── Display results ───────────────────────────────────────────────────────────
if "doc_review_results" not in st.session_state:
    st.stop()

results = st.session_state["doc_review_results"]
reviewed = results["reviewed_docs"]
checklist = results["checklist"]
missing = results["required_missing"]
all_ok = results["all_required_present"]

st.divider()

# Summary banner
if all_ok:
    st.success("✅ **All required documents are present.** Review individual results below.")
elif missing:
    missing_labels = ", ".join(m["label"] for m in missing)
    st.error(f"❌ **Missing required documents:** {missing_labels}")
else:
    st.warning("⚠️ Some documents may need attention. Review results below.")

st.markdown("---")

# ── Per-document cards ────────────────────────────────────────────────────────
st.subheader("📑 Uploaded Documents")

ICON_MAP = {"ok": "✅", "warning": "⚠️", "error": "❌"}
BADGE_MAP = {"ok": "badge-ok", "warning": "badge-warning", "error": "badge-error"}

for doc in reviewed:
    status = doc.get("status", "warning")
    icon = ICON_MAP.get(status, "⚠️")
    label = doc.get("label", "Document")
    fname = doc.get("filename", "")
    summary = doc.get("summary", "")
    issues = doc.get("issues", [])
    suggestions = doc.get("suggestions", [])
    inz_notes = doc.get("inz_notes", "")
    word_count = doc.get("word_count", 0)
    badge_class = BADGE_MAP.get(status, "badge-warning")

    with st.expander(f"{icon} **{label}** — `{fname}`", expanded=(status != "ok")):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{summary}**")
        with col2:
            st.markdown(
                f'<span class="status-badge {badge_class}">{status.upper()}</span>',
                unsafe_allow_html=True,
            )

        if word_count < 30:
            st.warning("⚠️ Very little text was extracted — document may be scanned or image-only.")

        if issues:
            st.markdown("**Issues found:**")
            for iss in issues:
                st.markdown(f"- 🔴 {iss}")

        if suggestions:
            st.markdown("**Suggestions:**")
            for sug in suggestions:
                st.markdown(f"- 💡 {sug}")

        if inz_notes:
            st.caption(f"INZ requirement: {inz_notes}")

st.markdown("---")

# ── INZ Checklist ─────────────────────────────────────────────────────────────
st.subheader("📋 INZ SMC Document Checklist")

col_h1, col_h2, col_h3 = st.columns([4, 2, 2])
col_h1.markdown("**Document**")
col_h2.markdown("**Required**")
col_h3.markdown("**Status**")

for item in checklist:
    col1, col2, col3 = st.columns([4, 2, 2])
    col1.markdown(item["label"])
    col2.markdown("🔴 Required" if item["required"] else "🔵 Recommended")
    if item["present"]:
        col3.markdown("✅ Present")
    elif item["required"]:
        col3.markdown("❌ Missing")
    else:
        col3.markdown("⬜ Not uploaded")

# ── Save results & navigate ───────────────────────────────────────────────────
st.markdown("---")
st.info(
    "💾 Results are saved. Go to **Full Report** to generate and download the complete client report.",
    icon="📥",
)

col_a, col_b = st.columns(2)
with col_a:
    if st.button("← Back to Visa Eligibility", use_container_width=True):
        st.switch_page("pages/1_Visa_Eligibility.py")
with col_b:
    if st.button("Generate Full Report →", type="primary", use_container_width=True):
        st.switch_page("pages/3_Full_Report.py")