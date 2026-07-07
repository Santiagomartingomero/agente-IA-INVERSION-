"""
Obtiene precios actuales de las posiciones de Capa 2 (acciones) vía Yahoo Finance
(endpoint público, sin API key), y precio de BTC vía CoinGecko (gratis, sin API key).
"""

import requests

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AgenteCartera/1.0)"}

TICKERS_CAPA_2 = ["CIFR", "LEU", "OKLO", "CRDO", "IREN"]


def fetch_stock_prices(tickers=None):
    """Devuelve dict {ticker: {precio, variacion_pct, variacion_abs}} para una lista de tickers."""
    if tickers is None:
        tickers = TICKERS_CAPA_2

    result = {}
    for ticker in tickers:
        url = YAHOO_CHART_URL.format(ticker=ticker)
        resp = requests.get(
            url, params={"interval": "1d", "range": "1d"}, headers=YAHOO_HEADERS, timeout=15
        )
        resp.raise_for_status()
        meta = resp.json()["chart"]["result"][0]["meta"]

        precio = meta.get("regularMarketPrice")
        cierre_anterior = meta.get("previousClose") or meta.get("chartPreviousClose")
        variacion_abs = None
        variacion_pct = None
        if precio is not None and cierre_anterior:
            variacion_abs = round(precio - cierre_anterior, 2)
            variacion_pct = round((precio / cierre_anterior - 1) * 100, 2)

        result[ticker] = {
            "precio": precio,
            "variacion_pct": variacion_pct,
            "variacion_abs": variacion_abs,
            "nombre": meta.get("symbol"),
        }
    return result


def fetch_btc_price_eur():
    """Precio actual de BTC en EUR vía CoinGecko (sin API key, endpoint público)."""
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin",
        "vs_currencies": "eur",
        "include_24hr_change": "true",
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    return {
        "precio_eur": data["bitcoin"]["eur"],
        "variacion_24h_pct": data["bitcoin"].get("eur_24h_change"),
    }


if __name__ == "__main__":
    print("Precios Capa 2 (acciones):")
    precios = fetch_stock_prices()
    for ticker, info in precios.items():
        print(f"  {ticker}: ${info['precio']} ({info['variacion_pct']}%)")

    print("\nPrecio BTC:")
    btc = fetch_btc_price_eur()
    print(f"  BTC: {btc['precio_eur']}€ ({btc['variacion_24h_pct']:.2f}% 24h)")
