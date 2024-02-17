import os
import typing

import pydantic


class OsEnv(pydantic.BaseModel):
    dsn: pydantic.PostgresDsn | None = pydantic.Field(default=None, alias="PGDSN")


parsed: typing.Final = OsEnv.model_validate(os.environ)
