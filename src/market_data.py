import yfinance as yf


def get_nifty_close():
    try:
        nifty = yf.Ticker("^NSEI")
        if hasattr(nifty, "fast_info") and nifty.fast_info is not None:
            price = nifty.fast_info.last_price
            if price is not None and price > 0:
                return float(price)
    except Exception:
        pass

    try:
        nifty = yf.Ticker("^NSEI")
        data = nifty.history(period="1d")
        if not data.empty and "Close" in data.columns:
            return float(data["Close"].iloc[-1])
    except Exception:
        pass

    return 0.0


# Alias for backward compatibility (used in scripts like test_market.py)
get_nifty_price = get_nifty_close