# Data Deuce: A Tennis Data Engineering Project

> 🚧 Work in progress.

Full documentation lives in the [Wiki](https://gitlab.com/anajuliabellini/data-engineering-portfolio/DataDeuce/-/wikis/Home).

## How this project was built

This is a learning project, built with an AI assistant (Claude Code). To keep that transparent, here is how the work was split.

**Decided and written by me**
- The key decisions: the medallion layout, the choice of data source, schema-on-read bronze tables with a file-level hash for idempotent loads, one Airflow task per file with no file content in XCom, and one database role per process (`ingestion_runner`, later `dbt_runner`) instead of one per layer.
- The ingestion code: `fetch.py`, `load.py`, retries and structured logging, and the skeleton of the `bronze_layer` DAG.
- The dbt models, when that milestone starts.

**Done with AI assistance**
- Proposing alternatives and trade-offs for many of those decisions, which I then chose between, and spotting problems (for example, `load()` returning 0 for both "already loaded" and "empty file").
- Infrastructure and tooling: `docker-compose.yml`, the custom Airflow image, CI, pre-commit, the changelog setup, and the role/DCL script.
- The unit tests, and the final wiring of the DAG (task payloads, scheduling, summary task).
- Code review, and explanations of the concepts I was learning (Airflow task mapping, XCom, dbt).
