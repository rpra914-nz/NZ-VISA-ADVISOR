import os
import json
import anthropic
from dotenv import load_dotenv
 
load_dotenv()
 
# ── GREEN LIST OCCUPATIONS ────────────────────────────────────────────
# Source: INZ Green List (Tier 1 = straight to residence; Tier 2 = work-to-residence)
# Last updated: 2025. LIA must verify against current INZ Green List.
GREEN_LIST_TIER1 = {
    # Health
    "medical officer": "Green List Tier 1 — eligible for straight-to-residence pathway",
    "specialist physician": "Green List Tier 1 — eligible for straight-to-residence pathway",
    "psychiatrist": "Green List Tier 1 — eligible for straight-to-residence pathway",
    "general practitioner": "Green List Tier 1 — eligible for straight-to-residence pathway",
    "gp": "Green List Tier 1 — eligible for straight-to-residence pathway",
    "surgeon": "Green List Tier 1 — eligible for straight-to-residence pathway",
    "anaesthetist": "Green List Tier 1 — eligible for straight-to-residence pathway",
    "radiologist": "Green List Tier 1 — eligible for straight-to-residence pathway",
    "obstetrician": "Green List Tier 1 — eligible for straight-to-residence pathway",
    # Engineering & IT
    "civil engineer": "Green List Tier 1 — eligible for straight-to-residence pathway",
    "structural engineer": "Green List Tier 1 — eligible for straight-to-residence pathway",
    "electrical engineer": "Green List Tier 1 — eligible for straight-to-residence pathway",
    "software engineer": "Green List Tier 1 — eligible for straight-to-residence pathway",
    "software developer": "Green List Tier 1 — eligible for straight-to-residence pathway",
    "ict security specialist": "Green List Tier 1 — eligible for straight-to-residence pathway",
}
 
GREEN_LIST_TIER2 = {
    # Education
    "teacher": "Green List Tier 2 — work-to-residence pathway available (2-year Accredited Employer Work Visa first)",
    "secondary school teacher": "Green List Tier 2 — work-to-residence pathway available",
    "primary school teacher": "Green List Tier 2 — work-to-residence pathway available",
    "early childhood teacher": "Green List Tier 2 — work-to-residence pathway available",
    # Health
    "registered nurse": "Green List Tier 2 — work-to-residence pathway available",
    "nurse": "Green List Tier 2 — work-to-residence pathway available",
    "midwife": "Green List Tier 2 — work-to-residence pathway available",
    "pharmacist": "Green List Tier 2 — work-to-residence pathway available",
    "physiotherapist": "Green List Tier 2 — work-to-residence pathway available",
    "occupational therapist": "Green List Tier 2 — work-to-residence pathway available",
    "social worker": "Green List Tier 2 — work-to-residence pathway available",
    # Trades
    "plumber": "Green List Tier 2 — work-to-residence pathway available",
    "electrician": "Green List Tier 2 — work-to-residence pathway available",
    "carpenter": "Green List Tier 2 — work-to-residence pathway available",
    "construction manager": "Green List Tier 2 — work-to-residence pathway available",
    "chef": "Green List Tier 2 — work-to-residence pathway available",
    # Vet
    "veterinarian": "Green List Tier 2 — work-to-residence pathway available",
    "vet": "Green List Tier 2 — work-to-residence pathway available",
}
 
def check_green_list(occupation: str) -> dict:
    """
    Returns Green List status for a given occupation.
    Matches on partial/lowercase occupation string.
    """
    occ_lower = occupation.lower().strip()
 
    for keyword, description in GREEN_LIST_TIER1.items():
        if keyword in occ_lower or occ_lower in keyword:
            return {
                "on_green_list": True,
                "tier": 1,
                "pathway": "straight_to_residence",
                "description": description,
                "lia_action": (
                    "⚡ Green List Tier 1 detected. LIA must verify the specific ANZSCO code "
                    "against the current INZ Green List before advising the Straight to Residence pathway. "
                    "Registration requirements vary by occupation."
                )
            }
 
    for keyword, description in GREEN_LIST_TIER2.items():
        if keyword in occ_lower or occ_lower in keyword:
            return {
                "on_green_list": True,
                "tier": 2,
                "pathway": "work_to_residence",
                "description": description,
                "lia_action": (
                    "⚡ Green List Tier 2 detected. LIA must verify: (1) ANZSCO code match on current "
                    "INZ Green List, (2) whether client has or can obtain an Accredited Employer Work Visa, "
                    "(3) 2-year qualifying period requirement, (4) registration requirements for this occupation."
                )
            }
 
    return {
        "on_green_list": False,
        "tier": None,
        "pathway": "smc_standard",
        "description": "Occupation not detected on Green List — standard SMC pathway applies",
        "lia_action": None
    }
 
 
# ── LIA INTERVENTION POINTS ───────────────────────────────────────────
# Defines exactly where a Licensed Immigration Adviser must review before proceeding.
 
def get_lia_interventions(profile: dict, parsed: dict, green_list_result: dict) -> list:
    """
    Returns a list of LIA intervention points based on the full assessment.
    These are mandatory human review steps — not suggestions.
    """
    interventions = []
 
    # 1. Green List occupation found
    if green_list_result["on_green_list"]:
        interventions.append({
            "trigger": "Green List Occupation",
            "severity": "HIGH",
            "action": green_list_result["lia_action"],
            "reason": f"Occupation '{profile.get('occupation')}' may qualify for a faster pathway than SMC."
        })
 
    # 2. Age borderline (50–55)
    age = profile.get("age")
    try:
        age = int(age)
        if 50 <= age <= 55:
            interventions.append({
                "trigger": "Age Near Threshold",
                "severity": "HIGH",
                "action": "Verify client's exact age and confirm they will be under 56 at time of application lodgement. Calculate processing timeline carefully.",
                "reason": f"Client is {age} — SMC age limit is 55. Timing is critical."
            })
        elif age > 55:
            interventions.append({
                "trigger": "Exceeds Age Limit",
                "severity": "CRITICAL",
                "action": "Client exceeds the SMC age limit of 55. Do not proceed with SMC without confirming an exemption applies. Consider alternative pathways.",
                "reason": f"Client is {age} years old. SMC requires applicants to be 55 or under."
            })
    except (TypeError, ValueError):
        pass
 
    # 3. Points borderline (exactly 6 or 7)
    try:
        total_pts = int(parsed.get("total_points", 0))
        if total_pts == 6:
            interventions.append({
                "trigger": "Borderline Points Score",
                "severity": "MEDIUM",
                "action": "Client meets minimum threshold exactly. LIA should review all supporting evidence carefully and consider whether additional points could be claimed before lodging.",
                "reason": "Minimum 6-point threshold met exactly — any documentation gap could make the application fail."
            })
    except (TypeError, ValueError):
        pass
 
    # 4. Unknown or low salary
    salary = str(profile.get("salary", "")).lower()
    if salary in ["unknown", "", "0", "none"]:
        interventions.append({
            "trigger": "Salary Not Confirmed",
            "severity": "MEDIUM",
            "action": "Obtain confirmed salary/hourly rate from employer offer letter before assessing income pillar. Points calculation is inaccurate without this.",
            "reason": "Income is one of the three main scoring pillars — an unconfirmed salary means points may be under- or over-stated."
        })
 
    # 5. No job offer
    if not profile.get("job_offer"):
        interventions.append({
            "trigger": "No Accredited Employer Job Offer",
            "severity": "HIGH",
            "action": "SMC requires a skilled job offer from an INZ-accredited employer. LIA must confirm employer has accreditation before lodging. If no offer exists, advise client to secure employment first.",
            "reason": "A job offer from an accredited employer is a mandatory requirement for SMC."
        })
 
    # 6. ANZSCO code unknown
    anzsco = str(profile.get("anzsco_code", "")).lower()
    if anzsco in ["unknown", "", "none", "n/a"]:
        interventions.append({
            "trigger": "ANZSCO Code Unconfirmed",
            "severity": "MEDIUM",
            "action": "Confirm the correct ANZSCO code for client's occupation before assessing. The code determines whether the role qualifies as 'skilled' under INZ rules and affects points.",
            "reason": "Incorrect ANZSCO classification can invalidate the entire SMC points claim."
        })
 
    # 7. English language — check exemption first, then score
    import re
    english = str(profile.get("english_level", "")).lower()
    nationality = str(profile.get("nationality", "")).lower()
 
    # Countries whose citizens are exempt from English evidence requirements
    ENGLISH_EXEMPT_COUNTRIES = {
        "new zealand", "nz", "kiwi",
        "australia", "australian",
        "united kingdom", "uk", "british", "england", "scotland", "wales",
        "united states", "usa", "us", "american",
        "canada", "canadian",
        "ireland", "irish",
    }
 
    is_exempt = any(c in nationality for c in ENGLISH_EXEMPT_COUNTRIES) or                 any(c in english for c in ["native", "citizen", "nz citizen", "australian citizen"])
 
    if is_exempt:
        pass  # No English intervention needed — exempt nationality
    elif "ielts" in english or "pte" in english or "toefl" in english or "oet" in english:
        scores = re.findall(r'\d+\.?\d*', english)
        if scores:
            score = float(scores[0])
            # IELTS threshold 6.5, PTE threshold 58, TOEFL 79
            threshold = 6.5
            if "pte" in english:
                threshold = 58
            elif "toefl" in english:
                threshold = 79
            if score < threshold:
                interventions.append({
                    "trigger": "English Score Below Threshold",
                    "severity": "HIGH",
                    "action": "Client's English score appears to be below the minimum required for SMC. Advise retesting. IELTS 6.5+ (no band below 6.5), PTE 58+, TOEFL 79+, OET Grade B+.",
                    "reason": f"Detected score {score} — below the {threshold} threshold for the test type identified."
                })
    elif english in ["", "unknown", "none"]:
        interventions.append({
            "trigger": "English Evidence Not Provided",
            "severity": "MEDIUM",
            "action": "Confirm English language evidence before lodging. If client is from NZ, AU, UK, US, CA, or Ireland — they are exempt. Otherwise require IELTS 6.5+, PTE 58+, TOEFL 79+, or OET Grade B+.",
            "reason": "English requirements must be satisfied or exemption confirmed."
        })
    # If they said something like "fluent" or "good" — low priority note only
    else:
        interventions.append({
            "trigger": "English Evidence Unclear",
            "severity": "LOW",
            "action": "Clarify English evidence type. If from an exempt country (NZ/AU/UK/US/CA/IE) no test needed. Otherwise obtain official test results: IELTS 6.5+, PTE 58+, TOEFL 79+, OET B+.",
            "reason": f"English level recorded as '{english}' — INZ requires specific evidence or confirmed exemption."
        })
 
    return interventions
 
 
# ── POINTS RULES ─────────────────────────────────────────────────────
# Based on current INZ SMC 6-point system (2025/2026)
 
QUALIFICATION_POINTS = {
    "phd": 5,
    "doctorate": 5,
    "masters": 4,
    "master": 4,
    "postgraduate": 4,
    "honours": 4,
    "bachelors": 3,
    "bachelor": 3,
    "degree": 3,
    "diploma": 0,
    "certificate": 0
}
 
INCOME_POINTS = {
    "3x_median": 6,   # $105+/hr
    "2x_median": 5,   # $70-104/hr
    "1.5x_median": 4, # $52-69/hr
    "1x_median": 3,   # $35-51/hr
    "below_median": 0
}
 
NZ_EXPERIENCE_POINTS_PER_YEAR = 1
MAX_NZ_EXPERIENCE_POINTS = 3
 
 
# ── CLASSIFICATION AGENT ─────────────────────────────────────────────
def classify_applicant(profile: dict) -> dict:
    """
    Takes applicant profile JSON from intake agent
    Returns eligibility assessment with points breakdown
    """

    # ── Pre-flight consistency fixes (BEFORE sending to Claude) ──────
    profile = dict(profile)  # don't mutate caller's dict

    has_job_offer = profile.get("job_offer")
    salary = str(profile.get("salary", "")).lower().strip()
    salary_provided = salary not in ["", "unknown", "none", "null", "0", "n/a"]
    _pre_flags = []

    # No job offer + salary given → zero it out before Claude sees it
    if has_job_offer is False and salary_provided:
        _pre_flags.append(
            "Input inconsistency: Salary provided but no NZ job offer exists. "
            "Salary has been excluded from scoring. LIA must clarify with client."
        )
        profile["salary"] = "N/A — no job offer"

    # Tell Claude explicitly so it cannot award income points
    if has_job_offer is False:
        profile["job_offer_note"] = (
            "CLIENT HAS NO NZ JOB OFFER. "
            "Do NOT award any income pillar points. "
            "Status MUST be NOT_ELIGIBLE regardless of other factors."
        )

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": f"""You are an expert NZ immigration eligibility assessor.

Analyse this applicant profile and assess their eligibility for the 
Skilled Migrant Category (SMC) Resident Visa.

CURRENT SMC RULES (2025/2026):
- Need minimum 6 points total
- Choose ONE main pillar (qualification, occupational registration, or income)
- ALWAYS choose the pillar that gives the HIGHEST points
- Example: if income gives 3pts and qualification gives 0pts, use income pillar
- Diploma/Certificate = 0 qualification points — never use as pillar, use income instead
- Can add up to 3 points from NZ skilled work experience
- MANDATORY: Must have skilled job offer from accredited NZ employer
  If job_offer is False or missing → status MUST be NOT_ELIGIBLE regardless of points
  State this clearly in gaps: "No job offer — mandatory SMC requirement not met"
- Must be 55 or under
- Must meet English language requirements UNLESS exempt:
  EXEMPT (no test needed): Citizens of NZ, Australia, UK, USA, Canada, Ireland, or someone educated for 5+ years in English in those countries
  If NOT exempt: IELTS 6.5+ (no band below 6.5), PTE Academic 58+, TOEFL iBT 79+, OET Grade B+
  If nationality suggests exempt country — note the exemption, do NOT require a test score

POINTS FOR QUALIFICATIONS (overseas):
- PhD/Doctorate: 5 points
- Masters/Postgraduate: 4 points  
- Bachelors/Honours: 3 points
- Below degree level: 0 points
- NZ qualification gets 1 extra point

POINTS FOR INCOME (annual NZD salary, 2025 median ~$73,000/yr):
- 3x median = $219,000+/yr  OR $105+/hr  → 6 points
- 2x median = $146,000–218,999/yr  OR $70–104/hr  → 5 points
- 1.5x median = $109,500–145,999/yr  OR $52–69/hr  → 4 points
- 1x median = $73,000–109,499/yr  OR $35–51/hr  → 3 points
- Below median = under $73,000/yr OR under $35/hr  → 0 points

IMPORTANT: Salary may be given as annual (e.g. "$80,000" or "80k") OR hourly.
Convert annual to hourly by dividing by 2080 (40hrs x 52wks).
Examples: $80k/yr = $38.46/hr = 3pts | $100k/yr = $48.08/hr = 3pts | $120k/yr = $57.69/hr = 4pts | $150k/yr = $72.12/hr = 5pts

CRITICAL SALARY RULE: $100,000/yr = $48/hr = above $35/hr threshold = 3 points (1x median). Do NOT say it is below median.
Only flag salary as a gap if it is genuinely BELOW $73,000/yr.

NZ WORK EXPERIENCE TOP-UP:
- 1 point per year in NZ (max 3 points)

APPLICANT PROFILE:
{json.dumps(profile, indent=2)}
CRITICAL: Respond in PLAIN TEXT only. No markdown, no ## headers, no ** bold, no --- dividers.
Format your response exactly as shown below with no additional formatting.

Respond in this EXACT format:
RECOMMENDED_VISA: [visa name or "Not currently eligible"]
POINTS_FROM_PILLAR: [number]
PILLAR_USED: [qualification/income/registration]
NZ_EXPERIENCE_POINTS: [number]
TOTAL_POINTS: [number]
THRESHOLD: 6
STATUS: [ELIGIBLE/LIKELY_ELIGIBLE/NOT_ELIGIBLE]
CONFIDENCE: [HIGH/MEDIUM/LOW]

STRENGTHS:
- [strength 1]
- [strength 2]

GAPS:
- [gap 1]
- [gap 2]

RECOMMENDED_ACTIONS:
- [action 1]
- [action 2]

RISK_FLAGS:
- [flag 1 or "None"]

DISCLAIMER: This is an automated assessment tool for Licensed Immigration 
Advisers only. All recommendations must be verified against current INZ 
policy before lodging any application."""
            }
        ]
    )

    raw_response = message.content[0].text
    result = parse_classification_response(raw_response, profile)

    # ── Attach pre-flight flags to result ────────────────────────────
    if _pre_flags:
        existing_flags = result["parsed"].get("risk_flags", [])
        result["parsed"]["risk_flags"] = _pre_flags + existing_flags

    # ── Hard mandatory rule overrides (never trust LLM for these) ────
    if not profile.get("job_offer"):
        result["parsed"]["status"] = "NOT_ELIGIBLE"
        gaps = result["parsed"].get("gaps", [])
        job_offer_gap = "No job offer from an accredited NZ employer — this is a mandatory SMC requirement. Client cannot lodge without it."
        if not any("job offer" in g.lower() for g in gaps):
            gaps.insert(0, job_offer_gap)
        result["parsed"]["gaps"] = gaps
        risks = result["parsed"].get("risk_flags", [])
        risks.insert(0, "CRITICAL: No accredited employer job offer — application cannot proceed.")
        result["parsed"]["risk_flags"] = risks

    # Age hard limit — over 55 = NOT_ELIGIBLE
    try:
        age = int(profile.get("age", 0) or 0)
        if age > 55:
            result["parsed"]["status"] = "NOT_ELIGIBLE"
            gaps = result["parsed"].get("gaps", [])
            gaps.insert(0, f"Client is {age} years old — exceeds the SMC age limit of 55.")
            result["parsed"]["gaps"] = gaps
    except (TypeError, ValueError):
        pass

    # ── Green List check ─────────────────────────────────────────────
    occupation = profile.get("occupation", "")
    green_list_result = check_green_list(occupation)
    result["green_list"] = green_list_result

    # ── LIA intervention points ───────────────────────────────────────
    lia_interventions = get_lia_interventions(profile, result["parsed"], green_list_result)
    result["lia_interventions"] = lia_interventions

    # ── Override pathway if Green List detected ───────────────────────
    if green_list_result["on_green_list"]:
        tier = green_list_result["tier"]
        if tier == 1:
            result["parsed"]["recommended_pathway"] = "straight_to_residence"
            result["parsed"]["pathway_note"] = (
                f"Green List Tier 1: {occupation.title()} may qualify for the "
                "Straight to Residence pathway — faster than SMC. LIA must verify ANZSCO code."
            )
        elif tier == 2:
            result["parsed"]["recommended_pathway"] = "work_to_residence"
            result["parsed"]["pathway_note"] = (
                f"Green List Tier 2: {occupation.title()} may qualify for the "
                "Work to Residence pathway via Accredited Employer Work Visa. "
                "LIA must verify eligibility and 2-year qualifying period."
            )
    else:
        result["parsed"]["recommended_pathway"] = "smc_standard"
        result["parsed"]["pathway_note"] = None

    return result
 
 
# ── PARSE RESPONSE ───────────────────────────────────────────────────
def _extract_bullets(lines: list, start_index: int) -> list:
    """Extract bullet point lines starting from start_index until next section."""
    items = []
    for line in lines[start_index:]:
        stripped = line.strip()
        if stripped.startswith("-"):
            clean = stripped.lstrip("- ").strip()
            items.append(clean)
        elif stripped == "" or stripped == "---":
            continue
        elif any(stripped.startswith(k) for k in [
            "RECOMMENDED_VISA:", "POINTS_FROM_PILLAR:", "PILLAR_USED:",
            "NZ_EXPERIENCE_POINTS:", "TOTAL_POINTS:", "THRESHOLD:",
            "STATUS:", "CONFIDENCE:", "STRENGTHS:", "GAPS:",
            "RECOMMENDED_ACTIONS:", "RISK_FLAGS:", "DISCLAIMER:"
        ]):
            break
    return items
 
 
def parse_classification_response(raw: str, profile: dict) -> dict:
    """Parses Claude's structured response into a clean dict — including all sections."""
 
    # Strip markdown formatting Claude sometimes adds despite instructions
    import re
    raw = re.sub(r'\*\*([^*]+)\*\*', r'\1', raw)   # remove **bold**
    raw = re.sub(r'^#{1,3}\s*', '', raw, flags=re.MULTILINE)  # remove ## headers
    raw = re.sub(r'^---+$', '', raw, flags=re.MULTILINE)      # remove --- dividers
    lines = raw.strip().split("\n")
    result = {
        "profile": profile,
        "raw_assessment": raw,
        "parsed": {}
    }
 
    for i, line in enumerate(lines):
        stripped = line.strip()
 
        # ── Single-value fields ──
        if stripped.startswith("RECOMMENDED_VISA:"):
            result["parsed"]["visa"] = stripped.split(":", 1)[1].strip()
 
        elif stripped.startswith("POINTS_FROM_PILLAR:"):
            result["parsed"]["pillar_points"] = stripped.split(":", 1)[1].strip()
 
        elif stripped.startswith("PILLAR_USED:"):
            result["parsed"]["pillar"] = stripped.split(":", 1)[1].strip()
 
        elif stripped.startswith("NZ_EXPERIENCE_POINTS:"):
            result["parsed"]["nz_experience_points"] = stripped.split(":", 1)[1].strip()
 
        elif stripped.startswith("TOTAL_POINTS:"):
            result["parsed"]["total_points"] = stripped.split(":", 1)[1].strip()
 
        elif stripped.startswith("STATUS:"):
            result["parsed"]["status"] = stripped.split(":", 1)[1].strip()
 
        elif stripped.startswith("CONFIDENCE:"):
            result["parsed"]["confidence"] = stripped.split(":", 1)[1].strip()
 
        # ── Multi-line bullet sections ──
        elif stripped.startswith("STRENGTHS:"):
            result["parsed"]["strengths"] = _extract_bullets(lines, i + 1)
 
        elif stripped.startswith("GAPS:"):
            result["parsed"]["gaps"] = _extract_bullets(lines, i + 1)
 
        elif stripped.startswith("RECOMMENDED_ACTIONS:"):
            result["parsed"]["recommended_actions"] = _extract_bullets(lines, i + 1)
 
        elif stripped.startswith("RISK_FLAGS:"):
            result["parsed"]["risk_flags"] = _extract_bullets(lines, i + 1)
 
    return result
 
 
# ── TEST ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
 
    test_profile = {
        "nationality": "indian",
        "age": 29,
        "occupation": "graduate engineer",
        "job_offer": False,
        "years_experience": 2,
        "qualification": "bachelors",
        "english_level": "pte 8",
        "family": "child",
        "currently_in_nz": False
    }
 
    print("🧠 Running classification agent...")
    print("=" * 50)
 
    result = classify_applicant(test_profile)
 
    print("\n📊 PARSED SUMMARY:")
    print(f"  Visa:         {result['parsed'].get('visa')}")
    print(f"  Pillar:       {result['parsed'].get('pillar')}")
    print(f"  Points:       {result['parsed'].get('total_points')}/6")
    print(f"  Status:       {result['parsed'].get('status')}")
    print(f"  Confidence:   {result['parsed'].get('confidence')}")
    print(f"  Strengths:    {result['parsed'].get('strengths')}")
    print(f"  Gaps:         {result['parsed'].get('gaps')}")
    print(f"  Actions:      {result['parsed'].get('recommended_actions')}")
    print(f"  Risk Flags:   {result['parsed'].get('risk_flags')}")