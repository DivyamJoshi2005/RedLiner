# RedLiner — Autonomous B2B Contract Negotiation & Legal Redlining

> **Milestone Deliverable (40–50% Core Architecture Implementation)**  
> Built strictly following the multi-agent & subgraph architecture from `AG_AI_Project_Synopsis_Grp_8.pdf`.

---

## 🏗️ Architecture: Agents & Subgraphs (Section 5 from Synopsis)

RedLiner's folder structure mirrors the agents and subgraphs specified in Section 5 of the project synopsis:

```
RedLiner/
├── AG_AI_Project_Synopsis_Grp_8.pdf   # Original group synopsis
├── Helpers/                           # Metadata, audit trails, and execution telemetry
│   ├── logger.py                      # Centralized structured JSON logger
│   ├── parser_metadata.jsonl          # Clause extraction & timing telemetry
│   ├── redline_audit.jsonl            # Policy violations & OpenXML diff logs
│   ├── email_audit.jsonl              # Cloudflare inbound/outbound email logs
│   └── vendor_risk_audit.jsonl        # OSINT screening & sanctions records
├── core/                              # Shared domain models & negotiation state
│   ├── models.py                      # Typed Clause, RedlineAction, VendorProfile
│   └── state.py                       # LangGraph NegotiationDealState schema
├── agents/                            # Core Agents (Section 5.1 & 5.2 in PDF)
│   ├── orchestrator.py                # 1) Main Orchestrator (supervisor / state manager)
│   ├── procurement_negotiator.py      # 2.a) Procurement Negotiator (concessions & pricing)
│   ├── legal_redliner.py              # 2.b) Legal Redliner Agent (playbook enforcement)
│   ├── finance_compliance_risk.py     # 2.c) Finance, Compliance & Risk (boundary checker)
│   ├── vendor_intelligence.py         # 2.d) Vendor Intelligence Agent (due diligence)
│   └── email_writer.py                # 2.e) Email Writer Agent (negotiation emails)
├── subgraphs/                         # Subgraphs (Section 5.3 in PDF)
│   ├── document_parser/               # 3.a) Document Parser Subgraph
│   │   ├── xml_extractor.py           # Native .docx XML extraction
│   │   ├── pdf_extractor.py           # Digital PDF extraction (no OCR)
│   │   ├── clause_segmenter.py        # Indexed array of typed clause objects
│   │   └── subgraph.py                # DocumentParserSubgraph executor
│   ├── playbook_matcher/              # 3.b) Playbook Rule Matcher Subgraph
│   │   ├── policy_comparator.py       # Compares clauses with active policies
│   │   ├── parallel_policy_checks.py  # Parallel checks: Liability, IP, and Law
│   │   ├── redline_action_generator.py# Exact strikethroughs, replacements, comments
│   │   ├── word_modifier.py           # Native Word OpenXML editor (<w:del>, <w:ins>)
│   │   └── subgraph.py                # PlaybookMatcherSubgraph executor
│   ├── tradeoff_engine/               # 3.c) Tradeoff Engine Subgraph
│   │   ├── tradeoff_generator.py      # Proposes counter-offers (price vs payment terms)
│   │   ├── math_engine.py             # Deterministic utility scoring module
│   │   ├── guardrail_checker.py       # Budget caps & minimum utility checker
│   │   └── subgraph.py                # TradeoffEngineSubgraph executor
│   ├── vendor_information/            # 3.d) Vendor Information Subgraph
│   │   ├── osint_collectors.py        # OSINT collectors (registry, sanctions, domain age)
│   │   ├── score_aggregator.py        # Multi-factor score aggregator & SQLite persistence
│   │   ├── exception_handler.py       # Manages timeouts and fallback retries
│   │   └── subgraph.py                # VendorInformationSubgraph executor
│   └── human_approval/                # 3.e) Human Approval Subgraph
│       ├── summary_agent.py           # Summarizes redlines & trade-offs in plain English
│       ├── interruption_gate.py       # Pauses execution when thresholds are crossed
│       ├── feedback_agent.py          # Processes Approve, Reject, Manual Edit
│       └── subgraph.py                # HumanApprovalSubgraph executor
├── services/                          # External infrastructure connectors
│   └── email_connector.py             # Cloudflare worker webhook & outbound dispatch
├── server/                            # FastAPI Server & API routes
│   └── app.py                         # REST routes serving UI and agent pipelines
├── cloudflare-email-worker/           # Cloudflare Email Routing Worker
│   ├── wrangler.toml                  # Cloudflare worker configuration
│   └── src/index.ts                   # email(message, env, ctx) handler + /api/send-email
├── playbooks/                         # Corporate Playbooks
│   └── enterprise_playbook.yaml       # Standard legal guardrails (Liability, IP, Net 60)
├── dashboard/                         # White-Themed UI (Zapier typography & styling)
│   ├── index.html                     # Control panel with 4 workbench tabs
│   ├── app.js                         # Interactive controller
│   └── style.css                      # Zapier color tokens, Inter font, warm white theme
├── data/
│   ├── sample_contracts/              # Sample .docx and .pdf B2B contracts
│   ├── vendors_seed.json              # 52 enterprise vendor seed records
│   ├── vendor_intelligence.db         # SQLite database
│   ├── uploads/                       # User contract uploads
│   └── outputs/                       # Redlined Word documents (.docx)
├── tests/
│   └── test_redliner_core.py          # 10 automated unit & integration tests
└── README.md
```

---

## 🚦 How to Run the Server

```bash
# Start server from root
PYTHONPATH=. .venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8000 --reload
```
Open **`http://127.0.0.1:8000`** in your browser.

---

## 🧪 Run Automated Tests

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_redliner_core.py -v
```
All 10 tests verify the agents, subgraphs, parallel policy checks, Word OpenXML tracked changes, and Helpers logging.
