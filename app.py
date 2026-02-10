import re
import pandas as pd
import streamlit as st
from flask import Flask, render_template
from data_sources.bvb_matches import fetch_bvb_matches

app = Flask(__name__)

@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/football')
def display_matches():
    matches = fetch_bvb_matches()
    return render_template('matches.html', matches=matches)

@app.route('/formula1')
def formula1_placeholder():
    return render_template('placeholder.html', sport="Formula 1")

@app.route('/american_football')
def american_football_placeholder():
    return render_template('placeholder.html', sport="American Football")

if __name__ == '__main__':
    app.run(debug=True)

# ---------- Seiteneinstellungen ----------
st.set_page_config(page_title="Sports Dashboard", layout="wide")
st.title("Mein Sports Dashboard")

# ---------- Haupt-Tabs (erweiterbar) ----------
tab_bvb, tab_f1, tab_chiefs = st.tabs(["⚽ Borussia Dortmund", "🏎 Formel 1", "🏈 Kansas City Chiefs"])

# =======================
# TAB: BORUSSIA DORTMUND
# =======================
with tab_bvb:
    st.header("Borussia Dortmund")

    sub_spielplan, sub_injuries, sub_stats = st.tabs(["📅 Spielplan", "Verletztenliste", "📊 Statistiken"])

    # ---- Spielplan ----
    with sub_spielplan:
        st.subheader("Spielplan nach Wettbewerb")

        matches_by_comp = fetch_bvb_matches() or {}

        if not matches_by_comp:
            st.warning("Aktuell keine Spieldaten gefunden.")
        else:
            # Filter-Optionen
            col1, col2 = st.columns([1, 2])
            with col1:
                show_only_upcoming = st.checkbox("Nur kommende Spiele", value=False)
            with col2:
                st.caption("Tipp: Nutze die Spaltensuche in der Tabelle, um Gegner zu filtern.")

            comp_names = list(matches_by_comp.keys())
            comp_tabs = st.tabs(comp_names)

            for i, comp in enumerate(comp_names):
                with comp_tabs[i]:
                    df = pd.DataFrame(matches_by_comp[comp]) if matches_by_comp[comp] else pd.DataFrame(columns=["Datum", "Teams", "Ergebnis"])

                    if df.empty:
                        st.info("Keine Daten verfügbar.")
                        continue

                    # Datum extrahieren & sortieren (z. B. 'Di, 17.06.2025' -> '17.06.2025')
                    if "Datum" in df.columns:
                        extracted = df["Datum"].astype(str).str.extract(r"(\d{2}\.\d{2}\.\d{4})", expand=False)
                        df["_Datum_parsed"] = pd.to_datetime(extracted, format="%d.%m.%Y", errors="coerce")

                        # Optional: nur kommende Spiele
                        if show_only_upcoming:
                            today = pd.Timestamp.now().normalize()
                            df = df[df["_Datum_parsed"].isna() | (df["_Datum_parsed"] >= today)]

                        df = df.sort_values("_Datum_parsed", na_position="last").drop(columns=["_Datum_parsed"])

                    # Anzeige mit schmalen/spitzen Spalten
                    st.dataframe(
                        df,
                        width='stretch',
                        column_config={
                            "Datum": st.column_config.TextColumn("Datum", width="small"),
                            "Teams": st.column_config.TextColumn("Teams", width="large"),
                            "Ergebnis": st.column_config.TextColumn("Ergebnis", width="small"),
                        }
                    )

    # ---- Verletztenliste ----
    #with sub_injuries:
        st.subheader("Aktuelle Verletztenliste")

    # ---- Statistiken ----
    with sub_stats:
        st.subheader("Spieler-Statistiken (Beta)")

# =======================
# TAB: FORMEL 1 (Platzhalter)
# =======================
with tab_f1:
    st.header("Formel 1")
    st.info("Demnächst: Rundenzeiten, Boxenstopps, Quali vs. Rennen – Daten via Ergast API.")

# =======================
# TAB: KANSAS CITY CHIEFS (Platzhalter)
# =======================
with tab_chiefs:
    st.header("Kansas City Chiefs")
    st.info("Demnächst: Spielplan, Spieler- und Team-Stats – Daten via ESPN/NFL Scraping oder API.")
