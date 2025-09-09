import re
import pandas as pd
import streamlit as st
from data_sources import *

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

        matches_by_comp = bvb.get_bvb_matches() or {}

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
    with sub_injuries:
        st.subheader("Aktuelle Verletztenliste")

        injuries = bvb.get_bvb_injuries()
        # Egal ob Liste oder DataFrame – in DataFrame bringen
        if isinstance(injuries, list):
            injuries_df = pd.DataFrame(injuries)
        else:
            injuries_df = injuries.copy() if injuries is not None else pd.DataFrame()

        if injuries_df is None or injuries_df.empty:
            st.info("Aktuell keine Verletzten (oder Daten nicht verfügbar).")
        else:
            # Spaltennamen angleichen/umsortieren, falls vorhanden
            preferred_order = ["Spieler", "Verletzung", "Seit", "Voraussichtlich bis"]
            cols = [c for c in preferred_order if c in injuries_df.columns] + [c for c in injuries_df.columns if c not in preferred_order]
            injuries_df = injuries_df[cols]

            st.dataframe(
                injuries_df,
                width='stretch',
                column_config={
                    "Spieler": st.column_config.TextColumn("Spieler", width="large"),
                    "Verletzung": st.column_config.TextColumn("Verletzung", width="large"),
                    "Seit": st.column_config.TextColumn("Seit", width="small"),
                    "Voraussichtlich bis": st.column_config.TextColumn("Voraussichtlich bis", width="small"),
                }
            )

    # ---- Statistiken ----
    with sub_stats:
        st.subheader("Spieler-Statistiken (Beta)")
        # Optionaler Hook: nur anzeigen, wenn vorhanden
        if hasattr(bvb, "get_player_stats") and callable(getattr(bvb, "get_player_stats")):
            try:
                stats_df = bvb.get_player_stats()
            except Exception:
                stats_df = pd.DataFrame()

            if stats_df is None or stats_df.empty:
                st.info("Noch keine Statistiken verfügbar.")
            else:
                st.dataframe(
                    stats_df,
                    width='stretch',
                    column_config={
                        "Spieler": st.column_config.TextColumn("Spieler", width="large"),
                    }
                )
                # Kleine Balkenansicht, sofern Tore/Vorlagen existieren
                numeric_cols = [c for c in ["Tore", "Vorlagen"] if c in stats_df.columns]
                if numeric_cols:
                    st.bar_chart(stats_df.set_index("Spieler")[numeric_cols])
        else:
            st.info("Statistik-Funktion wird später ergänzt.")

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
