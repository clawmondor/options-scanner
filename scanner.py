"""
Options Opportunities Scanner
Finds stocks with unusual options activity, IV expansion, and setup opportunities.
"""

import logging
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

from cache import cached_yfinance


# Popular stocks with liquid options
WATCHLIST = [
    'SPY', 'QQQ', 'IWM', 'TSLA', 'NVDA', 'AMD', 'AAPL', 'MSFT', 'AMZN', 'META',
    'GOOGL', 'NFLX', 'COIN', 'GME', 'AMC', 'PLTR', 'SOFI', 'RIVN', 'LCID', 'NIO',
    'SPX', 'NDX', 'SMH', 'XLF', 'XLE', 'XLV', 'XLK', 'ARKK', 'SOXX', 'VB'
]


@cached_yfinance("stock_info")
def get_stock_info(ticker):
    """Get basic stock info."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            'ticker': ticker,
            'price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
            'volume': info.get('volume', 0),
            'avgVolume': info.get('averageVolume', 0),
            'marketCap': info.get('marketCap', 0),
            'name': info.get('shortName', ticker),
            'sector': info.get('sector', 'Unknown'),
            'change_pct': info.get('regularMarketChangePercent', 0),
        }
    except (KeyError, ValueError, AttributeError, TypeError) as e:
        logger.warning("get_stock_info failed for %s: %s", ticker, e)
        return None


@cached_yfinance("options_chain")
def get_options_chain(ticker):
    """Get options chain data."""
    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options
        if not expirations:
            return None

        nearest_exp = expirations[0]

        calls = stock.option_chain(nearest_exp).calls
        puts = stock.option_chain(nearest_exp).puts

        return {
            'expiration': nearest_exp,
            'calls': calls,
            'puts': puts,
        }
    except (KeyError, ValueError, AttributeError, TypeError) as e:
        logger.warning("get_options_chain failed for %s: %s", ticker, e)
        return None


def calculate_iv_rank(chain_data, lookback_ivs=None):
    """Calculate IV rank (simplified)."""
    if chain_data is None:
        return None

    calls = chain_data['calls']
    puts = chain_data['puts']

    try:
        price = yf.Ticker(chain_data.get('ticker', '')).info.get('currentPrice', 100)
        otm_calls = calls[calls['strike'] > price * 1.02]
        otm_puts = puts[puts['strike'] < price * 0.98]

        if len(otm_calls) > 0:
            atm_iv = otm_calls['impliedVolatility'].median()
        elif len(otm_puts) > 0:
            atm_iv = otm_puts['impliedVolatility'].median()
        else:
            atm_iv = calls['impliedVolatility'].median()

        return atm_iv * 100 if atm_iv else None
    except (KeyError, ValueError, AttributeError, TypeError) as e:
        logger.warning("calculate_iv_rank failed: %s", e)
        return None


def find_unusual_activity(ticker):
    """Find stocks with unusual options activity."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not stock.options:
            return None

        chain = stock.option_chain(stock.options[0])
        calls = chain.calls
        puts = chain.puts

        calls['vol_oi_ratio'] = calls['volume'] / (calls['openInterest'] + 1)
        puts['vol_oi_ratio'] = puts['volume'] / (puts['openInterest'] + 1)

        high_vol_calls = calls[calls['vol_oi_ratio'] > 2].head(3)
        high_vol_puts = puts[puts['vol_oi_ratio'] > 2].head(3)

        if len(high_vol_calls) > 0 or len(high_vol_puts) > 0:
            return {
                'ticker': ticker,
                'price': info.get('currentPrice', 0),
                'change_pct': info.get('regularMarketChangePercent', 0),
                'unusual_calls': len(high_vol_calls),
                'unusual_puts': len(high_vol_puts),
                'total_call_volume': calls['volume'].sum(),
                'total_put_volume': puts['volume'].sum(),
                'put_call_ratio': puts['volume'].sum() / (calls['volume'].sum() + 1),
            }
    except (KeyError, ValueError, AttributeError, TypeError) as e:
        logger.warning("find_unusual_activity failed for %s: %s", ticker, e)
    return None


def find_iv_expansion(ticker):
    """Find stocks with high IV relative to history."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        hist = stock.history(period="3mo")
        if len(hist) < 30:
            return None

        returns = hist['Close'].pct_change().dropna()
        hv20 = returns.rolling(20).std().iloc[-1] * np.sqrt(252) * 100

        if not stock.options:
            return None

        chain = stock.option_chain(stock.options[0])
        calls = chain.calls

        price = info.get('currentPrice', 100)
        atm_call = calls[(calls['strike'] - price).abs() < price * 0.02]

        if len(atm_call) > 0:
            iv = atm_call['impliedVolatility'].iloc[0] * 100
            iv_rank = (iv - hv20) / (hv20 + 1) * 100 if hv20 else 0

            if iv_rank > 30:
                return {
                    'ticker': ticker,
                    'price': price,
                    'iv': iv,
                    'hv20': hv20,
                    'iv_premium': iv_rank,
                    'change_pct': info.get('regularMarketChangePercent', 0),
                }
    except (KeyError, ValueError, AttributeError, TypeError) as e:
        logger.warning("find_iv_expansion failed for %s: %s", ticker, e)
    return None


def find_credit_spread_setup(ticker):
    """Find credit spread setup opportunities."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get('currentPrice', 0)

        if not stock.options or price == 0:
            return None

        valid_exps = [e for e in stock.options if 25 <= (pd.Timestamp(e) - pd.Timestamp.now()).days <= 45]
        if not valid_exps:
            return None

        exp = valid_exps[0]
        chain = stock.option_chain(exp)
        calls = chain.calls
        puts = chain.puts

        support_strikes = puts[puts['strike'] < price * 0.95].sort_values('strike', ascending=False)
        resistance_strikes = calls[calls['strike'] > price * 1.05].sort_values('strike')

        if len(support_strikes) > 0 and len(resistance_strikes) > 0:
            short_put = support_strikes.iloc[0]
            long_put = support_strikes.iloc[min(1, len(support_strikes)-1)]

            short_call = resistance_strikes.iloc[0]
            long_call = resistance_strikes.iloc[min(1, len(resistance_strikes)-1)]

            put_credit = short_put['bid'] - long_put['ask']
            call_credit = short_call['bid'] - long_call['ask']

            put_width = abs(long_put['strike'] - short_put['strike'])
            call_width = abs(short_call['strike'] - long_call['strike'])

            put_risk = put_width - put_credit if put_credit > 0 else None
            call_risk = call_width - call_credit if call_credit > 0 else None

            return {
                'ticker': ticker,
                'price': price,
                'expiration': exp,
                'put_credit': put_credit,
                'put_risk': put_risk,
                'put_risk_reward': (put_risk / put_credit) if (put_risk is not None and put_credit > 0) else None,
                'call_credit': call_credit,
                'call_risk': call_risk,
                'call_risk_reward': (call_risk / call_credit) if (call_risk is not None and call_credit > 0) else None,
            }
    except (KeyError, ValueError, AttributeError, TypeError) as e:
        logger.warning("find_credit_spread_setup failed for %s: %s", ticker, e)
    return None


def scan_watchlist(tickers=None):
    """Scan entire watchlist for opportunities."""
    if tickers is None:
        tickers = WATCHLIST

    results = {
        'unusual_activity': [],
        'iv_expansion': [],
        'credit_spreads': [],
    }

    for ticker in tickers:
        ua = find_unusual_activity(ticker)
        if ua:
            results['unusual_activity'].append(ua)

        iv = find_iv_expansion(ticker)
        if iv:
            results['iv_expansion'].append(iv)

        cs = find_credit_spread_setup(ticker)
        if cs and cs.get('put_credit', 0) > 0.30:
            results['credit_spreads'].append(cs)

    return results


if __name__ == "__main__":
    print("Testing options scanner...")
    results = scan_watchlist(['SPY', 'QQQ', 'TSLA', 'NVDA'])
    print(results)
