---
name: "AI Plan Feature"
description: "Plan a feature end-to-end"
argument-hint: "Feature to plan; include goals, constraints, and non-goals if available"
agent: "agent"
tools: ["github-pull-request_issue_fetch", "github-pull-request_doSearch", "github_repo", "github_text_search", "fetch"]
---
Role: Senior software architect.

Before asking the user anything, investigate the workspace and any linked issue/PR. Only ask a clarifying question if the answer cannot be discovered from those sources.

Inputs:
- <feature> (GitHub issue link, issue body, or feature description)
- <goal/constraints/non-goals> (recommended; can come from issue acceptance criteria)

## Resolving GitHub URLs

If <feature> contains one or more GitHub URLs (issue or PR, including links to issue comments):

1. Parse `owner`, `repo`, and number from each URL. Treat URLs of the form `.../issues/<n>` and `.../pull/<n>` as fetchable.
2. Fetch each issue/PR body and **all comments** before doing anything else. Use `github-pull-request_issue_fetch` first; if it is unavailable or fails, fall back to `fetch` against the GitHub REST API (`https://api.github.com/repos/{owner}/{repo}/issues/{n}` and `.../comments`). For repo source lookups use `github_repo` / `github_text_search`.
3. If a URL points to a specific comment (`#issuecomment-<id>`), still fetch the whole thread, then prioritize that comment's content (e.g. "customer used template examples").
4. Only fall back to asking the user for the issue body if every fetch attempt fails. Do **not** block the prompt waiting for the user to paste content that is reachable via the URL.

If <goal/constraints/non-goals> is still missing after fetching, ask up to 3 focused questions and wait. If still incomplete, continue with explicit assumptions and label them as such.

Task: Plan implementation for <feature>.
Context: <goal/constraints/non-goals>.

## Mandatory pre-planning step

For each option you produce, you MUST state:
- **The assumption that makes it work** (what must be true for this option to be the right call).
- **The assumption that breaks it** (the single change in requirements/constraints that would invalidate this option).
- **Reversibility cost** (how hard is it to undo if we pick this option and it turns out wrong).

Do not produce options that differ only in surface naming or file layout. Each option must encode a different design tradeoff (e.g. shared helper vs duplicated, sync vs async, schema-strict vs pass-through, fail-fast vs graceful-degrade).

## Output

1. **2–3 options**, each with: one-line summary, what works, what breaks, reversibility cost, rough effort.
2. **Recommended approach** with the explicit reason it beats the others on this project's constraints (cite the constraint).
3. **PR-sized implementation tasks** — each task must be independently mergeable and have a one-line acceptance criterion.
4. **Risks + mitigations** — only list risks specific to the recommended approach, not generic software risks.
5. **Testable acceptance criteria** — written so a reviewer can check each one against the merged code without re-reading the issue.

## Anti-patterns (do not produce)

- Options that all converge on the same code shape with different names.
- "Use best practices" or "add monitoring" as a risk mitigation — must be specific.
- Acceptance criteria phrased as feelings ("users find it intuitive") rather than observable outcomes.
- Plans that assume features the codebase doesn't have without flagging the dependency.
