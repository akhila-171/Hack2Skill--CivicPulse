# CivicPulse — BRICS Innovation Challenge Prototype

A working prototype of a scalable, multilingual AI platform that aggregates
citizen development requests and aligns them with infrastructure data to
recommend high-priority projects to policymakers.

## What's inside

- `data.py` — synthetic data generator (10 wards + 400 simulated multilingual
  complaints across WhatsApp/Voice/SMS/Web channels)
- `scoring.py` — the prioritization engine: a transparent, auditable formula
  combining complaint volume, population, infrastructure gap, and urgency
- `app.py` — the Streamlit dashboard (policymaker view, complaint submission,
  citizen status tracker, and an "About" tab mapping the prototype to the
  challenge brief)

## How to run it

1. Install dependencies (Python 3.9+):
   ```bash
   pip install -r requirements.txt
   ```
2. Launch the app:
   ```bash
   streamlit run app.py
   ```
3. It will open in your browser at `http://localhost:8501`

## What to try in the demo

- **Dashboard tab** — see the hotspot map and the ranked project priority
  list with plain-language "why" explanations for each ranking
- **Submit a Complaint tab** — add a new complaint in any language/ward and
  watch it immediately affect the ranking on the Dashboard
- **Track Status tab** — filter complaints by ward/status/ID, the
  citizen-facing accountability loop
- Open `scoring.py` and change the `weights` dict (complaints / population /
  infra_gap / urgency) to show judges the ranking logic is transparent and
  tunable, not a black box

## Extending toward production

Swap the simulated pieces for real integrations:
- `data.py`'s complaint generator → WhatsApp Business API / Twilio IVR / SMS
  gateway webhook
- `_sample_text()` translation stub → Whisper (speech-to-text) + a
  multilingual LLM for translation and intent extraction
- `WARDS` list → live census, infrastructure-index, and public investment
  plan datasets via government APIs
- Session-state dataframes → PostgreSQL + PostGIS for geospatial querying
  at scale
