import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import re
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

    for i, p in enumerate(data[:100], start=1):

        rows.append({
            "Rank": i,
            "Name": p.get("username", "Unknown"),
            "Elo": int(p.get("elo", 0)),
            "GXE": p.get("gxe", 0)
        })

    return pd.DataFrame(rows)

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

    try:

        r = requests.get(
            f"https://replay.pokemonshowdown.com/{replay_id}.log",
            timeout=20
        )

        if r.status_code != 200:
            return ""

        return r.text

    except:

        return ""

# =========================
# TEAM
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
# ICON
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
# LAST REPLAY
# =========================

def latest_replay_info(name):

    replays = fetch_replays(name)

    if len(replays) == 0:

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

    now = datetime.now(
        timezone.utc
    )

    diff = (now - dt).days

    if diff <= 1:
        status = "🟢"

    elif diff <= 7:
        status = "🟡"

    else:
        status = "🔴"

    return (
        status,
        dt.strftime("%Y-%m-%d"),
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

    st.title(
        "🎮 Champions M-A Tracker"
    )

    st.caption(
        "[Gen 9 Champions] VGC 2026 Reg M-A"
    )

    ladder_df = fetch_ladder()

    search = st.text_input(
        "🔍 Player Search"
    )

    if search:

        ladder_df = ladder_df[
            ladder_df["Name"]
            .str.contains(
                search,
                case=False
            )
        ]

    # =====================
    # TABLE
    # =====================

    html = """

    <style>

    body {
        background:#0f172a;
        color:white;
        margin:0;
        padding:0;
        font-family:sans-serif;
    }

    table {
        width:100%;
        border-collapse:collapse;
        font-size:14px;
        text-align:center;
    }

    th {
        background:#111827;
        padding:12px;
        position:sticky;
        top:0;
        z-index:1;
    }

    td {
        padding:12px;
        border-top:1px solid #222;
    }

    tr:hover {
        background:#1f2937;
    }

    .playerbtn {
        background:#2563eb;
        color:white;
        padding:8px 14px;
        border-radius:10px;
        text-decoration:none;
        font-weight:bold;
        display:inline-block;
    }

    .playerbtn:hover {
        background:#3b82f6;
    }

    </style>

    <div style="
    overflow-x:auto;
    border-radius:16px;
    border:1px solid #222;
    ">

    <table>

    <tr>
    <th>#</th>
    <th>Player</th>
    <th>Elo</th>
    <th>GXE</th>
    <th>Latest Replay</th>
    </tr>

    """

    for _, row in ladder_df.iterrows():

        status, replay_date, diff = (
            latest_replay_info(
                row["Name"]
            )
        )

        replay_color = "#22c55e"

        if diff > 7:
            replay_color = "#ef4444"

        elif diff > 1:
            replay_color = "#facc15"

        html += f"""

        <tr>

        <td>
        #{row['Rank']}
        </td>

        <td>

        <a
        class="playerbtn"
        href="/?player={row['Name']}"
        target="_top"
        >

        {status} {row['Name']}

        </a>

        </td>

        <td>
        <b>{row['Elo']}</b>
        </td>

        <td>
        {row['GXE']}
        </td>

        <td>

        <span style="
        color:{replay_color};
        font-weight:bold;
        ">

        {replay_date}

        </span>

        </td>

        </tr>
        """

    html += "</table></div>"

    components.html(
        html,
        height=2200,
        scrolling=True
    )

# =========================
# PLAYER PAGE
# =========================

else:

    st.markdown(f"""
    <a href="/" target="_top">
    <button style="
    padding:8px 16px;
    border-radius:10px;
    border:none;
    background:#2563eb;
    color:white;
    font-weight:bold;
    cursor:pointer;
    margin-bottom:10px;
    ">
    ← Back
    </button>
    </a>
    """, unsafe_allow_html=True)

    st.title(player)

    replays = fetch_replays(player)

    st.caption(
        f"{len(replays)} Public Replays"
    )

    if len(replays) == 0:

        st.info("公開Replayなし")

        st.stop()

    # =====================
    # TABLE
    # =====================

    table_html = """

    <style>

    body {
        background:#0f172a;
        color:white;
        margin:0;
        padding:0;
        font-family:sans-serif;
    }

    table {
        width:100%;
        border-collapse:collapse;
        font-size:14px;
        text-align:center;
    }

    th {
        background:#111827;
        padding:10px;
        position:sticky;
        top:0;
        z-index:1;
    }

    td {
        padding:10px;
        border-top:1px solid #222;
    }

    tr:hover {
        background:#1f2937;
    }

    img {
        image-rendering:pixelated;
    }

    </style>

    <div style="
    overflow-x:auto;
    border-radius:16px;
    border:1px solid #222;
    ">

    <table>

    <tr>

    <th>Rate</th>
    <th>Player 1</th>
    <th>Player 2</th>
    <th>Result</th>
    <th>Date</th>

    </tr>

    """

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
                "%Y/%m/%d"
            )

        else:

            date_text = "Unknown"

        log_text = fetch_log(
            replay_id
        )

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

        p1_name = (
            p1_name_match.group(1)
            if p1_name_match
            else "P1"
        )

        p2_name = (
            p2_name_match.group(1)
            if p2_name_match
            else "P2"
        )

        win_match = re.search(
            r"\|win\|([^\n]+)",
            log_text
        )

        if win_match:

            winner = win_match.group(1)

            if winner == player:

                result = (
                    '<span style="color:#22c55e;font-weight:bold;">WIN</span>'
                )

            else:

                result = (
                    '<span style="color:#ef4444;font-weight:bold;">LOSE</span>'
                )

        else:

            result = "-"

        p1_icons = ""

        for mon in p1_team:

            p1_icons += (
                f'<img src="{icon_url(mon)}" width="32">'
            )

        p2_icons = ""

        for mon in p2_team:

            p2_icons += (
                f'<img src="{icon_url(mon)}" width="32">'
            )

        table_html += f"""

        <tr
        onclick="window.open('{replay_url}')"
        style="cursor:pointer;"
        >

        <td>
        <b>{rating}</b>
        </td>

        <td>

        <div style="
        font-weight:bold;
        margin-bottom:6px;
        ">
        {p1_name}
        </div>

        <div>
        {p1_icons}
        </div>

        </td>

        <td>

        <div style="
        font-weight:bold;
        margin-bottom:6px;
        ">
        {p2_name}
        </div>

        <div>
        {p2_icons}
        </div>

        </td>

        <td>
        {result}
        </td>

        <td>
        {date_text}
        </td>

        </tr>
        """

    table_html += "</table></div>"

    components.html(
        table_html,
        height=2400,
        scrolling=True
    )
