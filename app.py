import streamlit as st

st.set_page_config(
    page_title="Análise de Dados Musicais",
    layout="wide"
)
# Define the pages
main_page = st.Page("main.py", title="Início", icon="🎈")
page_2 = st.Page("page2.py", title="Finanças", icon="❄️")
page_3 = st.Page("page3.py", title="Geocoding", icon="🎉")
page_4 = st.Page("pythonbanco.py", title="Banco", icon="🎵")

# Set up navigation
pg = st.navigation([main_page, page_2, page_3, page_4])

# Run the selected page
pg.run()