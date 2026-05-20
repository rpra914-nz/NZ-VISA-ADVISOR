# utils/auth.py
import streamlit as st

# ── Credentials (hardcoded for demo — move to DB for production) ──────
USERS = {
    "lia_admin": {
        "password": "arataki2025",
        "name": "LIA Administrator",
        "firm": "Arataki Immigration Advisers"
    },
    "praveena": {
        "password": "demo123",
        "name": "Praveena Ravishankar",
        "firm": "University of Auckland — Demo"
    }
}

def check_login() -> bool:
    """
    Shows login form if not authenticated.
    Returns True if logged in, False if not.
    Call at top of every page — if returns False, call st.stop().
    """
    if st.session_state.get("authenticated"):
        return True

    st.markdown("## 🛂 Arataki Adviser")
    st.markdown("#### Licensed Immigration Adviser Portal")
    st.divider()

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        user = USERS.get(username.strip().lower())
        if user and user["password"] == password:
            st.session_state["authenticated"] = True
            st.session_state["user_name"] = user["name"]
            st.session_state["user_firm"] = user["firm"]
            st.rerun()
        else:
            st.error("Invalid username or password.")

    st.caption("For demo: username `lia_admin` / password `arataki2025`")
    return False

def logout():
    """Call from a logout button."""
    for key in ["authenticated", "user_name", "user_firm"]:
        st.session_state.pop(key, None)
    st.rerun()