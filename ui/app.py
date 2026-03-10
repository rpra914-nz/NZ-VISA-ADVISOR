

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from agents.rag_agent import load_inz_webpage, build_vector_store, retrieve, ask_claude

# ── PAGE CONFIG ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="NZ Visa Advisor",
    page_icon="🛂",
    layout="centered"
)

st.title("🛂 NZ Visa Advisor")
st.caption("Ask anything about the Skilled Migrant visa — powered by official INZ documents")
st.divider()

# ── LOAD VECTOR STORE ONCE ───────────────────────────────────────────
@st.cache_resource
def initialise():
    url = "https://www.immigration.govt.nz/visas/skilled-migrant-category-resident-visa/"
    chunks = load_inz_webpage(url)
    collection = build_vector_store(chunks)
    return collection

with st.spinner("Loading INZ documents..."):
    collection = initialise()

st.success("✅ INZ documents loaded. Ask your question below!")

# ── CHAT HISTORY ─────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── CHAT INPUT ───────────────────────────────────────────────────────
if query := st.chat_input("e.g. What documents do I need?"):
    
    # Show user message
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Get answer
    with st.chat_message("assistant"):
        with st.spinner("Searching INZ documents..."):
            chunks_retrieved, pages = retrieve(collection, query)
            answer = ask_claude(query, chunks_retrieved, pages)
        
        st.markdown(answer)
        
        # Show source pages
        with st.expander("📄 Source pages used"):
            for i, chunk in enumerate(chunks_retrieved):
                st.markdown(f"**Page {pages[i]}**")
                st.caption(chunk[:300] + "...")
    
    st.session_state.messages.append({"role": "assistant", "content": answer})
    