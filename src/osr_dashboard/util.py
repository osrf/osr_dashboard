import argparse
import os
import urllib.request as request

from osr_dashboard import __version__ as dashboard_version


def resolve_uri(uri):
    if isinstance(uri, str):
        uri = file_or_url_type(uri)
    try:
        if isinstance(uri, request.Request):
            uri = request.urlopen(uri)
    except (RuntimeError, request.URLError) as ex:
        print(ex)
        return None

    return uri


def file_or_url_type(value):
    if os.path.exists(value) or "://" not in value:
        return argparse.FileType("r")(value)
    # use another user agent to avoid getting a 403 (forbidden) error,
    # since some websites blacklist or block unrecognized user agents
    return request.Request(
        value, headers={"User-Agent": f"osr-dashboard/{dashboard_version}"}
    )


def existing_dir(path):
    """
    Function to check if a directory is existing for argparse

    """
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(f"Path '{path}' does not exist.")
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError(f"Path '{path}' is not a directory.")
    return path
