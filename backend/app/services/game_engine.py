from random import randint


def roll_d6() -> int:
    """Server-side dice roll."""
    return randint(1, 6)
