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

from utils.auth import check_login
if not check_login():
    st.stop()

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

if "intake_complete" not in st.session_state:
    st.session_state.intake_complete = False

if "assessment_result" not in st.session_state:
    st.session_state.assessment_result = None

if "client_profile" not in st.session_state:
    st.session_state.client_profile = None

DAILY_ASSESSMENT_LIMIT = 10  # Free/Trial = 3, Pro = 10, Enterprise = unlimited

# ── REAL-TIME GUIDANCE ENGINE ─────────────────────────────────────────────────
# Generates instant feedback after each answer — no extra API call needed.
# Helps LIA understand impact of each answer before running full assessment.
 
QUESTION_CONTEXT = {
    "full_name":              None,  # No guidance needed
    "nationality":            "💡 Citizens of NZ, AU, UK, US, Canada, or Ireland are exempt from English language test requirements.",
    "age":                    "💡 SMC requires applicants to be 55 or under at time of lodgement.",
    "occupation":             "💡 Some occupations qualify for the Green List — a faster pathway than standard SMC.",
    "job_offer":              "💡 SMC requires a skilled job offer from an INZ-accredited employer. Confirm the employer holds accreditation.",
    "years_experience":       "💡 Experience contributes to the qualification pillar assessment and demonstrates skilled employment.",
    "qualification":          "💡 Qualification pillar: Bachelor's = 3pts | Master's/Postgrad = 4pts | PhD = 5pts. NZ qualification adds 1pt.",
    "english_level":          "💡 Required unless client is from NZ, AU, UK, US, Canada, or Ireland. IELTS 6.5+ (no band below 6.5).",
    "family":                 "💡 A partner's qualification or NZ work experience may add bonus points to the application.",
    "currently_in_nz":        "💡 Being in NZ on a valid visa may affect processing options and timing.",
    "salary":                 "💡 Income pillar (2025): $73k-109k = 3pts | $110k-145k = 4pts | $146k-218k = 5pts | $219k+ = 6pts.",
    "nz_work_experience_years": "💡 NZ skilled work experience: 1pt per year, max 3pts. Adds on top of your main pillar score.",
    "anzsco_code":            "💡 The ANZSCO code determines whether the role qualifies as 'skilled'. Check the INZ skills shortage list.",
}
 
def get_realtime_guidance(key: str, value) -> str | None:
    """
    Returns a real-time guidance note based on the answer just given.
    Rule-based — instant, no API call.
    """
    if value is None:
        return None
 
    # Age check
    if key == "age":
        try:
            age = int(value)
            if age > 55:
                return "🔴 **Age alert:** Client is over 55 — does not meet SMC age requirement. Consider alternative pathways."
            elif age >= 50:
                return f"⚠️ **Age note:** Client is {age} — within 5 years of the 55 limit. Timing of lodgement is critical."
            else:
                return f"✅ **Age:** {age} — meets SMC age requirement."
        except:
            return None
 
    # Salary → instant points estimate
    if key == "salary":
        import re
        sal_str = str(value).lower().replace(",", "").replace("$", "").replace("nzd", "").strip()
        # Check for hourly
        if "/hr" in sal_str or "per hour" in sal_str or "hourly" in sal_str:
            nums = re.findall(r'\d+\.?\d*', sal_str)
            if nums:
                hourly = float(nums[0])
                annual = hourly * 2080
                if hourly >= 105:   pts, label = 6, "3x median ✅"
                elif hourly >= 70:  pts, label = 5, "2x median ✅"
                elif hourly >= 52:  pts, label = 4, "1.5x median ✅"
                elif hourly >= 35:  pts, label = 3, "1x median ✅"
                else:               pts, label = 0, "below median ❌"
                return f"💰 **Salary estimate:** ${hourly}/hr (~${annual:,.0f}/yr) = **{label} → {pts} income pillar points**"
        else:
            # Annual salary
            nums = re.findall(r'\d+\.?\d*', sal_str)
            if nums:
                annual = float(nums[0])
                if annual < 1000:  # entered as "80" meaning 80k
                    annual *= 1000
                if annual >= 219000:   pts, label = 6, "3x median ✅"
                elif annual >= 146000: pts, label = 5, "2x median ✅"
                elif annual >= 110000: pts, label = 4, "1.5x median ✅"
                elif annual >= 73000:  pts, label = 3, "1x median ✅"
                else:                  pts, label = 0, "below median ❌"
                hourly = annual / 2080
                return f"💰 **Salary estimate:** ${annual:,.0f}/yr (~${hourly:.2f}/hr) = **{label} → {pts} income pillar points**"
        return None
 
    # Qualification → instant points
    if key == "qualification":
        val = str(value).lower()
        if "phd" in val or "doctor" in val:
            return "🎓 **Qualification:** PhD/Doctorate = **5 points** on qualification pillar ✅"
        elif "master" in val or "postgrad" in val or "honours" in val or "hons" in val:
            return "🎓 **Qualification:** Master's/Postgrad/Honours = **4 points** on qualification pillar ✅"
        elif "bachelor" in val or "degree" in val or "bsc" in val or "ba " in val or "beng" in val:
            return "🎓 **Qualification:** Bachelor's degree = **3 points** on qualification pillar ✅"
        elif "diploma" in val or "certificate" in val:
            return "🎓 **Qualification:** Diploma/Certificate — may not qualify for qualification pillar. Check INZ requirements."
        return None
 
    # NZ work experience → instant points
    if key == "nz_work_experience_years":
        try:
            yrs = int(float(value))
            pts = min(yrs, 3)
            if yrs == 0:
                return "📍 **NZ experience:** 0 years — no NZ experience top-up points."
            else:
                return f"📍 **NZ experience:** {yrs} year(s) = **{pts} bonus point(s)** on top of main pillar ✅"
        except:
            return None
 
    # English level
    if key == "english_level":
        val = str(value).lower()
        exempt = any(c in val for c in ["native", "citizen", "nz", "australian", "british", "american", "canadian", "irish"])
        if exempt:
            return "✅ **English:** Likely exempt from test requirement — confirm citizenship country with client."
        import re
        if "ielts" in val:
            scores = re.findall(r'\d+\.?\d*', val)
            if scores:
                score = float(scores[0])
                if score >= 6.5:
                    return f"✅ **IELTS {score}** — meets the 6.5 minimum requirement."
                else:
                    return f"🔴 **IELTS {score}** — below the 6.5 minimum. Client will need to retest before lodging."
        if "pte" in val:
            scores = re.findall(r'\d+\.?\d*', val)
            if scores:
                score = float(scores[0])
                if score >= 58:
                    return f"✅ **PTE {score}** — meets the 58 minimum requirement."
                else:
                    return f"🔴 **PTE {score}** — below the 58 minimum. Client will need to retest."
        return None
 
    # Occupation — Green List hint
    if key == "occupation":
        from agents.classification_agent import check_green_list
        gl = check_green_list(str(value))
        if gl["on_green_list"]:
            tier = gl["tier"]
            if tier == 1:
                return f"⚡ **Green List Tier 1 detected!** {value.title()} may qualify for Straight to Residence — faster than SMC. LIA must verify ANZSCO code."
            elif tier == 2:
                return f"⚡ **Green List Tier 2 detected!** {value.title()} may qualify for Work to Residence pathway. LIA must verify eligibility."
        return None
 
    return None
 
# ── Live points tracker sidebar ───────────────────────────────────────────────
def render_live_tracker(profile: dict):
    """Shows a live running estimate of SMC points as answers come in."""
    with st.sidebar:
        st.markdown("### 📊 Live Points Estimate")
        st.caption("Updates as you answer each question")
        st.divider()
 
        # Salary points
        import re
        sal_pts = "—"
        sal = str(profile.get("salary", "")).lower().replace(",", "").replace("$", "")
        nums = re.findall(r'\d+\.?\d*', sal)
        if nums:
            annual = float(nums[0])
            if annual < 1000: annual *= 1000
            if "/hr" in sal or "hourly" in sal or "per hour" in sal:
                annual = annual * 2080
            if annual >= 219000:   sal_pts = "6 pts"
            elif annual >= 146000: sal_pts = "5 pts"
            elif annual >= 110000: sal_pts = "4 pts"
            elif annual >= 73000:  sal_pts = "3 pts"
            else:                  sal_pts = "0 pts ❌"
 
        # Qualification points
        qual_pts = "—"
        qual = str(profile.get("qualification", "")).lower()
        if "phd" in qual or "doctor" in qual:        qual_pts = "5 pts"
        elif "master" in qual or "postgrad" in qual or "honours" in qual: qual_pts = "4 pts"
        elif "bachelor" in qual or "degree" in qual: qual_pts = "3 pts"
        elif qual and qual != "none":                qual_pts = "check ⚠️"
 
        # NZ experience points
        nz_pts = "—"
        try:
            yrs = int(float(profile.get("nz_work_experience_years", 0) or 0))
            nz_pts = f"{min(yrs, 3)} pts"
        except: pass
 
        # Age status
        age_ok = "—"
        try:
            age = int(profile.get("age", 0) or 0)
            if age > 0:
                age_ok = "✅ OK" if age <= 55 else "❌ Over limit"
        except: pass
 
        # English status
        eng_ok = "—"
        eng = str(profile.get("english_level", "")).lower()
        nat = str(profile.get("nationality", "")).lower()
        exempt_countries = ["new zealand", "nz", "australia", "australian", "uk", "british",
                           "united states", "usa", "american", "canada", "canadian", "ireland", "irish"]
        if any(c in nat for c in exempt_countries) or "native" in eng or "citizen" in eng:
            eng_ok = "✅ Exempt"
        elif "ielts" in eng or "pte" in eng or "toefl" in eng:
            scores = re.findall(r'\d+\.?\d*', eng)
            if scores:
                score = float(scores[0])
                threshold = 58 if "pte" in eng else 79 if "toefl" in eng else 6.5
                eng_ok = "✅ OK" if score >= threshold else "❌ Too low"
 
        col1, col2 = st.columns(2)
        col1.metric("Income Pillar", sal_pts)
        col2.metric("Qual Pillar", qual_pts)
        col1.metric("NZ Exp Bonus", nz_pts)
        col2.metric("Age", age_ok)
        st.metric("English", eng_ok)
 
        # Green List
        occ = str(profile.get("occupation", ""))
        if occ:
            from agents.classification_agent import check_green_list
            gl = check_green_list(occ)
            if gl["on_green_list"]:
                st.success(f"⚡ Green List Tier {gl['tier']} detected!")
 
        st.divider()
        st.caption("Run full assessment for official score")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🛂 Visa Eligibility")
st.markdown("Skilled Migrant Category (SMC) — Client Assessment")
st.divider()

# ══════════════════════════════════════════════════════════════════════
# PHASE 1 — INTAKE FORM
# ══════════════════════════════════════════════════════════════════════

if not st.session_state.intake_complete:

    st.subheader("📋 Client Intake Form")
    st.caption("Complete all fields and click Submit to run the assessment.")

    with st.form("intake_form"):

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Full Name**")
            full_name = st.text_input("Full Name", label_visibility="collapsed",
                                      placeholder="e.g. Priya Sharma")

            st.markdown("**Nationality / Country of Citizenship**")
            st.caption("💡 NZ, AU, UK, US, CA, IE citizens exempt from English test")
            nationality = st.text_input("Nationality", label_visibility="collapsed",
                                        placeholder="e.g. Indian")

            st.markdown("**Age**")
            st.caption("💡 Must be 55 or under at time of lodgement")
            age = st.number_input("Age", label_visibility="collapsed",
                                  min_value=18, max_value=80, value=30, step=1)

            st.markdown("**Occupation / Job Title**")
            st.caption("💡 Some occupations qualify for Green List faster pathway")
            occupation = st.text_input("Occupation", label_visibility="collapsed",
                                       placeholder="e.g. Software Engineer")

            st.markdown("**ANZSCO Code**")
            st.caption("💡 Determines if role qualifies as skilled under INZ rules")
            anzsco_code = st.text_input("ANZSCO", label_visibility="collapsed",
                                        placeholder="e.g. 261313")

            st.markdown("**Highest Qualification**")
            st.caption("💡 PhD=5pts | Masters=4pts | Bachelors=3pts")
            qualification = st.selectbox("Qualification", label_visibility="collapsed",
                options=[
                    "Select...",
                    "PhD / Doctorate",
                    "Masters / Postgraduate",
                    "Bachelor's / Honours",
                    "Diploma / Certificate",
                    "No formal qualification"
                ])

        with col2:
            st.markdown("**Annual Salary Offered (NZD)**")
            st.caption("💡 $73k-109k=3pts | $110k-145k=4pts | $146k-218k=5pts | $219k+=6pts")
            salary = st.text_input("Salary", label_visibility="collapsed",
                                   placeholder="e.g. 120000 (leave blank if no job offer)")

            st.markdown("**Years of Professional Experience**")
            years_experience = st.number_input("Experience", label_visibility="collapsed",
                                               min_value=0, max_value=50, value=3, step=1)

            st.markdown("**NZ Work Experience (years)**")
            st.caption("💡 1pt per year, max 3pts — adds on top of main pillar")
            nz_work_experience_years = st.number_input("NZ Experience",
                                                        label_visibility="collapsed",
                                                        min_value=0, max_value=20,
                                                        value=0, step=1)

            st.markdown("**English Proficiency**")
            st.caption("💡 IELTS 6.5+ | PTE 58+ | TOEFL 79+ | or exempt if NZ/AU/UK/US/CA/IE")
            english_level = st.text_input("English", label_visibility="collapsed",
                                          placeholder="e.g. IELTS 7.0 or Native speaker")

            st.markdown("**Currently in New Zealand?**")
            currently_in_nz = st.radio("In NZ", ["Yes", "No"],
                                       label_visibility="collapsed", horizontal=True)

            st.markdown("**Family Members in Application?**")
            st.caption("💡 Partner's qualification or NZ experience may add bonus points")
            family = st.text_input("Family", label_visibility="collapsed",
                                   placeholder="e.g. Spouse and 2 children, or None")

        st.divider()
        submitted = st.form_submit_button("🚀 Submit & Run Assessment",
                                          use_container_width=True,
                                          type="primary")

    if submitted:
        # Validate mandatory fields
        errors = []
        if not full_name.strip():
            errors.append("Full Name is required")
        if not nationality.strip():
            errors.append("Nationality is required")
        if qualification == "Select...":
            errors.append("Please select a qualification level")

        if errors:
            for e in errors:
                st.error(e)
        else:
            # Build profile dict — same keys as intake_agent
            profile = {
                "full_name": full_name.strip(),
                "nationality": nationality.strip(),
                "age": age,
                "occupation": occupation.strip(),
                "anzsco_code": anzsco_code.strip() or "unknown",
                "qualification": qualification,
                "job_offer": True,
                "salary": salary.strip() if salary.strip() else "unknown",
                "years_experience": years_experience,
                "nz_work_experience_years": nz_work_experience_years,
                "english_level": english_level.strip() or "unknown",
                "currently_in_nz": currently_in_nz == "Yes",
                "family": family.strip() or "None",
            }

            st.session_state.client_profile = profile
            st.session_state.intake_agent.profile = profile
            st.session_state.intake_complete = True
            st.session_state.active_case_id = None  # new case, not yet saved
            st.session_state.assessment_result = None
            st.rerun()

agent: IntakeAgent = st.session_state.intake_agent
render_live_tracker(st.session_state.client_profile if st.session_state.intake_complete else {})

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
        "job_offer": "NZ Job Offer (Confirmed ✅)",
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
            for key in ["intake_agent", "intake_complete", "assessment_result", 
                        "client_profile", "doc_review_results", "active_case_id"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    with col_b:
        if st.button("🧠 Run SMC Assessment", type="primary", use_container_width=True):
            with st.spinner("Analysing eligibility against INZ SMC rules…"):
                try:
                    result = classify_applicant(profile)
                    #st.write(result["parsed"])
                    st.session_state.assessment_result = result
                    from utils.database import save_case
                    case_id = save_case(profile, result)
                    st.session_state["active_case_id"] = case_id
                    st.success(f"✅ Case saved as **{case_id}**")
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
    green_list = result.get("green_list", {})
    lia_interventions = result.get("lia_interventions", [])
    
    st.subheader("📊 SMC Assessment Results")

    # ── Green List banner (shown ABOVE status — it changes the pathway) ──
    if green_list.get("on_green_list"):
        tier = green_list.get("tier")
        pathway_note = parsed.get("pathway_note", "")
        if tier == 1:
            st.info(f"⚡ **Green List Tier 1 Detected** — {pathway_note}")
        elif tier == 2:
            st.info(f"⚡ **Green List Tier 2 Detected** — {pathway_note}")

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

    # ── LIA Intervention Points ───────────────────────────────────────
    st.subheader("🔐 LIA Mandatory Review Points")
    st.caption("These items require human review by a Licensed Immigration Adviser before lodging.")
 
    if lia_interventions:
        critical = [i for i in lia_interventions if i["severity"] == "CRITICAL"]
        high     = [i for i in lia_interventions if i["severity"] == "HIGH"]
        medium   = [i for i in lia_interventions if i["severity"] == "MEDIUM"]
        low      = [i for i in lia_interventions if i["severity"] == "LOW"]
 
        for item in critical:
            st.error("**CRITICAL — " + item["trigger"] + "**  \n" + item["action"] + "  \n*" + item["reason"] + "*")
        for item in high:
            st.warning("**HIGH — " + item["trigger"] + "**  \n" + item["action"] + "  \n*" + item["reason"] + "*")
        for item in medium:
            st.warning("**MEDIUM — " + item["trigger"] + "**  \n" + item["action"] + "  \n*" + item["reason"] + "*")
        for item in low:
            st.info("**LOW — " + item["trigger"] + "**  \n" + item["action"] + "  \n*" + item["reason"] + "*")
    else:
        st.success("✅ No mandatory LIA interventions identified for this profile.")
 
    st.divider()

    # Raw assessment collapsed
    with st.expander("📄 Full Raw Assessment", expanded=False):
        st.text(raw)

    st.divider()

    # Navigation
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("🔄 New Client", use_container_width=True):
            for key in ["intake_agent", "intake_complete", "assessment_result", 
                        "client_profile", "doc_review_results", "active_case_id"]:
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