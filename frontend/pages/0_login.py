from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from shared import (  # noqa: E402
    MY_BOOKS_PAGE,
    api_request,
    configure_page,
    go_to_page,
    render_hero,
    render_sidebar,
)

configure_page("Login")
render_sidebar("pages/0_login.py", show_logout=False)

if st.session_state.get("token"):
    go_to_page(MY_BOOKS_PAGE)

notice = st.session_state.pop("auth_notice", None)
if notice:
    st.info(notice)

render_hero(
    "Welcome Back to Your Library",
    (
        "Sign in to track your reading, or create an account and jump straight "
        "into your bookshelf."
    ),
    kicker="Authentication",
)

login_tab, register_tab = st.tabs(["Login", "Register"])

with login_tab:
    with st.form("login_form", clear_on_submit=False):
        login_email = st.text_input("Email Address", placeholder="reader@example.com")
        login_password = st.text_input("Password", type="password")
        login_submitted = st.form_submit_button(
            "Login", width="stretch", type="primary"
        )

    if login_submitted:
        if not login_email or not login_password:
            st.error("Please enter both email and password.")
        else:
            try:
                with st.spinner("Signing you in..."):
                    response = api_request(
                        "POST",
                        "/auth/login",
                        auth_required=False,
                        json={"email": login_email.strip(), "password": login_password},
                    )
                st.session_state["token"] = response["access_token"]
                st.toast("Login successful.")
                go_to_page(MY_BOOKS_PAGE)
            except RuntimeError as exc:
                st.error(str(exc))

with register_tab:
    with st.form("register_form", clear_on_submit=False):
        register_email = st.text_input(
            "Email Address", key="register_email", placeholder="reader@example.com"
        )
        register_password = st.text_input(
            "Password", key="register_password", type="password"
        )
        confirm_password = st.text_input(
            "Confirm Password", key="register_confirm_password", type="password"
        )
        register_submitted = st.form_submit_button(
            "Create Account", width="stretch", type="primary"
        )

    if register_submitted:
        if not register_email or not register_password or not confirm_password:
            st.error("Please fill in all registration fields.")
        elif register_password != confirm_password:
            st.error("Passwords do not match.")
        else:
            try:
                with st.spinner("Creating your account..."):
                    api_request(
                        "POST",
                        "/auth/register",
                        auth_required=False,
                        json={
                            "email": register_email.strip(),
                            "password": register_password,
                        },
                    )
                    response = api_request(
                        "POST",
                        "/auth/login",
                        auth_required=False,
                        json={
                            "email": register_email.strip(),
                            "password": register_password,
                        },
                    )
                st.session_state["token"] = response["access_token"]
                st.toast("Account created and signed in.")
                go_to_page(MY_BOOKS_PAGE)
            except RuntimeError as exc:
                st.error(str(exc))
