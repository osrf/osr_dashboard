#!/usr/bin/env python3

import argparse
import datetime
import json
import os
import sys
from typing import Any, Dict, List

from osr_dashboard.distribution import Distribution, get_distributions
from osr_dashboard.repository import Repository
from osr_dashboard.util import existing_dir, file_or_url_type


def add_compute_arguments(parser: argparse.ArgumentParser):
    """
    Add arguments for the compute command
    """

    group = parser.add_argument_group("compute")
    group.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Additional debug information",
    )
    group.add_argument(
        "--clean",
        action="store_true",
        default=False,
        help="Clean repository directories before sync",
    )
    group.add_argument(
        "--config",
        type=file_or_url_type,
        default="-",
        metavar="FILE_OR_URL",
        help="Configuration to parse distribution from",
    )
    group.add_argument(
        "--output-dir",
        default=os.path.join(os.curdir, "pages"),
        help="Output path for generated json files",
    )
    group.add_argument(
        "--distro-path",
        nargs="?",
        type=existing_dir,
        default=os.path.join(os.curdir, "distributions"),
        help="Location of the distribution cache path",
    )


def clean_commit_message(message: str | bytes) -> List[str]:
    """
    Turn a commit message into a series of lines
    """
    if isinstance(message, bytes):
        message = message.decode()
    ret = []
    lines = message.split("\n")
    for line in lines:
        line = line.strip("\r")
        if len(line) > 0:
            ret.append(line)
    return ret


def timedelta_to_json(delta: datetime.timedelta) -> Dict[str, int]:
    """
    Convert a python timedelta into something for json
    """
    return {"days": int(delta.days), "seconds": int(delta.seconds)}


def compute_repo_stats(repo: Repository, generation_time: datetime.datetime):
    """
    Generate a dictionary of repository properties
    """
    ret: Dict[str, Any] = {}
    ret["name"] = repo.name

    github_info = repo.github_info
    if github_info:
        base_url = f"https://github.com/{github_info[0]}/{github_info[1]}"
    else:
        base_url = None

    ret["url"] = base_url
    if repo.branch:
        ret["branch"] = {
            "name": repo.branch,
            "url": f"{base_url}/tree/{repo.branch}",
        }

    if repo.head:
        commit = repo.head
        ret["latest_commit"] = {
            "SHA": str(commit),
            "url": f"{base_url}/commit/{commit}",
            "author": str(commit.author),
            "authored_date": str(
                commit.authored_datetime.replace(
                    tzinfo=datetime.timezone.utc
                ).isoformat()
            ),
            "commit_date": str(
                commit.committed_datetime.replace(
                    tzinfo=datetime.timezone.utc
                ).isoformat()
            ),
            "message": clean_commit_message(commit.message),
        }

    if repo.branch is not None and repo.latest_tag:
        commit = repo.latest_tag.commit
        ret["latest_tag"] = {
            "name": repo.latest_tag.name,
            "SHA": str(commit),
            "url": f"{base_url}/releases/tag/{repo.latest_tag.name}",
            "author": str(commit.author),
            "authored_date": str(
                commit.authored_datetime.replace(
                    tzinfo=datetime.timezone.utc
                ).isoformat()
            ),
            "commit_date": str(
                commit.committed_datetime.replace(
                    tzinfo=datetime.timezone.utc
                ).isoformat()
            ),
            "message": clean_commit_message(commit.message),
        }

    if repo.branch is not None and repo.head is not None and repo.latest_tag:
        commits_since_tag = list(
            repo.repo.iter_commits(f"{repo.latest_tag}..{repo.branch}")
        )
        head_dt = repo.head.committed_datetime.replace(tzinfo=datetime.timezone.utc)
        tag_dt = repo.latest_tag.commit.committed_datetime.replace(
            tzinfo=datetime.timezone.utc
        )
        diffstat = repo.repo.git.diff(repo.latest_tag, repo.head, stat=True)

        ret["release_delta"] = {
            "url": f"{base_url}/compare/{repo.latest_tag}...{repo.branch}",
            "commit_count": len(commits_since_tag),
            "tag_to_head": timedelta_to_json(head_dt - tag_dt),
            "tag_to_now": timedelta_to_json(generation_time - tag_dt),
            "head_to_now": timedelta_to_json(generation_time - head_dt),
            "diffstat": diffstat.split("\n"),
        }

    if repo.rosdistro_version is not None:
        ret["rosdistro_version"] = repo.rosdistro_version

    return ret


def compute_distro_stats(distro: Distribution) -> Dict[str, Any]:
    """
    Generate a dictionary of distribution properties
    """
    ret: Dict[str, Any] = {}
    now = datetime.datetime.now(datetime.timezone.utc)
    ret["name"] = distro.name
    ret["url"] = distro.url
    ret["generation_time"] = now.isoformat()
    ret["has_rosdistro_data"] = distro.rosdistro_url is not None
    ret["repos"] = []
    for repo in distro.repos.values():
        ret["repos"].append(compute_repo_stats(repo, now))
    return ret


def compute(args=None) -> int:
    """
    Entrypoint for the compute command
    """
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser()
    add_compute_arguments(parser)
    args = parser.parse_args(args)

    os.makedirs(args.output_dir, exist_ok=True)
    distributions = get_distributions(args.config, args.distro_path)

    for distro in distributions:
        with open(
            f"{args.output_dir}/{distro.name}.json", "w", encoding="utf8"
        ) as json_out:
            json.dump(compute_distro_stats(distro), json_out, indent=4)
    return 0


if __name__ == "__main__":
    sys.exit(compute())
