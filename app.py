import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime, timezone

st.set_page_config(
    page_title="Champions M-A Tracker",
    page_icon="🎮",
    layout="wide"
)

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

@st.cache_data(ttl=300)
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
# REPLAY STATUS
# =========================

def latest_replay_info(name):

    replays = fetch_replays(name)

    if not replays:

        return (
            "🔴",
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
        "🔍 Search Player"
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

        status, replay_date, diff = (
            latest_replay_info(
                row["Name"]
            )
        )

        with st.container(border=True):

            c1, c2, c3, c4 = st.columns(
                [1, 5, 2, 2]
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

            c3.markdown(
                f"""
                **Elo**  
                {row['Elo']}
                """
            )

            c4.markdown(
                f"""
                **GXE**  
                {row['GXE']}
                """
            )

            st.caption(
                f"Latest Replay: {replay_date}"
            )

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

    if not replays:

        st.info("Replayなし")
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

            result = (
                "🟢 WIN"
                if winner == player
                else "🔴 LOSE"
            )

        else:

            result = "-"

        with st.container(border=True):

            top1, top2, top3 = st.columns(
                [2, 2, 1]
            )

            top1.markdown(
                f"### {rating}"
            )

            top2.markdown(
                f"### {result}"
            )

            top3.markdown(
                f"### {date_text}"
            )

            st.divider()

            p1_icons = ""

            for mon in p1_team:

                p1_icons += (
                    f'<img src="{icon_url(mon)}" width="30">'
                )

            p2_icons = ""

            for mon in p2_team:

                p2_icons += (
                    f'<img src="{icon_url(mon)}" width="30">'
                )

            st.markdown(
                f"""
                **{p1_name}**

                {p1_icons}

                vs

                **{p2_name}**

                {p2_icons}
                """,
                unsafe_allow_html=True
            )

            st.link_button(
                "Open Replay",
                replay_url,
                use_container_width=True
            )
