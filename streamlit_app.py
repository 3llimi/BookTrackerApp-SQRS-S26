from __future__ import annotations

import streamlit as st

from frontend.shared import LOGIN_PAGE, MY_BOOKS_PAGE, configure_page, go_to_page

configure_page("Home")
go_to_page(MY_BOOKS_PAGE if st.session_state.get("token") else LOGIN_PAGE)
