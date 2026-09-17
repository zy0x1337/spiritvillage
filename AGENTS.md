# Spirit Village

Cozy mobile farming/idle game. Direction: Godot 4/GDScript; Blender-Python → GLB; CC0 environment assets; original rounded, nonhuman garden beings. Portrait, elevated orthographic camera. Generated mockups are visual references, not implemented assets.

## Working agreement

- ChatGPT orchestrates architecture, task scope, model selection and review. Executors implement bounded assignments; the user relays tasks.
- Follow the current task and applicable repository instructions. Make routine implementation decisions independently; finish the requested scope, including feasible validation and fixes.
- Preserve unrelated work. Flag consequential scope or architecture changes with a recommendation.
- Use one writer per file; parallel work requires separate ownership. Delegate only when the task requests it.

## Context

- Read only files needed for the task. Use targeted searches and diffs; expand when evidence requires it.
- On resuming or planning, consult docs/STATUS.md. For an isolated edit, use it only if relevant.
- Consult art/README.md for asset generation/export, if present. Load other documentation only when needed.
- Treat code, current Git refs and executed checks as evidence. Status notes may be stale.
- Do not repeat project background, unchanged plans, whole files or successful logs in chat. Keep material failures and limitations visible.

## Environment and validation

- Remote agents and the user's PC are separate environments. Check required tools once per environment; do not infer PC access from the mobile app.
- If Blender/Godot is unavailable, complete feasible source work and report runtime/export/render checks as NOT RUN. Syntax checks do not validate Blender APIs or visuals.
- Validate affected behavior proportionately. Broaden testing for a concrete risk, not by default.
- Keep simulation independent of rendering. Keep generation scripts portable and record third-party asset provenance.

## Handoff

- Report: task/result; branch and commit or UNCOMMITTED; changed paths; checks PASS/FAIL/NOT RUN with evidence; blocker or next step.
- Target 150 words, expanding for actionable failures. Link pushed commits/PRs; identify unpushed work explicitly.
- Update docs/STATUS.md when task completion changes project state. Keep it under 200 words; replace stale state instead of appending a diary.
- Follow task-specific commit/push instructions. Never imply local changes are visible on GitHub.

## Orchestrator

- Select the model outside the executor prompt.
- Task brief: outcome, base branch/ref when known, relevant inputs, write scope, acceptance criteria, execution environment, publication instructions.
- Specify constraints and interfaces; leave routine implementation to the executor.
- Review the reported revision and relevant diff. Request only missing evidence; do not repeat verified work without a reason.
- Keep durable rules here, current state in STATUS, specialist procedures near their code. Add instructions only for recurring problems.
