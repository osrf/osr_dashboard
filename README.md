# osr_dashboard

A program to compute and display information about sets of repositories, including:

* Repository name
* Default branch
* The latest commit
* The # of days since the last commit
* The latest tagged source version
* The days since the last source version was tagged
* The number of new commits since the latest source version was tagged

# Generating data

You can run this either using poetry, which manages dependencies for you, or just regular python.
In this example we'll use the ros2.yaml file as an example, but other `vcstool` files should work as well.

## Generating data using poetry

1. Install `poetry` (on Linux distributions, there is usually a `poetry` package).
1. Install dependencies of this project: `poetry install`
1. Gather the necessary data: `poetry run sync --config ./config/ros2.yaml`
1. Compute the necessary data: `poetry run compute --config ./config/ros2.yaml`
1. Run an http server locally: `poetry run serve`

## Generating data without poetry

1. Install `vcstool`
1. Gather the necessary data: `PYTHONPATH=src python3 ./src/osr_dashboard/command/sync.py --config ./config/ros2.yaml`
1. Compute the necessary data: `PYTHONPATH=src python3 ./src/osr_dashboard/command/compute.py --config ./config/ros2.yaml`
1. Run an http server locally: `PYTHONPATH=src python3 ./src/osr_dashboard/command/serve.py`

# Viewing the result

Visit http://localhost:8000?distribution=rolling
