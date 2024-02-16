"""@desc
        Making use of the parser through cli
"""
from __future__ import print_function

import argparse
import sys
from datetime import datetime
from importlib import import_module

from blessed import Terminal
from web_tools import __version__
from web_tools.core.base import ReturnType
from web_tools.core.exceptions import NoResultsOrTrafficError


def display(results, term, args):
    """ Displays search results
    """
    def print_one(kwargs):
        """ Print one result to the console """
        # Header
        if kwargs.get("title"):
            print("\t{}".format(term.magenta(kwargs.pop("title"))))
        if kwargs.get("link"):
            print("\t{}".format(kwargs.pop("link")))
            print("\t-----------------------------------------------------")
        if kwargs.get("description"):
            print(kwargs.pop("description"))
        if kwargs.values():
            for k, v in kwargs.items():
                if v:
                    print(k.strip(), " : ", v)
        print("\n")

    if args.rank and args.rank > 10:
        sys.exit(
            "Results are only limited to 10, specify a different page number instead")

    if not args.rank:
        for i in results:
            print_one(i)
    else:
        rank = args.rank
        print_one(results[rank])


def get_engine_class(engine):
    """ Return the Engine Class """
    try:
        module = import_module(
            "web_tools.core.engines.{}".format(
                engine.lower()))
        return getattr(module, "Search")
    except (ImportError, ModuleNotFoundError):
        sys.exit('Engine < {} > does not exist'.format(engine))


def show_summary(term, engine_class):
    """ Show the summary of an Engine"""
    print("\t{}".format(term.magenta(engine_class.name)))
    print("\t-----------------------------------------------------")
    print(engine_class.summary)


def main(args):  # pylint: disable=too-many-branches
    """
        Executes logic from parsed arguments
    """
    term = Terminal()
    engine_class = get_engine_class(args.engine)

    if args.show_summary:
        show_summary(term, engine_class)
        return

    if not args.query:
        print("--show-summary or --query argument must be passed")
        sys.exit(1)

    # Initialize search Engine with required params
    engine = engine_class()
    try:
        if args.clear_cache:
            engine.clear_cache()
        # Display full details: Header, Link, Description
        start = datetime.now()
        results = engine.search(
            args.query, args.page, return_type=ReturnType(args.type), url=args.url, proxy=args.proxy, proxy_auth=(args.proxy_user, args.proxy_password))
        duration = datetime.now() - start
        display(results, term, args)
        print("Total search took -> %s seconds" % (duration))
    except NoResultsOrTrafficError as exc:
        print('\n', '{}'.format(term.red(str(exc))))


def create_parser():
    """
    runner that handles parsing logic
    """
    parser = argparse.ArgumentParser(description='SearchEngineParser', prog="pysearch")

    parser.add_argument('-V', '--version', action="version", version="%(prog)s v" + __version__)

    parser.add_argument(
        '-e', '--engine',
        help='Engine to use for parsing the query e.g google, yahoo, bing,'
             'duckduckgo (default: google)',
        default='google')

    parser.add_argument(
        '--show-summary',
        action='store_true',
        help='Shows the summary of an engine')

    parser.add_argument(
        '-u',
        '--url',
        help='A custom link to use as base url for search e.g google.de')

    parser.add_argument(
        '-p',
        '--page',
        type=int,
        help='Page of the result to return details for (default: 1)',
        default=1)

    parser.add_argument(
        '-t', '--type',
        help='Type of detail to return i.e full, link, desciptions or title (default: full)',
        default="full")

    parser.add_argument(
        '-cc', '--clear-cache',
        action='store_true',
        help='Clear cache of engine before searching')

    parser.add_argument(
        '-r',
        '--rank',
        type=int,
        help='ID of Detail to return e.g 5 (default: 0)')

    parser.add_argument(
        '--proxy',
        required=False,
        help='Proxy address to make use of')

    parser.add_argument(
        '--proxy-user',
        required='--proxy' in sys.argv,
        help='Proxy user to make use of')

    parser.add_argument(
        '--proxy-password',
        required='--proxy' in sys.argv,
        help='Proxy password to make use of')

    parser.add_argument(
        'query', type=str, nargs='?',
        help='Query string to search engine for')

    return parser


def runner():
    parser = create_parser()
    args = parser.parse_args(sys.argv[1:])
    main(args)


if __name__ == '__main__':
    runner()
