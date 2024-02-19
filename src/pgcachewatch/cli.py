import argparse
import sys

import asyncpg

from pgcachewatch import queries


def cliparser() -> argparse.Namespace:
    common_arguments = argparse.ArgumentParser(add_help=False)
    common_arguments.add_argument(
        "--channel-name",
        default="ch_pgcachewatch_table_change",
        help=(
            "The PGNotify channel that will be used by pgcachewatch to listen "
            "for changes on tables, this should be uniq to pgcachewatch clients."
        ),
    )
    common_arguments.add_argument(
        "--function-name",
        default="fn_pgcachewatch_table_change",
        help=(
            "The name of postgres 'helper function' that emits the on change evnets. "
            "This must be uniq."
        ),
    )
    common_arguments.add_argument(
        "--trigger-name",
        default="tg_pgcachewatch_table_change_",
        help="All triggers installed on tables will start with this prefix.",
    )
    common_arguments.add_argument(
        "--commit",
        action="store_true",
        help="Commit changes to DB.",
    )

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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

    match parsed.command:
        case "install":
            install = [
                queries.create_notify_function(
                    channel_name=parsed.channel_name,
                    function_name=parsed.function_name,
                )
            ]

            for table in parsed.tables:
                install.append(
                    queries.create_after_change_trigger(
                        table_name=table,
                        channel_name=parsed.channel_name,
                        function_name=parsed.function_name,
                        trigger_name_prefix=parsed.trigger_name,
                    )
                )

            combined = "\n".join(install)
            print(combined, flush=True)
            if parsed.commit:
                await (await asyncpg.connect()).execute(combined)
            else:
                print(
                    "::: Use '--commit' to write changes to db. :::",
                    file=sys.stderr,
                )

        case "uninstall":
            trigger_names = await (await asyncpg.connect()).fetch(
                queries.fetch_trigger_names(parsed.trigger_name),
            )
            combined = "\n".join(
                (
                    "\n".join(
                        queries.drop_trigger(t["trigger_name"], t["table"])
                        for t in trigger_names
                    ),
                    queries.drop_function(parsed.function_name),
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
