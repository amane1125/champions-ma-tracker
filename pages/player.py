import streamlit as st
import requests
import re
from datetime import datetime

st.set_page_config(
    page_title="Player Detail",
    layout="wide"
)

FORMAT_ID = "gen9championsvgc2026regmb"

REPLAY_SEARCH_URL = (
    "https://replay.pokemonshowdown.com/search.json"
)

# =========================
# PLAYER
# =========================

player = st.session_state.get(
    "selected_player",
    "Unknown"
)

# =========================
# HEADER
# =========================

top1, top2 = st.columns([1, 5])

if top1.button("← Back"):

    st.switch_page("app.py")

top2.title(player)

# =========================
# API
# =========================

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
# MAIN
# =========================

replays = fetch_replays(player)

st.subheader("Replay一覧")

if len(replays) == 0:

    st.info("公開Replayなし")

    st.stop()

# =========================
# REPLAY CARDS
# =========================

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
