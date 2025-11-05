import io
from typing import Any, Dict, List

import plotly.graph_objects as go


def build_performance_figure(reports: List[Dict[str, Any]]) -> go.Figure:
    if not reports:
        # Return empty figure if no reports
        return go.Figure()
        
    # Sort by evaluation time if present
    def key_fn(r):
        return r.get("evaluated_at") or r.get("collected_at") or ""
    
    data = sorted(reports, key=key_fn)
    
    # Always use sequence numbers for x-axis to ensure all points are visible
    x = list(range(1, len(data) + 1))
    y = [float(((r.get("scores") or {}).get("final_score") or 0.0)) for r in data]
    
    # Get timestamps for hover text
    timestamps = [r.get("evaluated_at") or r.get("collected_at") or "" for r in data]
    
    # Create hover text with both timestamp and score
    hover_text = [
        f"Snapshot {i+1}<br>"
        f"Time: {ts}<br>"
        f"Score: {score:.2f}"
        for i, (ts, score) in enumerate(zip(timestamps, y))
    ]

    fig = go.Figure()
    
    # Add scatter plot with hover text
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode="lines+markers",
        name="Final Score",
        text=hover_text,
        hoverinfo="text+y",
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=8, line=dict(width=1, color='DarkSlateGrey'))
    ))
    
    # Add annotations for first and last points
    if len(data) > 1:
        for idx in [0, -1]:
            fig.add_annotation(
                x=x[idx],
                y=y[idx],
                text=f"{y[idx]:.2f}",
                showarrow=True,
                arrowhead=1,
                ax=0,
                ay=-20 if idx == 0 else 20
            )
    
    fig.update_layout(
        title="Agent Performance Over Time",
        xaxis_title="Snapshot #",
        yaxis_title="Final Score",
        template="plotly_white",
        height=500,
        width=900,
        margin=dict(l=50, r=30, t=60, b=50),
        hovermode='closest',
        xaxis=dict(
            tickmode='array',
            tickvals=x,
            ticktext=[f"{i}" for i in x]
        )
    )
    return fig


def figure_to_png_bytes(fig: go.Figure) -> bytes:
    buf = io.BytesIO()
    fig.write_image(buf, format="png", engine="kaleido")
    return buf.getvalue()
