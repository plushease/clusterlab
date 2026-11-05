# ClusterLab

A real Python / Streamlit classroom app for collecting student cluster predictions for eight 2D points and teaching K-means from the same dataset.

## Start on Windows

Install Python 3.12 or later, open PowerShell in this folder, and run:

```powershell
./start.ps1
```

Open http://localhost:8501. The first run installs the dependencies into `.venv`. If your PowerShell policy disallows scripts, use the manual commands below instead; no policy change is required.

The server generates a random admin password in `data/admin-password.txt`. Open that local file and use its contents under **Admin dashboard**. The password is never shown to student browsers. Alternatively, set `ADMIN_PASSWORD` (at least 10 characters) before starting the app. Admin sessions expire after eight hours; five failed login attempts lock sign-in for five minutes.

## Manual setup (Windows, macOS, Linux)

```text
python -m venv .venv
```

Activate the environment, then run:

```text
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

For Windows activation use `.venv\Scripts\Activate.ps1`; on macOS/Linux use `source .venv/bin/activate`. You can also call the environment's Python directly without activation.

## In the classroom

1. Sign in to **Admin dashboard**. The starter session is **DEMO** with no sample ballots.
2. In **Session controls**, create a session. Keep the default points or edit all eight coordinates; choose K from 2–4 and exactly K starting points, in cluster order.
3. Share the app URL and session code. A link such as `https://your-host/?room=ABC234` preselects the session.
4. Students choose **Student voting**, join the session, enter a nickname and a private ballot password, assign A–H, and submit. A matching nickname and password lets them revise their eight votes.
5. **Overview** refreshes every five seconds and shows counts, the consensus map, vote distributions, and comparison with the final K-means result.
6. **All ballots** shows every student's eight choices, with search and CSV export. Both summary and full-ballot exports are available. Times are UTC.
7. Close voting, then open **K-means walkthrough**. Use Next / Previous to present actual initialization, assignment, mean updates, and convergence. Expand individual point distances for a worked calculation.

Students use self-chosen classroom codes; this is not a verified school identity system. Their ballot passwords prevent another person who only knows their nickname from overwriting an existing ballot. The instructor sees nicknames and choices, never passwords. Use classroom nicknames rather than personal identifiers.

## Let students connect

For devices on the same trusted network, run `./start.ps1 -Classroom` (or append `--server.address 0.0.0.0` to the Streamlit command). Students open `http://<server-computer-LAN-address>:8501`; `localhost` only works on the server computer. Network/firewall access must permit that port. For access across the internet, deploy to a Python-compatible host with HTTPS, a persistent disk, and WebSocket support. This project has not been published to a public host.

### Docker deployment

```text
docker build -t clusterlab .
docker run --rm -p 8501:8501 -v clusterlab-data:/app/data -e ADMIN_PASSWORD clusterlab
```

Set `ADMIN_PASSWORD` in the shell or host's secret manager before running the container. A mounted volume must be writable by the container's `appuser`. Keep the same admin secret across restarts. Put the service behind HTTPS for remote use.

**Persistence:** ballots and session settings live in `data/classroom.sqlite3`, or the directory specified by `CLUSTERLAB_DATA_DIR`. Keep that directory on persistent storage. SQLite supports concurrent classroom submissions on one server process; do not deploy multiple replicas with separate disks. An ephemeral hosting filesystem will lose votes on redeploy/restart. Sites' JavaScript Workers hosting cannot execute this Streamlit app.

To back up a running database, use SQLite's backup API rather than copying an actively written database file. The data folder also contains the local generated admin password, so keep backups private. There is no destructive reset button: a fresh session retains previous classes for later review.

## What students learn

- Eight default points: A(2,10), B(2,5), C(8,4), D(5,8), E(7,5), F(6,4), G(1,2), H(4,9).
- Default K=3, with starting centers at A, D, G.
- Euclidean nearest-center assignment followed by arithmetic-mean updates.
- Stable cluster numbers anchored to the initial centers, deterministic tie-breaking, and explicit handling of empty clusters.
- Within-cluster sum of squares, convergence, and the limits of K-means.

Student votes are predictions of the final clustering. They do not change the K-means calculation. A tie in class votes stays a tie; it is never shown as a winning cluster. Session configurations are immutable so all votes refer to the same experiment.

## Verification

```text
python -m unittest discover -s tests -v
```

The tests cover expected cluster membership, nearest-center assignments, mean updates, non-increasing objective, K options, invalid data, tied votes, concurrent submissions, ballot revisions and passwords, session isolation, closed voting, login throttling, safe CSV exports, and Streamlit student/admin flows.

Implementation reference: [Streamlit AppTest documentation](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest). The walkthrough is rendered directly inside Streamlit; no external presentation software is required.
