import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime
from sqlalchemy import create_engine

st.set_page_config(
    page_title="Champions M-A Tracker",
    layout="wide"
)

# =========================
# CONFIG
# =========================

FORMAT_ID = "gen9championsvgc2026regma"

LADDER_URL = (
    "https://pokemonshowdown.com/ladder/"
    f"{FORMAT_ID}.json"
)

REPLAY_SEARCH_URL = (
    "https://replay.pokemonshowdown.com/search/"
)

DB_PATH = "sqlite:///champions_ma.db"

engine = create_engine(DB_PATH)

# =========================
# DATABASE
# =========================

def save_ladder(df):
    df.to_sql(
        "ladder",
        engine,
        if_exists="replace",
        index=False
    )

def load_ladder():
    try:
        return pd.read_sql(
            "SELECT * FROM ladder ORDER BY Elo DESC",
            engine
        )
    except:
        return pd.DataFrame()

def append_ladder_history(df):
    df["timestamp"] = datetime.now()

    df.to_sql(
        "ladder_history",
        engine,
        if_exists="append",
        index=False
    )

def save_replays(df):
    df.to_sql(
        "replays",
        engine,
        if_exists="append",
        index=False
    )

# =========================
# API
# =========================

@st.cache_data(ttl=300)
def fetch_ladder():

    res = requests.get(LADDER_URL, timeout=20)
    data = res.json()

    if isinstance(data, dict):
        if "toplist" in data:
            data = data["toplist"]

    rows = []

    for i, p in enumerate(data[:100], start=1):

        wins = p.get("w", 0)
        losses = p.get("l", 0)

        total = wins + losses

        if total > 0:
            winrate = round((wins / total) * 100, 1)
        else:
            winrate = 0

        rows.append({
            "Rank": i,
            "Name": p.get("username", "Unknown"),
            "Elo": p.get("elo", 0),
            "Wins": wins,
            "Losses": losses,
            "Winrate": winrate
        })

    df = pd.DataFrame(rows)

    save_ladder(df)
    append_ladder_history(df)

    return df

@st.cache_data(ttl=300)
def fetch_replays(username):

    params = {
        "user": username,
        "format": FORMAT_ID,
        "output": "json"
    }

    try:

        r = requests.get(
            REPLAY_SEARCH_URL,
            params=params,
            timeout=20
        )

        data = r.json()

        if not isinstance(data, list):
            return []

        return data

    except:
        return []

@st.cache_data(ttl=300)
def fetch_replay_log(replay_id):

    url = (
        "https://replay.pokemonshowdown.com/"
        f"{replay_id}.log"
    )

    try:

        r = requests.get(url, timeout=20)

        if r.status_code != 200:
            return ""

        return r.text

    except:
        return ""

# =========================
# TEAM EXTRACTION
# =========================

POKE_REGEX = r"\|poke\|p1\|([^,\n]+)"

def extract_team(log_text):

    mons = re.findall(POKE_REGEX, log_text)

    unique = []

    for mon in mons:
        if mon not in unique:
            unique.append(mon)

    return unique[:6]

# =========================
# REPLAY DATE
# =========================

def get_last_replay_date(username):

    replays = fetch_replays(username)

    if len(replays) == 0:
        return "No Replay"

    latest = replays[0]

    uploadtime = latest.get("uploadtime")

    if not uploadtime:
        return "Unknown"

    try:

        dt = datetime.fromtimestamp(uploadtime)

        return dt.strftime("%Y-%m-%d")

    except:
        return "Unknown"

# =========================
# LOAD DATA
# =========================

st.title("[Gen 9 Champions] VGC 2026 Reg M-A")

ladder_df = fetch_ladder()

if ladder_df.empty:

    st.error("Ladder取得失敗")

    cached = load_ladder()

    if cached.empty:
        st.stop()

    ladder_df = cached

# =========================
# LAST REPLAY
# =========================

with st.spinner("Replay情報取得中..."):

    replay_dates = []

    for name in ladder_df["Name"]:

        replay_dates.append(
            get_last_replay_date(name)
        )

    ladder_df["Last Replay"] = replay_dates

# =========================
# TOP TABLE
# =========================

st.subheader("Top 100 Ladder")

selected_player = st.selectbox(
    "プレイヤー選択",
    ladder_df["Name"].tolist()
)

st.dataframe(
    ladder_df,
    use_container_width=True,
    hide_index=True
)

# =========================
# PLAYER DETAIL
# =========================

st.divider()

player_row = ladder_df[
    ladder_df["Name"] == selected_player
].iloc[0]

st.header(selected_player)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Rank", int(player_row["Rank"]))

c2.metric("Elo", int(player_row["Elo"]))

c3.metric(
    "Winrate",
    f"{player_row['Winrate']}%"
)

c4.metric(
    "Record",
    f"{player_row['Wins']}-{player_row['Losses']}"
)

# =========================
# REPLAYS
# =========================

replays = fetch_replays(selected_player)

st.subheader("Replay一覧")

if len(replays) == 0:

    st.info("公開Replayなし")

else:

    replay_rows = []

    for replay in replays:

        replay_id = replay.get("id", "")

        if not replay_id:
            continue

        replay_url = (
            "https://replay.pokemonshowdown.com/"
            f"{replay_id}"
        )

        rating = replay.get("rating", "?")

        uploadtime = replay.get("uploadtime")

        if uploadtime:

            date_text = datetime.fromtimestamp(
                uploadtime
            ).strftime("%Y-%m-%d %H:%M")

        else:

            date_text = "Unknown"

        log_text = fetch_replay_log(replay_id)

        team = extract_team(log_text)

        replay_rows.append({
            "player": selected_player,
            "replay_id": replay_id,
            "url": replay_url,
            "rating": rating,
            "date": date_text,
            "team": " / ".join(team)
        })

        with st.container(border=True):

            st.markdown(
                f"### [{replay_id}]({replay_url})"
            )

            st.write(f"**Rate:** {rating}")

            st.write(f"**Date:** {date_text}")

            if len(team) > 0:

                st.write("### Team")

                st.write(" / ".join(team))

            else:

                st.write("構築取得失敗")

    if len(replay_rows) > 0:

        replay_df = pd.DataFrame(replay_rows)

        save_replays(replay_df)

# =========================
# HISTORY GRAPH
# =========================

st.divider()

st.subheader("レート履歴")

try:

    history_df = pd.read_sql(
        f"""
        SELECT *
        FROM ladder_history
        WHERE Name = '{selected_player}'
        ORDER BY timestamp
        """,
        engine
    )

    if not history_df.empty:

        chart_df = history_df[
            ["timestamp", "Elo"]
        ].set_index("timestamp")

        st.line_chart(chart_df)

except:
    pass
