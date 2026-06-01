"""Constant-product AMM for binary YES/NO markets."""

K_INITIAL = 100.0 * 100.0  # yes_reserve * no_reserve at launch


def yes_price(yes_reserve: float, no_reserve: float) -> float:
    total = yes_reserve + no_reserve
    if total <= 0:
        return 0.5
    return no_reserve / total


def no_price(yes_reserve: float, no_reserve: float) -> float:
    return 1.0 - yes_price(yes_reserve, no_reserve)


def buy_shares(
    side: str, amount: float, yes_reserve: float, no_reserve: float
) -> tuple[float, float, float, float]:
    """
    Spend `amount` USDC to buy YES or NO shares.
    Returns (shares_received, new_yes_reserve, new_no_reserve, avg_price).
    """
    if amount <= 0:
        raise ValueError("Amount must be positive")

    k = yes_reserve * no_reserve
    if side == "yes":
        new_no = no_reserve + amount
        new_yes = k / new_no
        shares = yes_reserve - new_yes
        avg = amount / shares if shares > 0 else yes_price(yes_reserve, no_reserve)
        return shares, new_yes, new_no, avg

    if side == "no":
        new_yes = yes_reserve + amount
        new_no = k / new_yes
        shares = no_reserve - new_no
        avg = amount / shares if shares > 0 else no_price(yes_reserve, no_reserve)
        return shares, new_yes, new_no, avg

    raise ValueError("side must be 'yes' or 'no'")
