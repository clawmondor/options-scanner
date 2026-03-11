# Options Opportunities Scanner

A Streamlit web app that scans a watchlist of liquid stocks for actionable options trading setups.

url: [options.cmondor.com](https://options.cmondor.com)
## Features

- **Unusual Activity** — Detects options contracts with high volume-to-open-interest ratios, which can signal institutional or insider positioning. Includes put/call ratio for directional bias.
- **IV Expansion** — Identifies stocks where implied volatility is significantly elevated above 20-day historical volatility — ideal conditions for selling premium (credit spreads, iron condors).
- **Credit Spread Setups** — Surfaces defined-risk put and call credit spread opportunities 30–45 days out, with calculated credit, max risk, and risk/reward ratio.
- **Individual Stock Lookup** — Analyze any ticker on demand for all three signal types.

## Watchlist

Default watchlist covers major ETFs and high-liquidity equities:

`SPY, QQQ, IWM, TSLA, NVDA, AMD, AAPL, MSFT, AMZN, META, GOOGL, NFLX, COIN, GME, AMC, PLTR, SOFI, RIVN, LCID, NIO, SPX, NDX, SMH, XLF, XLE, XLV, XLK, ARKK, SOXX, VB`

## Tech Stack

- [Streamlit](https://streamlit.io/) — UI
- [yfinance](https://github.com/ranaroussi/yfinance) — Market data & options chains
- [pandas](https://pandas.pydata.org/) / [numpy](https://numpy.org/) — Data processing
- [Plotly](https://plotly.com/python/) — Charting

## Running Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deployment

Configured for [Railway](https://railway.app/) via `Procfile`:

```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

## CI

GitHub Actions runs a security scan on every push and pull request:

- **Bandit** — static analysis for Python security issues
- **Safety** — dependency vulnerability check against known CVEs

## Disclaimer

This tool is for informational and educational purposes only. It is not financial advice. Always do your own research before making any trading decisions.
