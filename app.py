import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime, timezone
from sqlalchemy import create_engine

# =========================
# PAGE
# =========================

st.set_page_config(
    page_title="Champions M-A Tracker",
    page_icon="🎮",
    layout="wide"
)

# =========================
# STYLE
# =========================

st.markdown("""
<style>

.block-container {
    padding-top: 1rem;
    max-width: 100%;
}

.player-card {
    padding: 10px;
    border-radius: 14px;
    background-color: #111827;
    margin-bottom: 8px;
    border: 1px solid #1f2937;
}

.small {
    font-size: 0.85rem;
    opacity: 0.8;
}

table {
    border-collapse: collapse;
}

tr:hover {
    background-color: #1f2937;
}

</style>
""", unsafe_allow_html=True)

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
            "No Replay"
        )

    latest = replays[0]

    uploadtime = latest.get(
        "uploadtime"
    )

    if not uploadtime:

        return (
            "⚪",
            "Unknown"
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
        dt.strftime("%Y-%m-%d")
    )

# =========================
# QUERY
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
        "🎮 Champions M-A Tracker"
    )

    st.caption(
        "[Gen 9 Champions] VGC 2026 Reg M-A"
    )

    ladder_df = fetch_ladder()

    search = st.text_input(
        "🔍 プレイヤー検索"
    )

    if search:

        ladder_df = ladder_df[
            ladder_df["Name"]
            .str.contains(
                search,
                case=False
            )
        ]

    st.divider()

    for _, row in ladder_df.iterrows():

        status, replay_date = latest_replay_info(
            row["Name"]
        )

        with st.container():

            st.markdown(
                '<div class="player-card">',
                unsafe_allow_html=True
            )

            c1, c2, c3, c4, c5 = st.columns(
                [1, 4, 2, 2, 2]
            )

            c1.markdown(
                f"### #{row['Rank']}"
            )

            if c2.button(
                f"{status} {row['Name']}",
                key=row["Name"],
                use_container_width=True
            ):

                st.query_params["player"] = (
                    row["Name"]
                )

                st.rerun()

            c3.metric(
                "Elo",
                int(row["Elo"])
            )

            c4.metric(
                "GXE",
                row["GXE"]
            )

            c5.markdown(
                f"""
                <div class="small">
                Latest Replay<br>
                <b>{replay_date}</b>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
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

    st.caption(
        f"{len(replays)} Public Replays"
    )

    st.divider()

    if len(replays) == 0:

        st.info("公開Replayなし")

        st.stop()

    # =========================
    # TABLE UI
    # =========================

    table_html = """
    <div style="
    overflow-x:auto;
    border-radius:16px;
    border:1px solid #333;
    ">

    <table style="
    width:100%;
    border-collapse:collapse;
    font-size:14px;
    text-align:center;
    ">

    <tr style="
    background:#111827;
    ">

    <th style="padding:10px;">
    Rate
    </th>

    <th>
    Player 1
    </th>

    <th>
    Player 2
    </th>

    <th>
    Result
    </th>

    <th>
    Date
    </th>

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

        # =====================
        # PLAYER NAMES
        # =====================

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

        # =====================
        # WINNER
        # =====================

        win_match = re.search(
            r"\|win\|([^\n]+)",
            log_text
        )

        if win_match:

            winner = win_match.group(1)

            if winner == p1_name:

                result = (
                    '<span style="color:#22c55e;">'
                    'WIN'
                    '</span>'
                )

            else:

                result = (
                    '<span style="color:#ef4444;">'
                    'LOSE'
                    '</span>'
                )

        else:

            result = "-"

        # =====================
        # ICONS
        # =====================

        p1_icons = ""

        for mon in p1_team:

            p1_icons += f'''
            <img src="{icon_url(mon)}"
            width="32">
            '''

        p2_icons = ""

        for mon in p2_team:

            p2_icons += f'''
            <img src="{icon_url(mon)}"
            width="32">
            '''

        # =====================
        # ROW
        # =====================

        table_html += f"""

        <tr
        onclick="window.open('{replay_url}')"
        style="
        cursor:pointer;
        border-top:1px solid #222;
        "
        >

        <td style="padding:10px;">
        {rating}
        </td>

        <td style="padding:10px;">

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

        <td style="padding:10px;">

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

    st.markdown(
        table_html,
        unsafe_allow_html=True
    )
