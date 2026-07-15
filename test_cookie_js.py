import streamlit as st
import streamlit.components.v1 as components

def set_cookie_js(name, value, max_age_days=7):
    components.html(f"""
    <script>
        const date = new Date();
        date.setTime(date.getTime() + ({max_age_days} * 24 * 60 * 60 * 1000));
        const expires = "expires=" + date.toUTCString();
        window.parent.document.cookie = "{name}={value};" + expires + ";path=/";
    </script>
    """, height=0, width=0)

st.write("Cookies in st.context:")
if hasattr(st, "context") and hasattr(st.context, "cookies"):
    st.write(st.context.cookies)

if st.button("Set Cookie"):
    set_cookie_js("test_cookie", "hello_world")
    st.write("Cookie set JS injected.")
