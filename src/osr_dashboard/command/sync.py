#!/usr/bin/env python3
import argparse
import os
import sys

from osr_dashboard.distribution import get_distributions
from osr_dashboard.util import file_or_url_type


def add_sync_arguments(parser: argparse.ArgumentParser):
    """
    Add arguments for the sync command
    """

    group = parser.add_argument_group("sync")
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
        "--distro-path",
        nargs="?",
        default=os.path.join(os.curdir, "distributions"),
        help="Location of the distribution cache path",
    )


def sync(args=None) -> int:
    """
    Entrypoint for the sync command
    """
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser()
    add_sync_arguments(parser)
    args = parser.parse_args(args)

    os.makedirs(args.distro_path, exist_ok=True)
    distributions = get_distributions(args.config, args.distro_path)

    for distro in distributions:
        if not distro.import_():
            print(f"Error importing {distro.name}")
    return 0


if __name__ == "__main__":
    sys.exit(sync())
