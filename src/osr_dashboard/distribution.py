import os
from typing import Dict, List

import requests

import yaml
from vcstool.commands.import_ import add_dependencies, get_repositories
from vcstool.executor import execute_jobs, output_results

from osr_dashboard.repository import Repository
from osr_dashboard.util import resolve_uri


class Distribution:
    """Class for keeping track of a software distribution"""

    def __init__(self, name: str, url: str, rosdistro_url: str, ros2_repos_to_rosdistro_name_map: Dict[str, str], cache_root: str) -> None:
        self.name: str = name
        self.url: str = url
        self.rosdistro_url: str = rosdistro_url
        self.ros2_repos_to_rosdistro_name_map: Dict[str, str] = ros2_repos_to_rosdistro_name_map
        self._cache_dir = (
            os.path.join(os.path.curdir, "distributions")
            if cache_root == ""
            else cache_root
        )

        self.repos: Dict[str, Repository] = {}
        config = get_repositories(resolve_uri(url))

        if self.rosdistro_url is not None:
            response = requests.get(self.rosdistro_url)
            if response.status_code != 200:
                raise RuntimeException(f'Failed to get data from {self.rosdistro_url}: {response.reason}')

            try:
                rosdistro_yaml = yaml.safe_load(response.text)
            except yaml.YAMLError as ex:
                raise RuntimeError(f'rosdistro URL {self.rosdistro_url} is not valid YAML')
                return False

        for local_path, entry in config.items():
            repo_name_only = local_path.split('/')[-1]
            if repo_name_only in self.ros2_repos_to_rosdistro_name_map:
                alt_name = self.ros2_repos_to_rosdistro_name_map[repo_name_only]
            else:
                alt_name = repo_name_only

            rosdistro_version = None
            if self.rosdistro_url is not None:
                # If we have a rosdistro_url, make sure that all repositories can be resolved in it
                rosdistro_version = ''
                key = ''
                if repo_name_only in rosdistro_yaml['repositories']:
                    key = repo_name_only
                elif alt_name in rosdistro_yaml['repositories']:
                    key = alt_name
                else:
                    raise RuntimeError(f'Could not find ros2 repos repository {repo_name_only} in rosdistro')

                rosdistro_repo_data = rosdistro_yaml['repositories'][key]
                if 'release' in rosdistro_repo_data:
                    rosdistro_release_data = rosdistro_repo_data['release']
                    if 'version' in rosdistro_release_data:
                        rosdistro_version = rosdistro_release_data['version']

            self.repos[local_path] = Repository(
                local_path=local_path,
                vcs_entry=entry,
                distro_root=self.path,
                rosdistro_version=rosdistro_version,
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
            ros2_repos_to_rosdistro_name_map = {}
            rosdistro_url = None
            if "rosdistro" in values:
                if not "url" in values["rosdistro"]:
                    raise RuntimeError("rosdistro section specified, but no 'url' given")
                rosdistro_url = values["rosdistro"]["url"]

                if "ros2_repos_to_rosdistro_name_map" in values["rosdistro"]:
                    ros2_repos_to_rosdistro_name_map = values["rosdistro"]["ros2_repos_to_rosdistro_name_map"]

            ret.append(Distribution(distro_name, values["url"], rosdistro_url, ros2_repos_to_rosdistro_name_map, cache_root))
        return ret
    except KeyError as ex:
        raise RuntimeError(f"Input data is not valid format: {ex}") from ex


def get_distributions(uri, cache_root: str) -> List[Distribution]:
    """
    Retrieve a list of distributions from a file or URL
    """
    uri = resolve_uri(uri)
    try:
        return _parse_distributions(uri, cache_root)
    except (yaml.YAMLError, KeyError) as ex:
        raise RuntimeError("Input data in not valid YAML format: {ex}") from ex
