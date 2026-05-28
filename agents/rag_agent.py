import os
import chromadb
import anthropic
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from rank_bm25 import BM25Okapi  # keyword search
import re

from utils.urls import INZ_URLS
n_results = max(5, len(INZ_URLS))  # at least 1 chunk per URL

load_dotenv()

# ── 1. SCRAPE INZ WEBPAGE ────────────────────────────────────────────
def load_inz_webpage(url):
    print(f"🌐 Fetching: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}")
        return []  # return empty, handle gracefully upstream
    
    #response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Remove nav/footer noise
    for tag in soup(["nav", "footer", "script", "style"]):
        tag.decompose()
    
    # Get all text blocks
    chunks = []
    for i, section in enumerate(soup.find_all(["p", "li", "h2", "h3"])):
        text = section.get_text(strip=True)
        if len(text) > 100:
            chunks.append({
                "text": text,
                "page": i + 1
            })
    
    print(f"✅ Extracted {len(chunks)} text chunks from webpage")
    return chunks


# ── 2. STORE IN CHROMADB ─────────────────────────────────────────────
def build_vector_store(chunks):
    if not chunks:
        raise ValueError(
            "No content scraped from INZ URLs. "
            "Check your internet connection and that immigration.govt.nz is reachable."
        )
    client = chromadb.PersistentClient(path=".chroma")
    
    try:
        client.delete_collection("visa_docs")
    except:
        pass
    
    collection = client.create_collection("visa_docs")
    
    collection.add(
        documents=[c["text"] for c in chunks],
        metadatas=[{"page": c["page"]} for c in chunks],
        ids=[f"page_{c['page']}" for c in chunks]
    )
    print(f"✅ Stored {len(chunks)} chunks in ChromaDB")
    return collection

# ── 3. LOAD MULTIPLE PAGES ───────────────────────────────────────────────
def load_multiple_pages(urls):
    all_chunks = []
    chunk_counter = 0
    for url in urls:
        chunks = load_inz_webpage(url)
        for chunk in chunks:
            chunk["page"] = chunk_counter + 1
            chunk["url"] = url  # track source URL per chunk
            chunk_counter += 1
        all_chunks.extend(chunks)
    print(f"✅ Total chunks from {len(urls)} pages: {len(all_chunks)}")
    return all_chunks

# ── KEYWORD SEARCH (BM25) ─────────────────────────────────────────────
# Finds chunks with exact word/term matches (e.g. "clause 4.2", "160 points")
# Complements semantic search which finds meaning but may miss exact terms
def bm25_retrieve(all_chunks, query, n=3):
    tokenized_corpus = [c["text"].lower().split() for c in all_chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    # Get top n indices sorted by score
    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:n]
    return [all_chunks[i] for i in top_indices]

# ── CONFLICT DETECTION ────────────────────────────────────────────────
# Checks if retrieved chunks contradict each other on key thresholds
# e.g. one chunk says "6 points" another says "160 points"
# Flags conflict so LIA knows to manually verify before advising client
def detect_conflicts(chunks):
    # Key terms that could have conflicting values in INZ policy
    conflict_patterns = [
        r"\b\d+\s*points\b",        # e.g. "6 points" vs "160 points"
        r"\bielts\s*\d+\.?\d*\b",   # e.g. "IELTS 6.5" vs "IELTS 7.0"
        r"\$\d+[\d,]*",             # e.g. "$35/hr" vs "$52/hr"
        r"\b\d+\s*years?\b",        # e.g. "2 years" vs "5 years"
    ]

    found_values = {}  # pattern → list of values found across chunks
    conflicts = []

    for pattern in conflict_patterns:
        matches_per_chunk = [
            re.findall(pattern, chunk.lower())
            for chunk in chunks
        ]
        # Flatten all matches for this pattern
        all_matches = [m for matches in matches_per_chunk for m in matches]
        unique_values = set(all_matches)

        # If more than one unique value found → potential conflict
        if len(unique_values) > 1:
            conflicts.append({
                "pattern": pattern,
                "values_found": list(unique_values),
                "message": f"⚠️ Conflicting values detected: {', '.join(unique_values)}"
            })

    return conflicts

# ── QUERY EXPANSION ───────────────────────────────────────────────────
# Rewrites user query into better search terms before retrieval
# Fixes mismatch between casual questions and policy document language
def expand_query(query: str) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": f"""Rewrite this question as 3 different search phrases 
that would match NZ immigration policy document language.
Return ONLY the 3 phrases separated by newlines, nothing else.

Question: {query}"""
        }]
    )
    expanded = message.content[0].text.strip()
    # Combine original + expanded for maximum coverage
    return query + " " + " ".join(expanded.split("\n"))

# ── 4. HYBRID RETRIEVE ───────────────────────────────────────────────────
# Combines semantic search (ChromaDB) + keyword search (BM25)
# Semantic = finds meaning, BM25 = finds exact terms
# Merged results = better coverage than either alone
def retrieve(collection, query, n=n_results, all_chunks=None):
    # --- Semantic search (ChromaDB embeddings) ---
    expanded = expand_query(query)
    semantic_results = collection.query(
    query_texts=[query],
    n_results=n,
    include=["documents", "metadatas", "distances"]
)
    semantic_chunks = semantic_results["documents"][0]
    semantic_pages = [m["page"] for m in semantic_results["metadatas"][0]]
    semantic_distances = semantic_results["distances"][0]
    avg_distance = sum(semantic_distances) / len(semantic_distances) if semantic_distances else 1.0

    # --- Keyword search (BM25) ---
    keyword_chunks = []
    keyword_pages = []
    if all_chunks:
        bm25_results = bm25_retrieve(all_chunks, query, n=n)
        keyword_chunks = [c["text"] for c in bm25_results]
        keyword_pages = [c["page"] for c in bm25_results]

    # --- Merge results (deduplicate by text) ---
    seen = set()
    merged_chunks = []
    merged_pages = []
    for chunk, page in zip(
        semantic_chunks + keyword_chunks,
        semantic_pages + keyword_pages
    ):
        if chunk not in seen:
            seen.add(chunk)
            merged_chunks.append(chunk)
            merged_pages.append(page)

    # --- Conflict detection ---
    conflicts = detect_conflicts(merged_chunks)

    # Confidence: distance 0=perfect, 2=worst. Convert to 0-100% score.
    confidence_score = max(0, round((1 - avg_distance / 2) * 100))
    return merged_chunks, merged_pages, conflicts, confidence_score


# ── 5. ASK CLAUDE ────────────────────────────────────────────────────
def ask_claude(query, chunks, pages, conflicts=None):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    context = "\n\n".join([
        f"[Section {pages[i]}]:\n{chunks[i]}" 
        for i in range(len(chunks))
    ])

    # Warn Claude if conflicts were detected
    conflict_warning = ""
    if conflicts:
        conflict_warning = "\n⚠️ CONFLICT WARNING: The retrieved sections may contain contradictory information. Flag this in your response and advise the LIA to verify manually.\n"

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""You are an NZ immigration assistant helping a Licensed Immigration Adviser (LIA).
Answer the question using ONLY the context below.
Always cite the section number you got the answer from.
If the exact answer is not explicitly stated, infer it from the available context and clearly label it as an inference.
If the context is genuinely insufficient, say so and suggest the LIA verify directly with INZ.
Never say you don't know if the answer can be reasonably inferred from the context.
Use plain text formatting only — do not use markdown headers (no # or ##). Use bold (**text**) and bullet points only.
{conflict_warning}
CONTEXT:
{context}

QUESTION: {query}"""
            }
        ]
    )
    return message.content[0].text


# ── 6. MAIN ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    from utils.urls import INZ_URLS

    chunks = load_multiple_pages(INZ_URLS)
    collection = build_vector_store(chunks)
    
    print("\n🔍 Testing RAG pipeline...\n")
    query = "What documents do I need for a skilled migrant visa?"
    chunks_retrieved, pages, conflicts = retrieve(collection, query, all_chunks=chunks)
    if conflicts:
        print(f"\n⚠️ Conflicts detected: {[c['message'] for c in conflicts]}")
    answer = ask_claude(query, chunks_retrieved, pages, conflicts)
        
    print(f"Q: {query}")
    print(f"\nA: {answer}")