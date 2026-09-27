"""
CivicPulse — BRICS Innovation Challenge prototype
A scalable, multilingual platform that aggregates citizen development
requests and aligns them with infrastructure data to recommend
high-priority projects to policymakers.

Run with:  streamlit run app.py
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from data import (CATEGORIES, CHANNELS, LANGUAGES, STATUSES,
                   generate_complaints_df, generate_wards_df, _sample_text)
from scoring import compute_ward_priority

st.set_page_config(page_title="CivicPulse", page_icon="🏛️", layout="wide")

# ---------------------------------------------------------------------------
# Session state (acts as our "database" for the demo)
# ---------------------------------------------------------------------------
if "wards_df" not in st.session_state:
    st.session_state.wards_df = generate_wards_df()
if "complaints_df" not in st.session_state:
    st.session_state.complaints_df = generate_complaints_df(400)

wards_df = st.session_state.wards_df
complaints_df = st.session_state.complaints_df

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🏛️ CivicPulse")
st.caption(
    "A multilingual, AI-powered Digital Public Good prototype — "
    "aggregating citizen feedback and aligning it with infrastructure "
    "data to recommend high-priority development projects."
)

tab_dashboard, tab_submit, tab_track, tab_about = st.tabs(
    ["📊 Policymaker Dashboard", "📝 Submit a Complaint", "🔍 Track Status", "ℹ️ About"]
)

# ---------------------------------------------------------------------------
# TAB 1 — Policymaker Dashboard
# ---------------------------------------------------------------------------
with tab_dashboard:
    priority_df = compute_ward_priority(wards_df, complaints_df)
    merged_geo = wards_df.merge(
        priority_df[["ward", "priority_score", "complaint_count", "why"]], on="ward"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Complaints", f"{len(complaints_df):,}")
    c2.metric("Wards Monitored", f"{len(wards_df)}")
    c3.metric("Open Cases", int((complaints_df["status"] != "Resolved").sum()))
    c4.metric("Top Priority Ward", priority_df.iloc[0]["ward"].split(" - ")[0])

    st.subheader("Demand Hotspot Map")
    st.caption("Bubble size = complaint volume · Color = priority score (red = most urgent)")
    try:
        # Plotly >= 6: scatter_map (MapLibre-based, no token needed)
        fig_map = px.scatter_map(
            merged_geo, lat="lat", lon="lon", size="complaint_count",
            color="priority_score", color_continuous_scale="OrRd",
            hover_name="ward",
            hover_data={"lat": False, "lon": False, "priority_score": True,
                        "complaint_count": True},
            zoom=10, height=450, map_style="open-street-map",
        )
    except AttributeError:
        # Older plotly versions: fall back to scatter_mapbox
        fig_map = px.scatter_mapbox(
            merged_geo, lat="lat", lon="lon", size="complaint_count",
            color="priority_score", color_continuous_scale="OrRd",
            hover_name="ward",
            hover_data={"lat": False, "lon": False, "priority_score": True,
                        "complaint_count": True},
            zoom=10, height=450, mapbox_style="open-street-map",
        )
    fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_map, use_container_width=True)

    st.subheader("Recommended Project Priorities")
    st.caption(
        "Score = weighted mix of complaint volume, population affected, "
        "infrastructure gap, and urgency. Formula is fixed and auditable — "
        "not a black-box AI ranking."
    )
    for _, row in priority_df.head(5).iterrows():
        with st.container(border=True):
            cols = st.columns([0.5, 3, 1.5, 1.5])
            cols[0].markdown(f"### #{row['rank']}")
            cols[1].markdown(f"**{row['ward']}**")
            cols[1].caption(row["why"])
            cols[2].metric("Priority Score", f"{row['priority_score']}/100")
            cols[3].metric("Budget / capita", f"₹{row['budget_per_capita']}")

    with st.expander("View full ranking table"):
        st.dataframe(priority_df, use_container_width=True, hide_index=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Complaints by Category")
        cat_counts = complaints_df["category"].value_counts().reset_index()
        cat_counts.columns = ["category", "count"]
        fig1 = px.bar(cat_counts, x="count", y="category", orientation="h")
        fig1.update_layout(height=350, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig1, use_container_width=True)
    with col_b:
        st.subheader("Complaints by Language")
        lang_counts = complaints_df["language"].value_counts().reset_index()
        lang_counts.columns = ["language", "count"]
        fig2 = px.pie(lang_counts, names="language", values="count", hole=0.4)
        fig2.update_layout(height=350)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Complaint Volume Trend (last 90 days)")
    trend = complaints_df.copy()
    trend["date"] = trend["submitted_at"].dt.date
    trend_counts = trend.groupby("date").size().reset_index(name="count")
    fig3 = px.line(trend_counts, x="date", y="count")
    fig3.update_layout(height=300)
    st.plotly_chart(fig3, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 2 — Submit a Complaint (simulates WhatsApp / IVR / Web intake)
# ---------------------------------------------------------------------------
with tab_submit:
    st.subheader("Submit a Development Request")
    st.caption(
        "Simulates omnichannel intake — in production this would arrive via "
        "WhatsApp Business API, an IVR voice hotline, or SMS/USSD, then pass "
        "through speech-to-text + multilingual NLU automatically."
    )

    with st.form("complaint_form"):
        f1, f2 = st.columns(2)
        ward = f1.selectbox("Ward / Area", wards_df["ward"].tolist())
        category = f2.selectbox("Category", CATEGORIES)
        f3, f4 = st.columns(2)
        language = f3.selectbox("Language spoken", LANGUAGES)
        channel = f4.selectbox("Channel", CHANNELS)
        urgency = st.slider("Urgency (auto-estimated from tone in production)", 1, 10, 6)
        custom_text = st.text_area(
            "Describe the issue (in your own language)",
            placeholder="e.g. Hamare mohalle mein paani nahi aa raha..."
        )
        submitted = st.form_submit_button("Submit Complaint")

    if submitted:
        original = custom_text.strip() or _sample_text(category, language)[0]
        _, translated = _sample_text(category, language)
        new_row = {
            "complaint_id": f"CMP-{len(complaints_df)+1:04d}",
            "ward": ward, "category": category, "language": language,
            "channel": channel, "original_text": original,
            "translated_text": translated if not custom_text.strip() else original,
            "urgency": urgency, "status": "Received",
            "submitted_at": datetime.now(),
        }
        st.session_state.complaints_df = pd.concat(
            [complaints_df, pd.DataFrame([new_row])], ignore_index=True
        )
        st.success(
            f"✅ Complaint {new_row['complaint_id']} received for **{ward}** "
            f"and auto-tagged as **{category}**. It has been added to the "
            f"prioritization engine — check the Dashboard tab."
        )

# ---------------------------------------------------------------------------
# TAB 3 — Track Status (citizen-facing accountability loop)
# ---------------------------------------------------------------------------
with tab_track:
    st.subheader("Track Complaint Status")
    st.caption("The transparency loop that's usually missing — citizens can see what happened after they reported an issue.")

    f1, f2, f3 = st.columns(3)
    filt_ward = f1.selectbox("Filter by Ward", ["All"] + wards_df["ward"].tolist())
    filt_status = f2.selectbox("Filter by Status", ["All"] + STATUSES)
    search_id = f3.text_input("Search Complaint ID", placeholder="CMP-0001")

    view = st.session_state.complaints_df.copy()
    if filt_ward != "All":
        view = view[view["ward"] == filt_ward]
    if filt_status != "All":
        view = view[view["status"] == filt_status]
    if search_id:
        view = view[view["complaint_id"].str.contains(search_id.strip(), case=False)]

    view = view.sort_values("submitted_at", ascending=False)
    st.dataframe(
        view[["complaint_id", "ward", "category", "language", "channel",
              "translated_text", "urgency", "status", "submitted_at"]],
        use_container_width=True, hide_index=True, height=450,
    )

    status_counts = st.session_state.complaints_df["status"].value_counts().reindex(STATUSES).fillna(0)
    fig_status = px.bar(x=STATUSES, y=status_counts.values,
                         labels={"x": "Status", "y": "Count"},
                         title="Pipeline: Received → Resolved")
    st.plotly_chart(fig_status, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 4 — About
# ---------------------------------------------------------------------------
with tab_about:
    st.subheader("How this maps to the BRICS challenge brief")
    st.markdown("""
| Layer | What it does | In this prototype | In production |
|---|---|---|---|
| **Omnichannel ingestion** | Collects requests via voice, text, messaging apps | Web form simulating WhatsApp/IVR/SMS intake | WhatsApp Business API, Twilio IVR, USSD gateway |
| **Multilingual understanding** | Understands citizens in their own language | Sample phrase bank per language/category | Whisper ASR + multilingual LLM for translation & intent extraction |
| **Data fusion** | Joins feedback with demographic & infra data | Synthetic ward dataset (population, infra index, budget) | National census APIs, infra indices, public investment plan data |
| **Prioritization engine** | Ranks needs objectively and transparently | Explainable weighted-sum formula (`scoring.py`) | Same principle, calibrated with policymaker input, auditable |
| **Policymaker dashboard** | Surfaces hotspots and recommendations | Map + ranked list + "why" explanations | Same, integrated into e-governance systems |
| **Public accountability** | Citizens see what happened to their request | Status tracker tab | Same, linked to real project execution data |

**Digital Public Good principles honored:**
- Open architecture, no vendor lock-in
- Low-bandwidth channels supported (SMS/USSD), not just smartphone apps
- Data sovereignty — each nation would run its own instance
- Transparent, auditable scoring rather than a black-box AI decision
    """)
    st.info(
        "This is a working prototype with simulated data. The scoring "
        "weights in `scoring.py` are adjustable — try changing them to see "
        "how priorities shift."
    )
