# utils/database.py — SQLite persistence layer: save, load, and search client cases and assessments across sessions.
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "arataki.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id     TEXT PRIMARY KEY,
            full_name   TEXT,
            nationality TEXT,
            status      TEXT,
            created_at  TEXT,
            updated_at  TEXT
        );

        CREATE TABLE IF NOT EXISTS assessments (
            case_id     TEXT PRIMARY KEY,
            profile     TEXT,
            result      TEXT,
            created_at  TEXT,
            FOREIGN KEY (case_id) REFERENCES cases(case_id)
        );

        CREATE TABLE IF NOT EXISTS documents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id     TEXT,
            doc_type    TEXT,
            status      TEXT,
            reviewed_at TEXT,
            FOREIGN KEY (case_id) REFERENCES cases(case_id)
        );
    """)
    conn.commit()
    conn.close()

def generate_case_id() -> str:
    """Generate next sequential case ID e.g. CASE-001."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cases")
    count = c.fetchone()[0]
    conn.close()
    return f"CASE-{str(count + 1).zfill(3)}"

def save_case(profile: dict, assessment: dict) -> str:
    """Save a new case — returns the generated case_id."""
    init_db()
    conn = get_connection()
    c = conn.cursor()

    case_id = generate_case_id()
    now = datetime.now().strftime("%d %b %Y %H:%M")
    status = assessment.get("parsed", {}).get("status", "INCOMPLETE")

    c.execute("""
        INSERT OR REPLACE INTO cases
        (case_id, full_name, nationality, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        case_id,
        profile.get("full_name", "Unknown"),
        profile.get("nationality", "Unknown"),
        status,
        now, now
    ))

    c.execute("""
        INSERT OR REPLACE INTO assessments
        (case_id, profile, result, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        case_id,
        json.dumps(profile),
        json.dumps(assessment.get("parsed", {})),
        now
    ))

    conn.commit()
    conn.close()
    return case_id

def save_documents(case_id: str, doc_review: dict):
    """Save document review results for a case."""
    init_db()
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().strftime("%d %b %Y %H:%M")

    for doc in doc_review.get("checklist", []):
        status = "present" if doc["present"] else "missing"
        c.execute("""
            INSERT INTO documents (case_id, doc_type, status, reviewed_at)
            VALUES (?, ?, ?, ?)
        """, (case_id, doc["label"], status, now))

    conn.commit()
    conn.close()

def get_all_cases() -> list:
    """Return all cases for dashboard."""
    init_db()
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT case_id, full_name, nationality, status, created_at
        FROM cases ORDER BY created_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return [
        {
            "case_id": r[0],
            "full_name": r[1],
            "nationality": r[2],
            "status": r[3],
            "created_at": r[4]
        }
        for r in rows
    ]

def get_case(case_id: str) -> dict:
    """Load a single case by ID."""
    init_db()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT profile, result FROM assessments WHERE case_id=?", (case_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "profile": json.loads(row[0]),
            "parsed": json.loads(row[1])
        }
    return {}

def search_cases(query: str) -> list:
    """Search by case_id or full_name."""
    init_db()
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT case_id, full_name, nationality, status, created_at
        FROM cases
        WHERE case_id LIKE ? OR full_name LIKE ?
        ORDER BY created_at DESC
    """, (f"%{query}%", f"%{query}%"))
    rows = c.fetchall()
    conn.close()
    return [
        {
            "case_id": r[0],
            "full_name": r[1],
            "nationality": r[2],
            "status": r[3],
            "created_at": r[4]
        }
        for r in rows
    ]