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
    padding-top: 1.5rem;
}

div[data-testid="stVerticalBlock"] > div:has(div.replay-card) {
    border-radius: 18px;
}

.replay-card {
    padding: 12px;
    border-radius: 16px;
    background-color: #111827;
    margin-bottom: 14px;
    border: 1px solid #1f2937;
}

.player-card {
    padding: 10px;
    border-radius: 14px;
    background-color: #111827;
    margin-bottom: 8px;
    border: 1px solid #1f2937;
}

.good {
    color: #22c55e;
    font-weight: bold;
}

.bad {
    color: #ef4444;
    font-weight: bold;
}

.small {
    font-size: 0.9rem;
    opacity: 0.8;
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
                "%Y-%m-%d %H:%M"
            )

        else:

            date_text = "Unknown"

        log_text = fetch_log(
            replay_id
        )

        p1_team, p2_team = extract_teams(
            log_text
        )

        st.markdown(
            '<div class="replay-card">',
            unsafe_allow_html=True
        )

        c1, c2, c3 = st.columns(
            [3, 2, 2]
        )

        c1.link_button(
            "▶ Open Replay",
            replay_url,
            use_container_width=True
        )

        c2.metric(
            "Rate",
            rating
        )

        c3.markdown(
            f"""
            <div class="small">
            Date<br>
            <b>{date_text}</b>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write("### P1")

        cols = st.columns(6)

        for i, mon in enumerate(p1_team):

            if i >= 6:
                break

            with cols[i]:

                st.image(
                    icon_url(mon),
                    width=54
                )

        st.write("### P2")

        cols2 = st.columns(6)

        for i, mon in enumerate(p2_team):

            if i >= 6:
                break

            with cols2[i]:

                st.image(
                    icon_url(mon),
                    width=54
                )

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )
