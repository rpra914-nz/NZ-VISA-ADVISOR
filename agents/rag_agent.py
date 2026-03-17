import os
import chromadb
import anthropic
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

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
        if len(text) > 50:
            chunks.append({
                "text": text,
                "page": i + 1
            })
    
    print(f"✅ Extracted {len(chunks)} text chunks from webpage")
    return chunks


# ── 2. STORE IN CHROMADB ─────────────────────────────────────────────
def build_vector_store(chunks):
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


# ── 3. RETRIEVE RELEVANT CHUNKS ──────────────────────────────────────
def retrieve(collection, query, n=3):
    results = collection.query(
        query_texts=[query],
        n_results=n
    )
    chunks = results["documents"][0]
    pages = [m["page"] for m in results["metadatas"][0]]
    return chunks, pages


# ── 4. ASK CLAUDE ────────────────────────────────────────────────────
def ask_claude(query, chunks, pages):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    context = "\n\n".join([
        f"[Section {pages[i]}]:\n{chunks[i]}" 
        for i in range(len(chunks))
    ])
    
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""You are an NZ immigration assistant. 
Answer the question using ONLY the context below.
Always cite the section number you got the answer from.

CONTEXT:
{context}

QUESTION: {query}"""
            }
        ]
    )
    return message.content[0].text


# ── 5. MAIN ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    url = "https://www.immigration.govt.nz/visas/skilled-migrant-category-resident-visa/"
    chunks = load_inz_webpage(url)
    collection = build_vector_store(chunks)
    
    print("\n🔍 Testing RAG pipeline...\n")
    query = "What documents do I need for a skilled migrant visa?"
    chunks_retrieved, pages = retrieve(collection, query)
    answer = ask_claude(query, chunks_retrieved, pages)
    
    print(f"Q: {query}")
    print(f"\nA: {answer}")