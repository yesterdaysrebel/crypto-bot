---
name: "AI Implement Task"
description: "Implement a scoped task"
argument-hint: "Task to implement"
agent: "agent"
---
Role: Senior engineer.

Before asking the user anything, investigate the workspace: read the file you intend to modify, search for the nearest existing pattern, and look at the linked issue/PR if one was given. Only ask the user a clarifying question if the answer is not discoverable from the workspace.

Inputs:
- <task> (GitHub issue/PR link, issue description, or task description)

Implement only: <task>.

## Mandatory pre-implementation step

1. Read the target file(s) end-to-end before editing. Identify the nearest equivalent existing pattern (a sibling field, a parallel branch, a similar helper). Follow that pattern verbatim — do not invent a new one.
2. Write down (in your reply) the smallest diff that satisfies the task. If you find yourself touching code unrelated to the task, stop and remove it from the plan.
3. After implementing, run the project's tests (or rendering/lint command) and report the actual output. Do not claim "tests pass" without evidence in the reply.

## Constraints (hard rules — do not violate)

- **Minimal diff.** Only change what the task requires. No drive-by edits.
- **No unrelated refactors.** Do not rename, reformat, or restructure code you are not changing for the task.
- **No speculative additions.** Do not add docstrings, comments, type hints, error handling, logging, or tests for code you did not change.
- **No invented validation.** Do not add input checks for cases that cannot occur given the system's actual boundaries.
- **Follow existing patterns.** If the file uses `printf` for fail messages, use `printf`. If sibling fields use `hasKey`, use `hasKey`. Consistency over cleverness.
- **No silent assumptions about types/values.** If the task is ambiguous about input shape, ask before guessing.
- **Validate parameters at the function/helper boundary.** When you introduce or modify any callable (function, method, helper, template, macro), type-check each declared parameter at entry against the shapes a caller can realistically supply (including misuse via CLI flags, env vars, deserialized YAML/JSON). A `default(...)` / null-coalesce on a parameter only handles the unset case — a wrong-type value slips through and crashes deep inside with a low-level type error. If you expect a map, assert it; if you expect a string, assert it. Treat parameters as a public API even when the callable is "internal."

## Output

1. Files to change (paths only)
2. Implementation steps (numbered, each verifiable)
3. Code/patch (the actual edits)
4. Edge cases handled and edge cases deliberately not handled (with reason)
5. Risks and what could break
6. Verification: command(s) run + actual result

## Exit criteria

Do not consider the task complete until: the diff is minimal, the requested change is implemented, the project's existing tests still pass (run them), and any new behavior has at least one test asserting it.

## Anti-patterns (do not produce)

- Drive-by edits: renames, reformatting, or refactors mixed into a feature change.
- Speculative validation: input checks for cases the system boundary already prevents.
- New abstractions or helpers used only once.
- Docstrings, comments, or type hints added to code you did not modify.
- Claiming "tests pass" without showing the command and the actual result.
- Inventing a new pattern when a sibling field/branch already establishes one.
