from market_data import MARKETS


def test_problematic_market_mappings_are_updated():
    india = dict((name, ticker) for name, ticker, _ in MARKETS["India"])
    hong_kong = dict((name, ticker) for name, ticker, _ in MARKETS["Hong Kong"])
    japan = dict((name, ticker) for name, ticker, _ in MARKETS["Japan"])
    vietnam = dict((name, ticker) for name, ticker, _ in MARKETS["Vietnam"])
    thailand = dict((name, ticker) for name, ticker, _ in MARKETS["Thailand"])

    assert india["NIFTY Midcap 100"] == "NIFTY_MIDCAP_100.NS"
    assert hong_kong["Hang Seng Tech"] == "HSTECH.HK"
    assert japan["TOPIX"] == "998405.T"
    assert vietnam["VN-Index"] == "^VNINDEX.VN"
    assert thailand["SET Index"] == "SET.BK"


def test_dsex_uses_dse_provider_symbol():
    bangladesh = dict((name, ticker) for name, ticker, _ in MARKETS["Bangladesh"])
    assert bangladesh["DSEX"] == "DSEX"


def test_no_market_mapping_uses_known_bad_symbols():
    all_markets = [item for markets in MARKETS.values() for item in markets]
    tickers = {ticker for _, ticker, _ in all_markets}
    assert "^CNXMC" not in tickers
    assert "^HSTECH" not in tickers
    assert "^VNINDEX" not in tickers
