import streamlit as st
from connectors.hubspot import HubSpotConnector
from connectors.pipedrive import PipedriveConnector
from connectors.mock import MockConnector
from core.discovery import SchemaDiscovery
from core.translator import QueryTranslator
import json

st.set_page_config(
    page_title="Treelife AI — Business Data Layer",
    page_icon="🌿",
    layout="wide"
)

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Sora:wght@600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main { background: #0d0f12; }
    .block-container { padding: 2rem 3rem; max-width: 900px; }

    h1, h2, h3 { font-family: 'Sora', sans-serif; }

    .brand-header {
        display: flex; align-items: center; gap: 12px;
        margin-bottom: 0.25rem;
    }
    .brand-title {
        font-family: 'Sora', sans-serif;
        font-size: 1.8rem; font-weight: 700;
        color: #e8f5e9; letter-spacing: -0.5px;
    }
    .brand-sub {
        font-size: 0.85rem; color: #6b7280;
        margin-bottom: 2rem;
    }

    .step-label {
        font-size: 0.7rem; font-weight: 600; letter-spacing: 1.5px;
        text-transform: uppercase; color: #4ade80;
        margin-bottom: 0.4rem;
    }

    .schema-card {
        background: #111418; border: 1px solid #1e2530;
        border-radius: 10px; padding: 1.2rem 1.5rem;
        margin: 1rem 0;
    }
    .schema-card h4 {
        color: #cbd5e1; font-size: 0.85rem;
        font-weight: 600; margin: 0 0 0.6rem 0;
    }
    .schema-pill {
        display: inline-block;
        background: #1a2332; color: #7dd3fc;
        border: 1px solid #1e3a5f;
        border-radius: 999px; font-size: 0.72rem;
        padding: 2px 10px; margin: 2px 3px 2px 0;
    }

    .answer-box {
        background: #0f1e12; border: 1px solid #166534;
        border-left: 4px solid #4ade80;
        border-radius: 10px; padding: 1.4rem 1.6rem;
        margin: 1.2rem 0;
    }
    .answer-number {
        font-family: 'Sora', sans-serif;
        font-size: 2.2rem; font-weight: 700;
        color: #4ade80; line-height: 1;
        margin-bottom: 0.3rem;
    }
    .answer-text { color: #d1fae5; font-size: 1rem; }

    .reasoning-box {
        background: #111418; border: 1px solid #1e2530;
        border-radius: 10px; padding: 1.2rem 1.5rem;
        margin: 0.8rem 0;
    }
    .reasoning-label {
        font-size: 0.7rem; font-weight: 600; letter-spacing: 1px;
        text-transform: uppercase; color: #94a3b8;
        margin-bottom: 0.6rem;
    }
    .reasoning-text { color: #94a3b8; font-size: 0.88rem; line-height: 1.6; }

    .warning-box {
        background: #1a1200; border: 1px solid #713f12;
        border-left: 4px solid #f59e0b;
        border-radius: 10px; padding: 1rem 1.4rem;
        color: #fde68a; font-size: 0.88rem; margin: 0.8rem 0;
    }
    .error-box {
        background: #1a0808; border: 1px solid #7f1d1d;
        border-left: 4px solid #f87171;
        border-radius: 10px; padding: 1rem 1.4rem;
        color: #fca5a5; font-size: 0.88rem; margin: 0.8rem 0;
    }

    .divider { border: none; border-top: 1px solid #1e2530; margin: 1.5rem 0; }

    .stTextInput > div > div > input {
        background: #111418 !important;
        border: 1px solid #1e2530 !important;
        color: #e2e8f0 !important;
        border-radius: 8px !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #4ade80 !important;
        box-shadow: 0 0 0 2px rgba(74,222,128,0.15) !important;
    }
    .stSelectbox > div > div {
        background: #111418 !important;
        border: 1px solid #1e2530 !important;
        color: #e2e8f0 !important;
        border-radius: 8px !important;
    }
    .stButton > button {
        background: #166534 !important;
        color: #d1fae5 !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.5rem !important;
        transition: background 0.2s !important;
    }
    .stButton > button:hover {
        background: #15803d !important;
    }

    .example-chip {
        display: inline-block;
        background: #111418; border: 1px solid #1e2530;
        color: #94a3b8; border-radius: 6px;
        font-size: 0.78rem; padding: 4px 10px;
        margin: 3px 4px 3px 0; cursor: pointer;
    }

    .platform-badge {
        display: inline-block;
        background: #1a2332; color: #7dd3fc;
        border: 1px solid #1e3a5f;
        border-radius: 6px; font-size: 0.75rem;
        padding: 3px 10px; margin-right: 6px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="brand-header">
    <span style="font-size:1.8rem">🌿</span>
    <span class="brand-title">Treelife AI</span>
</div>
<div class="brand-sub">
    Semantic Business Data Layer &nbsp;·&nbsp;
    <span class="platform-badge">HubSpot</span>
    <span class="platform-badge">Pipedrive</span>
    <span class="platform-badge">Mock Demo</span>
</div>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
if "schema_map" not in st.session_state:
    st.session_state.schema_map = None
if "connector" not in st.session_state:
    st.session_state.connector = None
if "platform" not in st.session_state:
    st.session_state.platform = None
if "history" not in st.session_state:
    st.session_state.history = []

# ── Step 1: Connect ───────────────────────────────────────────────────────────
st.markdown('<div class="step-label">Step 1 — Connect your platform</div>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 2])

with col1:
    platform = st.selectbox(
        "Platform",
        ["Mock Demo (no API key needed)", "HubSpot", "Pipedrive"],
        label_visibility="collapsed"
    )

with col2:
    if platform == "Mock Demo (no API key needed)":
        st.markdown('<p style="color:#6b7280;font-size:0.85rem;padding-top:0.5rem">▶ Uses built-in messy demo data — no API key required</p>', unsafe_allow_html=True)
        api_key_input = ""
        groq_key = st.text_input("Your Groq API key", type="password", placeholder="gsk_...")
    else:
        api_key_input = st.text_input(
            f"{platform} API key",
            type="password",
            placeholder="Your API key...",
            label_visibility="collapsed"
        )
        groq_key = st.text_input("Your Groq API key", type="password", placeholder="gsk_...")

connect_clicked = st.button("Connect & Discover Schema")

if connect_clicked:
    if not groq_key and platform != "Mock Demo (no API key needed)":
        st.markdown('<div class="error-box">Please enter your Groq API key.</div>', unsafe_allow_html=True)
    elif platform != "Mock Demo (no API key needed)" and not api_key_input:
        st.markdown('<div class="error-box">Please enter your API key.</div>', unsafe_allow_html=True)
    else:
        with st.spinner("Connecting and discovering schema..."):
            try:
                if platform == "HubSpot":
                    connector = HubSpotConnector(api_key_input)
                elif platform == "Pipedrive":
                    connector = PipedriveConnector(api_key_input)
                else:
                    connector = MockConnector()

                raw_schema = connector.get_schema()
                sample_data = connector.get_sample_records(limit=20)

                discovery = SchemaDiscovery(groq_key if groq_key else None)
                semantic_map = discovery.build_semantic_map(raw_schema, sample_data, platform)

                st.session_state.schema_map = semantic_map
                st.session_state.connector = connector
                st.session_state.platform = platform
                st.session_state.groq_key = groq_key
                st.session_state.history = []

            except Exception as e:
                st.markdown(f'<div class="error-box">Connection failed: {str(e)}</div>', unsafe_allow_html=True)

# ── Show schema if connected ───────────────────────────────────────────────────
if st.session_state.schema_map:
    smap = st.session_state.schema_map
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="schema-card">
        <h4>✅ Connected · Schema discovered</h4>
        <div style="color:#6b7280;font-size:0.8rem;margin-bottom:0.8rem">
            {smap.get('summary', '')}
        </div>
    """, unsafe_allow_html=True)

    if smap.get("owner_fields"):
        pills = "".join([f'<span class="schema-pill">👤 {f}</span>' for f in smap["owner_fields"]])
        st.markdown(f'<div style="margin-bottom:0.5rem"><span style="color:#94a3b8;font-size:0.78rem">Owner fields: </span>{pills}</div>', unsafe_allow_html=True)

    if smap.get("status_fields"):
        pills = "".join([f'<span class="schema-pill">📊 {f["field"]} → {f["meaning"]}</span>' for f in smap["status_fields"][:5]])
        st.markdown(f'<div style="margin-bottom:0.5rem"><span style="color:#94a3b8;font-size:0.78rem">Status fields: </span>{pills}</div>', unsafe_allow_html=True)

    if smap.get("quirks"):
        for q in smap["quirks"]:
            st.markdown(f'<div style="color:#fde68a;font-size:0.78rem;margin-top:0.3rem">⚠ {q}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Step 2: Ask ────────────────────────────────────────────────────────────
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="step-label">Step 2 — Ask a question in plain English</div>', unsafe_allow_html=True)

    # Example questions
    examples = [
        "How many open deals does Garima own?",
        "Show all leads assigned to Ishan",
        "How many lost deals are there?",
        "Who has the most active deals?",
        "List all high priority deals",
    ]
    st.markdown("**Try an example:**", unsafe_allow_html=False)
    example_cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        with example_cols[i]:
            if st.button(ex, key=f"ex_{i}", use_container_width=True):
                st.session_state["prefill_question"] = ex

    question = st.text_input(
        "Your question",
        value=st.session_state.get("prefill_question", ""),
        placeholder="e.g. How many open deals does Garima own?",
        label_visibility="collapsed"
    )

    ask_clicked = st.button("Ask →", key="ask_btn")

    if ask_clicked and question:
        with st.spinner("Thinking..."):
            try:
                translator = QueryTranslator(st.session_state.groq_key)
                result = translator.answer(
                    question=question,
                    schema_map=st.session_state.schema_map,
                    connector=st.session_state.connector,
                    platform=st.session_state.platform
                )
                st.session_state.history.insert(0, {"q": question, "r": result})
                if "prefill_question" in st.session_state:
                    del st.session_state["prefill_question"]
            except Exception as e:
                st.markdown(f'<div class="error-box">Error: {str(e)}</div>', unsafe_allow_html=True)

    # ── History ────────────────────────────────────────────────────────────────
    for item in st.session_state.history:
        q = item["q"]
        r = item["r"]
        st.markdown(f'<div style="color:#6b7280;font-size:0.82rem;margin-top:1.2rem">❓ {q}</div>', unsafe_allow_html=True)

        if r.get("error"):
            st.markdown(f'<div class="error-box">{r["error"]}</div>', unsafe_allow_html=True)
        elif r.get("warning"):
            st.markdown(f'<div class="warning-box">{r["warning"]}</div>', unsafe_allow_html=True)
        else:
            answer_html = f"""
            <div class="answer-box">
                <div class="answer-number">{r.get('headline', '')}</div>
                <div class="answer-text">{r.get('answer', '')}</div>
            </div>
            """
            st.markdown(answer_html, unsafe_allow_html=True)

        if r.get("reasoning"):
            st.markdown(f"""
            <div class="reasoning-box">
                <div class="reasoning-label">How I got there</div>
                <div class="reasoning-text">{r['reasoning']}</div>
            </div>
            """, unsafe_allow_html=True)

        if r.get("records") and len(r["records"]) > 0:
            with st.expander(f"View {len(r['records'])} record(s)"):
                st.dataframe(r["records"], use_container_width=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
