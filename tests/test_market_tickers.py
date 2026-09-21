from market_data import MARKETS


def _ticker(country, name):
    return next(ticker for market_name, ticker, _ in MARKETS[country] if market_name == name)


def test_problematic_tickers_are_corrected():
    assert _ticker("India", "NIFTY Midcap 100") == "NIFTY_MIDCAP_100.NS"
    assert _ticker("Hong Kong", "Hang Seng Tech") == "HSTECH.HK"
    assert _ticker("Japan", "TOPIX") == "998405.T"
    assert _ticker("Vietnam", "VN-Index") == "^VNINDEX.VN"
    assert _ticker("Thailand", "SET Index") == "SET.BK"


def test_non_yahoo_markets_are_explicitly_handled():
    assert _ticker("Bangladesh", "DSEX") == "DSEX"
    south_africa = next(item for item in MARKETS["South Africa"] if item[0].startswith("Satrix 40"))
    assert south_africa[1] == "STX40.JO"
    assert south_africa[2] == "ETF proxy"


def test_no_known_broken_tickers_remain():
    all_tickers = {ticker for markets in MARKETS.values() for _, ticker, _ in markets}
    assert "^CNXMC" not in all_tickers
    assert "^HSTECH" not in all_tickers
    assert "^TOPX" not in all_tickers
    assert "^VNINDEX" not in all_tickers
    assert "^SET.BK" not in all_tickers
    assert "^JTOPI" not in all_tickers
