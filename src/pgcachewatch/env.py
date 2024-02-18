import os
import typing

from pgcachewatch import models

parsed: typing.Final = models.OsEnv.model_validate(os.environ)
