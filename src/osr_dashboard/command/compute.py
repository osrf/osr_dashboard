from typing import Dict, Any

import argparse
import datetime
import json
import os
import sys

from osr_dashboard.distribution import get_distributions, Distribution
from osr_dashboard.repository import Repository
from osr_dashboard.util import existing_dir, file_or_url_type

from ghapi.all import GhApi


api = GhApi()


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
        "--path",
        nargs="?",
        type=existing_dir,
        default=os.path.join(os.curdir, "distributions"),
    )


def clean_commit_message(message: str):
    ret = []
    lines = message.split('\n')
    for line in lines:
        line = line.strip('\r')
        if len(line) > 0:
            ret.append(line)
    return ret


def compute_repo_stats(repo: Repository, generation_time: datetime.datetime):
    ret: Dict[str, Any] = {}
    ret["name"] = repo.name
    ret["url"] = f"https://github.com/{repo.owner}/{repo.name}"
    if repo.branch:
        ret["branch"] = {
            "name": repo.branch,
            "url": f"https://github.com/{repo.owner}/{repo.name}/tree/{repo.branch}",
        }

    if repo.head:
        commit = repo.head
        ret["latest_commit"] = {
            "SHA": str(commit),
            "url": f"https://github.com/{repo.owner}/{repo.name}/commit/{commit}",
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

    if repo.latest_tag:
        commit = repo.latest_tag.commit
        ret["latest_tag"] = {
            "name": repo.latest_tag.name,
            "SHA": str(commit),
            "url": f"https://github.com/{repo.owner}/{repo.name}/releases/tag/{repo.latest_tag.name}",
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

    if repo.head and repo.latest_tag:
        commits_since_tag = list(repo.repo.iter_commits(f'{repo.latest_tag}..{repo.branch}'))
        head_dt = repo.head.committed_datetime.replace(tzinfo=datetime.timezone.utc)
        tag_dt = repo.latest_tag.commit.committed_datetime.replace(tzinfo=datetime.timezone.utc)
        diffstat = repo.repo.git.diff(repo.latest_tag, repo.head, stat=True)

        def dt_to_json(dt):
            return {"days": int(dt.days), "seconds": int(dt.seconds)}

        ret["release_delta"] = {
            "url": f"https://github.com/{repo.owner}/{repo.name}/compare/{repo.latest_tag}...{repo.branch}",
            "commit_count": len(commits_since_tag),
            "tag_to_head": dt_to_json(head_dt - tag_dt),
            "tag_to_now": dt_to_json(generation_time - tag_dt),
            "head_to_now": dt_to_json(generation_time - head_dt),
            "diffstat": diffstat.split('\n'),
        }
    return ret


def compute_distro_stats(distro: Distribution):
    ret = {}
    now = datetime.datetime.now(datetime.timezone.utc)
    ret["name"] = distro.name
    ret["url"] = distro.url
    ret["generation_time"] = now.isoformat()
    ret["repos"] = []
    for repo_name, repo in distro.repos.items():
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

    distributions = get_distributions(args.config)

    for distro in distributions:
        distro.cache_dir = args.path
        with open(f'{distro.name}.json', 'w', encoding='utf8') as json_out:
            json.dump(compute_distro_stats(distro), json_out, indent=4)
    return 0


if __name__ == "__main__":
    sys.exit(compute())
