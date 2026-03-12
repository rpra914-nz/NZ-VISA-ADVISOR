import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import json
from agents.intake_agent import IntakeAgent

st.set_page_config(
    page_title="NZ Visa Advisor — Client Intake",
    page_icon="📋",
    layout="centered"
)

st.title("📋 Client Intake")
st.caption("Answer each question about your client to build their profile")
st.divider()

# ── INITIALISE AGENT IN SESSION ──────────────────────────────────────
if "intake_agent" not in st.session_state:
    st.session_state.intake_agent = IntakeAgent()
    st.session_state.chat_history = []

agent = st.session_state.intake_agent

# ── SHOW PROGRESS BAR ────────────────────────────────────────────────
st.progress(
    agent.get_progress() / 100,
    text=f"Progress: {agent.get_progress()}%"
)

# ── SHOW CHAT HISTORY ────────────────────────────────────────────────
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── SHOW CURRENT QUESTION OR COMPLETION ──────────────────────────────
if not agent.complete:
    # Show current question
    current_q = agent.get_current_question()

    # Only show question if not already in history
    if not st.session_state.chat_history or \
       st.session_state.chat_history[-1]["content"] != current_q:
        with st.chat_message("assistant"):
            st.markdown(f"**{current_q}**")

    # Get answer from LIA
    if answer := st.chat_input("Type your answer..."):
        # Add to history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": current_q
        })
        st.session_state.chat_history.append({
            "role": "user",
            "content": answer
        })

        # Process answer
        agent.process_answer(answer)
        st.rerun()

else:
    # ── INTAKE COMPLETE ───────────────────────────────────────────
    st.success("✅ Client intake complete!")
    st.divider()

    st.subheader("📊 Client Profile")
    profile = json.loads(agent.get_profile_summary())

    # Display nicely in two columns
    col1, col2 = st.columns(2)
    fields = list(profile.items())
    mid = len(fields) // 2

    with col1:
        for key, value in fields[:mid]:
            st.metric(
                label=key.replace("_", " ").title(),
                value=str(value)
            )

    with col2:
        for key, value in fields[mid:]:
            st.metric(
                label=key.replace("_", " ").title(),
                value=str(value)
            )

    st.divider()

    # Show raw JSON for developers
    with st.expander("🔧 Raw JSON Profile"):
        st.json(profile)

    # Reset button
    if st.button("🔄 Start New Client Intake"):
        st.session_state.intake_agent = IntakeAgent()
        st.session_state.chat_history = []
        st.rerun()