import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime, timezone

# =========================
# PAGE
# =========================

st.set_page_config(
    page_title="Champions M-A Tracker"
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

    st.divider()

    header = st.columns(
        [1, 4, 2, 2, 3]
    )

    header[0].markdown("### #")
    header[1].markdown("### Player")
    header[2].markdown("### Elo")
    header[3].markdown("### GXE")
    header[4].markdown("### Latest")

    st.divider()

    for _, row in ladder_df.iterrows():

        status, replay_date, diff = (
            latest_replay_info(
                row["Name"]
            )
        )

        cols = st.columns(
            [1, 4, 2, 2, 3]
        )

        cols[0].markdown(
            f"### {row['Rank']}"
        )

        if cols[1].button(
            f"{status} {row['Name']}",
            key=row["Name"],
            use_container_width=True
        ):

            st.query_params["player"] = (
                row["Name"]
            )

            st.rerun()

        cols[2].metric(
            "",
            row["Elo"]
        )

        cols[3].metric(
            "",
            row["GXE"]
        )

        replay_color = "🟢"

        if diff > 7:
            replay_color = "🔴"

        elif diff > 1:
            replay_color = "🟡"

        cols[4].markdown(
            f"""
            ### {replay_color}
            {replay_date}
            """
        )

        st.divider()

# =========================
# PLAYER PAGE
# =========================

else:

    if st.button("← Back"):

        st.query_params.clear()

        st.rerun()

    st.title(player)

    replays = fetch_replays(player)

    st.caption(
        f"{len(replays)} Public Replays"
    )

    if len(replays) == 0:

        st.info("公開Replayなし")

        st.stop()

    # =====================
    # TABLE HEADER
    # =====================

    header = st.columns(
        [1, 4, 4, 2, 2]
    )

    header[0].markdown("### Rate")
    header[1].markdown("### Player 1")
    header[2].markdown("### Player 2")
    header[3].markdown("### Result")
    header[4].markdown("### Date")

    st.divider()

    # =====================
    # REPLAYS
    # =====================

    for i, replay in enumerate(replays):

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

                result = "🟢 WIN"

            else:

                result = "🔴 LOSE"

        else:

            result = "-"

        # =====================
        # ICONS
        # =====================

        p1_icons = ""

        for mon in p1_team:

            p1_icons += (
                f'<img src="{icon_url(mon)}" width="28">'
            )

        p2_icons = ""

        for mon in p2_team:

            p2_icons += (
                f'<img src="{icon_url(mon)}" width="28">'
            )

        cols = st.columns(
            [1, 4, 4, 2, 2]
        )

        cols[0].markdown(
            f"### {rating}"
        )

        cols[1].markdown(
            f"""
            **{p1_name}**

            {p1_icons}
            """,
            unsafe_allow_html=True
        )

        cols[2].markdown(
            f"""
            **{p2_name}**

            {p2_icons}
            """,
            unsafe_allow_html=True
        )

        cols[3].markdown(
            f"### {result}"
        )

        cols[4].markdown(
            f"### {date_text}"
        )

        if st.button(
            "Open Replay",
            key=f"replay_{i}",
            use_container_width=True
        ):

            st.link_button(
                "Go",
                replay_url
            )

        st.divider()
