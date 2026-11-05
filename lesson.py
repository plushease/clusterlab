import numpy as np
import pandas as pd
import streamlit as st
from clustering import POINT_NAMES, kmeans_steps
from charts import scatter


def render_lesson(room):
    frames = kmeans_steps(room["points"], room["k"], room["seeds"])
    key = f"slide_{room['code']}"
    if key not in st.session_state:
        st.session_state[key] = 0
    st.markdown("### Follow the algorithm, one decision at a time.")
    st.caption("These slides use this session’s exact points and starting centers. X and Y are treated as equally scaled features.")
    index = st.session_state[key]
    frame = frames[index]
    prev, progress, nxt = st.columns([1, 4, 1])
    if prev.button("← Previous", disabled=index == 0, key=f"prev_{room['code']}", width="stretch"):
        st.session_state[key] -= 1
        st.rerun()
    progress.progress((index + 1) / len(frames), text=f"SLIDE {index+1:02d} / {len(frames):02d}  ·  " + (f"ITERATION {frame.iteration}" if frame.iteration else "GETTING STARTED"))
    if nxt.button("Next →", disabled=index == len(frames)-1, key=f"next_{room['code']}", width="stretch", type="primary"):
        st.session_state[key] += 1
        st.rerun()
    headings = {"initialize": "01 / Start with a question", "assign": "02 / Find the nearest center",
                "update": "03 / Move to the mean", "finish": "04 / The clusters settle"}
    with st.container(border=True):
        left, right = st.columns([1.65, 1], gap="large")
        with left:
            st.plotly_chart(scatter(room["points"], frame.centers, frame.labels, frame.previous_centers,
                                    connections=frame.kind == "assign", height=480), width="stretch", key=f"lesson_chart_{room['code']}")
        with right:
            st.markdown(f"#### {headings[frame.kind]}")
            if frame.kind == "initialize":
                st.markdown(f"We have **8 points** and want **{room['k']} groups**. K-means finds groups whose points are close to their group’s center.")
                st.markdown("**Choose K, then pick K starting centers.** For this lesson, the centers start on these points:")
                for j, seed in enumerate(room["seeds"]):
                    st.markdown(f"• Center **{j+1}** → point **{POINT_NAMES[seed]}** {tuple(room['points'][seed])}")
                st.info("The × symbols are centers. Cluster numbers stay tied to these starting centers throughout the lesson.")
            elif frame.kind == "assign":
                st.markdown("Measure each point’s distance to every center. Assign it to the **nearest** center.")
                st.latex(r"d(x,\mu)=\sqrt{(x_1-\mu_1)^2+(x_2-\mu_2)^2}")
                st.markdown("The dotted lines connect each point to its selected center. The centers **stay still** during this step.")
                st.caption("An exact distance tie goes to the lowest numbered cluster.")
            elif frame.kind == "update":
                st.markdown("Keep the assignments fixed. Move each center to the **average X and average Y** of its assigned points.")
                st.latex(r"\mu_j=\frac{1}{|C_j|}\sum_{x_i\in C_j}x_i")
                shift = float(np.linalg.norm(frame.centers-frame.previous_centers, axis=1).max())
                st.metric("Largest center movement", f"{shift:.3f}")
                st.success("No centers moved. We have converged.") if frame.converged else st.info("The centers moved. Next, assign every point again using these new centers.")
                st.caption("If a cluster is empty, its center stays where it was.")
            else:
                st.markdown(f"After **{frame.iteration} assignment / update rounds**, the centers no longer move. The assignments are stable.")
                st.metric("Within-cluster sum of squares", f"{frame.inertia:.2f}")
                st.markdown("K-means reduces the sum of squared distances from points to their centers. **Smaller is better for a fixed K and dataset.**")
                st.info("Different starting centers can lead to different results. This is a local optimum, not a guarantee of the best possible clustering.")
                st.markdown("**Discuss:** Which point divided the class? Would a different K tell a different story?")
    if frame.kind == "assign":
        st.markdown("#### Show the distance calculation")
        selected = st.selectbox("Inspect a point", POINT_NAMES, key=f"inspect_{room['code']}")
        i = POINT_NAMES.index(selected)
        values = frame.distances[i]
        table = pd.DataFrame({"Cluster": [f"Cluster {j+1}" for j in range(room["k"])],
                              "Center X": frame.centers[:, 0], "Center Y": frame.centers[:, 1],
                              "Distance": values, "Nearest": ["✓" if j == frame.labels[i] else "" for j in range(room["k"])]})
        st.dataframe(table, hide_index=True, width="stretch", column_config={"Distance": st.column_config.NumberColumn(format="%.3f")})
        p, c = np.array(room["points"])[i], frame.centers[frame.labels[i]]
        st.latex(rf"d({selected},\mu_{{{frame.labels[i]+1}}})=\sqrt{{({p[0]:g}-{c[0]:.2f})^2+({p[1]:g}-{c[1]:.2f})^2}}={values[frame.labels[i]]:.3f}")
    elif frame.labels is not None:
        rows = []
        for j, center in enumerate(frame.centers):
            rows.append({"Cluster": f"Cluster {j+1}", "Members": ", ".join(POINT_NAMES[i] for i in np.where(frame.labels == j)[0]) or "Empty",
                         "Mean X": center[0], "Mean Y": center[1]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    with st.expander("Teaching notes · assumptions & limitations"):
        st.markdown("""- **Votes are predictions.** K-means uses point coordinates, not the student votes.
- **Feature scale matters.** Standardize features first if their units or ranges differ substantially.
- **Cluster labels are arbitrary.** We keep labels anchored to the same initial centers so votes are comparable.
- **K is chosen in advance.** K-means does not discover the number of clusters by itself.
- **Initialization matters.** Try another session with different starting points; real applications often use K-means++ and several restarts.
- **Shape matters.** K-means works best for compact groups; outliers and non-spherical groups can be challenging.""")
    if st.button("↺ Restart walkthrough", key=f"restart_{room['code']}"):
        st.session_state[key] = 0
        st.rerun()
