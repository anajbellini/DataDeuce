## [0.1.0] - 2026-10-08

### Features

- Add docker-compose.yml for Airflow (LocalExecutor)
- Add warehouse-postgres service to docker-compose
- Start ATP/WTA source data profiling notebook
- Add pandas dependency and basic ATP/WTA exploration
- Split ATP/WTA files and profile date range and timestamp format
- Profile draw_size mismatches, score outcomes, and duplicate rows
- Investigate bye handling and draw_size inconsistency across formats
- Validate player_id-to-name referential integrity
- Validate serve-stat column consistency across matches
- Validate break-point saved/faced consistency
- Validate categorical columns against the TML-Database dictionary
- Add historical consistency checks across sample years
- Add bronze DDL for ATP/WTA raw match history
- Index (_source_file, _source_file_hash) on bronze tables
- Mount infra/postgres into warehouse-postgres's initdb.d
- Started fetch.py
- Default source_url to SOURCE_URL in list_source_files
- Enforce pydocstyle (google convention) via ruff
- Add get_connection()
- Add already_loaded idempotency check
- Add load()
- Implemented configure_logger()
- Add retry with backoff to fetch()
- Add structured logs to fetch.py
- Add module logger to load.py
- Log skipped files in load()
- Log row count on successful insert in load()
- Log insert failures before re-raising in load()
- Generate CHANGELOG.md from commit history via git-cliff
- Build a custom Airflow image with src/ installed
- Create a dedicated bronze_writer role at warehouse init
- Pass warehouse connection env vars to Airflow containers
- Add first draft of the bronze_layer DAG
- Log and summarize loaded rows in the bronze_layer DAG
- Schedule the bronze_layer DAG daily with retries
- Raise on source files with no data rows
- Add bronze tables for the ongoing tournament files
- Created DDL script for schema "meta"
- Grant the ingestion role access to the meta schema
- Add get_state to read the ingested mtime of each source file
- Add has_changed to detect updated source files
- Add save_state to record the ingested mtime of a source file
- List ongoing source files and expose their mtime
- Load ongoing files into their own bronze tables
- Log the ongoing flag in the load events
- Skip unchanged source files in the bronze DAG
- Always summarize and log skipped files in the bronze DAG
- Run the bronze DAG every three hours

### Bug Fixes

- Exclude .uv-cache from yamllint scope
- Align ATP and WTA Deep Dive question order
- Disambiguate ATP table comment from the WTA file pattern
- Added pattern detection to separate ATP and WTA
- Check HTTP status before parsing JSON in list_source_files
- Preserve malformed CSV rows via DictReader restkey
- Rollback on insert failure to keep the connection usable
- Guard against a None response in _is_transient
- Bind published ports to loopback only
- Pass plain dicts between tasks in the bronze_layer DAG
- Send JSON logs to stdout instead of stderr
- Store processed_at as timestamptz and make it not null
- Reload a file that goes back to an earlier version

### Documentation

- Mark project as WIP and link to Wiki
- Switch profiling notebook source to TennisMyLife
- Nest First Look header section, matching Loka notebook pattern
- Add takeaways to remaining Deep Dive questions
- Cross-check Hobart serve-stat anomaly against Sofascore
- Profile current-season data behavior for the raw schema key design
- Add docstrings to ingestion fetch functions
- Trim verbose module docstring in test_load.py
- Add a "How this project was built" section to the README
- Fixed typo on comment
- Point the compose env comment to db.py
- Update the README for the incremental ingestion
- Regenerate CHANGELOG.md

### Refactor

- Let pandas render notebook output instead of print()
- Shorten load.py param names (conn, content)
- Rename bronze_writer role to ingestion_runner
- Configure the JSON logger once at DAG import
- Store _ingested_at as timestamptz in the bronze tables
- Move get_connection to a dedicated db module

### Testing

- Add unit tests for fetch.py and load.py
- Add integrity and task tests for the bronze_layer DAG

### Styling

- Use lowercase SQL keywords in the bronze DDL

### Miscellaneous Tasks

- Scaffold project folder structure
- Add .gitignore
- Add MIT license and MR template
- Add CLAUDE.md with repo language rule
- Document issue-tracking workflow in CLAUDE.md
- Add .env.example template
- Pin Python and dbt tool versions
- Manage Python deps with uv
- Add basic CI pipeline with Python and dbt lint checks
- Add yamllint to the CI pipeline
- Add pre-commit hooks mirroring CI lint checks
- Add sqlfluff-fix autofix to pre-commit
- Add jupyterlab and ipykernel as dev dependencies
- Declare requests as an explicit dependency
- Add psycopg as direct dependency
- Add python-dotenv and warehouse host/port env vars
- Added dependencies
- Add apache-airflow as a dev dependency for DAG authoring
- Add src and the DAGs folder to the pytest path
- Renamed some Postgres scripts
- Renamed Bronze layer DDL script
- Trim .gitignore to the tools actually used
