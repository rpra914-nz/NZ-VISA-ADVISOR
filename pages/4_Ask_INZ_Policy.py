import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from agents.rag_agent import load_inz_webpage, build_vector_store, retrieve, ask_claude

st.set_page_config(
    page_title="Ask INZ Policy",
    page_icon="❓",
    layout="centered"
)

if st.button("← Back to Home"):
    st.switch_page("Home.py")

st.title("❓ Ask INZ Policy")
st.caption("Questions answered from live INZ documentation")
st.divider()

@st.cache_resource(ttl=86400)
def initialise():
    url = "https://www.immigration.govt.nz/visas/skilled-migrant-category-resident-visa/"
    chunks = load_inz_webpage(url)
    collection = build_vector_store(chunks)
    return collection

with st.spinner("Loading INZ documents..."):
    collection = initialise()

st.success("✅ INZ documents loaded. Ask your question below!")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if query := st.chat_input("e.g. What documents do I need?"):
    st.session_state.messages.append({
        "role": "user",
        "content": query
    })
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Searching INZ documents..."):
            chunks_retrieved, pages = retrieve(collection, query)
            answer = ask_claude(query, chunks_retrieved, pages)
        st.markdown(answer)
        with st.expander("📄 Source sections used"):
            for i, chunk in enumerate(chunks_retrieved):
                st.markdown(f"**Section {pages[i]}**")
                st.caption(chunk[:300] + "...")

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })