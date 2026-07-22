# Prompt Index

One line per stored prompt. The bot reads this file first to know what already exists before generating something new.

Format: `| name | stage | path | description |`

| Name | Stage | Path | Description |
|---|---|---|---|
| project-planner | planning | prompts/planning/project-planner.md | First pipeline agent; turns a raw idea into a tech-agnostic vision + milestone plan with architecture handoff |
| system-architect | architecture | prompts/architecture/system-architect.md | Stage 4 Design; turns plan + analysis into a technical design with explicit trade-offs, tech choices, and a test strategy |
| feature-implementer | implementation | prompts/implementation/feature-implementer.md | Stage 5; implements one milestone to the design on a branch + PR, with a changelog and deviations log |
| generic-pr-review | code-review | prompts/code-review/generic-pr-review.md | Language-agnostic PR review vs. the design; severity labels, file:line citations, design-escalation verdict |
| ts-pr-review | code-review | prompts/code-review/ts-pr-review.md | Reviews TypeScript PR diffs with severity labels and file:line citations |
| test-verifier | testing | prompts/testing/test-verifier.md | Stage 6; derives tests from acceptance criteria, reports run results + coverage against the gate |
| doc-writer | documentation | prompts/documentation/doc-writer.md | Documents only what shipped and passed tests, for a named audience and format |
| release-manager | release | prompts/release/release-manager.md | Stage 7 Deployment; cuts a gated, versioned release with mandatory rollback |
