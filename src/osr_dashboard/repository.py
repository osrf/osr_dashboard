from typing import Dict, List, Optional

import os

from vcstool.clients import vcstool_clients
from vcstool.commands.import_ import ImportCommand

import git


def get_recent_tags(repo: git.Repo) -> List[git.TagReference]:
    ret = []
    all_tags = {tag.commit: tag for tag in repo.tags}
    for commit in repo.iter_commits(
        repo.active_branch.name, max_count=100, first_parent=True
    ):
        if commit in all_tags:
            ret.append(all_tags[commit])
    return ret


class _ImportArgs(dict):
    def __init__(self) -> None:
        super().__init__()
        self.__dict__ = self
        self.path: str
        self.recursive = False
        self.shallow = False
        self.retry = 2
        self.force = False
        self.skip_existing = False
        self.workers = 4


class Repository:
    """A single entry in a distribution"""

    def __init__(
        self, local_path: str, vcs_entry: Dict[str, str], distro_root: str
    ) -> None:
        self._local_path: str = local_path
        self._distro_root = distro_root

        self._type: str = vcs_entry["type"]
        self._remote_url: str = vcs_entry["url"]
        self._version: Optional[str] = (
            vcs_entry["version"] if "version" in vcs_entry else None
        )

    @property
    def owner(self) -> Optional[str]:
        github_url = 'https://github.com/'
        if self._remote_url.find(github_url) >= 0:
            url = self._remote_url[self._remote_url.find(github_url) + len(github_url):]
            owner = url.split('/')[0]
            return owner
        return None

    @property
    def name(self) -> str:
        '''
        Get the name of the repository
        '''
        return self._local_path

    @property
    def path(self) -> str:
        '''
        Get the full filesystem path of the repository
        '''
        return os.path.join(self._distro_root, self._local_path)

    @property
    def repo(self) -> git.Repo:
        '''
        Get the underlying git repository object
        '''
        return git.Repo(self.path)

    @property
    def branch(self) -> Optional[str]:
        '''
        Get the head branch name from the repository
        '''
        return self.repo.active_branch.name

    @property
    def head(self) -> git.Commit:
        '''
        Get the head commit from the repository
        '''
        return self.repo.active_branch.commit

    @property
    def latest_tag(self) -> Optional[git.TagReference]:
        '''
        Get the latest release tag from the repository
        '''
        tags = get_recent_tags(self.repo)
        if len(tags) != 0:
            return tags[0]
        return None

    def import_job(self, shallow: bool = False, recursive: bool = False):
        '''
        Generate a vcs tool import job for this repository
        '''
        clients = [c for c in vcstool_clients if c.type == self._type]

        if not clients:
            from vcstool.clients.none import NoneClient
            job = {
                "client": NoneClient(self.path),
                "command": None,
                "cwd": self.path,
                "output": f"Repository type '{self._type}' is not supported",
                "returncode": NotImplemented,
            }
            return job

        client = clients[0](self.path)
        args = _ImportArgs()
        args.path = self.path

        command = ImportCommand(
            args,
            self._remote_url,
            str(self._version) if self._version else None,
            recursive=recursive,
            shallow=shallow,
        )
        return {"client": client, "command": command}
