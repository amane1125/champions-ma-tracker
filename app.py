import streamlit as st
import pandas as pd
import requests
import re
import time
import urllib.parse
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

@st.cache_data(ttl=3600)
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
# REPLAY STATUS
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
        "🔍 Search Player"
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

    st.caption(
        f"{len(ladder_df)} players"
    )

    # =====================
    # ROWS
    # =====================

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

        with st.container(border=True):

            c1, c2, c3, c4, c5 = st.columns(
                [1, 4, 2, 2, 2]
            )

            c1.markdown(
                f"### #{row['Rank']}"
            )

            if c2.button(
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

            c5.markdown(
                f"""
                **Latest**  
                {replay_date}
                """
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

    # =====================
    # LIMIT
    # =====================

    replay_limit = st.selectbox(
        "Replay Count",
        [10, 20, 50],
        index=0
    )

    replays = replays[:replay_limit]

    # =====================
    # REPLAYS
    # =====================

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
                "%m/%d"
            )

        else:

            date_text = "?"

        # =====================
        # LAZY LOAD LOG
        # =====================

        with st.container(border=True):

            top1, top2, top3 = st.columns(
                [2, 1, 1]
            )

            top1.markdown(
                f"### {rating}"
            )

            top2.markdown(
                f"### {date_text}"
            )

            st.link_button(
                "Open",
                replay_url,
                use_container_width=True
            )

            if st.button(
                "Show Teams",
                key=f"teams_{replay_id}",
                use_container_width=True
            ):

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
