import streamlit as st
import time
from streamlit_cookies_controller import CookieController

st.write("Testing cookies")

if "cookie_controller" not in st.session_state:
    st.session_state.cookie_controller = CookieController()

c = st.session_state.cookie_controller
cookies = c.getAll()

if st.button("Set Cookie"):
    c.set("my_cookie", "my_value")
    # st.switch_page won't work in single page script but we can simulate it with rerun
    st.write("Cookie set command issued")
    st.rerun()

st.write("Cookies:", cookies)
