"""Streamlit UI. Run: streamlit run app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st
from dotenv import load_dotenv

from brief_crew.config import Settings
from brief_crew.crew import run_brief
from brief_crew.demo import demo_result
from brief_crew.guardrails import CriticFailed, GuardrailViolation, count_words

load_dotenv()
st.set_page_config(page_title="Brief Crew", page_icon="🧾", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:wght@400;600;700&display=swap');
:root{--ink:#14213D;--muted:#5B6678;--line:#DDE2E9;--blue:#2457F5;--pass:#1B7F5C;--fail:#B42318;--amber:#B7791F;}
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif;color:var(--ink);}
.block-container{padding-top:2rem;max-width:1100px;}
h1.hero{font-family:'Source Serif 4',serif;font-weight:700;font-size:2.6rem;line-height:1.15;margin:0 0 .4rem;}
p.sub{color:var(--muted);font-size:1.05rem;max-width:60ch;margin:0 0 1.6rem;}
.verdict{border:1px solid var(--line);border-left:6px solid var(--pass);background:#fff;border-radius:6px;padding:.9rem 1.1rem;margin-bottom:1.2rem;}
.verdict.fail{border-left-color:var(--fail);}
.verdict b{font-size:1.05rem;}
.claim{background:#fff;border:1px solid var(--line);border-radius:6px;padding:.8rem 1rem;margin-bottom:.6rem;}
.claim a{color:var(--blue);font-size:.88rem;word-break:break-all;}
.gap{background:#FFF8EA;border:1px solid #F0DDB4;border-left:6px solid var(--amber);border-radius:6px;padding:.7rem 1rem;margin-bottom:.5rem;}
.brief{font-family:'Source Serif 4',serif;font-size:1.05rem;line-height:1.7;max-width:70ch;}
.stat{background:#fff;border:1px solid var(--line);border-radius:6px;padding:.7rem 1rem;}
.stat span{display:block;color:var(--muted);font-size:.8rem;}
.stat b{font-size:1.4rem;}
:focus-visible{outline:3px solid var(--blue)!important;outline-offset:2px;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<h1 class="hero">Briefs that show their sources, or don’t ship.</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub">Four agents research, challenge, write and audit. If the auditor returns FAIL, you get no brief.</p>',
    unsafe_allow_html=True,
)

env = Settings.from_env()
with st.sidebar:
    st.header("Run settings")
    model = st.text_input("Model", env.model)
    max_iter = st.slider("Max iterations per agent", 1, 10, env.max_iter)
    max_rpm = st.slider("Max requests per minute", 1, 60, env.max_rpm)
    max_words = st.slider("Word limit", 300, 1200, env.max_words, 50)
    verbose = st.toggle("Verbose logs (terminal)", env.verbose)
    demo = st.toggle("Demo mode (no API keys)", value=False)

topic = st.text_input("Topic", placeholder="e.g. Effect of remote work on productivity, 2020 to 2025")
go = st.button("Generate brief", type="primary", disabled=not topic.strip())

if go:
    settings = Settings.from_env(model=model, max_iter=max_iter, max_rpm=max_rpm, max_words=max_words, verbose=verbose)
    try:
        with st.status("Researcher, analyst, writer and auditor are working…", expanded=False):
            st.session_state["result"] = demo_result(topic) if demo else run_brief(topic, settings)
        st.session_state["error"] = None
    except CriticFailed as exc:
        st.session_state.update(result=None, error=("fail", exc.verdict.reasons, exc.verdict.unsupported_claims))
    except GuardrailViolation as exc:
        st.session_state.update(result=None, error=("blocked", exc.violations, []))
    except Exception as exc:  # fail loudly, with a fix
        st.session_state.update(result=None, error=("error", [f"{type(exc).__name__}: {exc}",
                                "Check your API keys in .env, or switch on Demo mode."], []))

err = st.session_state.get("error")
if err:
    kind, reasons, extra = err
    title = {"fail": "Critic returned FAIL. No brief released.", "blocked": "Guardrail blocked the brief.",
             "error": "The run failed."}[kind]
    items = "".join(f"<li>{r}</li>" for r in reasons + extra)
    st.markdown(f'<div class="verdict fail"><b>{title}</b><ul>{items}</ul></div>', unsafe_allow_html=True)

res = st.session_state.get("result")
if res:
    b, v = res.brief, res.verdict
    if res.demo:
        st.info("Demo mode: sample data, not real research.")
    st.markdown(
        f'<div class="verdict"><b>Critic: PASS</b><ul>{"".join(f"<li>{r}</li>" for r in v.reasons)}</ul></div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(4)
    stats = [("Claims", len(b.claims)), ("Contradictions", len(b.contradictions)),
             ("Unverified gaps", len(b.unverified)), ("Words", count_words(b.to_markdown()))]
    for col, (label, val) in zip(cols, stats):
        col.markdown(f'<div class="stat"><span>{label}</span><b>{val}</b></div>', unsafe_allow_html=True)

    t_brief, t_claims, t_gaps, t_trace = st.tabs(["Brief", "Claims and sources", "Contradictions and gaps", "Trace"])
    with t_brief:
        st.markdown(f'<div class="brief">{b.to_markdown()}</div>', unsafe_allow_html=False)
        st.download_button("Download markdown", b.to_markdown(), file_name="brief.md")
    with t_claims:
        for c in b.claims:
            st.markdown(f'<div class="claim">{c.text}<br><a href="{c.source_url}">{c.source_title or c.source_url}</a></div>',
                        unsafe_allow_html=True)
    with t_gaps:
        for x in b.contradictions:
            st.markdown(f'<div class="claim"><b>{x.claim}</b><br>{x.counter_evidence}<br>'
                        f'<a href="{x.source_url}">{x.source_url}</a></div>', unsafe_allow_html=True)
        for u in b.unverified:
            st.markdown(f'<div class="gap">Could not verify: {u}</div>', unsafe_allow_html=True)
    with t_trace:
        st.caption(f"Saved to {res.trace_path}  |  tokens: {res.token_usage.get('total_tokens', 'n/a')}")
        st.dataframe(res.trace_events, use_container_width=True)
