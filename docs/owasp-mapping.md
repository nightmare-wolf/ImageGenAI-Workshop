# OWASP Mapping

Each challenge is mapped to the **OWASP Top 10 for Large Language Model Applications (2025)**. The
point of the workshop is that these are *application* risks — so the mapping doubles as the syllabus.

## OWASP LLM Top 10 (2025) — quick reference

| ID | Category |
|----|----------|
| LLM01 | Prompt Injection (direct, indirect, multimodal) |
| LLM02 | Sensitive Information Disclosure |
| LLM03 | Supply Chain |
| LLM04 | Data and Model Poisoning |
| LLM05 | Improper Output Handling |
| LLM06 | Excessive Agency |
| LLM07 | System Prompt Leakage |
| LLM08 | Vector and Embedding Weaknesses |
| LLM09 | Misinformation |
| LLM10 | Unbounded Consumption |

## Challenge → risk mapping

| Lvl | Challenge | Primary OWASP | Secondary | Why this category |
|----:|-----------|---------------|-----------|-------------------|
| 1 | Hello, Operator | **LLM07** System Prompt Leakage | LLM02 | The asset recovered *is* the system prompt; the error-leak alt-path is LLM02 |
| 2 | The Polite Override | **LLM01** Prompt Injection (direct) | — | User instruction overrides an instruction-based guardrail |
| 3 | Negative Space | **LLM01** Prompt Injection | — | Injection routed through a field the validator forgot — improper input handling |
| 4 | Read the Fine Print | **LLM02** Sensitive Information Disclosure | LLM05 | Secret recovered from output metadata; the debug-dump path is improper output handling |
| 5 | Template Injection | **LLM01** Prompt Injection (template breakout) | LLM02 | Forging role delimiters via insecure templating; error-leak of the raw template is LLM02 |
| 6 | The Long Con | **LLM01** Prompt Injection (multi-turn) | LLM02 | Per-turn guardrail evasion across a conversation; recalled secret is LLM02 |
| 7 | Trust the Tool | **LLM01** Indirect/Multimodal Injection | **LLM06** Excessive Agency | Attacker text inside an uploaded image becomes instructions; an over-privileged tool executes |
| 8 | Full Chain | **Chained** | LLM07→LLM02→LLM01→LLM06 | Composition of partial defects into full compromise — the realistic incident pattern |

## Coverage and intentional gaps

- **Covered hands-on:** LLM01, LLM02, LLM05, LLM06, LLM07 — the categories most relevant to a
  team shipping an AI *application* and the ones you can exercise safely in a browser-only CTF.
- **Discussed in debrief, not exploited:** LLM10 Unbounded Consumption (we *defend* against it with
  the platform's rate limits/spend caps — a teachable contrast), and LLM03 Supply Chain / LLM04
  Poisoning (acknowledged as out of scope for a 3-hour event but flagged as where to go next).
- **Deliberately excluded:** LLM08 Vector/Embedding and LLM09 Misinformation don't fit an
  image-generation target cleanly and would dilute the narrative; mentioned only as "further study."

## Defensive control ↔ category

| OWASP | Mitigation taught (see [03 §14](03-architecture.md#14-security-controls-catalog-what-we-teach-as-the-fixes)) |
|-------|---------------------------------------------------------------|
| LLM01 | Structured prompting, validate all inputs, treat retrieved/extracted text as data, dual-LLM |
| LLM02 | Output filtering, metadata scrubbing, no secrets in prompts, disable verbose errors |
| LLM05 | Encode/validate outputs across *all* channels (body, files, metadata, logs) |
| LLM06 | Least-privilege tools, per-call authz keyed to real identity, human/trusted-code gating |
| LLM07 | System prompt ≠ secret; secrets in a vault the model can't read; output scan |
| LLM10 | Rate limits, concurrency caps, budget alarms, scale-to-zero (built into the platform) |
