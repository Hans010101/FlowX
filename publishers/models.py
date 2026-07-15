"""Lightweight publishing data models with no browser dependency."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Article:
    title: str
    content: str
    cover_image: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class PublishResult:
    ok: bool
    platform: str = ""
    account: str = ""
    as_draft: bool = True
    url: str | None = None
    error: str | None = None
