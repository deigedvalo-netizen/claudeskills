# Prompt Index

One line per stored prompt. The bot reads this file first to know what already exists before generating something new.

Format: `| name | stage | path | description |`

| Name | Stage | Path | Description |
|---|---|---|---|
| project-planner | planning | prompts/planning/project-planner.md | First pipeline agent; turns a raw idea into a tech-agnostic vision + milestone plan with architecture handoff |
| ts-pr-review | code-review | prompts/code-review/ts-pr-review.md | Reviews TypeScript PR diffs with severity labels and file:line citations |
