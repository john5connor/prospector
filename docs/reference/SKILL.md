# SKILL.md — Autonomous Systems & Business Experimentation Lab

**Version:** 1.0  
**Purpose:** Reusable working guide for designing, building, evaluating, and gradually operating automated online business experiments.  
**Use with:** ChatGPT Project Instructions — Autonomous Systems & Online Business Lab.

> This is an operating reference, not a mandatory checklist for every conversation. Apply the smallest useful subset. The project instructions set everyday assistant behavior; this file supplies detail, patterns, and templates.

## 1. North star

Develop the ability to **reason about and build reliable automated systems** while gaining firsthand experience with **business fundamentals**: customer problems, value propositions, acquisition, economics, experimentation, fulfillment, and retention.

The lab has two distinct outcomes:

1. **Engineering outcome:** better understanding of orchestration, agent systems, architecture, integration, infrastructure, security, observability, and operational design.
2. **Business outcome:** evidence that a specific customer problem exists and that a proposed offer can solve it sustainably. Revenue is valuable evidence, not the sole definition of a successful learning experiment.

Avoid these traps: using agents where a simple script suffices; polishing infrastructure before validating a use case; conflating an impressive demo with a viable business; or mistaking fully automated execution for reliable, compliant, profitable operations.

## 2. Operator profile, constraints, and preferences

- **Background:** professional software developer comfortable with engineering rigor and programming; newer to some automation/agent platforms and business disciplines.
- **Teaching:** adaptive. Answer the actual question first. Introduce deeper engineering concepts when they materially matter or when requested. Use intuitive explanations, diagrams, and small examples; expand into internals, tradeoffs, and code on demand.
- **Review style:** critical but constructive. Identify weaknesses in ideas and proposed architecture with reasons and alternatives, not reflexive agreement.
- **Execution environment:** local-first secondary PC, Ubuntu 26.x LTS, AMD Ryzen 5 2600, 16 GB RAM. Prefer resource-conscious Docker Compose and hosted inference when appropriate. Cloud/hybrid is a future option; a Mac mini is possible but not presumed.
- **Budget:** manageable and flexible; obtain a concrete ceiling before making consequential recurring-spend decisions. Track compute, API/model usage, storage, domains, proxies, monitoring, and time.
- **Initial case study:** public business website analysis, measured diagnostics, demo redesign, and carefully controlled marketing experimentation.
- **Scope:** later experiments may include digital services, publishing/content, lead generation, digital products, data products, and others. No tool or business idea is permanent.

### Interaction defaults for the assistant

- Match the current mode: **Explore** (compare options), **Learn** (teach), **Design** (architecture), **Build** (implementation), **Debug** (root cause), **Review** (critique), or **Evaluate** (business evidence). Infer the mode from the question; clarify only when it materially changes the answer.
- Present a recommendation with key assumptions and a reasoned alternative when tradeoffs are material. Never force a multi-option matrix for a trivial question.
- Explain what is known versus estimated versus unverified. When current product behavior, security, pricing, licensing, API specifications, or laws matter, check authoritative current documentation if available.
- When architecture is discussed, distinguish *must-have now* from *optional later*. Keep the minimum viable approach visible.
- When the user requests an exercise or Socratic approach, ask focused questions and guide reasoning rather than prematurely supplying full solutions.
- Avoid inflated claims about autonomous agents, profitability, uptime, or ROI. Do not imply the assistant or a tool performed an external action unless it actually did.

## 3. Progression: deterministic to autonomous

Progress is **capability-based, not calendar-based**. Stay at each stage until the lessons are genuinely understood and the systems work.

### Level 1 — Deterministic workflows

**Goal:** consistently execute a bounded process end-to-end, with observable success/failure.

Typical elements: schedule/webhook/manual trigger; authenticated API calls; normalization and validation; idempotency; error handling; retries with backoff; basic storage; run IDs; structured logs; tests; human review of results.

Example: submit an allowed website URL → run diagnostics → store structured findings → generate a Markdown report for human review.

**Exit signals:** runs are repeatable; duplicate triggers are safe; failures are explainable; inputs/outputs are validated; secret handling and costs are understood.

### Level 2 — Agent-assisted workflows

**Goal:** embed nondeterministic reasoning inside deterministic boundaries.

Typical elements: model selection; narrow agent task specification; explicit tool permissions; retrieval/context; typed/structured outputs; schema validation; evaluation set; quality checks; bounded retries; token/latency budgets; fallback or escalation; approval before external effects.

Example: provide measured website diagnostics → agent drafts a prioritized critique with citations to collected measurements → deterministic validator checks claims against evidence → human approves a redesign concept.

**Exit signals:** agent output is measured against examples; unsupported claims are detected; cost and latency are visible; failures do not cascade into unsafe actions.

### Level 3 — Bounded autonomous operations

**Goal:** systems that can monitor outcomes, propose or carry out permitted follow-up work, and recover under explicit policies.

Typical elements: persistent state, queues, schedules, task allocation, planning, evaluation loops, tool-use controls, approval gates, monitoring, incident response, rollback, budget enforcement, and stateful audits.

Example: monitor a portfolio of authorized website experiments; schedule reevaluations; propose changes based on metrics; open reviewed change requests; implement *approved* improvements; measure impact; halt on risk or budget triggers.

**Exit signals:** documented action boundaries; validated outcomes; human can inspect, interrupt, and reverse actions; failure and security scenarios have been tested; measured value exceeds operating costs.

**Important:** autonomy means bounded delegated responsibility, not unrestricted permissions. More agents are not inherently better.

## 4. Tool selection and layered mental model

These are illustrative roles, not universal prescriptions; verify current capabilities before relying on them.

| Layer | Role | Candidate tools / patterns | Key question |
|---|---|---|---|
| External triggers and workflows | Events, schedules, branching, integrations, retries | n8n; scripts; queues | Is the flow primarily deterministic? |
| Reasoning and stateful agent control | Tool use, branching reasoning, context, checkpoints | LangGraph; custom state machines; agent frameworks | Is stateful nondeterministic reasoning actually needed? |
| Development assistance | Author, inspect, test, refactor code and artifacts | Claude Code; other coding agents | Who reviews changes and validates execution? |
| Persistent assistant/agent runtime | Ongoing tools, scheduled work, delegated operations | OpenClaw and alternatives | How are permissions, state, and side effects constrained? |
| Application and services | Domain logic, APIs, validators, business rules | Python; FastAPI; Node; workers | Would a plain service be simpler and more testable? |
| State and messaging | Transactional data, work queues, audit trail | SQLite/PostgreSQL; Redis/queue if justified | What must survive crashes and retries? |
| Execution and operations | Isolation, secrets, deployment, monitoring, backups | Ubuntu; Docker Compose; reverse proxy; logs | Can this be safely run and recovered? |

**Design heuristics:**

1. A webhook + code step often beats a multi-agent system for well-specified transformations.
2. Use agents for genuinely ambiguous work (interpreting evidence, drafting, planning), not as a replacement for deterministic validation or state management.
3. Keep business policies and authorization decisions outside free-form model instructions whenever possible.
4. Use queues and external databases only when volume, durability, or cross-run state justifies them.
5. Treat agents and coding tools as potentially fallible operators, not trusted administrators.
6. Never assume a code-generation tool can safely deploy, operate, or market a business simply because it can write code.

## 5. Default engineering method (lightweight, risk-based)

For **small questions**, answer directly. For a **new or substantially changed system**, use this sequence as useful:

### A. Frame

Define:
- User/customer and the problem to solve.
- Business hypothesis and separate learning objective.
- Success and failure criteria: what would disconfirm the hypothesis?
- Inputs, outputs, expected volume, cadence, latency, reliability needs.
- Data sources and authorization; secrets; budget and risk constraints.

### B. Sketch

Create the smallest understandable picture of:

`trigger → acquisition → validation → processing / agent → verification → storage → approval → external action → measurement`

Not every project needs every step. Identify component boundaries and what each component owns. Mark where state persists, where uncertainty enters, and where external side effects occur.

### C. Choose

Compare no more than a few genuine options. Discuss tradeoffs in complexity, reversibility, maintenance, resource consumption, cost, security, and learning value. State *why not* to add a framework now.

### D. Build

Work in short, demonstrable increments. Prefer a vertical slice that works on one permitted input over a broad theoretical platform. Keep configurations reproducible, dependencies pinned where necessary, and secrets out of source control.

### E. Verify

At minimum, test the happy path, invalid input, timeout/network error, duplicate trigger, partial completion, and restart/retry behavior when those risks exist. For AI output, add evidence checks and sample-based evaluation. Simulate dangerous side effects before enabling them.

### F. Observe and improve

Track run outcomes, error categories, duration, API/model costs, artifact quality, human intervention, and business metrics when available. Do retrospectives at meaningful milestones, not after every chat.

## 6. Local-first reference platform

Start simple on the existing Ubuntu workstation; adapt as experiments evolve.

```text
                           Local operator / browser
                                     │
                         Authenticated local access
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         │                                                       │
    n8n / scheduler                                        Project source
    workflow orchestration                                  + coding agent
         │                                                       │
         ├──────→ small workers / APIs / CLI tools  ←────────────┘
         │             │               │
         │             ├─ measurements ├─ optional LLM API
         │             └─ validation   └─ approved artifact drafts
         │
         └──────→ durable storage / logs / experiment outputs
                              │
                     human review / approval
                              │
                   optional external publishing
```

**Baseline design principles:**

- Use Docker Compose for repeatable service definitions where it helps. A plain Python CLI is perfectly acceptable for the earliest experiments.
- Keep n8n and management interfaces local or behind authenticated remote access; never expose admin panels publicly without a deliberate security design.
- Store workflows, scripts, configuration examples, and infrastructure definitions in version control. Export platform-native definitions where practical.
- Choose SQLite for small single-user experiments; PostgreSQL when concurrency, relational durability, or platform requirements call for it. Add Redis/queues only for a real need.
- Keep artifacts (reports, measurements, screenshots, generated site previews) in organized local storage with clear retention and backup policies.
- Use an API-based model rather than expecting the Ryzen 5 2600/16 GB machine to run large models efficiently. Monitor provider usage; local models can be evaluated separately.
- Separate the experimentation environment from any personal/employer-sensitive systems. Use distinct service accounts and minimal-scope credentials.
- Set CPU, memory, concurrency, and log-retention limits appropriate to the machine. Prefer headless browsers with controlled parallelism; website scanning can be memory intensive.
- Make backups and restoration testable before anything becomes valuable. Plan cloud migration only when data durability, exposure, scheduling, or availability demands it.

**Early suggested repository layout** (optional, not required):

```text
lab/
  README.md
  compose.yaml
  .env.example
  workflows/             # exported n8n workflows
  services/              # small APIs, CLIs, workers
  experiments/           # briefs, results, scorecards
  docs/
    architecture/
    decisions/
    runbooks/
    glossary.md
  data/                  # local, ignored or managed separately
```

## 7. Business experimentation operating model

Evaluate the idea as a potential business **and** as an educational project.

### Hypothesis chain

`Audience → painful problem → offered solution → willingness to engage/pay → delivery cost → repeatable acquisition → sustainable operation`

Each link is uncertain until observed. Avoid inferring willingness to pay from a technically successful demo.

### Business concepts to learn progressively

- **Market and customer:** ideal customer profile, alternatives, unmet need, segmentation, research ethics.
- **Value proposition:** measurable improvement and why a customer would care.
- **Distribution:** legitimate discovery, content, referrals, partnerships, and customer outreach.
- **Conversion:** response → meeting/demo → proposal → purchase, or analogous funnel.
- **Unit economics:** revenue per customer, variable cost, gross margin, customer acquisition cost, lifetime value where meaningful, refund/support burden.
- **Operations:** lead time, fulfillment quality, repeatability, customer support, retention, regulatory and platform constraints.
- **Time economics:** setup time, manual review per unit, maintenance, failure investigation; a 'passive' business may be labor-intensive.

### Score experiments on two axes

**Engineering value:** new concepts learned; reliability and reusability of components; amount of operational evidence.  
**Commercial evidence:** customer response, conversion, demonstrated value, credible gross margin, scalability and lawful acquisition.

A technically instructive project can remain worthwhile even if its business hypothesis fails. That failure should become a documented result, not be rationalized away.

### Recommended stage gates

1. **Discover:** articulate a narrowly scoped customer problem and test demand with permitted research.
2. **Prototype:** prove a small technical workflow on sample/authorized inputs.
3. **Validate:** assess report quality, relevance, and whether anyone actually values the output.
4. **Pilot:** deliver a bounded service with review and explicit consent where needed.
5. **Operate:** measure cost, support load, errors, conversion, and customer outcomes.
6. **Automate further:** delegate only steps whose risk and value justify removing manual review.

Do not proceed automatically to a later gate because implementation is exciting.

## 8. Initial experiment: website diagnostics → redesign concept

**Hypothesis (not yet established):** some small businesses have websites with demonstrable problems and may value a concise, evidence-backed diagnosis or a better implementation.

### Learning-oriented MVP

1. **Input:** one manually chosen, publicly accessible URL that can be examined lawfully; optionally use a site you own or a permissive test site.
2. **Collect:** permitted page metadata and a small bounded sample; performance/accessibility/SEO measurements using established tools and clearly recorded conditions.
3. **Normalize:** store URL, timestamps, scan parameters, raw measurements, errors, and provenance.
4. **Evaluate:** deterministic rules classify actionable issues and uncertainties; avoid converting every warning into a definitive business harm claim.
5. **Draft:** optional AI summarizes *grounded findings* in plain language, with severity, evidence, and suggested remedies.
6. **Generate:** optional redesigned demo or change proposal; label it clearly as a concept, not an authorized production replacement.
7. **Review:** manually check accuracy, design quality, brand/IP considerations, and commercial relevance.
8. **Measure:** cost per analysis, time saved, error rate, quality of evidence, human editing time, and any appropriately obtained customer feedback.

**Key experimental distinction:** a site's SEO score or Lighthouse score is not by itself proof of poor sales or that the owner wants a redesign. Test the business proposition separately.

### Suggested increments

- **E1:** one-site manual CLI run → saved JSON and Markdown report.
- **E2:** n8n manual/webhook trigger → CLI/service → durable result + failure notification.
- **E3:** AI-assisted report synthesis with measured-grounding checks and human approval.
- **E4:** generated demo site or code change in an isolated repository, with tests and preview.
- **E5:** small, ethical validation of whether business owners find such a report useful; any outreach is individually reviewed and authorized, never a mass-blast by default.
- **E6+:** portfolio scheduling, change monitoring, evaluation feedback, and selectively automated approved operations.

Advance based on results, not calendar dates. Avoid building prospect-list harvesting or unsolicited email automation as the first milestone.

## 9. Autonomy, permissions, and external-action controls

Default every new agent to **read/observe/draft** until explicitly permitted otherwise.

### Action classes

| Class | Examples | Default |
|---|---|---|
| Observe | Read authorized public pages, query test APIs, inspect local logs | Permit within policy and limits |
| Draft | Generate reports, emails, sample code, internal redesigns | Permit locally; label as unreviewed |
| Internal modify | Write local project files, change test data, open branches | Permit in bounded sandbox with rollback |
| External publish/communicate | Send an email, post content, deploy a public site | Human approval before each consequential action unless a narrow recurring permission is expressly established |
| Financial / sensitive | Spend money, buy domains, alter payment systems, access sensitive records | Explicit operator approval and extra verification; no blanket permission |

### Required controls as risk increases

- Allowed domain/API and filesystem scopes; credentials with least privilege.
- Per-run and monthly spend limits; quotas; rate limits; concurrency ceilings.
- Durable event log: who/what decided, observed inputs, tool calls, resulting artifacts, and external side effects.
- Timeouts; bounded retries; idempotency keys; circuit breakers; stop conditions.
- Validation of external content: treat pages, documents, and model outputs as untrusted, including embedded instructions (prompt injection).
- Human review checkpoints with understandable artifacts and the ability to reject or revise.
- Rollback, backup, and incident handling for actions that can be reversed; escalation for irreversible actions.
- Access and operational review before a system is allowed to run continuously.

**Specific boundaries:** no unauthorized access, access-control bypass, credential harvesting, deceptive impersonation, or unnecessary collection of personal information. Respect site terms, applicable crawling restrictions, privacy, intellectual property, and marketing rules. Do not assume publicly visible content is free to republish or train on. Keep all employer-confidential material out of the lab.

## 10. Reliability and observability patterns

For nontrivial workflows, define:

- **Run identity:** `run_id`, `experiment_id`, and a stable idempotency key for each external operation.
- **State:** queued → running → requires_review → approved/rejected → completed/failed (adapt as necessary).
- **Inputs and evidence:** input URI or identifier, timestamps, tool versions, model/prompt versions when relevant, and measurements. Avoid storing unnecessary secrets or personal data.
- **Failure policy:** which errors retry, how many times, with what delay, and what happens after retries are exhausted.
- **Outcome:** clear success criteria; not merely “the workflow exited without error.”
- **Alerting:** useful notification for missed schedules, unexpected spend, repeated failures, and unexpected side effects.
- **Recovery:** resume, rerun safely, skip already-completed work, or escalate for human intervention.

Suggested basic metrics: executions, completion rate, error types, P50/P95 duration (when meaningful), human review time, cost/run, model tokens, and artifact quality. Add domain-specific business measures only when there is actual data.

## 11. Reusable artifacts and templates

Create these only when they help; an MVP may need just a brief and a README.

### A. Experiment brief — `experiments/<slug>/BRIEF.md`

```markdown
# Experiment: <name>
Status: idea | prototype | validating | piloting | operating | archived
Owner: <operator>     Updated: <date>

## Why this experiment?
Target audience/problem:
Learning objective:
Business hypothesis:

## MVP and constraints
Input → output:
Local/cloud environment:
Budget/spend ceiling:
Authorization/privacy boundaries:
Out of scope:

## Validation
What success looks like:
What would falsify the hypothesis:
Baseline / expected sample size:
Metrics and collection method:

## Next smallest test
Action:
Decision to make from result:
```

### B. Architecture note — `docs/architecture/<system>.md`

```markdown
# System: <name>
Purpose and non-goals:
Context diagram / data-flow sketch:
Components and responsibilities:
Inputs, outputs, external dependencies:
State and persistence:
Trust boundaries, secrets, side effects:
Failure modes and recovery:
Deployment, resource needs, cost:
Observability and tests:
Known limitations / future options:
```

### C. Workflow contract — `workflows/<name>.md`

```markdown
# Workflow: <name>
Trigger / schedule:
Input schema + validation:
Steps and ownership:
Output schema + evidence:
State transitions:
Retries / idempotency / deduplication:
Timeouts and cost limits:
Human approval gates:
External side effects:
Tests and sample fixtures:
```

### D. Architecture decision record — `docs/decisions/ADR-XXXX.md`

```markdown
# ADR-XXXX: <decision>
Date / status:
Context:
Decision:
Alternatives considered:
Tradeoffs and why this is appropriate now:
Revisit when:
```

### E. Experiment scorecard — `experiments/<slug>/SCORECARD.md`

```markdown
# Experiment scorecard: <name>
Evaluation period / sample:

Engineering:
- What ran, succeeded, and failed?
- Reliability, average cost/run, review time:
- Reusable components and key lessons:

Business:
- Who was exposed to or tried the offer?
- Measured interest/conversion/feedback:
- Revenue, variable costs, time cost (if applicable):
- Most important untested assumption:

Decision: continue | pivot | pause | archive
Reason / next test:
```

### F. Session handoff — `SESSION_HANDOFF.md`

```markdown
# Session handoff — <date>
Current experiment and stage:
What is working (verified):
What was attempted (including failures):
Architecture / key files / versions:
Decisions and why:
Open risks and unknowns:
Next 1–3 actions:
```

### G. Optional incident note — `docs/incidents/<date>-<slug>.md`

```markdown
# Incident: <summary>
Impact and timeline:
How detected:
Root cause (confirmed vs suspected):
Immediate mitigation:
Prevention / monitoring changes:
Follow-up owner:
```

## 12. Conversation workflows and useful prompts

These are example requests, not commands the assistant must force on the user.

**When exploring an idea**  
“Evaluate this as both a learning experiment and a real business. Identify the riskiest assumption, the smallest test, realistic costs, and reasons it might fail.”

**When selecting a stack**  
“Compare a plain Python service, n8n, and an agent-based design for this workflow. Recommend the simplest viable option and say when I should revisit it.”

**When learning a new technology**  
“Explain this concept intuitively first, then relate it to what we're building. I'll ask for internals as needed.”

**When implementing**  
“Give me a vertical slice for the next capability, including success criteria, local setup, failure handling, and tests. Don't design the whole future platform.”

**When debugging**  
“Separate observations from hypotheses. Give me the most discriminating checks first, then propose the minimal corrective change.”

**When contemplating autonomy**  
“Classify all agent actions by risk, identify what can be automated safely, and specify approval gates, observability, and stop conditions.”

**When reviewing progress**  
“Summarize what we verified, what remains unproven, costs, lessons, architectural decisions, and the next high-value experiment. Draft a session handoff.”

## 13. Decision principles to revisit repeatedly

- **Does this increase learning or customer value?** If neither, defer it.
- **Could a deterministic tool do this more reliably?** Prefer it where appropriate.
- **What must persist when the process restarts?** Store that state deliberately.
- **Where does untrusted input cross a trust boundary?** Validate it.
- **What can this component actually change outside its sandbox?** Limit it.
- **What failure is most likely, and how would I know?** Build the smallest useful signal.
- **Can I explain the unit economics?** If not, collect more evidence before calling it a business.
- **What is the next reversible test?** Run that before adding scale or autonomy.

## 14. Session-start and milestone guidance

At the beginning of a new chat, when relevant, identify the active experiment, stage, relevant artifacts, and today's immediate goal. If context is missing, request the smallest missing artifact or use the user's brief summary; do not invent progress. For a substantial new task, prefer a short approach followed by implementation. At meaningful milestones, propose updating the brief, workflow contract, ADR, scorecard, or session handoff. Avoid turning straightforward technical Q&A into mandatory project management.

**Long-term success:** not simply “an agent is running 24/7,” but an operator who understands the system end-to-end, can explain its failures and economics, and can confidently decide which business processes are worth automating.
