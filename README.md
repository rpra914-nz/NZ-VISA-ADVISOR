# 🛂 NZ Visa Advisor

> AI-powered Skilled Migrant Category assessment tool for New Zealand Licensed Immigration Advisers (LIAs).

Built as a COMPSCI 703 project at the University of Auckland. Combines a multi-agent AI pipeline with live INZ policy retrieval to help LIAs assess client eligibility, review supporting documents, and generate client-ready PDF reports — faster and more consistently than manual review.

---

## ⚠️ Disclaimer

This tool is intended **for use by Licensed Immigration Advisers only**. It does not constitute legal or immigration advice. All AI-generated assessments must be verified by a qualified LIA against current INZ policy before lodging any application. Immigration New Zealand makes all final decisions.

---

## ✨ Features

| Page | What it does |
|------|-------------|
| 🧠 **Visa Eligibility** | Guided 13-question intake → SMC 6-point scoring → strengths, gaps, actions, risk flags |
| 📄 **Document Review** | Upload client PDFs → INZ SMC checklist with ✅ ⚠️ ❌ per document |
| 📋 **Full Report** | One-click A4 PDF combining profile, points breakdown, and document checklist |
| ❓ **Ask INZ Policy** | RAG chatbot grounded in live INZ documentation with conflict detection |

**Key technical highlights:**
- Hybrid retrieval (BM25 + ChromaDB semantic search) for policy Q&A
- Query expansion via Claude before retrieval — fixes mismatch between casual questions and policy language
- Green List occupation detection (Tier 1 straight-to-residence / Tier 2 work-to-residence)
- LIA intervention points — flags exactly where human review is mandatory
- Conflict detection across 4 patterns: points, IELTS, salary, years of experience

---

## 🏗️ Architecture

```
Home.py                         ← Streamlit entry point, RAG warm-up
│
├── pages/
│   ├── 1_Visa_Eligibility.py   ← 3-phase UI: intake → review → results
│   ├── 2_Document_Review.py    ← Multi-PDF upload and checklist
│   ├── 3_Full_Report.py        ← PDF generation and download
│   └── 4_Ask_INZ_Policy.py     ← RAG chatbot
│
├── agents/
│   ├── intake_agent.py         ← 13-question conversational intake (Claude)
│   ├── classification_agent.py ← SMC 6-point scoring + Green List detection
│   ├── rag_agent.py            ← Hybrid BM25 + ChromaDB retrieval
│   ├── document_review_agent.py← PDF extraction + INZ doc checklist
│   └── report_agent.py         ← ReportLab A4 PDF generation
│
└── utils/
    ├── urls.py                 ← Single source of truth for 5 INZ URLs
    └── cache.py                ← st.cache_resource wrapper (TTL 24h)
```

**Data flow:**

```
Client details → intake_agent → classification_agent → session_state
                                                              ↓
Uploaded PDFs → document_review_agent ──────────────→ report_agent → PDF
                                                              ↑
INZ URLs → BeautifulSoup scraper → BM25 + ChromaDB → rag_agent → answer
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

### Installation

```bash
git clone https://github.com/rpra914-nz/NZ-VISA-ADVISOR.git
cd NZ-VISA-ADVISOR

python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=sk-ant-...
```

### Run

```bash
py -m streamlit run Home.py        # Windows
python -m streamlit run Home.py    # macOS / Linux
```

The app will open at `http://localhost:8501`. On first load, the RAG pipeline scrapes INZ documentation (~15 seconds). Subsequent loads use the 24-hour cache.

---

## 📁 Project Structure

```
NZ-VISA-ADVISOR/
├── Home.py
├── requirements.txt
├── .env                        ← not committed (add to .gitignore)
├── agents/
│   ├── __init__.py
│   ├── intake_agent.py
│   ├── classification_agent.py
│   ├── rag_agent.py
│   ├── document_review_agent.py
│   └── report_agent.py
├── pages/
│   ├── 1_Visa_Eligibility.py
│   ├── 2_Document_Review.py
│   ├── 3_Full_Report.py
│   └── 4_Ask_INZ_Policy.py
└── utils/
    ├── urls.py
    └── cache.py
```

---

## 🔑 Session State Keys

| Key | Set by | Used by |
|-----|--------|---------|
| `client_profile` | `intake_agent` | `classification_agent`, `report_agent`, page 1, page 3 |
| `assessment_result` | `classification_agent` | `report_agent`, page 1, page 3 |
| `doc_review_results` | `document_review_agent` | `report_agent`, page 2, page 3 |
| `rag_initialised` | `Home.py` | `Home.py` (prevents re-warm on nav) |
| `rag_error` | `cache.py` | `Home.py`, page 4 |

---

## 🤖 AI Model

All agents use **Claude Haiku** (`claude-haiku-4-5-20251001`) via the Anthropic API — chosen for speed and cost efficiency in a multi-agent pipeline. The RAG agent uses an additional query-expansion call before retrieval.

---

## 🗂️ INZ Sources

Policy content is scraped at runtime from:

- [Skilled Migrant Category Resident Visa](https://www.immigration.govt.nz/visas/skilled-migrant-category-resident-visa/)
- [Permanent Resident Visa](https://www.immigration.govt.nz/visas/permanent-resident-visa/)
- [Becoming a Permanent Resident](https://www.immigration.govt.nz/live/resident-visas-to-live-in-new-zealand/permanent-residence/becoming-a-permanent-resident-of-new-zealand/)
- [Check or Change Resident Visa Conditions](https://www.immigration.govt.nz/live/resident-visas-to-live-in-new-zealand/check-or-change-your-resident-visa-conditions/)
- [All Resident Visas Overview](https://www.immigration.govt.nz/live/resident-visas-to-live-in-new-zealand/)

> If the app cannot reach these URLs (network/firewall), the Ask INZ Policy page will be disabled. All other pages remain functional.

---

## 🛠️ Tech Stack

| Component | Library |
|-----------|---------|
| UI | Streamlit 1.55 |
| AI | Anthropic Claude (claude-haiku-4-5) |
| Vector DB | ChromaDB 1.5.4 |
| Keyword search | rank-bm25 |
| Web scraping | BeautifulSoup4, requests |
| PDF generation | ReportLab 4.2.5 |
| PDF reading | pypdf 4.3.1 |
| Env config | python-dotenv |

---

## 📋 Pending (Week 7+)

- [ ] Streamlit Cloud deployment
- [ ] Evaluation script (`tests/evaluate.py`)
- [ ] Architecture diagram (SVG)
- [ ] UI polish — Home.py layout gaps
- [ ] Extended Green List coverage
- [ ] Formal LIA intervention workflow

---

## 👩‍💻 Authors

Built by **Praveena** as part of COMPSCI 703 — Advanced Topics in AI, University of Auckland, 2025.

---

## 📄 License

For academic use only. Not licensed for commercial deployment.
