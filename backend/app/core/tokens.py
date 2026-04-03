from __future__ import annotations

import random

TOKEN_ASSETS = [
    "token-01.png",
    "token-02.png",
    "token-03.png",
    "token-04.png",
]

DEFAULT_TOKEN_ASSET = TOKEN_ASSETS[0]


def pick_random_token_asset() -> str:
    return random.choice(TOKEN_ASSETS)


def normalize_token_asset(value: str | None) -> str:
    if value in TOKEN_ASSETS:
        return value
    return DEFAULT_TOKEN_ASSET
