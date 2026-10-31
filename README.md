
# ISA Lens

[![CI](https://github.com/Ashwin-rathinakumar/examate-Genai-projects/actions/workflows/ci.yml/badge.svg)](https://github.com/Ashwin-rathinakumar/examate-Genai-projects/actions/workflows/ci.yml)

**Live health:** _Replace this text with the verified Render `/health` URL after the first deployment._

> An intelligent instruction-set reference desk for RISC-V chip design teams that finds the exact instruction, register, or extension every time.

## Problem

Verification engineers working on RISC-V processors struggle to find accurate information across thousands of pages of technical specifications. Engineers frequently search for exact terms such as `mstatus.MPP`, `Zicsr`, and `fence.i`, but traditional vector search can retrieve incorrect sections because technical identifiers often look similar. As a result, engineers spend valuable time manually searching multiple PDF documents. ISA Lens solves this problem by combining exact keyword matching, semantic search, and re-ranking to retrieve relevant specification sections with accurate citations.

## Who it is for

Verification engineers at RISC-V chip design startups in Chennai, particularly engineers working in processor core and System-on-Chip (SoC) development teams.

## Signature feature

Exact-Term Chips automatically identify and highlight CSR names, instruction mnemonics, and extension codes in user queries, prioritizing exact matches to retrieve the correct RISC-V specification sections.

## Hardest problem (my interview story)

The biggest challenge is making an AI search system accurately understand and retrieve technical identifiers such as `mstatus.MPP`, `Zicsr`, and `fence.i`. Traditional semantic search can confuse similar instruction names or register fields and return incorrect specification sections. To solve this, ISA Lens combines BM25 keyword search with vector-based semantic search and a re-ranking model. The system will be evaluated using 100 exact-term technical questions, comparing vector-only, BM25-only, and hybrid retrieval methods. The target is to achieve at least 90% top-3 retrieval accuracy.

## Dataset

| Source | Link | Documents | Pages | Licence / terms |
|---|---|---|---|---|
| RISC-V International Ratified Specifications | https://riscv.org/specifications/ratified/ | To be confirmed | 1,500+ (target) | Openly available specifications; licence to be verified for each document |

The dataset will contain official RISC-V unprivileged and privileged ISA specifications, along with ratified extensions.

Each document will be processed and divided into searchable sections while preserving instruction names, register identifiers, section references, and page information.

Core and SoC teams will also be able to add their own private design notes as tenant-specific documents.

## 10 real questions

See [docs/QUESTIONS.md](docs/QUESTIONS.md).

## Run it

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                 # Windows: copy .env.example .env
uvicorn app.main:app --reload
curl localhost:8000/health
```

## Chat with Gemini

Set `GEMINI_API_KEY` in your local `.env` file. `POST /chat` streams Server-Sent
Events and automatically tries the configured fallback model when the primary
model is unavailable before any text is emitted. Its final event contains the
model used, whether fallback was used, token usage and estimated cost.

The non-streaming `POST /ask` endpoint remains available for compatibility.
Keep `.env` private and never commit a real API key.

```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What is the RISC-V mstatus register?"}]}'
```

`GET /usage` reads `logs/cost_log.jsonl` and returns daily input/output token
totals and estimated USD cost. The log stores usage metadata only, not prompts
or answers. Dates use UTC. Costs use the configurable paid-tier prices in
`.env`; adjust them to match your Gemini billing tier. If Gemini omits token
metadata, that call is counted but marked in `calls_without_usage` and excluded
from token and cost totals.

## Quality checks

Install the development dependencies and enable the Git hook once:

```bash
pip install -r requirements-dev.txt
pre-commit install
pre-commit run --all-files
pytest -q
```

CI runs the same pre-commit formatting and lint checks on every push and pull
request.

## Deploy on Render

The included `render.yaml` and `Dockerfile` define a free Render web service.
Create a Render Blueprint from this repository, enter `GEMINI_API_KEY` and
`LLM_API_KEY` as secret environment values, and deploy. After `/health` returns
`{"status":"ok",...}`, replace the **Live health** placeholder at the top with
the verified public URL and push that README update.

The free service filesystem is ephemeral, so the local JSONL usage log may reset
when the service restarts. Local development retains the log normally.
