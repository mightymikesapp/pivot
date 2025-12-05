"""Lightweight settings loader to avoid external dependency on pydantic-settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from pydantic import AliasChoices, BaseModel, ConfigDict

SettingsConfigDict = dict[str, Any]


class BaseSettings(BaseModel):  # type: ignore[misc]
    """Simplified settings base class with environment loading support."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    def __init__(self, **data: Any):
        merged_data = self._load_environment()
        merged_data.update(data)
        super().__init__(**merged_data)

    @classmethod
    def _load_environment(cls) -> dict[str, Any]:
        config: SettingsConfigDict = getattr(cls, "model_config", {}) or {}
        env_file = config.get("env_file")
        env_file_encoding = config.get("env_file_encoding")
        if env_file:
            cls._load_env_files(env_file, env_file_encoding)

        case_sensitive = bool(config.get("case_sensitive", False))
        environ = cls._normalized_environ(case_sensitive)

        env_data: dict[str, Any] = {}
        for field_name, field_info in cls.model_fields.items():
            for env_key in cls._candidate_env_keys(field_name, field_info):
                lookup_key = env_key if case_sensitive else env_key.lower()
                if lookup_key in environ:
                    env_data[field_name] = environ[lookup_key]
                    break
        return env_data

    @staticmethod
    def _normalized_environ(case_sensitive: bool) -> dict[str, str]:
        if case_sensitive:
            return dict(os.environ)
        return {key.lower(): value for key, value in os.environ.items()}

    @classmethod
    def _candidate_env_keys(cls, field_name: str, field_info: Any) -> Iterable[str]:
        validation_alias = getattr(field_info, "validation_alias", None)
        if isinstance(validation_alias, AliasChoices):
            for choice in validation_alias.choices:
                yield cls._ensure_str(choice)
        elif validation_alias is not None:
            yield cls._ensure_str(validation_alias)
        else:
            yield field_name

    @staticmethod
    def _ensure_str(value: Any) -> str:
        return str(value)

    @classmethod
    def _load_env_files(cls, env_file: Any, encoding: str | None) -> None:
        if isinstance(env_file, (list, tuple)):
            for file_path in env_file:
                load_dotenv(dotenv_path=Path(file_path), encoding=encoding, override=False)
        else:
            load_dotenv(dotenv_path=Path(env_file), encoding=encoding, override=False)
