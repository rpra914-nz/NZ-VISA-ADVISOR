"""
document_review_agent.py
Analyses uploaded client PDFs for SMC visa applications.
- Identifies document type using Claude
- Checks each doc against INZ SMC requirements
- Returns structured checklist: ✅ ⚠️ ❌
"""

import os
import json
import anthropic
import pypdf

# ── INZ SMC required document matrix ────────────────────────────────────────
SMC_REQUIRED_DOCS = {
    "passport": {
        "label": "Passport (valid)",
        "required": True,
        "notes": "Must be valid for at least 3 months beyond intended stay. All pages visible.",
    },
    "job_offer": {
        "label": "Job Offer / Employment Contract",
        "required": True,
        "notes": "Must be from an accredited NZ employer. Include role title, salary, and hours.",
    },
    "qualification": {
        "label": "Academic Qualification(s)",
        "required": True,
        "notes": "Degree, diploma, or trade certificate. May need NZQA evaluation.",
    },
    "police_clearance": {
        "label": "Police Clearance Certificate",
        "required": True,
        "notes": "From every country lived in for 12+ months in the past 10 years.",
    },
    "medical": {
        "label": "Medical / Health Certificate",
        "required": True,
        "notes": "Completed by an INZ-approved panel physician.",
    },
    "bank_statement": {
        "label": "Bank Statement (funds evidence)",
        "required": False,
        "notes": "Recommended to show settlement funds. Usually 3 months of statements.",
    },
    "ielts_english": {
        "label": "English Language Evidence (IELTS / equivalent)",
        "required": False,
        "notes": "Required if not from a visa-waiver country or education not in English.",
    },
    "cv_resume": {
        "label": "CV / Résumé",
        "required": False,
        "notes": "Recommended to support skills and experience claims.",
    },
    "reference_letter": {
        "label": "Reference / Experience Letter",
        "required": False,
        "notes": "Employer references supporting work experience claims.",
    },
    "unknown": {
        "label": "Unknown Document",
        "required": False,
        "notes": "Could not identify this document type.",
    },
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def extract_pdf_text(uploaded_file) -> str:
    """Extract text from an uploaded Streamlit file object using pypdf."""
    try:
        reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        return f"[PDF extraction error: {e}]"


def classify_document(client: anthropic.Anthropic, filename: str, text_snippet: str) -> dict:
    """
    Ask Claude to identify the document type and assess it against INZ requirements.
    Returns a dict with: doc_type, label, status, issues, suggestions
    """
    valid_types = ", ".join(SMC_REQUIRED_DOCS.keys())
    snippet = text_snippet[:3000] if len(text_snippet) > 3000 else text_snippet

    prompt = f"""You are an expert NZ immigration document reviewer helping a Licensed Immigration Adviser (LIA).

A client has uploaded a document for their Skilled Migrant Category (SMC) residence visa application.

File name: {filename}

Document text (first 3000 chars):
\"\"\"
{snippet}
\"\"\"

Your tasks:
1. Identify the document type. Choose EXACTLY ONE from: {valid_types}
2. Assess whether this document meets INZ SMC requirements.
3. List any issues or missing information.
4. Provide concise suggestions for the client.

Respond ONLY with valid JSON (no markdown, no preamble) in this exact format:
{{
  "doc_type": "<one of the valid types above>",
  "status": "<one of: ok | warning | error>",
  "summary": "<one sentence describing what this document is>",
  "issues": ["<issue 1>", "<issue 2>"],
  "suggestions": ["<suggestion 1>", "<suggestion 2>"]
}}

Rules:
- status = "ok" → document looks complete and meets INZ requirements
- status = "warning" → document present but may have issues (expiry, missing details, etc.)
- status = "error" → document is incomplete, wrong type, or clearly inadequate
- If text is too short or unreadable, set status = "warning" and explain in issues.
"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown fences if Claude adds them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "doc_type": "unknown",
            "status": "error",
            "summary": "Could not parse Claude's response.",
            "issues": ["Document analysis failed. Please try again."],
            "suggestions": ["Re-upload the document or check that it is a readable PDF."],
        }

    # Merge in static INZ requirement info
    doc_meta = SMC_REQUIRED_DOCS.get(result.get("doc_type", "unknown"), SMC_REQUIRED_DOCS["unknown"])
    result["label"] = doc_meta["label"]
    result["required"] = doc_meta["required"]
    result["inz_notes"] = doc_meta["notes"]
    result["filename"] = filename

    return result


# ── Main entry point ─────────────────────────────────────────────────────────

def review_documents(uploaded_files: list) -> dict:
    """
    Process a list of Streamlit uploaded file objects.
    Returns a structured review result with per-doc analysis and overall checklist.
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    reviewed = []
    seen_types = set()

    for uf in uploaded_files:
        text = extract_pdf_text(uf)
        uf.seek(0)  # reset file pointer after reading
        result = classify_document(client, uf.name, text)
        result["word_count"] = len(text.split())
        reviewed.append(result)
        seen_types.add(result["doc_type"])

    # Build checklist: which required docs are present / missing
    checklist = []
    for doc_type, meta in SMC_REQUIRED_DOCS.items():
        if doc_type == "unknown":
            continue
        present = doc_type in seen_types
        checklist.append({
            "doc_type": doc_type,
            "label": meta["label"],
            "required": meta["required"],
            "present": present,
            "status": "ok" if present else ("error" if meta["required"] else "warning"),
        })

    required_missing = [c for c in checklist if c["required"] and not c["present"]]
    all_required_present = len(required_missing) == 0

    return {
        "reviewed_docs": reviewed,
        "checklist": checklist,
        "required_missing": required_missing,
        "all_required_present": all_required_present,
        "total_uploaded": len(uploaded_files),
    }