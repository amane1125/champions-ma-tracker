import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime
from sqlalchemy import create_engine

st.set_page_config(
    page_title="Champions M-A Ladder",
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
    "https://replay.pokemonshowdown.com/search.json"
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

@st.cache_data(ttl=300)
def fetch_replays(username):

    params = {
        "user": username,
        "format": FORMAT_ID
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
def fetch_log(replay_id):

    url = (
        "https://replay.pokemonshowdown.com/"
        f"{replay_id}.log"
    )

    try:

        r = requests.get(
            url,
            timeout=20
        )

        if r.status_code != 200:
            return ""

        return r.text

    except:

        return ""

# =========================
# TEAM EXTRACTION
# =========================

P1_REGEX = r"\|poke\|p1\|([^,\n]+)"
P2_REGEX = r"\|poke\|p2\|([^,\n]+)"

def extract_teams(log_text):

    p1 = re.findall(
        P1_REGEX,
        log_text
    )

    p2 = re.findall(
        P2_REGEX,
        log_text
    )

    p1_unique = []
    p2_unique = []

    for mon in p1:

        if mon not in p1_unique:
            p1_unique.append(mon)

    for mon in p2:

        if mon not in p2_unique:
            p2_unique.append(mon)

    return (
        p1_unique[:6],
        p2_unique[:6]
    )

# =========================
# ICON URL
# =========================

def clean_name(name):

    name = name.lower()

    replacements = {
        " ": "",
        ".": "",
        "'": "",
        "%": "",
        ":": "",
        "-": "",
    }

    for old, new in replacements.items():

        name = name.replace(old, new)

    return name

def icon_url(name):

    cleaned = clean_name(name)

    return (
        "https://play.pokemonshowdown.com/"
        f"sprites/gen5/{cleaned}.png"
    )

# =========================
# PLAYER QUERY
# =========================

player = st.query_params.get(
    "player",
    None
)

# =========================
# LADDER VIEW
# =========================

if not player:

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

    st.subheader("Top 100 Ladder")

    for _, row in ladder_df.iterrows():

        c1, c2, c3, c4 = st.columns(
            [1, 5, 2, 2]
        )

        c1.write(
            f"#{row['Rank']}"
        )

        if c2.button(
            row["Name"],
            key=row["Name"],
            use_container_width=True
        ):

            st.query_params["player"] = (
                row["Name"]
            )

            st.rerun()

        c3.write(
            f"{row['Elo']}"
        )

        c4.write(
            f"GXE {row['GXE']}"
        )

# =========================
# PLAYER VIEW
# =========================

else:

    top1, top2 = st.columns([1, 5])

    if top1.button("← Back"):

        st.query_params.clear()

        st.rerun()

    top2.title(player)

    replays = fetch_replays(player)

    st.subheader("Replay一覧")

    if len(replays) == 0:

        st.info("公開Replayなし")

        st.stop()

    for replay in replays:

        replay_id = replay.get(
            "id",
            ""
        )

        if not replay_id:
            continue

        replay_url = (
            "https://replay.pokemonshowdown.com/"
            f"{replay_id}"
        )

        rating = replay.get(
            "rating",
            "?"
        )

        uploadtime = replay.get(
            "uploadtime"
        )

        if uploadtime:

            date_text = datetime.fromtimestamp(
                uploadtime
            ).strftime(
                "%Y-%m-%d"
            )

        else:

            date_text = "Unknown"

        log_text = fetch_log(
            replay_id
        )

        p1_team, p2_team = extract_teams(
            log_text
        )

        with st.container(border=True):

            st.link_button(
                f"Rate {rating} | {date_text}",
                replay_url,
                use_container_width=True
            )

            st.write("### P1")

            cols = st.columns(6)

            for i, mon in enumerate(p1_team):

                if i >= 6:
                    break

                with cols[i]:

                    st.image(
                        icon_url(mon),
                        width=52
                    )

            st.write("### P2")

            cols2 = st.columns(6)

            for i, mon in enumerate(p2_team):

                if i >= 6:
                    break

                with cols2[i]:

                    st.image(
                        icon_url(mon),
                        width=52
                    )
