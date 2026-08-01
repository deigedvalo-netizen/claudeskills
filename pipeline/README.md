# SDLC Pipeline — Handoff Contract

`handoff.schema.json` is the single source of truth for every machine-to-machine
handoff in the autonomous SDLC pipeline. Each bot stage emits exactly one document
that MUST validate against this schema. Downstream bots MUST reject any document
that fails validation and treat it as a stage failure.

## Stages

| Stage | Bot | Emits (top-level key) |
|---|---|---|
| 1 | requirements-planner-bot | (requirements artifact — upstream input) |
| 2 | architect-bot | `architecture_spec` or `clarification_request` |
| 3 | implementation-bot | `implementation_manifest` or `clarification_request` |
| 4 | test-bot | `test_manifest` or `clarification_request` |
| 5 | review-bot | (consumes `test_manifest` + PR) |

Any stage may instead emit a `clarification_request` with `status: BLOCKED` and a
`route_to` naming the bot that must resolve the defect. A document has exactly one
top-level key (`minProperties`/`maxProperties` = 1).

## Using it in a bot prompt

Point the prompt's `{{handoff_schema_ref}}` placeholder at the raw URL:

```
https://raw.githubusercontent.com/deigedvalo-netizen/claudeskills/main/pipeline/handoff.schema.json
```

## Invariants the schema enforces

- Exactly one envelope per document (no mixed handoffs).
- `clarification_request.status` is always `BLOCKED`; `from`/`route_to` come from a
  fixed set of stage names.
- COMPLETE manifests require a `self_verification` object whose `schema_valid` is
  mandatory.
- `test_manifest.suite_result.failed` must be `0` — a green suite is the only valid
  COMPLETE handoff; failures route back as a `clarification_request`.
- `technology_choices[*].version` and `dependencies_used[*].version` are required
  pinned strings.
- Architect `options_considered` holds 2–3 options.

## Validating locally

```bash
pip install jsonschema
python -c "import json; from jsonschema import Draft202012Validator as V; V.check_schema(json.load(open('pipeline/handoff.schema.json'))); print('ok')"
```
