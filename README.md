# Trustworthy Brief Crew

A CrewAI project that produces a source-attributed research brief, and **returns nothing** if an
auditor agent cannot confirm it. Includes a Streamlit UI, a CLI, a typed schema, run traces and tests.

```
Researcher ──▶ Analyst ──▶ Writer ──▶ Critic ──▶ gate ──▶ Brief (or nothing)
primary        contradicts  800 words,  PASS / FAIL
sources        the research every claim
                            attributed
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate     # Python 3.10 to 3.13
pip install -r requirements.txt
cp .env.example .env                                  # add OPENAI_API_KEY and SERPER_API_KEY
streamlit run app.py                                  # UI (toggle "Demo mode" to explore without keys)
python -m brief_crew.cli "your topic" --verbose       # CLI; run verbose the first time
pytest                                                # tests, no API keys needed
```

Run from the project root; for the CLI use `PYTHONPATH=src`.

## The agents

| Agent | Role | Goal |
|---|---|---|
| 1 | Senior Research Analyst | Find primary sources, not blog posts |
| 2 | Contrarian Analyst | Find what contradicts the research |
| 3 | Brief Writer | Two-page brief, every claim attributed |
| 4 | Source Auditor | Mark the brief against the sources: PASS or FAIL |

## Tasks: description, expected_output, owner

Every task sets all three. `expected_output` is the contract. The writer's reads:
*a brief under 800 words, with a source URL for every claim, and a section listing what could not be verified.*
The handoffs use `context=[...]`: research feeds the analyst; research and contradictions feed the writer;
everything feeds the critic. Watch these in verbose mode, because that is where quality leaks.

## Four lines of defence

| # | Defence | Where | What it does |
|---|---|---|---|
| 1 | Hard stops | `config.py`, `crew.py` | `max_iter` (capped at 10 in code) and `max_rpm` on every agent. Loops fail loudly. |
| 2 | Critic agent | `crew.py`, `guardrails.release` | A fourth agent returns PASS or FAIL. FAIL raises `CriticFailed`; no brief is returned. |
| 3 | Typed output | `schemas.py` | `output_pydantic=Brief` on the writer, `CriticVerdict` on the critic. Bad shape means an error. URLs are validated. |
| 4 | Traces | `tracing.py` | Every step, task, verdict and token count appended to `traces/<run>.jsonl` as it happens. |

Beyond the model-based critic, `check_brief` applies deterministic rules (word limit, duplicates, required
"could not verify" section) that no model can talk its way past.

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `MODEL` | `gpt-4o` | Any model string CrewAI accepts |
| `MAX_ITER` | 10 | Cannot exceed 10 |
| `MAX_RPM` | 10 | Requests per minute per agent |
| `MAX_WORDS` | 800 | Enforced in code and stated in the task contract |
| `TRACE_DIR` | `traces` | |

Without `SERPER_API_KEY` the agents run with no search tools and rely on model knowledge. Treat that as
a smoke test only; the critic will usually FAIL it.

## Exit codes (CLI)

`0` released, `2` critic FAIL, `3` guardrail violation.

## Project layout

```
app.py                     Streamlit UI
src/brief_crew/            schemas, guardrails, tracing, crew, config, demo, cli
tests/                     33 tests; crewai-dependent ones skip if it isn't installed
docs/ARCHITECTURE.md       design notes and extension guide
```

## Honest limits

The output of a crew like this looks confident whether or not it is right. The critic checks the brief
against the research it was given, not against ground truth. Read the trace, and open the source URLs for
anything that matters.
