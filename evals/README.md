# Chatty Agent Eval

This directory contains evaluation cases and evaluation tooling for Chatty agents.

The eval system is intentionally kept separate from the Chatty runtime.

Its purpose is to evaluate agent behavior under the same runtime and harness
without modifying the runtime itself to satisfy individual test cases.

## Current Scope

The first evaluation target is the Technical Engineering Agent (`Tech`).

Tech Eval v1 focuses on whether the agent can:

- understand informal engineering requests
- distinguish product ambiguity from engineering uncertainty
- investigate the existing system autonomously
- reason from evidence instead of assumptions
- choose an appropriate and minimal change
- validate changes with an appropriate scope
- recover from validation failures when necessary
- stop investigating once sufficient evidence has been collected

The evaluation is not based on matching a predefined "correct answer".

Different implementations may be acceptable if they are well-supported by the
existing architecture, satisfy the user's intended outcome, and avoid
unnecessary changes.

## Directory Structure

    evals/
    ├── cases/
    ├── results/
    ├── runner/
    ├── scores/
    │   └── tech_v1.json
    └── README.md

### `cases/`

Contains evaluation case definitions.

Cases describe:

- the user request
- whether the task is read-only or may modify the project
- important expected behaviors
- which scoring dimensions apply

Cases should not encode an expected implementation unless a specific
implementation is itself part of the product requirement.

### `runner/`

Contains scripts that execute evaluation cases against Chatty.

The runner should remain external to the Agent runtime.

It may collect runtime observations such as:

- model
- iteration count
- tool calls
- read calls
- write calls
- validation calls
- approval events
- continuation events
- duplicate tool calls
- max-iteration termination
- completion status
- errors

The runner should not silently bypass Chatty's normal safety or approval
boundaries.

### `results/`

Contains evaluation run results.

Results may later be used to compare:

- different models
- prompt changes
- Tech personality changes
- engineering guide changes
- harness/runtime changes

### scores/

Human-reviewed benchmark judgments.

Raw runtime observations stay in `results/`. Manual evaluation is stored
separately in `scores/` so that evidence and judgment are never mixed.

`tech_v1.json` records:

- case validity
- run status
- manual dimension scores
- core score totals
- language consistency
- reviewer notes

Some historical cases preserve only their reviewed total score because a full
per-dimension breakdown was not recorded at the time. Those missing dimensions
remain `null` instead of being reconstructed from memory.

`TECH-REPAIR-01` is currently a placeholder and is not part of the formal v1
benchmark because a deterministic validation-failure fixture has not yet been
implemented.

## Core Scoring Dimensions

Each applicable dimension is scored manually using:

- `2` — Pass
- `1` — Partial pass / noticeable weakness
- `0` — Fail
- `N/A` — Not applicable to this case

### 1. Requirement Understanding

Does the agent identify the user's actual intended outcome rather than treating
the user's proposed implementation as the requirement?

A strong result separates, when relevant:

- observed behavior
- desired outcome
- proposed solution
- constraints
- unknowns

### 2. Clarification Judgment

Does the agent ask the user only when the intended product behavior is
materially ambiguous?

Engineering uncertainty should normally be resolved by investigating the
codebase, architecture, configuration, logs, tests, or runtime behavior.

The agent should not ask the user to make technical decisions that can be
resolved from the system itself.

### 3. Autonomous Investigation

Can the agent locate the relevant implementation and follow the necessary call
paths without requiring the user to provide filenames, modules, or technical
diagnosis?

Investigation should be driven by the problem rather than by a predefined file
list.

### 4. Evidence Judgment

Does the agent distinguish between:

- behavior confirmed by code or runtime evidence
- reasonable inference
- remaining uncertainty

The agent should not make strong conclusions from insufficient evidence.

### 5. Change Decision

When a change is needed, does the agent choose a solution that fits the current
architecture and avoids unnecessary restructuring?

The user's proposed solution should be treated as a hypothesis unless it is an
explicit requirement.

### 6. Validation

After modifying code, does the agent choose the smallest validation scope that
is sufficient for confidence?

Examples:

- localized frontend changes may require targeted tests, lint, build, or type validation depending on the change
- backend logic should normally begin with the smallest relevant test
- cross-stack changes should validate affected backend and frontend behavior separately when appropriate
- documentation-only changes normally do not require a full build or test suite

Validation quality is judged by appropriateness, not by the number of commands
executed.

### 7. Convergence

Does the agent stop investigating and finish the task once enough evidence has
been collected?

More tool calls are not automatically worse.

The important question is whether additional investigation continues to produce
meaningful evidence.

Repeated reads, repeated confirmation of already established facts, or
unnecessary exploration after the conclusion is already supported should lower
the convergence score.

## Auxiliary Metrics

Core scoring evaluates engineering behavior.

Auxiliary metrics provide additional observations and should not automatically
determine the score.

Possible metrics include:

- `iterations`
- `tool_calls`
- `read_calls`
- `write_calls`
- `validation_calls`
- `approval_count`
- `continuation_count`
- `duplicate_tool_calls`
- `max_iteration_hit`
- `task_completed`
- `language_consistency`

Language consistency is tracked as a user-experience and instruction-following
signal rather than a core engineering capability score.

## Case Modes

### `read_only`

The agent may inspect the project but should not modify it.

### `write`

The task permits project modification.

Write cases must continue to use Chatty's normal write approval and continuation
behavior.

The evaluation system should not bypass approval simply to make automated
evaluation easier.

## Evaluation Principles

1. Evaluate agent behavior, not agreement with a predefined implementation.
2. Keep the evaluation system outside the Agent runtime.
3. Do not change the runtime specifically to make an individual case pass.
4. Prefer representative engineering tasks over synthetic benchmark puzzles.
5. Preserve normal permissions, approval, tool execution, persistence, and continuation behavior.
6. Compare models under the same harness when possible.
7. Treat model-specific weaknesses separately from model-independent runtime correctness problems.
8. Use small smoke evaluations for frequent checks and the full suite for meaningful runtime or prompt changes.

## Smoke Eval

The initial smoke set is:

- `TECH-REQ-01`
- `TECH-CLARIFY-01`
- `TECH-WRITE-01`
- `TECH-CONV-01`

Together these cover:

- requirement understanding
- clarification boundaries
- full engineering execution
- convergence

## Known v1 Limitations

Some cases require additional support before they can be executed reliably.

### Conversation-dependent cases

`TECH-REF-01` contains a conversational reference such as "之前那个模型切换的地方".

A future case schema should support setup messages or conversation fixtures so
the reference can be evaluated in a controlled conversation context.

### Validation-recovery cases

`TECH-REPAIR-01` currently describes the expected recovery behavior but does not
yet define a deterministic project change that produces a safe validation
failure.

A concrete fixture should be designed before using this case as a formal
benchmark.

## Future Work

Possible later improvements include:

- case setup messages
- isolated evaluation worktrees
- automated runtime metric collection
- structured result files
- repeat-run comparison
- model comparison reports
- optional automated judging for selected objective behaviors

These should only be added when the simple evaluation workflow becomes
insufficient.
