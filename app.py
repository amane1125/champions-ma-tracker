import streamlit as st
import pandas as pd
import requests
import re
import time
import urllib.parse
import sqlite3
from datetime import datetime, timezone

# =====================================
# PAGE CONFIG
# =====================================

st.set_page_config(
    page_title="Champions M-A Tracker",
    page_icon="🎮",
    layout="wide"
)

# =====================================
# CONFIG
# =====================================

FORMAT_ID = "gen9championsvgc2026regmb"

LADDER_URL = (
    "https://pokemonshowdown.com/ladder/"
    f"{FORMAT_ID}.json"
)

REPLAY_SEARCH_URL = (
    "https://replay.pokemonshowdown.com/search.json"
)

PAGE_SIZE = 50

# =====================================
# SQLITE
# =====================================

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

# =====================================
# STYLE
# =====================================

st.html("""
<style>

html, body, [class*="css"] {
    font-family: sans-serif;
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 4rem;
    max-width: 900px;
}

a {
    text-decoration: none !important;
}

.ladder-row {
    transition: 0.15s;
}

.ladder-row:hover {
    transform: scale(1.01);
    border-color: #3b82f6 !important;
}

.replay-card:hover {
    border-color: #3b82f6 !important;
}

</style>
""")

# =====================================
# HEADER
# =====================================

top1, top2 = st.columns([8, 1])

with top1:
    st.title("🎮 Champions M-A Tracker")

with top2:
    if st.button("🔄"):
        st.cache_data.clear()
        st.rerun()

st.caption(
    "[Gen 9 Champions] VGC 2026 Reg M-A"
)

# =====================================
# API
# =====================================

@st.cache_data(ttl=300)
def fetch_ladder():

    r = requests.get(
        LADDER_URL,
        timeout=20
    )

    data = r.json()

    if isinstance(data, dict):
        data = data.get("toplist", [])

    rows = []

    for i, p in enumerate(data[:500], start=1):

        rows.append({
            "Rank": i,
            "Name": p.get("username", "Unknown"),
            "Elo": int(p.get("elo", 0)),
            "GXE": round(p.get("gxe", 0), 1)
        })

    return pd.DataFrame(rows)

@st.cache_data(ttl=300)
def fetch_replays(username):

    time.sleep(0.05)

    try:

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

    except:
        pass

    return ""

# =====================================
# ICON FIX
# =====================================

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

# =====================================
# UTIL
# =====================================

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

# =====================================
# CACHE
# =====================================

def cache_replay(replay):

    replay_id = replay.get("id")

    cur.execute("""
    SELECT replay_id
    FROM replay_cache
    WHERE replay_id = ?
    """, (replay_id,))

    if cur.fetchone():
        return

    log_text = fetch_log(replay_id)

    if not log_text:
        return

    p1_team, p2_team = extract_teams(
        log_text
    )

    p1_match = re.search(
        r"\|player\|p1\|([^\n]+)",
        log_text
    )

    p2_match = re.search(
        r"\|player\|p2\|([^\n]+)",
        log_text
    )

    win_match = re.search(
        r"\|win\|([^\n]+)",
        log_text
    )

    p1 = p1_match.group(1) if p1_match else ""
    p2 = p2_match.group(1) if p2_match else ""
    winner = win_match.group(1) if win_match else ""

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

# =====================================
# REPLAY STATUS
# =====================================

def latest_replay_info(name):

    replays = fetch_replays(name)

    if not replays:
        return "❌", "None"

    latest = replays[0]

    uploadtime = latest.get(
        "uploadtime"
    )

    if not uploadtime:
        return "⚪", "?"

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

    return status, dt.strftime("%m/%d")

# =====================================
# QUERY PARAM
# =====================================

player = st.query_params.get(
    "player",
    None
)

# =====================================
# TOP PAGE
# =====================================

if not player:

    ladder_df = fetch_ladder()

    col1, col2 = st.columns(2)

    with col1:
        search = st.text_input(
            "🔍 Player Search"
        )

    with col2:
        pokemon_search = st.text_input(
            "🐾 Pokemon Search"
        )

    only_replay = st.toggle(
        "📹 Replayありのみ",
        value=False
    )

    page = st.select_slider(
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
        value="1-50"
    )

    start_rank = int(
        page.split("-")[0]
    )

    start_idx = start_rank - 1
    end_idx = start_idx + PAGE_SIZE

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

    # =====================================
    # HEADER
    # =====================================

    st.html("""
    <div style="
    display:flex;
    align-items:center;

    background:#111827;

    border-radius:12px;
    padding:10px;

    margin-bottom:8px;

    color:#9ca3af;
    font-size:12px;
    font-weight:700;
    ">

    <div style="width:52px;">#</div>

    <div style="flex:1;">
    Player
    </div>

    <div style="
    width:70px;
    text-align:right;
    ">
    Elo
    </div>

    <div style="
    width:60px;
    text-align:right;
    ">
    GXE
    </div>

    <div style="
    width:72px;
    text-align:right;
    ">
    Replay
    </div>

    </div>
    """)

    # =====================================
    # ROWS
    # =====================================

    for _, row in ladder_df.iterrows():

        status, replay_date = (
            latest_replay_info(
                row["Name"]
            )
        )

        if (
            only_replay
            and replay_date == "None"
        ):
            continue

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

        bg = "#111827"

        if status == "🟢":
            bg = "#0f172a"

        st.html(f"""
        <a
        href="?player={urllib.parse.quote(row['Name'])}"
        target="_self"
        style="
        text-decoration:none;
        color:white;
        "
        >

        <div
        class="ladder-row"
        style="
        display:flex;
        align-items:center;

        background:{bg};

        border:1px solid #222;
        border-radius:12px;

        padding:12px 10px;
        margin-bottom:6px;

        color:white;
        "
        >

        <div style="
        width:52px;
        font-weight:700;
        ">
        #{row['Rank']}
        </div>

        <div style="
        flex:1;
        overflow:hidden;
        text-overflow:ellipsis;
        white-space:nowrap;
        font-weight:600;
        ">
        {status} {row['Name']}
        </div>

        <div style="
        width:70px;
        text-align:right;
        font-weight:700;
        ">
        {row['Elo']}
        </div>

        <div style="
        width:60px;
        text-align:right;
        ">
        {row['GXE']}
        </div>

        <div style="
        width:72px;
        text-align:right;
        color:#9ca3af;
        font-size:13px;
        ">
        {replay_date}
        </div>

        </div>

        </a>
        """)

# =====================================
# PLAYER PAGE
# =====================================

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

    replay_limit = st.select_slider(
        "Replay Count",
        options=[10, 20, 50],
        value=10
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
            "🟢 WIN"
            if winner == player
            else "🔴 LOSE"
        )

        p1_icons = "".join([
            f'<img src="{icon_url(mon)}" width="32">'
            for mon in p1_team.split(",")
            if mon
        ])

        p2_icons = "".join([
            f'<img src="{icon_url(mon)}" width="32">'
            for mon in p2_team.split(",")
            if mon
        ])

        st.html(f"""
        <a
        href="{replay_url}"
        target="_blank"
        style="
        text-decoration:none;
        color:white;
        "
        >

        <div
        class="replay-card"
        style="
        background:#111827;

        border:1px solid #222;
        border-radius:14px;

        padding:14px;
        margin-bottom:10px;
        "
        >

        <div style="
        display:flex;
        justify-content:space-between;
        align-items:center;

        margin-bottom:12px;

        font-size:14px;
        ">

        <div>
        ⭐ {rating}
        </div>

        <div>
        {result}
        </div>

        <div style="color:#9ca3af;">
        {date_text}
        </div>

        </div>

        <div style="
        margin-bottom:12px;
        ">

        <div style="
        font-weight:700;
        margin-bottom:6px;
        ">
        {p1}
        </div>

        <div>
        {p1_icons}
        </div>

        </div>

        <div>

        <div style="
        font-weight:700;
        margin-bottom:6px;
        ">
        {p2}
        </div>

        <div>
        {p2_icons}
        </div>

        </div>

        </div>

        </a>
        """)
