import streamlit as st
import pandas as pd
import requests
import re
import time
import urllib.parse
import sqlite3
from datetime import datetime, timezone

# =========================
# PAGE
# =========================

st.set_page_config(
    page_title="Champions M-A Tracker",
    page_icon="🎮",
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

PAGE_SIZE = 50

# =========================
# SQLITE
# =========================

conn = sqlite3.connect(
    "replays.db",
    check_same_thread=False
)

cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS replay_cache (

    replay_id TEXT PRIMARY KEY,
    p1 TEXT,
    p2 TEXT,
    p1_team TEXT,
    p2_team TEXT,
    winner TEXT,
    rating INTEGER,
    uploadtime INTEGER

)
""")

conn.commit()

# =========================
# REFRESH
# =========================

top1, top2 = st.columns([8, 1])

with top2:

    if st.button("🔄"):

        st.cache_data.clear()
        st.rerun()

# =========================
# API
# =========================

@st.cache_data(ttl=300)
def fetch_ladder():

    r = requests.get(
        LADDER_URL,
        timeout=20
    )

    data = r.json()

    if isinstance(data, dict):

        if "toplist" in data:
            data = data["toplist"]

    rows = []

    for i, p in enumerate(data[:500], start=1):

        rows.append({
            "Rank": i,
            "Name": p.get("username", "Unknown"),
            "Elo": int(p.get("elo", 0)),
            "GXE": p.get("gxe", 0)
        })

    return pd.DataFrame(rows)

@st.cache_data(ttl=300)
def fetch_replays(username):

    time.sleep(0.15)

    try:

        r = requests.get(
            REPLAY_SEARCH_URL,
            params={
                "user": username,
                "format": FORMAT_ID
            },
            timeout=20
        )

        if r.status_code == 429:

            time.sleep(1)

            r = requests.get(
                REPLAY_SEARCH_URL,
                params={
                    "user": username,
                    "format": FORMAT_ID
                },
                timeout=20
            )

        data = r.json()

        if isinstance(data, list):
            return data

        return []

    except:

        return []

def fetch_log(replay_id):

    try:

        r = requests.get(
            f"https://replay.pokemonshowdown.com/{replay_id}.log",
            timeout=20
        )

        if r.status_code == 200:
            return r.text

        return ""

    except:

        return ""

# =========================
# ICON FIX
# =========================

ICON_FIXES = {

    "urshifu-rapid-strike":
        "urshifurapidstrike",

    "urshifu-single-strike":
        "urshifu",

    "indeedee-f":
        "indeedeef",

    "ogerpon-wellspring":
        "ogerponwellspring",

    "ogerpon-hearthflame":
        "ogerponhearthflame",

    "ogerpon-cornerstone":
        "ogerponcornerstone",

    "tornadus-therian":
        "tornadustherian",

    "landorus-therian":
        "landorustherian",

    "thundurus-therian":
        "thundurustherian",

    "enamorus-therian":
        "enamorustherian"
}

# =========================
# TEAM
# =========================

def extract_teams(log_text):

    p1 = re.findall(
        r"\|poke\|p1\|([^,\n]+)",
        log_text
    )

    p2 = re.findall(
        r"\|poke\|p2\|([^,\n]+)",
        log_text
    )

    return (
        list(dict.fromkeys(p1))[:6],
        list(dict.fromkeys(p2))[:6]
    )

# =========================
# ICON
# =========================

def clean_name(name):

    name = name.lower()

    if name in ICON_FIXES:
        return ICON_FIXES[name]

    for c in [
        " ",
        ".",
        "'",
        "%",
        ":",
        "-"
    ]:

        name = name.replace(c, "")

    return name

def icon_url(name):

    return (
        "https://play.pokemonshowdown.com/"
        f"sprites/gen5/{clean_name(name)}.png"
    )

# =========================
# CACHE REPLAY
# =========================

def cache_replay(replay):

    replay_id = replay.get("id")

    cur.execute("""
    SELECT replay_id
    FROM replay_cache
    WHERE replay_id = ?
    """, (replay_id,))

    exists = cur.fetchone()

    if exists:
        return

    log_text = fetch_log(replay_id)

    if not log_text:
        return

    p1_team, p2_team = extract_teams(
        log_text
    )

    p1_name_match = re.search(
        r"\|player\|p1\|([^\n]+)",
        log_text
    )

    p2_name_match = re.search(
        r"\|player\|p2\|([^\n]+)",
        log_text
    )

    win_match = re.search(
        r"\|win\|([^\n]+)",
        log_text
    )

    p1 = (
        p1_name_match.group(1)
        if p1_name_match
        else ""
    )

    p2 = (
        p2_name_match.group(1)
        if p2_name_match
        else ""
    )

    winner = (
        win_match.group(1)
        if win_match
        else ""
    )

    cur.execute("""
    INSERT OR REPLACE INTO replay_cache
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        replay_id,
        p1,
        p2,
        ",".join(p1_team),
        ",".join(p2_team),
        winner,
        replay.get("rating", 0),
        replay.get("uploadtime", 0)

    ))

    conn.commit()

# =========================
# STATUS
# =========================

def latest_replay_info(name):

    replays = fetch_replays(name)

    if not replays:

        return (
            "❌",
            "No Replay",
            999
        )

    latest = replays[0]

    uploadtime = latest.get(
        "uploadtime"
    )

    if not uploadtime:

        return (
            "⚪",
            "Unknown",
            999
        )

    dt = datetime.fromtimestamp(
        uploadtime,
        tz=timezone.utc
    )

    diff = (
        datetime.now(timezone.utc)
        - dt
    ).days

    if diff <= 1:
        status = "🟢"

    elif diff <= 7:
        status = "🟡"

    else:
        status = "🔴"

    return (
        status,
        dt.strftime("%m/%d"),
        diff
    )

# =========================
# QUERY
# =========================

player = st.query_params.get(
    "player",
    None
)

# =========================
# TOP PAGE
# =========================

if not player:

    st.title("🎮 Champions M-A Tracker")

    st.caption(
        "[Gen 9 Champions] VGC 2026 Reg M-A"
    )

    ladder_df = fetch_ladder()

    search = st.text_input(
        "🔍 Player Search"
    )

    pokemon_search = st.text_input(
        "🐾 Pokemon Search"
    )

    only_replay = st.toggle(
        "📹 Replayありのみ表示",
        value=False
    )

    page = st.segmented_control(
        "Page",
        options=[
            "1-50",
            "51-100",
            "101-150",
            "151-200",
            "201-250",
            "251-300",
            "301-350",
            "351-400",
            "401-450",
            "451-500"
        ],
        default="1-50"
    )

    start_rank = int(
        page.split("-")[0]
    )

    start_idx = start_rank - 1

    end_idx = (
        start_idx
        + PAGE_SIZE
    )

    ladder_df = ladder_df.iloc[
        start_idx:end_idx
    ]

    if search:

        ladder_df = ladder_df[
            ladder_df["Name"]
            .str.contains(
                search,
                case=False
            )
        ]

    header = st.columns(
        [1, 5, 2, 2, 2]
    )

    header[0].markdown("**#**")
    header[1].markdown("**Player**")
    header[2].markdown("**Elo**")
    header[3].markdown("**GXE**")
    header[4].markdown("**Latest**")

    st.divider()

    for _, row in ladder_df.iterrows():

        status, replay_date, diff = (
            latest_replay_info(
                row["Name"]
            )
        )

        if (
            only_replay
            and replay_date == "No Replay"
        ):
            continue

        # =====================
        # POKEMON FILTER
        # =====================

        if pokemon_search:

            replays = fetch_replays(
                row["Name"]
            )

            found = False

            for replay in replays[:5]:

                cache_replay(replay)

                replay_id = replay.get("id")

                cur.execute("""
                SELECT p1_team, p2_team
                FROM replay_cache
                WHERE replay_id = ?
                """, (replay_id,))

                result = cur.fetchone()

                if not result:
                    continue

                team_text = (
                    result[0]
                    + ","
                    + result[1]
                ).lower()

                if (
                    pokemon_search.lower()
                    in team_text
                ):

                    found = True
                    break

            if not found:
                continue

        cols = st.columns(
            [1, 5, 2, 2, 2]
        )

        cols[0].markdown(
            f"**#{row['Rank']}**"
        )

        if cols[1].button(
            f"{status} {row['Name']}",
            key=f"player_{row['Name']}",
            use_container_width=True
        ):

            st.query_params["player"] = (
                urllib.parse.quote(
                    row["Name"]
                )
            )

            st.rerun()

        cols[2].markdown(
            str(row["Elo"])
        )

        cols[3].markdown(
            str(row["GXE"])
        )

        cols[4].markdown(
            replay_date
        )

# =========================
# PLAYER PAGE
# =========================

else:

    player = urllib.parse.unquote(
        player
    )

    if st.button("← Back"):

        st.query_params.clear()

        st.rerun()

    st.title(player)

    replays = fetch_replays(player)

    st.caption(
        f"{len(replays)} Public Replays"
    )

    if not replays:

        st.info("Replayなし")
        st.stop()

    replay_limit = st.selectbox(
        "Replay Count",
        [10, 20, 50],
        index=0
    )

    replays = replays[:replay_limit]

    for replay in replays:

        cache_replay(replay)

        replay_id = replay.get("id")

        cur.execute("""
        SELECT *
        FROM replay_cache
        WHERE replay_id = ?
        """, (replay_id,))

        cached = cur.fetchone()

        if not cached:
            continue

        (
            _,
            p1,
            p2,
            p1_team,
            p2_team,
            winner,
            rating,
            uploadtime
        ) = cached

        replay_url = (
            "https://replay.pokemonshowdown.com/"
            f"{replay_id}"
        )

        date_text = datetime.fromtimestamp(
            uploadtime
        ).strftime("%m/%d")

        result = (
            "🟢"
            if winner == player
            else "🔴"
        )

        p1_icons = ""

        for mon in p1_team.split(","):

            p1_icons += (
                f'<img src="{icon_url(mon)}" width="26">'
            )

        p2_icons = ""

        for mon in p2_team.split(","):

            p2_icons += (
                f'<img src="{icon_url(mon)}" width="26">'
            )

        st.markdown(
            f"""
            <a
            href="{replay_url}"
            target="_blank"
            style="
            text-decoration:none;
            color:inherit;
            "
            >

            <div style="
            border:1px solid #333;
            border-radius:10px;
            padding:10px;
            margin-bottom:8px;
            background:#111827;
            ">

            <div style="
            display:flex;
            justify-content:space-between;
            color:white;
            margin-bottom:8px;
            ">

            <div><b>{rating}</b></div>
            <div>{result}</div>
            <div>{date_text}</div>

            </div>

            <div style="color:white;">
            <b>{p1}</b><br>
            {p1_icons}
            </div>

            <div style="
            margin-top:6px;
            color:white;
            ">

            <b>{p2}</b><br>
            {p2_icons}

            </div>

            </div>

            </a>
            """,
            unsafe_allow_html=True
        )
