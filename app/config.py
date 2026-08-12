import os
from pathlib import Path

from pydantic import BaseModel, PostgresDsn


def load_env_file(env_path: str = ".env") -> None:
    path = Path(env_path)
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_file()


class Settings(BaseModel):
    database_url: str


settings = Settings(database_url=os.environ["DATABASE_URL"])
