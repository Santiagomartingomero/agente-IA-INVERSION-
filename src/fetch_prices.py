"""
Obtiene precios actuales de las posiciones de Capa 2 (acciones) vía Financial Modeling Prep,
y precio de BTC vía CoinGecko (gratis, sin API key).

Requiere variable de entorno FMP_API_KEY (plan gratuito: 250 req/día).
"""

import os
import requests

FMP_API_KEY = os.environ.get("FMP_API_KEY")
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

TICKERS_CAPA_2 = ["CIFR", "LEU", "OKLO", "CRDO", "IREN"]


def fetch_stock_prices(tickers=None):
    """Devuelve dict {ticker: {precio, variacion_pct, variacion_abs}} para una lista de tickers."""
    if tickers is None:
        tickers = TICKERS_CAPA_2

    if not FMP_API_KEY:
        raise RuntimeError(
            "Falta la variable de entorno FMP_API_KEY. "
            "Consíguela gratis en https://financialmodelingprep.com/developer/docs/ "
            "y expórtala o añádela como GitHub Secret."
        )

    symbols = ",".join(tickers)
    url = f"{FMP_BASE_URL}/quote/{symbols}?apikey={FMP_API_KEY}"

    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    result = {}
    for item in data:
        result[item["symbol"]] = {
            "precio": item.get("price"),
            "variacion_pct": item.get("changesPercentage"),
            "variacion_abs": item.get("change"),
            "nombre": item.get("name"),
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
    try:
        precios = fetch_stock_prices()
        for ticker, info in precios.items():
            print(f"  {ticker}: ${info['precio']} ({info['variacion_pct']}%)")
    except RuntimeError as e:
        print(f"  [!] {e}")

    print("\nPrecio BTC:")
    btc = fetch_btc_price_eur()
    print(f"  BTC: {btc['precio_eur']}€ ({btc['variacion_24h_pct']:.2f}% 24h)")
