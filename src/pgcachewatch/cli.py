import argparse
import os
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

    common_arguments.add_argument(
        "--pg-dsn",
        help=(
            "Connection string in the libpq URI format, including host, port, user, "
            "database, password, passfile, and SSL options. Must be properly quoted; "
            "IPv6 addresses must be in brackets. "
            "Example: postgres://user:pass@host:port/database. Defaults to PGDSN "
            "environment variable if set."
        ),
        default=os.environ.get("PGDSN"),
    )

    common_arguments.add_argument(
        "--pg-host",
        help=(
            "Database host address, which can be an IP or domain name. "
            "Defaults to PGHOST environment variable if set."
        ),
        default=os.environ.get("PGHOST"),
    )

    common_arguments.add_argument(
        "--pg-port",
        help=(
            "Port number for the server host Defaults to PGPORT environment variable "
            "or 5432 if not set."
        ),
        default=os.environ.get("PGPORT", "5432"),
    )

    common_arguments.add_argument(
        "--pg-user",
        help=(
            "Database role for authentication. Defaults to PGUSER environment "
            "variable if set."
        ),
        default=os.environ.get("PGUSER"),
    )

    common_arguments.add_argument(
        "--pg-database",
        help=(
            "Name of the database to connect to. Defaults to PGDATABASE environment "
            "variable if set."
        ),
        default=os.environ.get("PGDATABASE"),
    )

    common_arguments.add_argument(
        "--pg-password",
        help=(
            "Password for authentication. Defaults to PGPASSWORD "
            "environment variable if set"
        ),
        default=os.environ.get("PGPASSWORD"),
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

    async with asyncpg.create_pool(
        parsed.pg_dsn,
        database=parsed.pg_database,
        password=parsed.pg_password,
        port=parsed.pg_port,
        user=parsed.pg_user,
        host=parsed.pg_host,
        min_size=0,
        max_size=1,
    ) as pool:
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
                    await pool.execute(install)
                else:
                    print(
                        "::: Use '--commit' to write changes to db. :::",
                        file=sys.stderr,
                    )

            case "uninstall":
                trigger_names = await pool.fetch(
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
                    await pool.execute(combined)
                else:
                    print(
                        "::: Use '--commit' to write changes to db. :::",
                        file=sys.stderr,
                    )
