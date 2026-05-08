import streamlit as st
from agents.rag_agent import load_multiple_pages, build_vector_store
from utils.urls import INZ_URLS

@st.cache_resource(ttl=86400)
def get_collection():
    chunks = load_multiple_pages(INZ_URLS)
    collection = build_vector_store(chunks)
    return collection, chunks