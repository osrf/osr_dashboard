#!/usr/bin/env python3

import argparse
import contextlib
import http.server
import os
import socket
import sys


def add_serve_arguments(parser: argparse.ArgumentParser):
    """
    Add arguments for the serve command
    """

    group = parser.add_argument_group("serve")
    group.add_argument(
        "--pages-dir",
        default=os.path.join(os.curdir, "pages"),
        help="Output path for generated json files",
    )
    group.add_argument(
        "--port",
        default=8000,
        help="Server port",
    )


def serve(args=None) -> int:
    """
    Entrypoint for the compute command
    """

    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser()
    add_serve_arguments(parser)
    args = parser.parse_args(args)

    handler_class = http.server.SimpleHTTPRequestHandler

    class DualStackServer(http.server.ThreadingHTTPServer):
        def server_bind(self):
            # suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()

        def finish_request(self, request, client_address):
            self.RequestHandlerClass(
                request, client_address, self, directory=args.pages_dir
            )

    http.server.test(
        HandlerClass=handler_class, ServerClass=DualStackServer, port=args.port
    )
    return 0


if __name__ == "__main__":
    sys.exit(serve())
