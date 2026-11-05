"""ClusterLab — a shared classroom experiment in K-means clustering."""
import hashlib
import html
import os
import time
import numpy as np
import pandas as pd
import streamlit as st
from clustering import COLORS, DEFAULT_POINTS, POINT_NAMES, kmeans_steps
from charts import consensus, scatter, vote_bars, vote_counts
from lesson import render_lesson
import storage

st.set_page_config(page_title="ClusterLab · A classroom experiment", page_icon="✳", layout="wide")
storage.initialize()
ADMIN_FINGERPRINT = hashlib.sha256(storage.admin_password().encode()).hexdigest()

st.markdown("""<style>
  .stApp { background:#F7F9F7; }
  .block-container { max-width:1440px; padding-top:4.8rem; padding-bottom:3rem; }
  h1,h2,h3 { letter-spacing:-.045em !important; }
  h1 { font-size:3rem !important; font-weight:650 !important; line-height:1.08 !important; }
  h3 { font-size:1.45rem !important; }
  [data-testid="stSidebar"] { background:#EAF0EB; border-right:1px solid #D9E3DC; }
  [data-testid="stSidebar"] .block-container { padding-top:2rem; }
  [data-testid="stMetric"] { background:white; border:1px solid #DFE6E0; border-radius:14px; padding:18px 20px; }
  [data-testid="stMetricLabel"] { color:#63756D; }
  [data-testid="stMetricValue"] { font-weight:600; }
  [data-testid="stVerticalBlockBorderWrapper"] > div { border-radius:16px; }
  button { border-radius:9px !important; }
  .eyebrow { font-size:11px; font-weight:700; letter-spacing:.16em; color:#54776A; margin-bottom:14px; }
  .brand { font-size:27px; font-weight:750; letter-spacing:-1.2px; margin-bottom:0; }
  .brand span { color:#16866A; }
  .brand-sub { color:#687E73; font-size:12px; margin-bottom:32px; }
  .hero-note { color:#66796F; font-size:16px; max-width:710px; margin-bottom:1.5rem; }
  .room-banner { background:#193E33; border-radius:14px; padding:20px 24px; color:#E7F6EC; margin:16px 0 24px; }
  .room-banner strong { font-size:25px; color:#C3ED80; letter-spacing:3px; }
  .room-banner small { color:#B9D1C3; font-size:12px; }
  .cluster-chip { display:inline-block; border:1px solid #DBE4DD; background:white; padding:7px 13px; border-radius:30px; font-size:12px; margin:0 6px 9px 0; }
  .dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; }
  .footnote { font-size:12px; color:#75877C; margin-top:32px; }
  @media(max-width:700px) { h1 { font-size:2.2rem !important; } .block-container { padding-top:4.5rem; } }
</style>""", unsafe_allow_html=True)


def heading(kicker, title, subtitle):
    st.markdown(f'<div class="eyebrow">{html.escape(kicker)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="hero-note">{html.escape(subtitle)}</div>', unsafe_allow_html=True)


def chips(room):
    content = ""
    for j, seed in enumerate(room["seeds"]):
        content += f'<span class="cluster-chip"><span class="dot" style="background:{COLORS[j]}"></span>Cluster {j+1} · starts at {POINT_NAMES[seed]}</span>'
    st.markdown(content, unsafe_allow_html=True)


def authenticated():
    return (st.session_state.get("admin_auth") == ADMIN_FINGERPRINT
            and time.time() < st.session_state.get("admin_until", 0))


def login():
    heading("INSTRUCTOR WORKSPACE", "Your classroom, in clusters.", "Watch ideas become data. Collect every vote, compare the class prediction, and teach the algorithm step by step.")
    left, right = st.columns([1, 1.2], gap="large")
    with left, st.container(border=True):
        st.markdown("### Admin sign in")
        st.caption("Enter the admin password configured on the server.")
        with st.form("admin_login"):
            password = st.text_input("Admin password", type="password", key="admin_password_input")
            submitted = st.form_submit_button("Open dashboard →", type="primary", width="stretch")
        if submitted:
            success, message = storage.verify_admin(password)
            if success:
                st.session_state["admin_auth"] = ADMIN_FINGERPRINT
                st.session_state["admin_until"] = time.time() + 8 * 3600
                st.rerun()
            st.error(message)
        st.caption("Local setup: the generated password is in data/admin-password.txt. On a hosted server, set ADMIN_PASSWORD.")
    with right:
        st.plotly_chart(scatter(DEFAULT_POINTS, np.array(DEFAULT_POINTS)[[0, 3, 6]], height=380), width="stretch")
        st.caption("8 points. A few centers. A whole classroom of perspectives.")


def student():
    heading("THE CLASSROOM EXPERIMENT", "Eight points. Your perspective.", "Which points belong together? Assign every point to a cluster, then let your class discover what K-means sees.")
    if "joined_room" not in st.session_state:
        requested = st.query_params.get("room", "DEMO").strip().upper()
        st.session_state["joined_room"] = requested if storage.get_room(requested) else "DEMO"
    with st.expander("Join a class session", expanded=False):
        with st.form("join_class"):
            code = st.text_input("Session code", value=st.session_state["joined_room"], max_chars=12)
            if st.form_submit_button("Join session", type="primary"):
                room = storage.get_room(code)
                if room:
                    st.session_state["joined_room"] = room["code"]
                    st.rerun()
                st.error("Session not found. Check the code with your instructor.")
    room = storage.get_room(st.session_state["joined_room"])
    if not room:
        st.error("This session could not be found.")
        return
    status = "OPEN FOR VOTES" if room["is_open"] else "VOTING CLOSED"
    st.markdown(f'<div class="room-banner"><small>{status} &nbsp; / &nbsp; SESSION CODE</small><br><strong>{room["code"]}</strong><br>{html.escape(room["title"])}</div>', unsafe_allow_html=True)
    left, right = st.columns([1.05, 1], gap="large")
    with left:
        st.markdown("### Meet your eight data points")
        st.caption("Each dot is one observation. The × marks show where each cluster’s center begins.")
        chips(room)
        st.plotly_chart(scatter(room["points"], np.array(room["points"])[room["seeds"]]), width="stretch")
        with st.expander("View coordinates"):
            st.dataframe(pd.DataFrame(room["points"], columns=["Feature X", "Feature Y"], index=POINT_NAMES), width="stretch")
        st.info("Make a prediction about the final clusters. Keep the cluster numbers linked to the starting centers shown above.")
    with right, st.container(border=True):
        st.markdown("### Make your prediction")
        st.caption("Choose a cluster for every point. Your instructor will reveal the results together.")
        if not room["is_open"]:
            st.warning("Your instructor has closed voting for this session.")
            if st.button("Check if voting reopened"):
                st.rerun()
            return
        with st.form(f"ballot_{room['code']}"):
            c1, c2 = st.columns(2)
            student_id = c1.text_input("Student code or nickname", max_chars=40, placeholder="e.g. student-07")
            pin = c2.text_input("Private ballot password", type="password", max_chars=128, help="Choose at least 6 characters. Keep it to revise your ballot later.")
            st.caption("Use a classroom nickname, not your full name. Your nickname and assignments are visible to the instructor.")
            choices = []
            columns = st.columns(2)
            for i, (name, (x, y)) in enumerate(zip(POINT_NAMES, room["points"])):
                value = columns[i % 2].selectbox(f"Point {name}  ·  ({x:g}, {y:g})", list(range(room["k"])),
                                                  index=None, placeholder="Choose cluster…", format_func=lambda j: f"Cluster {j+1}",
                                                  key=f"vote_{room['code']}_{name}")
                choices.append(value)
            submitted = st.form_submit_button("Submit my eight votes →", type="primary", width="stretch")
        if submitted:
            try:
                updated = storage.submit_ballot(room["code"], student_id, pin, choices)
                st.success("Your ballot has been updated. All eight votes are saved." if updated else "You’re in! All eight votes have been saved.")
            except ValueError as exc:
                st.error(str(exc))
        st.caption("One ballot per student code, per session. Submit again with the same code and password to revise it.")


@st.fragment(run_every="5s")
def results(room_code):
    if not authenticated():
        st.warning("Your admin session has expired. Sign in again.")
        return
    room = storage.get_room(room_code)
    votes = storage.ballots(room_code)
    counts = vote_counts(votes, room["k"])
    majority = consensus(counts)
    final = kmeans_steps(room["points"], room["k"], room["seeds"])[-1]
    metrics = st.columns(4)
    metrics[0].metric("Student ballots", len(votes))
    metrics[1].metric("Point assignments", len(votes) * 8)
    metrics[2].metric("Clusters · K", room["k"])
    metrics[3].metric("Class / K-means match", f"{int(np.sum(majority == final.labels))} / 8" if votes else "—")
    st.caption("Refreshes every 5 seconds while this page is open. Match counts points with a unique class leader matching the final K-means label; ties do not match.")
    if not votes:
        st.info(f"Ready for your first ballot. Ask students to open the app, choose Student voting, and join session {room_code}.")
    left, right = st.columns([1.1, 1], gap="large")
    with left, st.container(border=True):
        st.markdown("### The classroom map")
        mode = st.radio("Color points by", ["Class consensus", "K-means result"], horizontal=True, key=f"map_{room_code}")
        st.plotly_chart(scatter(room["points"], final.centers if mode == "K-means result" else None,
                                final.labels if mode == "K-means result" else majority, height=380), width="stretch")
        st.caption("Grey points have no votes or a tie for the lead. Consensus is the most-voted cluster for each point.")
    with right, st.container(border=True):
        st.markdown("### Every point, every vote")
        st.plotly_chart(vote_bars(counts), width="stretch")
        st.caption("Each bar contains one vote per student. Colors follow the same starting centers throughout the session.")
    st.markdown("### Where does the class agree?")
    rows = []
    for i, name in enumerate(POINT_NAMES):
        rows.append({"Point": name, **{f"Cluster {j+1}": int(counts[i, j]) for j in range(room["k"])},
                     "Class prediction": f"Cluster {majority[i]+1}" if majority[i] >= 0 else ("Tie" if votes else "No votes"),
                     "K-means": f"Cluster {final.labels[i]+1}",
                     "Leading share": f"{counts[i].max()/len(votes):.0%}" if votes else "—"})
    table = pd.DataFrame(rows)
    st.dataframe(table, hide_index=True, width="stretch")
    st.download_button("↓ Export point summary", storage.safe_csv(table), file_name=f"{room_code}-summary.csv", mime="text/csv")


@st.fragment(run_every="5s")
def ballot_log(room_code):
    if not authenticated():
        st.warning("Your admin session has expired. Sign in again.")
        return
    st.markdown("### The complete ballot book")
    st.caption("All saved ballots for this session. Revisions replace previous assignments. Timestamps are in UTC.")
    votes = storage.ballots(room_code)
    rows = [{"Student code": vote["student_id"], **{name: f"Cluster {vote['choices'][i]+1}" for i, name in enumerate(POINT_NAMES)},
             "First submitted (UTC)": vote["submitted_at"], "Last updated (UTC)": vote["updated_at"]} for vote in votes]
    if not rows:
        st.info("No ballots yet. Votes will appear here as soon as students submit them.")
        return
    table = pd.DataFrame(rows)
    search = st.text_input("Find a student code", placeholder="Search ballots…", key=f"search_{room_code}")
    filtered = table[table["Student code"].str.contains(search, case=False, regex=False)] if search else table
    st.caption(f"Showing {len(filtered)} of {len(table)} ballots · {len(table)*8} total point assignments")
    st.dataframe(filtered, hide_index=True, width="stretch")
    st.download_button("↓ Export all ballots", storage.safe_csv(table), file_name=f"{room_code}-ballots.csv", mime="text/csv")


def session_settings(room):
    st.markdown("### Run the room")
    st.write(f"Current session: **{room['code']}** · {room['title']}")
    st.caption("Close voting before discussing results. Reopening lets students submit or revise their ballots.")
    if st.button("Close voting" if room["is_open"] else "Reopen voting", key="toggle_voting"):
        storage.set_open(room["code"], not room["is_open"])
        st.rerun()
    st.divider()
    st.markdown("### Start a fresh experiment")
    st.caption("A new session has its own code and empty ballot book. Existing sessions and votes stay available.")
    with st.form("new_session"):
        title = st.text_input("Session title", value="The eight-point experiment", max_chars=80)
        k = st.selectbox("Number of clusters (K)", [2, 3, 4], index=1)
        seed_names = st.multiselect("Starting centers, in cluster order", POINT_NAMES, default=["A", "D", "G"],
                                    help="Select exactly K points. The first is Cluster 1, the second is Cluster 2, and so on.")
        st.caption("Edit the coordinates below, or keep the classic eight-point example.")
        edited = st.data_editor(pd.DataFrame({"Point": POINT_NAMES, "X": [float(p[0]) for p in DEFAULT_POINTS], "Y": [float(p[1]) for p in DEFAULT_POINTS]}),
                                hide_index=True, disabled=["Point"], num_rows="fixed", width="stretch", key="point_editor")
        create = st.form_submit_button("Create session →", type="primary")
    if create:
        try:
            code = storage.create_room(title, edited[["X", "Y"]].to_numpy().tolist(), k, [POINT_NAMES.index(n) for n in seed_names])
            st.session_state["pending_admin_room"] = code
            st.session_state["created_message"] = f"Session {code} is ready. Share its code with your class."
            st.rerun()
        except (ValueError, TypeError) as exc:
            st.error(str(exc))
    with st.expander("Current experiment data"):
        st.dataframe(pd.DataFrame(room["points"], index=POINT_NAMES, columns=["X", "Y"]), width="stretch")
        st.caption("Coordinates, K, and starting centers are fixed within a session so every ballot is comparable. Create a new session to change them.")


def admin():
    if not authenticated():
        login()
        return
    # Discard the login widget's raw secret after successful authentication.
    st.session_state.pop("admin_password_input", None)
    heading("INSTRUCTOR WORKSPACE", "A class full of perspectives.", "Collect the predictions. Find the patterns. Walk through the mathematics together.")
    all_rooms = storage.rooms()
    codes = [r["code"] for r in all_rooms]
    lookup = {r["code"]: r for r in all_rooms}
    if "pending_admin_room" in st.session_state:
        st.session_state["admin_room"] = st.session_state.pop("pending_admin_room")
    select, info = st.columns([2, 1])
    code = select.selectbox("Class session", codes, key="admin_room", format_func=lambda c: f"{c} · {lookup[c]['title']}")
    room = storage.get_room(code)
    info.markdown(f'<div class="room-banner" style="margin:0;padding:10px 20px"><small>{"VOTING OPEN" if room["is_open"] else "VOTING CLOSED"} · JOIN CODE</small><br><strong>{code}</strong></div>', unsafe_allow_html=True)
    if "created_message" in st.session_state:
        st.success(st.session_state.pop("created_message"))
    chips(room)
    overview, all_votes, slides, settings = st.tabs(["Overview", "All ballots", "K-means walkthrough", "Session controls"])
    with overview:
        results(code)
    with all_votes:
        ballot_log(code)
    with slides:
        render_lesson(room)
    with settings:
        session_settings(room)


with st.sidebar:
    st.markdown('<div class="brand"><span>✳</span> ClusterLab</div><div class="brand-sub">Small dataset. Big discoveries.</div>', unsafe_allow_html=True)
    view = st.radio("WORKSPACE", ["Student voting", "Admin dashboard"], key="workspace")
    st.divider()
    st.markdown("**An experiment in grouping.**")
    st.caption("Predict where eight points belong, then watch K-means find its way.")
    st.markdown("**01**  Observe the points\n\n**02**  Cast your eight votes\n\n**03**  Discover the clusters")
    st.divider()
    if authenticated():
        st.caption("Signed in as instructor")
        if st.button("Sign out", width="stretch"):
            st.session_state.pop("admin_auth", None)
            st.session_state.pop("admin_until", None)
            st.rerun()
    st.markdown('<div class="footnote">BUILT FOR THE CURIOUS CLASSROOM<br>Euclidean distance · Lloyd’s algorithm</div>', unsafe_allow_html=True)

if view == "Student voting":
    student()
else:
    admin()
