import httpx


def get_price(query: str) -> str:
    text = query.lower().strip()
    coins = {
        "bitcoin": "bitcoin", "btc": "bitcoin",
        "ethereum": "ethereum", "eth": "ethereum",
        "solana": "solana", "sol": "solana",
    }
    for word, coin_id in coins.items():
        if word in text:
            return _crypto(coin_id, word.upper())
    if any(code in text.upper() for code in ["USD", "EUR", "GBP"]):
        return _fx(text)
    return "I can price bitcoin, ethereum, solana, or a rate like GBP to USD."


def _crypto(coin_id: str, label: str) -> str:
    url = "https://api.coingecko.com/api/v3/simple/price"
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url, params={"ids": coin_id, "vs_currencies": "gbp,usd"})
            resp.raise_for_status()
            data = resp.json()[coin_id]
        return f"{label}: £{data['gbp']} / ${data['usd']} (CoinGecko)"
    except Exception as e:
        return f"Price lookup failed: {e}"


def _fx(text: str) -> str:
    upper = text.upper()
    base = "GBP" if "GBP" in upper else "USD"
    quote = "USD" if base == "GBP" else "EUR"
    if "EUR" in upper and "USD" in upper:
        base, quote = "EUR", "USD"
    url = f"https://api.frankfurter.app/latest?from={base}&to={quote}"
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            rate = resp.json()["rates"][quote]
        return f"1 {base} = {rate} {quote} (Frankfurter)"
    except Exception as e:
        return f"Rate lookup failed: {e}"
