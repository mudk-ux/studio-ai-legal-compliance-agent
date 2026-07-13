"""
app_adk2_studio.py: Next-Generation Google ADK 2.0 Multi-Agent & HITL Executive Studio.
100% Pure Cloud-Native Dark-Mode Glassmorphism UI identical in aesthetics to `app.py`.
Connects directly to serverless container `ReasoningEngine 8283630993466720256` on
Gemini Enterprise Agent Platform (formerly Vertex AI).
"""

import json
import os
import re
import sys
import time
import streamlit as st
from google.cloud import storage
import vertexai
from vertexai.preview import reasoning_engines

# Target Remote Serverless Container Configuration
PROJECT_ID = "your-gcp-project-id"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://your-staging-bucket"
RESOURCE_NAME = "projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID"

st.set_page_config(
    page_title="Studio AI | ADK 2.0 Multi-Agent & HITL Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)


def determine_clearance_status(clean_resp: str) -> tuple:
    """Dynamically parses itemized findings to determine clearance and sign-off recommendation."""
    try:
        report = json.loads(clean_resp)
        findings = []
        for k, v in report.items():
            if isinstance(v, list):
                findings.extend(v)
        if any(isinstance(f, dict) and f.get("severity") == "CRITICAL" for f in findings):
            return (
                "BLOCKED",
                "blocked",
                "🚫",
                "🚫 Sign-Off Recommendation: DO NOT DISTRIBUTE. Critical Standards & Practices (S&P) or Sponsor Exclusivity violations detected. Mandatory VFX paint-out or asset substitution required."
            )
        if any(isinstance(f, dict) and f.get("severity") in ("HIGH", "MEDIUM") for f in findings):
            return (
                "CONDITIONAL_CLEARANCE",
                "flagged",
                "⚠️",
                "⚠️ Sign-Off Recommendation: CONDITIONAL BROADCAST CLEARANCE. Review flagged E&O right-of-publicity or secondary trademark mentions."
            )
    except Exception:
        pass

    resp_upper = clean_resp.upper()
    if any(p in resp_upper for p in ['"OVERALL_STATUS": "BLOCKED"', "CRITICAL"]):
        return (
            "BLOCKED",
            "blocked",
            "🚫",
            "🚫 Sign-Off Recommendation: DO NOT DISTRIBUTE. Critical Standards & Practices (S&P) or Sponsor Exclusivity violations detected."
        )
    return (
        "CLEARED",
        "cleared",
        "✅",
        "✅ Sign-Off Recommendation: APPROVED FOR BROADCAST. No critical copyright infringements or un-cleared competitor trademarks detected."
    )


# Obsidian Dark-Mode Glassmorphism CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@400;600;700;800&display=swap');

    .stApp {
        background: radial-gradient(circle at 15% 15%, #0d1527 0%, #060913 50%, #030509 100%);
        color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    .hero-container {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 18px;
        padding: 2.2rem 2.8rem;
        margin-bottom: 2rem;
        backdrop-filter: blur(20px);
        position: relative;
        overflow: hidden;
    }
    .hero-container::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899, #10b981);
    }
    .hero-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(130deg, #ffffff 40%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 0 0.4rem 0;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        margin: 0;
    }
    .cloud-verdict-box {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 14px;
        overflow: hidden;
        margin-top: 1.5rem;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    }
    .cloud-verdict-header {
        background: rgba(30, 41, 59, 0.6);
        padding: 0.9rem 1.4rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.15);
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 600;
    }
    .cloud-verdict-body {
        padding: 1.4rem;
        max-height: 480px;
        overflow-y: auto;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        background: rgba(2, 6, 23, 0.9);
    }
    .cloud-verdict-footer {
        padding: 1.1rem 1.4rem;
        font-weight: 700;
        font-size: 0.95rem;
        border-top: 1px solid rgba(148, 163, 184, 0.15);
    }
    .footer-cleared { background: rgba(16, 185, 129, 0.15); color: #34d399; }
    .footer-blocked { background: rgba(239, 68, 68, 0.15); color: #f87171; }
    .footer-flagged { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }

    .hitl-modal {
        background: rgba(127, 29, 29, 0.35);
        border: 2px solid #f43f5e;
        border-radius: 16px;
        padding: 1.8rem;
        margin: 1.5rem 0;
        box-shadow: 0 15px 35px rgba(244, 63, 94, 0.2);
    }
    .adk-trace-card {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 12px;
        padding: 1.2rem;
        margin-top: 1.2rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
    }
</style>

<div class="hero-container">
    <div class="hero-title">🎬 Studio AI | 100% Cloud-Native Legal & VFX Clearance</div>
    <div class="hero-subtitle">
        Pure Serverless ADK 2.0 Multi-Agent Graph (Automatic GCS Staging + Gemini Enterprise Agent Platform)
    </div>
    <div style="margin-top: 0.6rem;">
        <span style="background: rgba(56, 189, 248, 0.15); border: 1px solid #38bdf8; border-radius: 6px; padding: 3px 10px; font-size: 0.78rem; color: #38bdf8;">
            ☁️ REASONING ENGINE: 8283630993466720256
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SIDEBAR INTAKE FORM
# ---------------------------------------------------------------------------
st.sidebar.markdown("### 📋 Studio Intake & Sponsor Exclusivity Matrix")
mode_choice = st.sidebar.radio(
    "Load Studio Asset:",
    ["Custom Drag-and-Drop Upload", "Select Benchmark Media Asset"]
)

uploaded_file = None
selected_preset = None

if mode_choice == "Custom Drag-and-Drop Upload":
    uploaded_file = st.sidebar.file_uploader(
        "Drop Media Asset (.mp4, .mov, .jpg, .txt)",
        type=["mp4", "mov", "jpg", "jpeg", "png", "txt"]
    )
else:
    selected_preset = st.sidebar.selectbox(
        "Select Benchmark Media Asset:",
        [
            "Luxury Handbag Wardrobe (.jpg) — Static Prop Exclusivity Audit (CRITICAL HITL PAUSE)",
            "The Social Network (.txt) — 110-Page Feature Script Docudrama Vetting",
            "Good Will Hunting (.txt) — 110-Page Feature Script Docudrama Vetting",
            "1960s Winston Commercial (.mp4) — Temporal Video Exclusivity Breach",
        ]
    )

show_title = st.sidebar.text_input("Show Title / Production Context:", "Primetime Feature Broadcast Special")
target_rating = st.sidebar.selectbox("Target Broadcast Rating:", ["TV-PG", "TV-14", "TV-MA", "R"])
primary_sponsor = st.sidebar.text_input("Primary Protected Sponsor:", "Gucci" if selected_preset and "Luxury Handbag" in selected_preset else "Starbucks")
restricted_brands_input = st.sidebar.text_input("Restricted Competitor Brands:", "Louis Vuitton, Prada, Chanel" if selected_preset and "Luxury Handbag" in selected_preset else "Dunkin' Donuts, Winston, Louis Vuitton")
vetting_instructions = st.sidebar.text_area(
    "Legal & S&P HITL Vetting Instructions:",
    "Audit full asset for broadcast Standards & Practices (S&P) rules and sponsor exclusivity conflicts. Flag un-cleared competitor mentions or logos and require VFX removal."
)

# ---------------------------------------------------------------------------
# MAIN EXECUTION & PREVIEW SECTION
# ---------------------------------------------------------------------------
st.markdown("### 🖥️ Active Media Asset Preview")

local_path = None
asset_type = None
cloud_asset_uri = None

if mode_choice == "Custom Drag-and-Drop Upload" and uploaded_file is not None:
    temp_dir = "/tmp/studio_ai_adk2_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    local_path = os.path.join(temp_dir, uploaded_file.name)
    with open(local_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    ext = uploaded_file.name.lower()
    if ext.endswith((".mp4", ".mov")):
        asset_type = "TEMPORAL_VIDEO"
        st.video(local_path)
    elif ext.endswith((".jpg", ".jpeg", ".png")):
        asset_type = "VISUAL_IMAGE"
        st.image(local_path, width=420, caption=f"Uploaded: {uploaded_file.name}")
    else:
        asset_type = "TEXT_SCREENPLAY"
        with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
            prev = f.read()[:2600]
        st.code(prev, language="text")

elif mode_choice == "Select Benchmark Media Asset" and selected_preset:
    preset_map = {
        "Luxury Handbag Wardrobe": ("sample_data/new_suite_2/mock_luxury_handbag.jpg", "VISUAL_IMAGE"),
        "The Social Network": ("sample_data/old_suite_1/social_network_script.txt", "TEXT_SCREENPLAY"),
        "Good Will Hunting": ("sample_data/new_suite_2/good_will_hunting_script.txt", "TEXT_SCREENPLAY"),
        "1960s Winston Commercial": ("sample_data/new_suite_2/elephantsdream_teaser.mp4", "TEMPORAL_VIDEO"),
    }
    key = next(k for k in preset_map if k in selected_preset)
    local_path, asset_type = preset_map[key]

    if asset_type == "VISUAL_IMAGE":
        st.image(local_path, width=420, caption=f"Benchmark Asset: {key}")
    elif asset_type == "TEMPORAL_VIDEO":
        st.video(local_path)
    else:
        with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
            prev = f.read()[:2600]
        st.code(prev, language="text")

# ---------------------------------------------------------------------------
# SERVERLESS CLOUD EXECUTION BUTTON
# ---------------------------------------------------------------------------
st.markdown("---")

if local_path and os.path.exists(local_path):
    if st.button("🚀 Execute Pure Cloud ADK 2.0 Multi-Agent Evaluation", use_container_width=True, type="primary"):
        with st.spinner("Staging media to GCS & executing ADK 2.0 multi-agent graph on Gemini Enterprise Agent Platform..."):
            client = storage.Client(project=PROJECT_ID)
            bucket = client.bucket("your-staging-bucket")
            blob_name = f"intake_uploads/{int(time.time())}_{os.path.basename(local_path)}"
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(local_path)
            cloud_asset_uri = f"gs://your-staging-bucket/{blob_name}"

            constraints = {
                "show_context": show_title,
                "target_rating": target_rating,
                "exclusivity_deals": {
                    "primary_sponsor": primary_sponsor,
                    "restricted_competitors": [c.strip() for c in restricted_brands_input.split(",")]
                }
            }

            vertexai.init(project=PROJECT_ID, location=LOCATION)
            remote_engine = reasoning_engines.ReasoningEngine(RESOURCE_NAME)
            result = remote_engine.query(
                asset_path=cloud_asset_uri,
                asset_type=asset_type,
                constraints_data=constraints
            )

            clean_resp = json.dumps(result, indent=2)
            status_val, footer_cls, badge_icon, sign_off_text = determine_clearance_status(clean_resp)

            # 1. Universal Severity Status Banner
            if status_val == "CLEARED":
                st.success(f"### {badge_icon} STUDIO CLEARANCE VERDICT: CLEARED (Run ID: {result.get('run_id')})")
            elif status_val == "CONDITIONAL_CLEARANCE":
                st.warning(f"### {badge_icon} STUDIO CLEARANCE VERDICT: CONDITIONAL CLEARANCE (Run ID: {result.get('run_id')})")
            else:
                st.error(f"### {badge_icon} STUDIO CLEARANCE VERDICT: BLOCKED / CRITICAL INFRACTION (Run ID: {result.get('run_id')})")

            # 2. Check for Explicit Human-in-the-Loop (HITL) Execution Pause
            if result.get("hitl_interruption_triggered"):
                hitl = result["hitl_execution_pause"]
                st.markdown(f"""
                <div class="hitl-modal">
                    <h3 style="color: #fb7185; margin: 0 0 10px 0;">🛑 EXPLICIT HUMAN-IN-THE-LOOP (HITL) EXECUTION PAUSE HOOK</h3>
                    <p><b>Execution Status:</b> <code>{hitl.get('execution_status')}</code> | <b>Required Reviewer Role:</b> {hitl.get('required_role')}</p>
                    <p><b>Flagged Infringement:</b> {hitl.get('flagged_violation', {}).get('finding', '')}</p>
                    <p><b>Required Action:</b> {hitl.get('interactive_prompt', '')}</p>
                </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ CONFIRM & APPROVE VFX REMEDIATION SLATE", key="approve_btn"):
                        st.success("✔ Senior E&O Reviewer Sign-Off Confirmed. Releasing HITL Hold.")
                with c2:
                    if st.button("🚫 OVERRIDE & REJECT BROADCAST AIRING", key="reject_btn"):
                        st.error("🚫 Reviewer Rejected Airing. Asset permanently blocked.")

            # 3. Native ADK 2.0 Multi-Agent Execution Trace Card
            st.markdown("#### 🌐 Native ADK 2.0 Multi-Agent Execution Trace Flow")
            trace_json = json.dumps(result.get("adk_agent_execution_trace", []), indent=2)
            st.markdown(f'<div class="adk-trace-card"><pre>{trace_json}</pre></div>', unsafe_allow_html=True)

            # 4. Classic Combined Verdict Card (Option A Layout)
            st.markdown("#### 📊 Comprehensive Deliverable Report & Senior E&O Reviewer Sign-Off")
            st.markdown(f"""
            <div class="cloud-verdict-box">
                <div class="cloud-verdict-header">
                    <span>📡 PURE CLOUD ADK 2.0 COMPLIANCE DELIVERABLE (REASONING ENGINE 8283630993466720256)</span>
                    <span>RUN ID: {result.get('run_id')}</span>
                </div>
                <div class="cloud-verdict-body"><pre>{clean_resp}</pre></div>
                <div class="cloud-verdict-footer footer-{footer_cls}">
                    {sign_off_text}
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("👆 Select a Benchmark Media Asset or upload a custom file in the sidebar to execute the ADK 2.0 Multi-Agent evaluation.")
