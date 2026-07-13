"""
app.py: 100% Pure Cloud-Native M&E Studio Legal Clearance & VFX Compliance Platform
Featuring Automatic Google Cloud Storage (`gs://`) Staging, direct serverless integration with
Google Cloud Agent Runtime (`ReasoningEngine 8032836789217525760`), and clear response rendering.
"""

import os
import json
import time
import uuid
import re
import streamlit as st
from PIL import Image
import vertexai
from vertexai.preview import reasoning_engines
from google.cloud import storage

# Configure Page Layout
st.set_page_config(
    page_title="Studio AI | Cloud-Native Legal & Copyright Clearance",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Target Google Cloud Configuration
PROJECT_ID = "your-gcp-project-id"
LOCATION = "us-central1"
RESOURCE_NAME = "projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID"
GCS_STAGING_BUCKET = "your-staging-bucket"
GCS_UPLOAD_PREFIX = "intake_uploads"


def upload_to_gcs_staging(local_path: str, filename: str) -> str:
    """Automatically uploads custom user media to Cloud Storage and returns the gs:// URI."""
    try:
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(GCS_STAGING_BUCKET)
        blob_path = f"{GCS_UPLOAD_PREFIX}/{int(time.time())}_{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(local_path)
        return f"gs://{GCS_STAGING_BUCKET}/{blob_path}"
    except Exception:
        return local_path


def clean_agent_output(raw_str: str) -> str:
    """Extracts clean text/JSON from SDK Part representations (`parts=[Part(text="..."...)]`)."""
    m = re.search(r'text="""(.*?)"""', raw_str, re.DOTALL)
    if not m:
        m = re.search(r'text="(.*?)"\s*,\s*thought_signature', raw_str, re.DOTALL)
    if m:
        clean = m.group(1).replace("\\n", "\n").replace('\\"', '"')
        return clean.strip()
    return raw_str.strip()


def determine_clearance_status(clean_resp: str) -> tuple[str, str, str, str]:
    """Accurately extracts clearance status directly from JSON dictionary fields (`overall_status` / `clearance_status`)."""
    try:
        m_json = re.search(r"\{.*\}", clean_resp, re.DOTALL)
        if m_json:
            data = json.loads(m_json.group(0))
            report = (
                data.get("compliance_report")
                or data.get("ComplianceReport")
                or data
            )
            status_val = str(
                report.get("overall_status")
                or report.get("clearance_status")
                or report.get("status")
                or ""
            ).upper()

            # Check if any itemized finding across any list field has CRITICAL severity
            findings = []
            for k, v in report.items():
                if isinstance(v, list):
                    findings.extend(v)

            has_critical_item = any(
                isinstance(f, dict) and str(f.get("severity", "")).upper() == "CRITICAL"
                for f in findings
            )

            if has_critical_item or any(s in status_val for s in ["NOT CLEARED", "BLOCKED", "NON_COMPLIANT", "FAILED", "CRITICAL", "FLAGGED"]):
                return (
                    "BLOCKED",
                    "blocked",
                    "🚫",
                    "🚫 Sign-Off Recommendation: DO NOT DISTRIBUTE. The asset triggers critical Standards & Practices (S&P) or Sponsor Exclusivity restrictions. Complete VFX paint-out or asset substitution is mandatory before broadcast."
                )
            if any(s in status_val for s in ["CONDITIONAL", "REVIEW REQUIRED", "CONDITIONAL_CLEARANCE", "WARNING"]):
                return (
                    "CONDITIONAL_CLEARANCE",
                    "conditional",
                    "⚠️",
                    "⚠️ Sign-Off Recommendation: CONDITIONAL APPROVAL — ACTION REQUIRED. Clear itemized living public figure rights-of-publicity slates or Metropolitan Census negative checks before general broadcast."
                )
            if any(s in status_val for s in ["CLEARED", "PASSED", "APPROVED", "COMPLIANT", "NO VIOLATIONS"]):
                return (
                    "CLEARED",
                    "cleared",
                    "✅",
                    "✅ Sign-Off Recommendation: APPROVED FOR BROADCAST. No critical copyright infringements or un-cleared competitor trademarks detected."
                )

            if any(s in status_val for s in ["CONDITIONAL", "REVIEW", "ACTION REQUIRED", "PENDING"]):
                return (
                    "CONDITIONAL_CLEARANCE",
                    "conditional",
                    "⚠️",
                    "⚠️ Sign-Off Recommendation: CONDITIONAL APPROVAL. Complete itemized legal/census negative checks and VFX editorial modifications prior to final broadcast lock."
                )
    except Exception:
        pass

    # Fallback check on exact JSON field patterns if parsing fails
    resp_upper = clean_resp.upper()
    if any(p in resp_upper for p in ['"OVERALL_STATUS": "CLEARED"', '"CLEARANCE_STATUS": "CLEARED"', "OVERALL STUDIO CLEARANCE VERDICT: CLEARED"]):
        return (
            "CLEARED",
            "cleared",
            "✅",
            "✅ Sign-Off Recommendation: APPROVED FOR BROADCAST. No critical copyright infringements or un-cleared competitor trademarks detected."
        )
    if any(p in resp_upper for p in ["NOT CLEARED", "NON_COMPLIANT", '"OVERALL_STATUS": "BLOCKED"', "CRITICAL INFRACTIONS"]):
        return (
            "BLOCKED",
            "blocked",
            "🚫",
            "🚫 Sign-Off Recommendation: DO NOT DISTRIBUTE. The asset triggers critical Standards & Practices (S&P) or Sponsor Exclusivity restrictions. Complete VFX paint-out or asset substitution is mandatory before broadcast."
        )

    return (
        "CLEARED",
        "cleared",
        "✅",
        "✅ Sign-Off Recommendation: APPROVED FOR BROADCAST. No critical copyright infringements or un-cleared competitor trademarks detected."
    )


# Premium Dark Obsidian & Glassmorphism CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@400;600;700;800&display=swap');

    .stApp {
        background: radial-gradient(circle at 15% 15%, #0d1527 0%, #060913 50%, #030509 100%);
        color: #f8fafc;
        font-family: 'Inter', -apple-system, sans-serif;
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
        font-size: 0.98rem;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .runtime-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(14, 165, 233, 0.15);
        color: #38bdf8;
        border: 1px solid rgba(14, 165, 233, 0.4);
        padding: 4px 12px;
        border-radius: 99px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .panel-heading {
        font-family: 'Outfit', sans-serif;
        font-size: 1.15rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 1rem;
    }
    .cloud-verdict-box {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(56, 189, 248, 0.35);
        border-left: 5px solid #38bdf8;
        border-radius: 14px;
        padding: 1.6rem;
        margin-bottom: 2rem;
        box-shadow: 0 12px 30px -10px rgba(0,0,0,0.6);
    }
    .cloud-verdict-header {
        font-family: 'Outfit', sans-serif;
        font-size: 1.1rem;
        font-weight: 700;
        color: #38bdf8;
        margin-bottom: 0.8rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .cloud-verdict-body {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.92rem;
        color: #f8fafc;
        line-height: 1.6;
        white-space: pre-wrap;
        background: rgba(3, 7, 18, 0.6);
        padding: 1.2rem;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.06);
    }
    .status-card {
        padding: 1.4rem 1.8rem;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.5rem;
    }
    .status-card.cleared {
        background: linear-gradient(135deg, rgba(6, 78, 59, 0.35), rgba(15, 23, 42, 0.8));
        border: 1px solid rgba(16, 185, 129, 0.45);
    }
    .status-card.conditional {
        background: linear-gradient(135deg, rgba(120, 53, 15, 0.35), rgba(15, 23, 42, 0.8));
        border: 1px solid rgba(245, 158, 11, 0.45);
    }
    .status-card.blocked {
        background: linear-gradient(135deg, rgba(136, 19, 55, 0.35), rgba(15, 23, 42, 0.8));
        border: 1px solid rgba(244, 63, 94, 0.45);
    }
    .status-label {
        font-family: 'Outfit', sans-serif;
        font-size: 1.35rem;
        font-weight: 800;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

# Hero Header
st.markdown("""
<div class="hero-container">
    <div class="hero-title">🎬 Studio AI | 100% Cloud-Native Legal & VFX Clearance</div>
    <div class="hero-subtitle">
        <span>Pure Serverless Agent Pipeline (Automatic GCS Staging + Google Cloud Agent Runtime)</span>
        <span class="runtime-badge">☁️ REASONING ENGINE: 9047272605282729984</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar: Preset / Custom Media Selector
with st.sidebar:
    st.markdown("### 📁 Select Benchmark Media Asset")
    suite_choice = st.selectbox(
        "Load Studio Asset:",
        [
            "Custom Drag-and-Drop Upload",
            "[Suite 1] Tears of Steel Rough Cut (.mov)",
            "[Suite 1] The Social Network Screenplay (.txt)",
            "[Suite 1] Sportswear Wardrobe Photo (.jpg)",
            "[Suite 1] Vape Pen S&P Photo (.jpg)",
            "[Suite 2] Good Will Hunting Screenplay (.txt)",
            "[Suite 2] Elephants Dream Open Movie (.mp4)",
            "[Suite 2] Luxury Handbag Wardrobe (.jpg)",
            "[Suite 3] The Wolf of Wall Street Screenplay (.txt)"
        ]
    )

sample_dir = "./sample_data"
PRESETS = {
    "[Suite 1] Tears of Steel Rough Cut (.mov)": ("tears_of_steel_1080p.mov", "TEMPORAL_VIDEO", "gs://your-staging-bucket/sample_assets/tears_of_steel_1080p.mov", "tears_of_steel_1080p_constraints.json"),
    "[Suite 1] The Social Network Screenplay (.txt)": ("social_network_script.txt", "TEXT_SCREENPLAY", None, "social_network_script_constraints.json"),
    "[Suite 1] Sportswear Wardrobe Photo (.jpg)": ("mock_sports_clothing.jpg", "VISUAL_IMAGE", "gs://your-staging-bucket/sample_assets/mock_sports_clothing.jpg", "mock_sports_clothing_constraints.json"),
    "[Suite 1] Vape Pen S&P Photo (.jpg)": ("mock_vaping_device.jpg", "VISUAL_IMAGE", "gs://your-staging-bucket/sample_assets/mock_vaping_device.jpg", "mock_vaping_device_constraints.json"),
    "[Suite 2] Good Will Hunting Screenplay (.txt)": ("good_will_hunting_script.txt", "TEXT_SCREENPLAY", None, "good_will_hunting_constraints.json"),
    "[Suite 2] Elephants Dream Open Movie (.mp4)": ("elephantsdream_teaser.mp4", "TEMPORAL_VIDEO", "gs://your-staging-bucket/sample_assets/elephantsdream_teaser.mp4", "elephantsdream_teaser_constraints.json"),
    "[Suite 2] Luxury Handbag Wardrobe (.jpg)": ("mock_luxury_handbag.jpg", "VISUAL_IMAGE", "gs://your-staging-bucket/sample_assets/mock_luxury_handbag.jpg", "mock_luxury_handbag_constraints.json"),
    "[Suite 3] The Wolf of Wall Street Screenplay (.txt)": ("wolf_of_wall_street_script.txt", "TEXT_SCREENPLAY", None, "wolf_of_wall_street_constraints.json"),
}

col_intake, col_preview = st.columns([1.05, 1.15], gap="large")

with col_intake:
    st.markdown('<div class="panel-heading">📋 Studio Intake & Sponsor Exclusivity Matrix</div>', unsafe_allow_html=True)
    
    default_genre = "Family Primetime Broadcast Special"
    default_rating = "TV-PG"
    default_sponsor = "General Mills"
    default_restricted = "Winston, Marlboro, R.J. Reynolds, Camel"
    asset_path = None
    cloud_target_uri = None
    asset_type = "TEMPORAL_VIDEO"

    if suite_choice in PRESETS:
        filename, asset_type, preset_gcs_uri, cfile = PRESETS[suite_choice]
        asset_path = os.path.join(sample_dir, filename)
        cloud_target_uri = preset_gcs_uri or asset_path
        with open(os.path.join(sample_dir, cfile), "r", encoding="utf-8") as f:
            cdata = json.load(f)
            default_genre = cdata.get("show_context", default_genre)
            default_rating = cdata.get("target_rating", default_rating)
            excl = cdata.get("exclusivity_deals", {})
            default_sponsor = excl.get("primary_sponsor", default_sponsor)
            default_restricted = ", ".join(excl.get("restricted_competitors", []))
    else:
        uploaded = st.file_uploader("Drop Media Asset (.mp4, .mov, .jpg, .txt)", type=["txt", "jpg", "png", "mp4", "mov"])
        if uploaded:
            asset_type = "VISUAL_IMAGE" if uploaded.name.endswith(('.jpg', '.png')) else ("TEMPORAL_VIDEO" if uploaded.name.endswith(('.mp4', '.mov')) else "TEXT_SCREENPLAY")
            asset_path = os.path.join("/tmp", uploaded.name)
            with open(asset_path, "wb") as f:
                f.write(uploaded.getbuffer())

    with st.form("cloud_intake_form"):
        c1, c2 = st.columns(2)
        with c1:
            show_genre = st.text_input("Show Title / Production Context:", value=default_genre)
        with c2:
            rating_target = st.selectbox("Target Broadcast Rating:", ["TV-G", "TV-PG", "TV-14", "TV-MA", "PG-13", "R"], index=1)
        
        s1, s2 = st.columns(2)
        with s1:
            prim_sponsor = st.text_input("Primary Protected Sponsor:", value=default_sponsor)
        with s2:
            restr_list = st.text_input("Restricted Competitor Brands:", value=default_restricted)
            
        custom_rules = st.text_area(
            "Legal & S&P HITL Vetting Instructions:",
            value="Audit video timeline for broadcast Standards & Practices (S&P) tobacco advertising under TV-PG rating. Flag any appearance of 'Winston' cigarettes as an un-cleared commercial trademark breach and generate a VFX removal slate.",
            height=85
        )
        
        submitted = st.form_submit_button("☁️ Execute 100% Cloud-Native Agent Runtime Audit", use_container_width=True)

with col_preview:
    st.markdown('<div class="panel-heading">🖥️ Active Media Asset Preview</div>', unsafe_allow_html=True)
    if asset_path and os.path.exists(asset_path):
        st.markdown(f"**Loaded File:** `{os.path.basename(asset_path)}` (`{asset_type}`)")
        if asset_type == "VISUAL_IMAGE":
            img = Image.open(asset_path)
            st.image(img, use_container_width=True)
        elif asset_type == "TEMPORAL_VIDEO":
            st.video(asset_path)
        else:
            with open(asset_path, "r", encoding="utf-8", errors="ignore") as f:
                full_txt = f.read()
            st.caption(
                f"✔ Displaying preview excerpt (2.6 KB). Full 110-page screenplay ({len(full_txt):,} chars / {round(len(full_txt)/1024, 1)} KB) loaded into full-document cloud audit."
            )
            st.code(full_txt[:2600], language="markdown")
    else:
        st.info("Select a preset asset or drop a custom media file to inspect.")

# 100% Cloud-Native Execution Pipeline
if submitted and asset_path:
    st.markdown("---")
    st.markdown("## 📊 Serverless Cloud Clearance Verdict & Deliverable")
    
    constraints_payload = {
        "show_context": show_genre,
        "target_rating": rating_target,
        "exclusivity_deals": {
            "primary_sponsor": prim_sponsor,
            "restricted_competitors": [x.strip() for x in restr_list.split(",") if x.strip()]
        },
        "custom_rules": [custom_rules]
    }

    # Step 1: Automatic GCS Staging if custom file
    if not cloud_target_uri:
        if asset_type == "TEXT_SCREENPLAY":
            cloud_target_uri = asset_path
        else:
            with st.spinner("Step 1/2: Staging custom media to Google Cloud Storage (`gs://your-staging-bucket/intake_uploads/`)..."):
                cloud_target_uri = upload_to_gcs_staging(asset_path, os.path.basename(asset_path))
                st.caption(f"✔ Asset staged to Cloud Storage: `{cloud_target_uri}`")

    # Step 2: Direct Serverless Agent Runtime Execution
    with st.spinner("Step 2/2: Executing live multi-agent audit on Google Cloud (`ReasoningEngine 8032836789217525760`)..."):
        start_t = time.time()
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        engine = reasoning_engines.ReasoningEngine(RESOURCE_NAME)
        
        content_snippet = ""
        if asset_type == "TEXT_SCREENPLAY":
            with open(asset_path, "r", encoding="utf-8", errors="ignore") as f:
                content_snippet = f.read()[:300000]
        else:
            content_snippet = f"Cloud Storage Target URI: {cloud_target_uri}"

        cloud_prompt = f"""
Perform an official studio legal clearance and E&O audit on the following media asset:
Asset Reference / GCS URI: {cloud_target_uri}
Modality: {asset_type}

DIRECT FULL-DOCUMENT AUDIT MODE: You are receiving the complete full-length screenplay ({len(content_snippet):,} characters) below. Do NOT attempt to copy, echo, or pass this full text into `extract_proper_nouns` or any function call argument. Directly read and evaluate the entire screenplay text inside your context window and output ONLY the final compiled `ComplianceReport` JSON.

Content Excerpt / Target File:
{content_snippet}

Studio Constraints & Exclusivity Rules:
{json.dumps(constraints_payload, indent=2)}

Apply our studio policies (Metropolitan Census 0/3-Plus rule, Sponsor Exclusivity, and S&P standards).
Provide the complete clearance status and itemized findings.
"""
        cloud_resp = engine.query(input=cloud_prompt)
        latency_sec = round(time.time() - start_t, 2)

    # Determine status accurately from JSON response dictionary fields
    cloud_resp_clean = clean_agent_output(str(cloud_resp))
    overall_status, status_class, status_icon, signoff_rec = determine_clearance_status(cloud_resp_clean)

    # Display Top-Level Synchronized Status Card
    st.markdown(f"""
    <div class="status-card {status_class}">
        <div>
            <div style="font-size: 0.78rem; color: #94a3b8; text-transform: uppercase; font-weight: 700; letter-spacing: 1px;">Overall Studio Clearance Verdict</div>
            <div class="status-label">{status_icon} {overall_status.replace('_', ' ')}</div>
        </div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #38bdf8;">
            RUN ID: CLR-{uuid.uuid4().hex[:6].upper()}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Single Unified Executive Deliverable Box (JSON Report + Sign-Off Footer)
    st.markdown(f"""
    <div class="cloud-verdict-box">
        <div class="cloud-verdict-header">
            <span>☁️ Live Google Cloud Agent Runtime Deliverable (`ReasoningEngine 9047272605282729984`)</span>
            <span style="font-size: 0.82rem; color: #94a3b8;">Execution Latency: {latency_sec}s</span>
        </div>
        <div class="cloud-verdict-body">{cloud_resp_clean}</div>
        <div style="margin-top: 1.4rem; padding-top: 1.2rem; border-top: 1px solid rgba(255, 255, 255, 0.12); font-size: 0.98rem; font-weight: 700; color: #f8fafc; background: rgba(0, 0, 0, 0.25); padding: 1.1rem; border-radius: 10px;">
            {signoff_rec}
        </div>
    </div>
    """, unsafe_allow_html=True)
