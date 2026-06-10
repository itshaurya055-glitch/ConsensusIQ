import yfinance as yf


def get_nifty_close():

    nifty = yf.Ticker("^NSEI")

    data = nifty.history(period="1d")

    return float(data["Close"].iloc[-1])