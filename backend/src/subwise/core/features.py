"""Feature vocabulary that OAVOE optimizes over (blueprint E.1 ``feature_definitions``).

The authoritative list is seeded from ``research/catalog_seed/features.yaml`` in M4; this
module only holds the codes that code paths reference directly.
"""

from __future__ import annotations

from typing import Final

from subwise.domain.enums import Category

CORE_FEATURES: Final[dict[str, Category]] = {
    "movies": Category.VIDEO,
    "tv_series": Category.VIDEO,
    "live_cricket": Category.VIDEO,
    "tv_screen": Category.VIDEO,
    "uhd_4k": Category.VIDEO,
    "ad_free_video": Category.VIDEO,
    "offline_download": Category.VIDEO,
    "music_streaming": Category.MUSIC,
    "ad_free_music": Category.MUSIC,
    "offline_music": Category.MUSIC,
}
