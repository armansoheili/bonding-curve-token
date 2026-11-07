# bonding-curve-token

A bonding curve token simulator in pure Python — no dependencies.

A continuous token model in the Bancor style: a token's price is set by a
reserve pool and a constant **reserve ratio** `R` (0 < R ≤ 1). Buying mints
tokens against reserve currency; selling burns tokens for reserve. The
price rises as supply grows, so early buyers get in cheaper.

## The maths (Bancor formulas)

- Spot price: `P = B / (S * R)` (reserve `B`, supply `S`)
- Buy `dB` reserve in → tokens out: `dS = S * ((1 + dB / B) ** R - 1)`
- Sell `dS` tokens in → reserve out: `dB = B * (1 - (1 - dS / S) ** (1 / R))`

The reserve ratio stays constant through every trade, and buying then
selling the same tokens back never returns more reserve than was paid in —
the difference is the curve's slippage.

## Usage

```python
from bonding_curve import BondingCurve

curve = BondingCurve(reserve_ratio=0.5, initial_supply=1000.0,
                     initial_reserve=1000.0)
print(curve.spot_price())          # 2.0
tokens = curve.buy(100.0)         # ~48.81 tokens minted
print(curve.spot_price())          # ~2.10 — price rose with supply
print(curve.sell(tokens))          # ~100.0 reserve back
```

## Run

```bash
python bonding_curve.py            # demo scenario
python bonding_curve.py --test     # doctests
```

## API

| Method | Description |
| --- | --- |
| `BondingCurve(reserve_ratio, initial_supply, initial_reserve)` | Create a market |
| `spot_price()` | Marginal price of one token |
| `market_cap()` | Supply valued at the spot price |
| `buy_quote(reserve_in)` / `sell_quote(tokens_in)` | Quote without changing state |
| `buy(reserve_in)` | Spend reserve, mint tokens |
| `sell(tokens_in)` | Burn tokens, receive reserve |
| `reserve_ratio_now()` | Effective reserve ratio (invariant) |
