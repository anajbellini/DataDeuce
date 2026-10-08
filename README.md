# Data Deuce: A Tennis Data Engineering Project

> 🚧 Work in progress.

Full documentation lives in the [Wiki](https://gitlab.com/anajuliabellini/data-engineering-portfolio/DataDeuce/-/wikis/Home).

## How this project was built

This is a learning project, built with an AI assistant (Claude Code). To keep that transparent, here is how the work was split.

**Decided and written by me**
- The key decisions: the medallion layout, the choice of data source, schema-on-read bronze tables with a file-level hash for idempotent loads, one Airflow task per file with no file content in XCom, and one database role per process (`ingestion_runner`, later `dbt_runner`) instead of one per layer.
- The ingestion code: `fetch.py`, `load.py`, `state.py` (the functions behind the incremental load), retries and structured logging, the skeleton of the `bronze_layer` DAG, and its filter that skips files that did not change.
- The dbt models, when that milestone starts.

**Done with AI assistance**
- Proposing alternatives and trade-offs for many of those decisions, which I then chose between, and spotting problems (for example, `load()` returning 0 for both "already loaded" and "empty file", or a hash check that would skip a file going back to an earlier version). For the ongoing files, that is where snapshots instead of upserts and the 3-hour schedule came from.
- Infrastructure and tooling: `docker-compose.yml`, the custom Airflow image, CI, pre-commit, the changelog setup, and the role/DCL script.
- The unit tests, and the final wiring of the DAG (task payloads, scheduling, the summary task that always runs).
- Running the incremental load end to end against the local stack, and the wiki pages on ingestion.
- Code review, and explanations of the concepts I was learning (Airflow task mapping, XCom, dbt).
