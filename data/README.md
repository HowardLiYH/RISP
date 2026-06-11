# Data

Bundled minimal real-data inputs so the repository is self-contained:

- `bybit/*_1D.csv` — daily OHLCV for 5 USDT perpetual pairs (BTC, ETH, SOL,
  XRP, DOGE), collected from the public Bybit API (2021–2025). Used by the
  E0 structure diagnostic and the E1s regime-stitched experiment.
- `commodities/fred_prices.csv` — daily commodity prices (WTI oil, copper,
  natural gas) from FRED (US Federal Reserve Economic Data, public domain).

Provenance and collection scripts: see the GAUSE companion repository
(https://github.com/HowardLiYH/GAUSE), whose `data/` directory these files
are a subset of. All sources are public; no proprietary data is included.
