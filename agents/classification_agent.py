import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

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
- Can add up to 3 points from NZ skilled work experience
- Must have skilled job offer from accredited NZ employer
- Must be 55 or under
- Must meet English language requirements (IELTS 6.5+ or equivalent)
- Must meet health and character requirements

POINTS FOR QUALIFICATIONS (overseas):
- PhD/Doctorate: 5 points
- Masters/Postgraduate: 4 points  
- Bachelors/Honours: 3 points
- Below degree level: 0 points
- NZ qualification gets 1 extra point

POINTS FOR INCOME:
- 3x median wage ($105+/hr): 6 points
- 2x median wage ($70-104/hr): 5 points
- 1.5x median wage ($52-69/hr): 4 points
- 1x median wage ($35-51/hr): 3 points

NZ WORK EXPERIENCE TOP-UP:
- 1 point per year in NZ (max 3 points)

APPLICANT PROFILE:
{json.dumps(profile, indent=2)}

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