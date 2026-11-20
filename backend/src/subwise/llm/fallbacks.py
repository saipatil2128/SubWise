"""Deterministic fallbacks used whenever the LLM is down, slow or wrong (blueprint J.2)."""

from __future__ import annotations

import re
from typing import Any

from subwise.domain.enums import Category, NextAction, OptimizeMode
from subwise.research.registry import PROVIDERS

_BUDGET_RE = re.compile(
    r"(?:budget|spend|under|within|max(?:imum)?|upto|up to|limit)[^₹\d]{0,25}"
    r"(?:₹|rs\.?|inr)?\s?(\d{2,3}(?:,\d{3})*|\d{2,6})",
    re.I,
)
_AMOUNT_RE = re.compile(r"(?:₹|rs\.?\s?|inr\s?)(\d{1,3}(?:,\d{2,3})*|\d+)", re.I)

KEYWORDS: dict[str, tuple[str, ...]] = {
    "movies": ("movie", "film", "cinema"),
    "tv_series": ("series", "shows", "tv show", "web series"),
    "live_sports": ("cricket", "sport", "ipl", "match"),
    "music_streaming": ("music", "song", "listen", "playlist", "podcast"),
    "ad_free_video": ("no ads", "ad-free", "ad free", "without ads"),
    "ad_free_music": ("no ads", "ad-free", "ad free", "without ads"),
    "uhd_4k": ("4k", "ultra hd", "uhd"),
    "full_hd": ("hd", "1080"),
    "tv_screen": (" tv", "television", "big screen", "smart tv"),
    "multi_screen": ("family", "two screens", "multiple screens", "share"),
    "offline_download": ("download", "offline", "travel"),
    "offline_music": ("offline", "download"),
    "lossless_audio": ("lossless", "hi-res", "audiophile"),
    "multi_account": ("family", "duo", "share with"),
}
VIDEO_FEATURES = {
    "movies",
    "tv_series",
    "live_sports",
    "ad_free_video",
    "uhd_4k",
    "full_hd",
    "tv_screen",
    "multi_screen",
    "offline_download",
}
MUSIC_FEATURES = {"music_streaming", "ad_free_music", "offline_music", "lossless_audio"}


def stated_budget_rupees(message: str) -> int | None:
    m = _BUDGET_RE.search(message) or _AMOUNT_RE.search(message)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def amount_stated(message: str, rupees: int) -> bool:
    """True if ``rupees`` literally appears in the message (guards LLM-invented budgets)."""
    digits = {int(x.replace(",", "")) for x in re.findall(r"\d{1,3}(?:,\d{2,3})+|\d+", message)}
    return rupees in digits


def parse_intent_rules(message: str) -> dict[str, Any]:
    """Keyword parser returning the same shape the LLM returns (``IntentLLM``)."""
    text = f" {message.lower()} "
    must: list[str] = []
    for code, words in KEYWORDS.items():
        if code in (
            "ad_free_video",
            "ad_free_music",
            "full_hd",
            "uhd_4k",
            "lossless_audio",
            "offline_music",
            "multi_account",
            "multi_screen",
        ):
            continue
        if any(w in text for w in words):
            must.append(code)
    nice = [
        c
        for c in (
            "ad_free_video",
            "ad_free_music",
            "uhd_4k",
            "lossless_audio",
            "offline_music",
            "multi_screen",
        )
        if any(w in text for w in KEYWORDS[c])
    ]
    cats: list[str] = []
    if VIDEO_FEATURES & set(must + nice) or any(
        p.name.lower() in text and p.category is Category.VIDEO for p in PROVIDERS
    ):
        cats.append("video")
    if MUSIC_FEATURES & set(must + nice) or any(
        p.name.lower() in text and p.category is Category.MUSIC for p in PROVIDERS
    ):
        cats.append("music")
    keep = [
        p.id
        for p in PROVIDERS
        if re.search(
            rf"(keep|need|must have|can't lose|cannot lose|without losing)[^.]{{0,40}}"
            rf"{re.escape(p.name.lower())}",
            text,
        )
    ]
    drop = [
        p.id
        for p in PROVIDERS
        if re.search(
            rf"(cancel|drop|stop|get rid of|remove|don't want|do not want)[^.]{{0,30}}"
            rf"{re.escape(p.name.lower())}",
            text,
        )
    ]
    mode = (
        OptimizeMode.SAVINGS
        if re.search(r"cheap|save|reduce|cut|lower|less", text)
        else (OptimizeMode.BALANCED)
    )
    budget = stated_budget_rupees(message)
    period = "annual" if re.search(r"per year|a year|yearly|annual", text) and budget else "monthly"
    return {
        "categories": cats or ["video", "music"],
        "budget_rupees": budget,
        "budget_period": period,
        "must_have": sorted(set(must)),
        "nice_to_have": nice,
        "keep_providers": keep,
        "drop_providers": drop,
        "mode": mode.value,
    }


def decide_rules(
    *, all_must_haves_usable: bool, failed_providers: int, research_round: int, max_rounds: int
) -> NextAction:
    """Blueprint D.1 rule table."""
    if all_must_haves_usable:
        return NextAction.PROCEED if failed_providers == 0 else NextAction.PROCEED_WITH_GAPS
    if research_round < max_rounds and failed_providers:
        return NextAction.RESEARCH_MORE
    return NextAction.PROCEED_WITH_GAPS
