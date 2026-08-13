"""Run or update the project. This file uses the `doit` Python package. It works
like a Makefile, but is Python-based

"""

#######################################
## Configuration and Helpers for PyDoit
#######################################
## Make sure the src folder is in the path
import sys

sys.path.insert(1, "./src/")

import shutil
from os import environ
from pathlib import Path

from settings import config

DOIT_CONFIG = {
    "backend": "sqlite3",
    "dep_file": "./.doit-db.sqlite",
    ## The teaching pipeline. The `monitor` task is deliberately NOT a
    ## default: it always re-pulls data (which would otherwise re-trigger
    ## notebook runs on every plain `doit`); invoke it as `doit monitor`.
    "default_tasks": [
        "config",
        "pull",
        "fedwatch_chart",
        "run_notebooks",
        "build_chartbook_site",
        "run_pytest",
    ],
}


BASE_DIR = config("BASE_DIR")
DATA_DIR = config("DATA_DIR")
MANUAL_DATA_DIR = config("MANUAL_DATA_DIR")
OUTPUT_DIR = config("OUTPUT_DIR")
OS_TYPE = config("OS_TYPE")

## Helpers for handling Jupyter Notebook tasks
environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"

# fmt: off
## Helper functions for automatic execution of Jupyter notebooks
def jupyter_execute_notebook(notebook_path):
    return f"jupyter nbconvert --execute --to notebook --ClearMetadataPreprocessor.enabled=True --inplace {notebook_path}"
def jupyter_to_html(notebook_path, output_dir=OUTPUT_DIR):
    return f"jupyter nbconvert --to html --output-dir={output_dir} {notebook_path}"
def jupyter_to_md(notebook_path, output_dir=OUTPUT_DIR):
    """Requires jupytext"""
    return f"jupytext --to markdown --output-dir={output_dir} {notebook_path}"
def jupyter_clear_output(notebook_path):
    """Clear the output of a notebook"""
    return f"jupyter nbconvert --ClearOutputPreprocessor.enabled=True --ClearMetadataPreprocessor.enabled=True --inplace {notebook_path}"
# fmt: on


def mv(from_path, to_path):
    """Move a file to a folder"""
    from_path = Path(from_path)
    to_path = Path(to_path)
    to_path.mkdir(parents=True, exist_ok=True)
    if OS_TYPE == "nix":
        command = f"mv {from_path} {to_path}"
    else:
        command = f"move {from_path} {to_path}"
    return command


def copy_file(origin_path, destination_path, mkdir=True):
    """Create a Python action for copying a file."""

    def _copy_file():
        origin = Path(origin_path)
        dest = Path(destination_path)
        if mkdir:
            dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, dest)

    return _copy_file


##################################
## Begin rest of PyDoit tasks here
##################################


def task_config():
    """Create empty directories for data and output if they don't exist"""
    return {
        "actions": ["python ./src/settings.py"],
        "targets": [DATA_DIR, OUTPUT_DIR],
        "file_dep": ["./src/settings.py"],
        "clean": [],
    }


def task_pull():
    """Pull data from external sources.

    The Databento pull is free under the course subscription; it verifies
    this with the free cost-estimate endpoint and refuses to download
    anything that is not $0.00. Once the target parquet exists the task is
    skipped; refresh with `doit forget pull && doit`.
    """
    yield {
        "name": "fed_funds_futures",
        "doc": "Pull 30-Day Fed Funds futures (ZQ) daily bars from Databento",
        "actions": [
            "python ./src/settings.py",
            "python ./src/pull_fed_funds_futures.py",
        ],
        "targets": [DATA_DIR / "fed_funds_futures.parquet"],
        "file_dep": ["./src/settings.py", "./src/pull_fed_funds_futures.py"],
        "verbosity": 2,  # show the cost estimate
        "clean": [],
    }
    yield {
        "name": "effr",
        "doc": "Pull daily EFFR from FRED (no API key required)",
        "actions": [
            "python ./src/settings.py",
            "python ./src/pull_effr.py",
        ],
        "targets": [DATA_DIR / "effr.parquet"],
        "file_dep": ["./src/settings.py", "./src/pull_effr.py"],
        "verbosity": 2,
        "clean": [],
    }


def task_monitor():
    """Daily monitor entrypoint: refresh the data and append today's snapshot.

    Re-pulls the trailing futures window and EFFR (both free), then runs the
    EFFR-anchored forecast: appends one row to _data/fedwatch_history.parquet,
    rewrites the latest CSV, and refreshes the published charts. Always runs
    when invoked (`doit monitor`) -- a monitor's job is to re-check -- and is
    excluded from the default `doit` task list.
    """
    return {
        "actions": [
            "python ./src/settings.py",
            "python ./src/pull_fed_funds_futures.py",
            "python ./src/pull_effr.py",
            "python ./src/fedwatch_monitor.py",
            "python ./src/fedwatch_chart.py",
        ],
        "file_dep": [
            "./src/pull_fed_funds_futures.py",
            "./src/pull_effr.py",
            "./src/fedwatch.py",
            "./src/fedwatch_monitor.py",
            "./src/fedwatch_chart.py",
            "./data_manual/fomc_meetings.csv",
        ],
        "targets": [
            OUTPUT_DIR / "fedwatch_monitor_latest.csv",
        ],
        "uptodate": [False],
        "verbosity": 2,
        "clean": True,
    }


def task_fedwatch_chart():
    """Compute the latest FOMC forecast and render the PNG + HTML charts"""
    return {
        "actions": [
            "python ./src/fedwatch_chart.py",
        ],
        "file_dep": [
            "./src/fedwatch_chart.py",
            "./src/fedwatch.py",
            "./src/fedwatch_monitor.py",
            "./src/pull_fed_funds_futures.py",
            "./src/pull_effr.py",
            "./data_manual/fomc_meetings.csv",
            DATA_DIR / "fed_funds_futures.parquet",
            DATA_DIR / "effr.parquet",
        ],
        "targets": [
            OUTPUT_DIR / "fedwatch_latest_forecast.png",
            OUTPUT_DIR / "fedwatch_latest_forecast.html",
        ],
        "clean": True,
        "verbosity": 2,  # show the forecast numbers
    }


notebook_tasks = {
    "01_fed_funds_futures_data.ipynb.py": {
        "path": "./src/01_fed_funds_futures_data.ipynb.py",
        "file_dep": [
            "./src/pull_fed_funds_futures.py",
            "./src/fedwatch.py",
            DATA_DIR / "fed_funds_futures.parquet",
        ],
        "targets": [],
    },
    "02_fedwatch_replication.ipynb.py": {
        "path": "./src/02_fedwatch_replication.ipynb.py",
        "file_dep": [
            "./src/pull_fed_funds_futures.py",
            "./src/pull_effr.py",
            "./src/fedwatch.py",
            "./src/fedwatch_monitor.py",
            "./src/fedwatch_chart.py",
            "./data_manual/fomc_meetings.csv",
            DATA_DIR / "fed_funds_futures.parquet",
            DATA_DIR / "effr.parquet",
        ],
        "targets": [],
    },
}


# fmt: off
def task_run_notebooks():
    """Preps the notebooks for presentation format.
    Execute notebooks if the script version of it has been changed.
    """
    for notebook in notebook_tasks.keys():
        pyfile_path = Path(notebook_tasks[notebook]["path"])
        notebook_path = pyfile_path.with_suffix("")  # strips .py, leaves .ipynb
        notebook_name = notebook_path.stem  # e.g. "01_example_notebook_interactive"
        yield {
            "name": notebook,
            "actions": [
                """python -c "import sys; from datetime import datetime; print(f'Start """ + notebook + """: {datetime.now()}', file=sys.stderr)" """,
                f"jupytext --to notebook --output {notebook_path} {pyfile_path}",
                jupyter_execute_notebook(notebook_path),
                jupyter_to_html(notebook_path),
                mv(notebook_path, OUTPUT_DIR),
                """python -c "import sys; from datetime import datetime; print(f'End """ + notebook + """: {datetime.now()}', file=sys.stderr)" """,
            ],
            "file_dep": [
                pyfile_path,
                *notebook_tasks[notebook]["file_dep"],
            ],
            "targets": [
                OUTPUT_DIR / f"{notebook_name}.html",
                *notebook_tasks[notebook]["targets"],
            ],
            "clean": True,
        }
# fmt: on

sphinx_targets = [
    "./docs/index.html",
]


def task_build_chartbook_site():
    """Compile Sphinx Docs"""
    notebook_scripts = [
        Path(notebook_tasks[notebook]["path"])
        for notebook in notebook_tasks.keys()
    ]
    file_dep = [
        "./README.md",
        "./chartbook.toml",
        *notebook_scripts,
    ]

    return {
        "actions": [
            "chartbook build -f",
        ],  # Use docs as build destination
        "targets": sphinx_targets,
        "file_dep": file_dep,
        "task_dep": [
            "run_notebooks",
            "fedwatch_chart",
        ],
        "clean": True,
    }


def task_run_pytest():
    """Run pytest and save results to OUTPUT_DIR"""
    src_py_files = list(Path("./src").glob("*.py"))
    test_output = OUTPUT_DIR / "pytest_results.xml"

    def run_pytest():
        import subprocess

        # Run only the pipeline test files. The self-attestation tests
        # (src/test_monitor_self_attestation.py) are graded by the autograder
        # alone: they fail by design until the live site is up, and this task
        # runs inside the deploy workflow, which must be able to publish the
        # site *before* the attestation flag can honestly be set to True.
        result = subprocess.run(
            [
                "pytest",
                f"--junitxml={test_output}",
                "./src/test_fedwatch.py",
                "./src/test_fedwatch_monitor.py",
                "./src/test_misc_tools.py",
            ],
        )
        if result.returncode != 0:
            # Remove the XML so doit won't consider the target up-to-date
            Path(test_output).unlink(missing_ok=True)
            raise RuntimeError(f"pytest failed with exit code {result.returncode}")

    return {
        "actions": [run_pytest],
        "targets": [test_output],
        "file_dep": src_py_files,
        "clean": True,
        "verbosity": 2,
    }
