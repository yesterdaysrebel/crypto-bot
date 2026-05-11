---
name: "AI Code Review"
description: "Structured review prompt"
argument-hint: "Diff or PR context to review"
agent: "agent"
---
If required inputs are missing or ambiguous, ask concise clarifying questions first and wait for answers before continuing.

Before asking the user, investigate the workspace and the linked PR/issue: read the changed files, the surrounding code, and any tests in the same suite. Only ask if the answer is genuinely undiscoverable.

Inputs:
- <diff or PR context> (GitHub PR link, issue link, or diff summary)

Review this <diff or PR context> as a senior engineer and production gatekeeper.
Priority: correctness, security, reliability, compatibility, test gaps.

For each finding provide:
- Severity
- Evidence (file + line or code snippet)
- Why it matters
- Suggested fix

Only report defects you can describe with a concrete bad input. If you're uncertain whether behavior is intentional, phrase it as a question to the author rather than a finding.

## Mandatory mechanical step (do this BEFORE writing the checklist review)

Review the diff **line by line and locally**, not holistically. For every changed or added line, ignore your model of the author's intent and ask in isolation: *"What does this exact expression do, for every input the runtime allows?"*

For each expression introduced or modified — conditionals, type checks, default chains, guards, accessors, comparisons, coercions, regexes, format strings, error messages, log lines — enumerate the inputs the language/runtime can actually pass through it (including the ones the author probably didn't think about), evaluate the new behavior for each, and compare it against the old behavior in the same spot.

For every **format string, error message, or log line** that interpolates a value (`%s`/`%v`/`%d`/`{0}`/`{}`/`${x}`/`f"{x}"`/template literals/etc.), independently verify that each interpolation slot actually contains what the surrounding text claims. If the text says "got unsupported type X" the slot must contain the *type*, not the *value*; if it says "for resource Y" the slot must contain the resource identifier, not a stringified object. Mismatched message-vs-slot is a category of bug that line-local truthiness review misses but a sentence-by-sentence read of the message catches.

Flag anything where:
- behavior changed without a test covering the changed input,
- the result is invalid for downstream consumers (broken output, wrong type, malformed message),
- a sibling input of the same logical category reaches a different / less precise branch,
- an input the language considers "edge" (whatever those are for this language) is silently coerced, swallowed, or routed to the wrong error path,
- a user-facing message describes one thing but interpolates another (e.g. claims to show the "type" but shows the "value"; claims to show the "field name" but shows a stringified struct).

When proposing or accepting a **new validation** that rejects an input class, verify the rejected inputs would *actually misbehave* downstream before locking the rejection in. Run a render/build/test with at least one representative member of each rejected class and confirm the prior behavior was broken. Rejecting inputs that previously round-tripped cleanly is a regression dressed as a fix — and "non-string", "non-empty", "non-zero", "non-null" are blunt instruments that often over-reject. Distinguish between *truly* unsafe inputs (e.g. silently swallowed by a default chain, would crash a downstream parser, would emit malformed output) and inputs that merely *look* unsafe but are handled correctly by an existing coercion (`toString`, `String(x)`, implicit cast, etc.). Only the former warrant a hard fail.

When a function, method, helper, template, macro, or any callable is introduced or modified, **enumerate its declared parameters and verify each is type-validated at entry against every realistic shape the caller could supply** — including misuse via CLI flags (`--set`, `--var`), environment variables, deserialized JSON/YAML, query strings, request bodies, and CLI args. Treat the parameter list as a public API even when the callable is "internal" or "private," because callers in the same repo can and do pass arbitrary shapes. Critically: a `default(...)` / null-coalesce / `?? fallback` / `or default_value` on a parameter is **not** validation — it only handles the unset/nil case, not the wrong-type case. A wrong-type value slips straight through and crashes deep inside the function with a low-level type error instead of an actionable boundary error. If a helper expects a map/dict/object/struct, assert that at entry; if it expects a string, assert that at entry; do not rely on downstream field accesses to surface the type mismatch.

Do this pass first. Do not let an architectural mental model of "what the change is for" cause you to skip line-local edge cases. The point of this step is to catch the class of bug that line-by-line reviewers find and holistic reviewers miss.

---

## Production Readiness Checklist

Apply these principles to every changed file. Think adversarially — assume the author was too close to the code to see their own mistakes.

### 1. Correctness
- Does the code do what it claims? Trace every code path manually against the stated intent.
- Are all branches exhaustive? Chains without a final catch-all silently swallow unexpected inputs — always ask "what happens to values not covered?"
- Are defaults safe? A silent fallback to a wrong value is harder to debug than an explicit failure.
- Do documentation, comments, and error messages match the actual implemented behavior? Mismatched docs are a maintenance hazard.
- **Cross-check the PR title, PR description, and any linked issue against the actual implementation.** PR descriptions go stale just like code comments. If the description says the code does X but the code does Y (e.g. "renders untagged image" vs "fails with error"), that is a finding — either the description or the code is wrong.
- **Doc/code parity: verify every behavioral assertion against the current implementation.** For every doc comment, README claim, error message, or PR description sentence that asserts behavior ("required for X", "supports Y", "always Z", "only used when W"), open the referenced code path and confirm the assertion holds against the *current* code, not an earlier draft. Stale assertions in helper doc-comments are as misleading as stale READMEs.

### 2. Input Validation & Defensive Coding
- Is every external or user-supplied input validated before use, at the earliest safe point?
- Is every field access guarded against the wrong parent type? Accessing `.field` on a value that could be a string, null, or list causes low-level crashes instead of actionable errors.
- Are all realistic input types handled explicitly? Each case must be either handled or rejected with a clear error — no silent fallthrough.
- Are empty, null, zero, and missing-key values treated consistently and deliberately throughout?
- **When a validation gap is found in one place, scan the entire function and file for all other inputs of the same kind.** A fix applied to one field (e.g. type-checking a flag value) is incomplete if sibling fields (e.g. registry, repository) have the same vulnerability.
- **Treat negative type guards as a silent-coercion smell.** When a branch is gated by a negative type check (`not kindIs "map"`, `!= nil`, `typeof x !== 'object'`, `!isinstance(x, dict)`, etc.), confirm that every value flowing into that branch is one specific expected type — not "everything else." Replace the negative guard with a positive one (`kindIs "string"`, `isinstance(x, str)`) and fail fast on unexpected types instead of coercing them (e.g. via `toString`, `String(x)`, `str(x)`).
- **Map keys rendered as YAML scalars must be quoted.** When iterating user-supplied maps and rendering the key into YAML output (`{{ $key }}`, `key: {{ $name }}`, `name: {{ .Key }}`), the key must be wrapped in `quote` (or equivalent) unless it is a statically known identifier. YAML 1.1 — what Kubernetes parses — interprets unquoted `true`/`yes`/`on`/`off`/`123`/`1.2`/`null` as bool/int/float/null, not strings, which silently breaks downstream CRD or schema validation (e.g. ESO `secretKey`, label/annotation keys, env var names). This is sibling-asymmetric to value validation: confirming that a map *value* is a string does not cover the map *key*. Apply the same rule to any user-supplied identifier rendered into a YAML scalar position (resource names, label values, annotation values), not just map keys.

### 3. Fail-Fast & Error Quality
- Does the code fail loudly on invalid state rather than silently producing wrong output?
- Do error messages include enough context for an on-call engineer with no prior knowledge to diagnose the issue? (field name, resource name, received value, expected value)
- Are errors surfaced at the right layer — early enough to prevent downstream corruption, not so late that context is lost?

### 4. Output & Side Effect Quality
- Is every output (rendered template, API response, file, log) free of debug artifacts, inline documentation, or extra content that should not be present in production?
- Are side effects idempotent where required?
- Does the change affect observability (logs, metrics, alerts) in a way that helps or hinders production diagnosis?

### 5. Backward Compatibility
- Does the change break any existing public interface, config schema, or behavioral contract?
- For changed defaults: is the old default preserved as opt-out, or are consumers silently migrated?
- For removed behavior: is there a migration path and is it documented?

### 6. Security
- Is any user-controlled input used in a way that could lead to injection, path traversal, privilege escalation, or information disclosure?
- Are secrets, credentials, or PII never logged, never rendered into output, never stored in plaintext?
- Does the change introduce new attack surface (new endpoints, new permissions, new external calls)?

### 7. Test Coverage
- Is there a test for every new code path, including every explicit error/fail branch?
- Are edge-case inputs tested: empty, null, wrong type, boundary values?
- Do tests assert on the specific behavior being changed, not just that the code runs?
- Would these tests catch a regression if the change were accidentally reverted?

### 8. Hygiene
- Do all modified files end with a trailing newline?
- Are there leftover debug statements, commented-out code, or unresolved TODOs introduced by this change?
- Is the diff minimal — no unrelated reformatting or refactors mixed in?

## Anti-patterns (do not produce)

- Reviews that only restate the diff in prose without naming a finding.
- Findings without severity or evidence ("this looks risky" — say where and why).
- Padding the report with low-value style nits when correctness/security findings exist.
- Approving silently when the mechanical pass surfaces an unresolved truth-table row.
- Skipping the mechanical pass because the change "looks obviously correct."
