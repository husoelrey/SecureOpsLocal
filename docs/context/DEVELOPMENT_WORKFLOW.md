# SecureOps Local — Development Workflow

## 1. Purpose

Development is performed through small, verifiable tasks regardless of the editor,
assistant, or automation tool in use. Each task must leave a clear technical result
and enough evidence for the user to understand what changed.

## 2. Required preflight

Before modifying the repository:

1. Read AGENTS.md and PLAN.md.
2. Read CURRENT_STATUS.md and the context documents relevant to the task.
3. Run git status --short --branch.
4. Inspect existing implementation and tests.
5. Identify the current P phase and its exit criteria.
6. Confirm that the requested mutation is within the user's authority.
7. Verify unstable package, runtime, model, and API facts through current primary sources.
8. Define the smallest useful change.

Use reasonable assumptions when they are safe and reversible. Do not turn preflight into unnecessary approval requests.

## 3. Task contract

Before implementation, establish:

- Objective
- Explicit non-goals
- Files expected to change
- Success criteria
- Validation commands
- Security and privacy impact
- Fallback behavior

Split broad work into bounded tasks. Do not generate the entire product in one step.

## 4. File and module policy

- Follow the repository layout and local instructions.
- Create a module only for a clear responsibility.
- Avoid ambiguous catch-all modules.
- Keep runtime-specific code inside provider adapters.
- Keep domain contracts independent of HTTP frameworks and runtime SDKs.
- Use readable synthetic fixtures.
- Exclude generated files, caches, databases, downloaded documents, logs, and model artifacts through repository policy.

## 5. Dependency policy

Before adding a dependency, determine:

1. Whether the standard library is sufficient
2. Whether the dependency reduces real complexity
3. Whether it supports Windows and the container environment
4. Whether it can be packaged offline
5. Whether its license and maintenance state are acceptable
6. Whether it conflicts with runtime-specific packages

Do not force a Windows-only Foundry dependency into the shared container dependency set. Keep host-specific requirements isolated when necessary.

## 6. Implementation loop

1. Add or identify a failing contract test or fixture.
2. Implement the smallest behavior that satisfies it.
3. Run the targeted success-path test.
4. Run relevant failure-path tests.
5. Run the broader deterministic test group.
6. Run Ruff and mypy for affected scope.
7. Review the diff for unrelated changes and sensitive content.
8. Update context documents and CURRENT_STATUS.md.
9. Report the outcome and evidence.

## 7. Validation ladder

Use the smallest useful sequence:

1. Target test
2. Related unit-test package
3. Deterministic suite
4. Ruff format and lint checks
5. mypy
6. Relevant integration tests
7. Explicitly requested or required slow, runtime, and offline checks

Normal development relies on contracts and fake providers. Do not download or invoke real models for every small code change.

## 8. Current-information verification

Treat the following as unstable and verify them against primary documentation before implementation:

- Foundry Local packages, CLI commands, SDK APIs, and catalog aliases
- Ollama API fields and runtime behavior
- Model names, revisions, digests, quantization, and licenses
- FastAPI, Pydantic, SQLAlchemy, and packaging compatibility
- Security advisories and dependency versions

Do not copy outdated sample code as current SDK behavior.

## 9. Failure diagnosis

When a command or test fails:

1. Preserve the exact error and exit code.
2. Reproduce it with the smallest command.
3. Separate environment, dependency, implementation, and external-runtime causes.
4. Collect evidence through versions, status, health checks, and minimal requests.
5. Change one hypothesis at a time.
6. Rerun the failing check after the fix.
7. If unresolved, document the proven boundary, last working state, and approved fallback.

## 10. Progress updates

During tool-heavy work, provide a concise update at least once per minute. State what was verified, which risk was resolved, and what bounded step is running next. Avoid flooding the user with raw terminal detail.

## 11. Completion report

Every implementation handoff includes:

- Result
- Created or changed files
- Validation commands
- Test results
- Known limitations or deferred decisions
- One safe next task

On failure, also include the minimum reproduction command, proven source of failure, last working state, and fallback.

## 12. Branch, commit, and push policy

Use tool-neutral branch names:

- feature/p<phase>-<feature> for product or project features
- fix/<topic> for bounded corrections
- docs/<topic> for documentation-only work
- spike/<topic> for uncertain experiments

Do not include an editor, assistant, automation product, contributor identity, or
vendor name in a branch merely to identify which tool performed the work.

Create one branch for each bounded feature or experiment. Keep main in a verified
state. Create small, single-purpose commits after the relevant checks pass. When the
active user request authorizes Git publication, push every verified feature commit to
its working branch. Merge into main only after the feature or phase exit criteria
pass. Failed experiments remain isolated from main.

Do not force-push, rewrite shared history, stage unrelated changes, or commit model
weights, caches, secrets, raw logs, generated runtime data, or operational databases.

Before each commit:

- Run git diff --check.
- Inspect git status --short.
- Confirm no unexpected generated or sensitive file exists.
- Run applicable tests and static checks.
- Update documentation and CURRENT_STATUS.md.
- Propose a single-purpose commit message.

Example messages:

- docs: normalize SecureOps Local project context
- chore: bootstrap Python quality tooling
- feat(parser): parse failed SSH authentication events
- feat(rag): add TF-IDF chunk retrieval
- feat(llm): add Ollama provider adapter
- test(benchmark): add labeled SSH incident cases

Commit and push only when the active user request authorizes them.

## 13. Phase discipline

- Work only inside the current P phase unless the user changes scope.
- Do not start a later phase while an earlier required exit criterion is failing.
- Update PLAN.md checkboxes only after evidence exists.
- Update CURRENT_STATUS.md with the exact next action and blockers.
- Record durable architecture or scope decisions in DECISION_LOG.md.

## 14. Prohibited workflow patterns

- Large untested implementation drops
- Hard-coding a Foundry model before device catalog inspection
- Treating invalid model output as a successful string response
- Logging raw logs, prompts, or complete model responses
- Adding a cloud fallback
- Using real organizational or attack data
- Overwriting unrelated user changes
- Ignoring a failed phase criterion
- Adding infrastructure solely for appearance
