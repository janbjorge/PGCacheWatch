import argparse
import sys

import asyncpg

from pgcachewatch import models, queries


def cliparser() -> argparse.Namespace:
    common_arguments = argparse.ArgumentParser(
        add_help=False,
        prog="pgcachewatch",
    )
    common_arguments.add_argument(
        "--channel-name",
        default=models.DEFAULT_PG_CHANNE,
        help=(
            "The PGNotify channel that will be used by pgcachewatch to listen "
            "for changes on tables, this should be uniq to pgcachewatch clients."
        ),
    )
    common_arguments.add_argument(
        "--function-name",
        default="fn_pgcachewatch_table_change",
        help=(
            "The prefix of the postgres 'helper function' that emits "
            "the on change evnets."
        ),
    )
    common_arguments.add_argument(
        "--trigger-name",
        default="tg_pgcachewatch_table_change",
        help="All triggers installed on tables will start with this prefix.",
    )
    common_arguments.add_argument(
        "--commit",
        action="store_true",
        help="Commit changes to database.",
    )

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog="pgcachewatch",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser(
        "install",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[common_arguments],
    )
    install.add_argument("tables", nargs=argparse.ONE_OR_MORE)

    subparsers.add_parser(
        "uninstall",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[common_arguments],
    )

    return parser.parse_args()


async def main() -> None:
    parsed = cliparser()

    pg_fn_name = f"{parsed.function_name}_{parsed.channel_name}"
    pg_tg_name = f"{parsed.trigger_name}_{parsed.channel_name}"

    match parsed.command:
        case "install":
            install = "\n".join(
                [
                    queries.create_notify_function(
                        channel_name=parsed.channel_name,
                        function_name=pg_fn_name,
                    )
                ]
                + [
                    queries.create_after_change_trigger(
                        trigger_name=pg_tg_name,
                        table_name=table,
                        function_name=pg_fn_name,
                    )
                    for table in parsed.tables
                ]
            )

            print(install, flush=True)

            if parsed.commit:
                await (await asyncpg.connect()).execute(install)
            else:
                print(
                    "::: Use '--commit' to write changes to db. :::",
                    file=sys.stderr,
                )

        case "uninstall":
            trigger_names = await (await asyncpg.connect()).fetch(
                queries.fetch_trigger_names(pg_tg_name),
            )
            combined = "\n".join(
                (
                    "\n".join(
                        queries.drop_trigger(t["trigger_name"], t["table"])
                        for t in trigger_names
                    ),
                    queries.drop_function(pg_fn_name),
                )
            )
            print(combined, flush=True)
            if parsed.commit:
                await (await asyncpg.connect()).execute(combined)
            else:
                print(
                    "::: Use '--commit' to write changes to db. :::",
                    file=sys.stderr,
                )
