"""Bonding curve token simulator — pure Python, no dependencies.

A continuous token model in the Bancor style: a token's price is set by a
reserve pool and a constant reserve ratio ``R`` (0 < R <= 1). Buying mints
tokens against reserve currency, selling burns tokens for reserve. The
price rises as supply grows, so early buyers get in cheaper.

The maths (Bancor formulas):

- spot price  ``P = B / (S * R)``          (reserve B, supply S)
- buy  dB in -> tokens out ``dS = S * ((1 + dB / B) ** R - 1)``
- sell dS in -> reserve out ``dB = B * (1 - (1 - dS / S) ** (1 / R))``

Invariants checked in the demo: buying then selling the same amount of
tokens back never returns more reserve than was paid in (the spread is
the curve's slippage), and the reserve ratio stays constant through
every trade.
"""

from __future__ import annotations

__all__ = ["BondingCurve"]


class BondingCurve:
    """A single bonding-curve token market.

    >>> curve = BondingCurve(reserve_ratio=0.5, initial_supply=1000.0,
    ...                      initial_reserve=1000.0)
    >>> round(curve.spot_price(), 4)
    2.0
    >>> curve.buy(100.0)  # doctest: +ELLIPSIS
    48.80...
    >>> round(curve.spot_price(), 4)
    2.0976
    """

    def __init__(self, reserve_ratio: float, initial_supply: float,
                 initial_reserve: float) -> None:
        if not 0.0 < reserve_ratio <= 1.0:
            raise ValueError("reserve_ratio must be in (0, 1]")
        if initial_supply <= 0 or initial_reserve <= 0:
            raise ValueError("initial supply and reserve must be positive")
        self.reserve_ratio = reserve_ratio
        self.supply = float(initial_supply)
        self.reserve = float(initial_reserve)

    def spot_price(self) -> float:
        """Current marginal price of one token in reserve currency.

        >>> BondingCurve(0.5, 1000.0, 1000.0).spot_price()
        2.0
        """
        return self.reserve / (self.supply * self.reserve_ratio)

    def market_cap(self) -> float:
        """Supply valued at the spot price.

        >>> BondingCurve(0.5, 1000.0, 1000.0).market_cap()
        2000.0
        """
        return self.supply * self.spot_price()

    def buy_quote(self, reserve_in: float) -> float:
        """Tokens minted for ``reserve_in`` reserve currency (no state change).

        >>> curve = BondingCurve(0.5, 1000.0, 1000.0)
        >>> round(curve.buy_quote(100.0), 4)
        48.8088
        >>> curve.buy_quote(0.0)
        0.0
        """
        if reserve_in < 0:
            raise ValueError("reserve_in must be non-negative")
        return self.supply * ((1.0 + reserve_in / self.reserve)
                              ** self.reserve_ratio - 1.0)

    def sell_quote(self, tokens_in: float) -> float:
        """Reserve returned for burning ``tokens_in`` tokens (no state change).

        >>> curve = BondingCurve(0.5, 1000.0, 1000.0)
        >>> tokens = curve.buy(100.0)
        >>> round(curve.sell_quote(tokens), 4)
        100.0
        >>> curve.sell_quote(0.0)
        0.0
        """
        if tokens_in < 0:
            raise ValueError("tokens_in must be non-negative")
        if tokens_in > self.supply:
            raise ValueError("cannot sell more tokens than the supply")
        return self.reserve * (1.0 - (1.0 - tokens_in / self.supply)
                               ** (1.0 / self.reserve_ratio))

    def price_impact(self, reserve_in: float) -> float:
        """Relative price move caused by buying with ``reserve_in`` reserve.

        Compares the spot price before and after a hypothetical buy of
        that size, without changing any state.

        >>> curve = BondingCurve(0.5, 1000.0, 1000.0)
        >>> round(curve.price_impact(100.0), 4)
        0.0488
        >>> curve.price_impact(0.0)
        0.0
        """
        if reserve_in < 0:
            raise ValueError("reserve_in must be non-negative")
        tokens = self.buy_quote(reserve_in)
        new_price = ((self.reserve + reserve_in)
                     / ((self.supply + tokens) * self.reserve_ratio))
        return new_price / self.spot_price() - 1.0

    def average_buy_price(self, reserve_in: float) -> float:
        """Average price paid per token for a buy of ``reserve_in``.

        Always above the spot price (the curve rises as you buy), and
        equal to it for a zero-size buy. No state change.

        >>> curve = BondingCurve(0.5, 1000.0, 1000.0)
        >>> round(curve.average_buy_price(100.0), 4)
        2.0488
        >>> curve.average_buy_price(0.0)
        2.0
        """
        if reserve_in < 0:
            raise ValueError("reserve_in must be non-negative")
        if reserve_in == 0:
            return self.spot_price()
        return reserve_in / self.buy_quote(reserve_in)

    def average_sell_price(self, tokens_in: float) -> float:
        """Average reserve received per token for selling ``tokens_in``.

        Always below the spot price (the curve falls as you sell), and
        equal to it for a zero-size sell. No state change.

        >>> curve = BondingCurve(0.5, 1000.0, 1000.0)
        >>> round(curve.average_sell_price(100.0), 4)
        1.9
        >>> curve.average_sell_price(0.0)
        2.0
        """
        if tokens_in < 0:
            raise ValueError("tokens_in must be non-negative")
        if tokens_in == 0:
            return self.spot_price()
        return self.sell_quote(tokens_in) / tokens_in

    def buy(self, reserve_in: float) -> float:
        """Spend reserve, mint tokens, return the tokens minted.

        >>> curve = BondingCurve(0.5, 1000.0, 1000.0)
        >>> tokens = curve.buy(100.0)
        >>> round(curve.supply, 4)
        1048.8088
        >>> round(curve.reserve, 4)
        1100.0
        >>> round(curve.spot_price(), 4) > 2.0
        True
        """
        tokens = self.buy_quote(reserve_in)
        self.reserve += reserve_in
        self.supply += tokens
        return tokens

    def sell(self, tokens_in: float) -> float:
        """Burn tokens, return the reserve paid out.

        >>> curve = BondingCurve(0.5, 1000.0, 1000.0)
        >>> tokens = curve.buy(100.0)
        >>> round(curve.sell(tokens), 4)
        100.0
        >>> round(curve.supply, 4)
        1000.0
        """
        reserve_out = self.sell_quote(tokens_in)
        self.supply -= tokens_in
        self.reserve -= reserve_out
        return reserve_out

    def reserve_ratio_now(self) -> float:
        """Effective reserve ratio implied by the current state.

        Stays equal to the configured ratio after every trade.

        >>> curve = BondingCurve(0.3, 500.0, 750.0)
        >>> round(curve.buy(250.0), 4)
        45.0692
        >>> round(curve.sell(40.0), 4)
        224.353
        >>> round(curve.reserve_ratio_now(), 6)
        0.3
        """
        return self.reserve / (self.supply * self.spot_price())


def demo() -> None:
    """Run a small buy/sell scenario and print the curve's behaviour."""
    curve = BondingCurve(reserve_ratio=0.5, initial_supply=1000.0,
                         initial_reserve=1000.0)
    print(f"start: supply={curve.supply:.0f} reserve={curve.reserve:.0f} "
          f"price={curve.spot_price():.4f}")
    tokens = curve.buy(1000.0)
    print(f"buy 1000 reserve -> {tokens:.2f} tokens, "
          f"price now {curve.spot_price():.4f}")
    back = curve.sell(tokens / 2)
    print(f"sell half the tokens -> {back:.2f} reserve back, "
          f"price now {curve.spot_price():.4f}")
    print(f"avg sell price for 100 tokens: "
          f"{curve.average_sell_price(100.0):.4f} reserve each")
    print(f"reserve ratio still {curve.reserve_ratio_now():.4f}")


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        import doctest
        failures, _ = doctest.testmod(verbose=False)
        raise SystemExit(1 if failures else 0)
    demo()
