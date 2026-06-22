"""Fußball-Daten: Re-Export-Modul für Rückwärtskompatibilität.

Die eigentliche Logik liegt in den spezifischen Modulen:
  - get_bundesliga_data.py       → Bundesliga (Vereinsspiele + Tabelle)
  - get_champions_league_data.py → Champions League
  - get_dfb_pokal_data.py        → DFB-Pokal
  - get_wm_data.py               → WM 2026

Dieses Modul exportiert alle öffentlichen Funktionen unter dem
bisherigen Namen, damit bestehende Imports unverändert bleiben.
"""

from .get_bundesliga_data import (
    fetch_team_matches,
    fetch_bundesliga_table,
    fetch_bvb_matches,
    get_team_logo_path,
    TEAM_LOGO_MAPPING,
)
from .get_champions_league_data import fetch_cl_data, fetch_cl_ligaphase_table
from .get_dfb_pokal_data import fetch_dfb_data
from .get_wm_data import fetch_wm_data

__all__ = [
    "fetch_team_matches",
    "fetch_bundesliga_table",
    "fetch_bvb_matches",
    "get_team_logo_path",
    "TEAM_LOGO_MAPPING",
    "fetch_cl_data",
    "fetch_cl_ligaphase_table",
    "fetch_dfb_data",
    "fetch_wm_data",
]
