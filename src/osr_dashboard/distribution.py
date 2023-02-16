import os
from typing import Dict, List

import yaml
from vcstool.commands.import_ import add_dependencies, get_repositories
from vcstool.executor import execute_jobs, output_results

from osr_dashboard.repository import Repository
from osr_dashboard.util import resolve_uri


class Distribution:
    """Class for keeping track of a software distribution"""

    def __init__(self, name: str, url: str, cache_root: str) -> None:
        self.name: str = name
        self.url: str = url
        self._cache_dir = (
            os.path.join(os.path.curdir, "distributions")
            if cache_root == ""
            else cache_root
        )

        self.repos: Dict[str, Repository] = {}
        config = get_repositories(resolve_uri(url))

        for local_path, entry in config.items():
            self.repos[local_path] = Repository(
                local_path=local_path,
                vcs_entry=entry,
                distro_root=self.path,
            )

    @property
    def path(self) -> str:
        return os.path.join(self._cache_dir, self.name)

    @property
    def cache_dir(self) -> str:
        return self._cache_dir

    def import_(self, workers: int = 4, debug: bool = False) -> bool:
        jobs = []
        for repo in self.repos.values():
            jobs.append(repo.import_job())
        add_dependencies(jobs)
        results = execute_jobs(
            jobs, show_progress=True, number_of_workers=workers, debug_jobs=debug
        )
        output_results(results)
        any_error = any(r["returncode"] for r in results)
        return not any_error


def _parse_distributions(yaml_file, cache_root: str) -> List[Distribution]:
    """
    Parse distributions from a yaml file
    """
    try:
        root = yaml.safe_load(yaml_file)
    except yaml.YAMLError as ex:
        raise RuntimeError(f"Input data is not valid yaml format: {ex}") from ex

    try:
        ret = []
        for distro_name, values in root["distributions"].items():
            ret.append(Distribution(distro_name, values["url"], cache_root))
        return ret
    except KeyError as ex:
        raise RuntimeError(f"Input data is not valid format: {ex}") from ex


def get_distributions(uri, cache_root: str) -> List[Distribution]:
    """
    Retrieve a list of distributions from a file or URL
    """
    uri = resolve_uri(uri)
    try:
        distributions = _parse_distributions(uri, cache_root)
        return distributions
    except (yaml.YAMLError, KeyError) as ex:
        raise RuntimeError("Input data in not valid YAML format: {ex}") from ex
