import asyncio
import contextlib
import signal

from pgnotefi import cli

if __name__ == "__main__":
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(cli.main())
