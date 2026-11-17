# ml

Training scripts, evaluation results and **model cards** for the models used by the enrichment service.
Each model card documents its data (source and licence), metrics and known limits.

## Models

| Model | Model card | Status |
|---|---|---|
| Language detection (FR / EN) | [language/](language/README.md) | In use (py3langid, off the shelf) |
| Sentiment | — | Planned |
| Topic | — | Planned |
| Churn risk (rules) | — | Planned |

Evaluation scripts are run from the repository root, e.g. `uv run python ml/language/evaluate.py`.
