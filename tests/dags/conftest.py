"""Keep Airflow's home directory out of the user's machine while testing DAGs."""

import os
import tempfile

# Must run before airflow is imported: it creates its config files in AIRFLOW_HOME.
os.environ.setdefault("AIRFLOW_HOME", tempfile.mkdtemp(prefix="airflow-test-"))
