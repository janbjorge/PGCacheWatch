import argparse
import datetime

import asyncpg

from pgnotefi import env, models, queries, utils


def cliparser() -> argparse.Namespace:
    trigger_fn_settings = argparse.ArgumentParser(add_help=False)
    trigger_fn_settings.add_argument(
        "--channel-name",
        default="ch_pgnotefi_table_change",
        help=(
            "The PGNotify channel that will be used by pgnotefi to listen "
            "for changes on tables, this should be uniq to pgnotefi clients."
        ),
    )
    trigger_fn_settings.add_argument(
        "--function-name",
        default="fn_pgnotefi_table_change",
        help=(
            "The name of postgres 'helper function' that emits the on change evnets. "
            "This must be uniq."
        ),
    )
    trigger_fn_settings.add_argument(
        "--trigger-name-prefix",
        default="tg_pgnotefi_table_change_",
        help="All triggers installed on tables will start with this prefix.",
    )

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dsn", default=str(env.parsed.dsn))
    subparsers = parser.add_subparsers(dest="command", required=True)

    mock = subparsers.add_parser(
        "mock",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[trigger_fn_settings],
    )
    install = subparsers.add_parser(
        "install",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[trigger_fn_settings],
    )
    subparsers.add_parser(
        "uninstall",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[trigger_fn_settings],
    )

    install.add_argument("tables", nargs=argparse.ONE_OR_MORE)
    install.add_argument(
        "--commit",
        action="store_true",
        help="Commit function and triggers to db.",
    )

    mock.add_argument(
        "operation",
        choices=["insert", "update", "delete"],
        help="Operation to be used on the mocked event.",
    )
    mock.add_argument(
        "table",
        help="Name of the table to mock a change on.",
    )
    return parser.parse_args()


async def main() -> None:
    parsed = cliparser()

    if parsed.command == "mock":
        await utils.emitevent(
            event=models.Event(
                channel=parsed.channel_name,
                operation=parsed.operation,
                table=parsed.table,
                sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
            ),
            conn=await asyncpg.connect(dsn=parsed.dsn),
        )

    if parsed.command == "install":
        install = [
            queries.notify_function(
                channel_name=parsed.channel_name,
                function_name=parsed.function_name,
            )
        ]

        for table in parsed.tables:
            install.append(
                queries.after_change_trigger(
                    table_name=table,
                    channel_name=parsed.channel_name,
                    function_name=parsed.function_name,
                    trigger_name_prefix=parsed.trigger_name_prefix,
                )
            )

        combined = "\n".join(install)
        print(combined, flush=True)
        if parsed.commit:
            await (await asyncpg.connect(dsn=parsed.dsn)).execute(combined)

    if parsed.command == "uninstall":
        trigger_names = await (await asyncpg.connect(dsn=parsed.dsn)).fetch(
            queries.fetch_trigger_names(parsed.trigger_name_prefix),
        )
        combined = "\n\n".join(
            (
                "\n".join(
                    queries.drop_trigger(t["trigger_name"], t["table"])
                    for t in trigger_names
                ),
                queries.drop_function(parsed.function_name),
            )
        )
        print(combined, flush=True)
        await (await asyncpg.connect(dsn=parsed.dsn)).execute(combined)
