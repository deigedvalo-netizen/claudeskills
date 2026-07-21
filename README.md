# Prompt Smith Library

The permanent home for my SDLC prompt-engineering bot and every prompt it produces.

## Layout

```
├── creation-prompt.md          # Meta prompt: rebuilds the whole bot from scratch
├── skills/
│   └── sdlc-prompt-smith/
│       └── SKILL.md            # The Claude skill (save via a .skill file or Claude settings)
├── project-prompts/
│   └── sdlc-prompt-smith-project-prompt.md   # System prompt for a Claude Project
└── prompts/                    # The library: every generated prompt, filed by SDLC stage
    ├── planning/
    ├── architecture/
    ├── implementation/
    ├── code-review/
    ├── testing/
    ├── ci-cd/
    ├── debugging/
    ├── documentation/
    ├── refactoring/
    └── release/
```

## How the bot uses this repo

- **INDEX.md** at the repo root lists every stored prompt with a one-line description. The bot reads the index first, then fetches only the prompt files it needs — keep the index current.
- When the bot generates a prompt worth keeping, save it under `prompts/<stage>/` as a `.md` file with a short frontmatter header (name, stage, description, placeholders used) and add a line to INDEX.md.
- This repo is **public**: any Claude session can read it with no auth via `https://raw.githubusercontent.com/deigedvalo-netizen/claudeskills/main/<path>`. Writes go through the GitHub connector.

## Prompt file convention

```markdown
---
name: ts-pr-review
stage: code-review
description: Reviews TypeScript PR diffs with severity labels and file:line citations
placeholders: project name, version, framework, diff
---

<the prompt itself in a fenced code block>
```
