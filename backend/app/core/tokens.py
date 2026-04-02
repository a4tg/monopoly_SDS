from __future__ import annotations

import random

TOKEN_ASSETS = [
    "token-01.png",
    "token-02.png",
    "token-03.png",
    "token-04.png",
    "token-05.png",
    "token-06.png",
    "token-07.png",
    "token-08.png",
]

DEFAULT_TOKEN_ASSET = TOKEN_ASSETS[0]


def pick_random_token_asset() -> str:
    return random.choice(TOKEN_ASSETS)
