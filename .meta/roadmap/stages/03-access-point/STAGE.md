# Stage 03 — The access point: schema, API and AI  (sketch)

**Goal:** a program or a model hands pyHermes a note and gets back checked documents. The rule
that makes it safe in research: **the model writes structure and prose; every number comes
from data.**

**Versions (sketch; cards are written when this stage is next):**

| Version | Epic | One line | Needs |
|---------|------|----------|-------|
| v0.21.0 | 3.1 | Public, versioned JSON Schema of the content model, with a stability policy | 2.2 |
| v0.22.0 | 3.2 | Stateless render service in a separate, separately licensed package (open core); the core stays Jinja2-only | 3.1 |
| v0.23.0 | 3.3 | MCP server: list templates, validate, render, return a preview image | 3.1 |
| v0.24.0 | 3.4 | Number grounding: prose cites figures by reference; a check flags unbound literal numbers | 1.2, 2.2 |
| v0.25.0 | 3.5 | Authoring loop: stable error codes and paths a model can act on; screenshots back | 3.3 |
| v0.26.0 | 3.6 | Evaluation suite: pass rate, numbers traced, time to a sent note | 3.4, 3.5 |
| v0.27.0 | 3.7 | Untrusted-input hardening: raw-HTML fields sanitised or refused in API mode; limits | 3.2 |

**Milestone (stage exit):** a model-authored note passes validation with every number traced
to its data, and one outside client renders through the API or the MCP server. Its stable
schema makes this gate the natural point to cut 1.0.

**Risk:** shipping 3.3 early against today's section tree publishes a layout schema that
Stage 02 would break. An internal prototype is fine; a public tool is not.
