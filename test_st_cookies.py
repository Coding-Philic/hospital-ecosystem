import streamlit as st

st.write("Cookies from st.context:")
try:
    if hasattr(st, "context") and hasattr(st.context, "cookies"):
        st.write(st.context.cookies)
    else:
        st.write("st.context.cookies not available")
except Exception as e:
    st.write("Error:", e)
