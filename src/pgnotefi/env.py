import os
import typing

from pgnotefi import models

parsed: typing.Final = models.OsEnv.model_validate(os.environ)
