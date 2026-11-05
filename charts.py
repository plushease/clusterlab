import numpy as np
import plotly.graph_objects as go
from clustering import COLORS, POINT_NAMES


def scatter(points, centers=None, labels=None, previous=None, connections=False, height=440):
    x = np.asarray(points)
    fig = go.Figure()
    if connections and labels is not None and centers is not None:
        for i, cluster in enumerate(labels):
            if cluster < 0:
                continue
            fig.add_trace(go.Scatter(x=[x[i, 0], centers[cluster, 0]], y=[x[i, 1], centers[cluster, 1]],
                                     mode="lines", line=dict(color=COLORS[cluster], width=1, dash="dot"),
                                     hoverinfo="skip", showlegend=False))
    if previous is not None:
        for i, (old, new) in enumerate(zip(previous, centers)):
            fig.add_annotation(x=new[0], y=new[1], ax=old[0], ay=old[1], xref="x", yref="y",
                               axref="x", ayref="y", showarrow=True, arrowhead=3, arrowwidth=2,
                               arrowcolor=COLORS[i])
        fig.add_trace(go.Scatter(x=previous[:, 0], y=previous[:, 1], mode="markers",
                                 marker=dict(symbol="x-open", size=17, color="#8C9C96"),
                                 name="Previous centers", hoverinfo="skip"))
    groups = sorted(set(labels)) if labels is not None else [-1]
    for j in groups:
        indices = np.where(np.array(labels) == j)[0] if labels is not None else np.arange(8)
        fig.add_trace(go.Scatter(
            x=x[indices, 0], y=x[indices, 1], mode="markers+text",
            text=[POINT_NAMES[i] for i in indices], textposition="top center",
            textfont=dict(size=15, color="#233C35"),
            marker=dict(size=17, color=COLORS[j] if j >= 0 else "#7D918B", line=dict(width=2, color="white")),
            name=f"Cluster {j + 1}" if j >= 0 else "Unassigned / tied",
            customdata=[POINT_NAMES[i] for i in indices],
            hovertemplate="Point %{customdata}<br>X: %{x}<br>Y: %{y}<extra></extra>"))
    if centers is not None:
        for j, center in enumerate(centers):
            fig.add_trace(go.Scatter(x=[center[0]], y=[center[1]], mode="markers",
                                     marker=dict(size=20, symbol="x", color=COLORS[j], line=dict(width=2, color="white")),
                                     name=f"Center {j + 1}", hovertemplate=f"Center {j+1}<br>(%{{x:.2f}}, %{{y:.2f}})<extra></extra>"))
    span = np.maximum(np.ptp(x, axis=0), 1)
    fig.update_layout(height=height, margin=dict(l=12, r=12, t=24, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F3F6F3",
                      font=dict(family="Arial, sans-serif", color="#324B43"),
                      legend=dict(orientation="h", y=-0.14, x=0, font=dict(size=11)),
                      xaxis=dict(title="Feature X", gridcolor="#DFE7E1", zeroline=False,
                                 range=[x[:, 0].min()-span[0]*.16, x[:, 0].max()+span[0]*.16]),
                      yaxis=dict(title="Feature Y", gridcolor="#DFE7E1", zeroline=False, scaleanchor="x", scaleratio=1,
                                 range=[x[:, 1].min()-span[1]*.16, x[:, 1].max()+span[1]*.16]))
    return fig


def vote_counts(ballots, k):
    counts = np.zeros((8, k), dtype=int)
    for ballot in ballots:
        for i, choice in enumerate(ballot["choices"]):
            counts[i, choice] += 1
    return counts


def consensus(counts):
    winners = np.argmax(counts, axis=1)
    for i, row in enumerate(counts):
        if row.sum() == 0 or np.count_nonzero(row == row.max()) != 1:
            winners[i] = -1
    return winners


def vote_bars(counts):
    fig = go.Figure()
    for j in range(counts.shape[1]):
        fig.add_bar(name=f"Cluster {j+1}", x=POINT_NAMES, y=counts[:, j], marker_color=COLORS[j],
                    hovertemplate=f"Point %{{x}}<br>Cluster {j+1}: %{{y}} votes<extra></extra>")
    fig.update_layout(barmode="stack", height=330, margin=dict(l=5, r=5, t=15, b=15),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#324B43"), legend=dict(orientation="h", y=1.15),
                      xaxis=dict(title=None), yaxis=dict(title="Student votes", dtick=1 if counts.sum(axis=1).max() < 10 else None, gridcolor="#DFE7E1"))
    return fig
