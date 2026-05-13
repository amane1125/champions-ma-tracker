import streamlit as st
import pandas as pd
import requests
from sqlalchemy import create_engine

st.set_page_config(
    page_title="Champions M-A Ladder",
    layout="wide"
)

FORMAT_ID = "gen9championsvgc2026regma"

LADDER_URL = (
    "https://pokemonshowdown.com/ladder/"
    f"{FORMAT_ID}.json"
)

engine = create_engine(
    "sqlite:///champions_ma.db"
)

# =========================
# DB
# =========================

def save_ladder(df):

    df.to_sql(
        "ladder",
        engine,
        if_exists="replace",
        index=False
    )

def load_cached_ladder():

    try:

        return pd.read_sql(
            "SELECT * FROM ladder ORDER BY Elo DESC",
            engine
        )

    except:

        return pd.DataFrame()

# =========================
# API
# =========================

@st.cache_data(ttl=300)
def fetch_ladder():

    res = requests.get(
        LADDER_URL,
        timeout=20
    )

    data = res.json()

    if isinstance(data, dict):

        if "toplist" in data:
            data = data["toplist"]

    rows = []

    for i, p in enumerate(data[:100], start=1):

        rows.append({
            "Rank": i,
            "Name": p.get("username", "Unknown"),
            "Elo": p.get("elo", 0),
            "GXE": p.get("gxe", 0)
        })

    df = pd.DataFrame(rows)

    save_ladder(df)

    return df

# =========================
# MAIN
# =========================

st.title(
    "[Gen 9 Champions] VGC 2026 Reg M-A"
)

try:

    ladder_df = fetch_ladder()

except:

    ladder_df = load_cached_ladder()

if ladder_df.empty:

    st.error("Ladder取得失敗")

    st.stop()

# =========================
# SEARCH
# =========================

search = st.text_input(
    "プレイヤー検索"
)

if search:

    ladder_df = ladder_df[
        ladder_df["Name"]
        .str.contains(
            search,
            case=False
        )
    ]

# =========================
# TABLE
# =========================

st.subheader("Top 100 Ladder")

for _, row in ladder_df.iterrows():

    c1, c2, c3, c4, c5 = st.columns(
        [1, 4, 2, 2, 2]
    )

    c1.write(
        f"#{row['Rank']}"
    )

    c2.page_link(
        "pages/player.py",
        label=row["Name"],
        query_params={
            "player": row["Name"]
        }
    )

    c3.write(
        f"{row['Elo']}"
    )

    c4.write(
        f"GXE {row['GXE']}"
    )
