import streamlit as st
from agents.rag_agent import load_multiple_pages, build_vector_store
from utils.urls import INZ_URLS

@st.cache_resource(ttl=86400)
def get_collection():
    """
    Scrapes INZ URLs, builds ChromaDB + returns (collection, all_chunks).
    Returns (None, []) with an error message stored in session state if scraping fails.
    """
    try:
        chunks = load_multiple_pages(INZ_URLS)
        if not chunks:
            st.session_state["rag_error"] = (
                "⚠️ Could not load INZ policy pages — all URLs returned empty. "
                "Check your internet connection. The Ask INZ Policy page will be unavailable."
            )
            return None, []
        collection = build_vector_store(chunks)
        return collection, chunks
    except Exception as e:
        st.session_state["rag_error"] = (
            f"⚠️ RAG pipeline failed to initialise: {e}. "
            "The Ask INZ Policy page will be unavailable until this is resolved."
        )