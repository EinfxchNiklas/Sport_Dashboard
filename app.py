import streamlit as st
import pandas as pd
from data_sources import bvb


st.set_page_config(page_title="Sports Dashboard", layout="wide")

st.title("🟡⚫ Borussia Dortmund Dashboard")

tab1, tab2 = st.tabs(["📅 Spielplan", " Verletztenliste"])

with tab1:
    st.subheader("Nächste Spiele")
    df_fixtures = bvb.get_bvb_fixtures()
    if df_fixtures.empty:
        st.warning("Keine Daten gefunden.")
    else:
        st.dataframe(df_fixtures, use_container_width=True)

with tab2:
    st.subheader("Aktuelle Verletztenliste")
    df_injuries = bvb.get_bvb_injuries()
    if df_injuries.empty:
        st.info("Aktuell keine Verletzten (oder Daten nicht verfügbar).")
    else:
        st.dataframe(df_injuries, use_container_width=True)
