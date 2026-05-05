"""
Configuration for the politics dashboard.

Loads a YAML file (path from CONFIG_PATH env, default /app/config.yaml) and
overlays env vars for secrets. The YAML defines feeds, categories, and LLM
provider; env vars carry credentials.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: Literal["openai_compatible", "anthropic"] = "openai_compatible"
    base_url: str = "http://localhost:11434/v1"
    model: str = "llama3.1:8b"
    api_key_env: str = "LLM_API_KEY"
    request_timeout: float = 180.0


class CategoryConfig(BaseModel):
    label: str
    urls: list[str] = Field(default_factory=list)
    freshrss_label: str | None = None  # if using freshrss source


class FreshRSSConfig(BaseModel):
    url: str
    username: str
    password_env: str = "FRESHRSS_API_PASSWORD"


class FeedsConfig(BaseModel):
    source: Literal["rss", "freshrss"] = "rss"
    lookback_hours: int = 96
    max_per_category: int = 75
    categories: dict[str, CategoryConfig] = Field(default_factory=dict)
    freshrss: FreshRSSConfig | None = None


class TwitterCategoryConfig(BaseModel):
    label: str
    handles: list[str] = Field(default_factory=list)


class TwitterConfig(BaseModel):
    enabled: bool = False
    nitter_url: str = ""
    handles_env_prefix: str = ""  # if set, read handles from env: {PREFIX}_{KEY}
    categories: dict[str, TwitterCategoryConfig] = Field(default_factory=dict)


class RefreshConfig(BaseModel):
    articles_seconds: int = 900
    digest_seconds: int = 3600
    twitter_seconds: int = 10800


class Config(BaseModel):
    title: str = "Politics & Government"
    llm: LLMConfig = Field(default_factory=LLMConfig)
    feeds: FeedsConfig = Field(default_factory=FeedsConfig)
    twitter: TwitterConfig = Field(default_factory=TwitterConfig)
    refresh: RefreshConfig = Field(default_factory=RefreshConfig)


def load_config() -> Config:
    path = Path(os.environ.get("CONFIG_PATH", "/app/config.yaml"))
    if path.exists():
        data = yaml.safe_load(path.read_text()) or {}
        cfg = Config(**data)
    else:
        cfg = Config()
    _apply_env_overrides(cfg)
    return cfg


def _apply_env_overrides(cfg: Config) -> None:
    """Allow env vars to override Twitter handle lists per category.

    If twitter.handles_env_prefix is set, for each category we look up
    ${PREFIX}_${UPPER_CATEGORY_KEY} (e.g. X_POLITICS) and, if present,
    replace the YAML-declared handles with the comma-separated env value.
    Useful when handle lists live in a Kubernetes Secret.
    """
    prefix = cfg.twitter.handles_env_prefix
    if not prefix:
        return
    for key, cat in cfg.twitter.categories.items():
        env_name = f"{prefix}_{key.upper()}"
        val = os.environ.get(env_name)
        if val:
            cat.handles = [h.strip() for h in val.split(",") if h.strip()]


config = load_config()
