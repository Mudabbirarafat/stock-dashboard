"""
Data ingestion: fetches stock data via yfinance, falls back to mock data
if the network is unavailable. Computes all required derived metrics.
"""

import os
import sqlite3
import datetime
import random
import math

import pandas as pd
import numpy as np

from database import get_db_connection

# ─── Company Universe ────────────────────────────────────────────────────────

COMPANIES = [
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries",    "sector": "Energy"},
    {"symbol": "TCS.NS",      "name": "Tata Consultancy Services","sector": "IT"},
    {"symbol": "INFY.NS",     "name": "Infosys",                "sector": "IT"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank",              "sector": "Finance"},
    {"symbol": "WIPRO.NS",    "name": "Wipro",                  "sector": "IT"},
    {"symbol": "ICICIBANK.NS","name": "ICICI Bank",             "sector": "Finance"},
    {"symbol": "HINDUNILVR.NS","name":"Hindustan Unilever",     "sector": "FMCG"},
    {"symbol": "ITC.NS",      "name": "ITC Limited",            "sector": "FMCG"},
    {"symbol": "SBIN.NS",     "name": "State Bank of India",    "sector": "Finance"},
    {"symbol": "BAJFINANCE.NS","name":"Bajaj Finance",          "sector": "Finance"},
]

# Base prices for mock data generation (realistic INR prices)
BASE_PRICES = {
    "RELIANCE.NS":   2800.0,
    "TCS.NS":        3900.0,
    "INFY.NS":       1600.0,
    "HDFCBANK.NS":   1700.0,
    "WIPRO.NS":       480.0,
    "ICICIBANK.NS":  1050.0,
    "HINDUNILVR.NS": 2500.0,
    "ITC.NS":         460.0,
    "SBIN.NS":        760.0,
    "BAJFINANCE.NS": 7200.0,
}


# ─── Mock Data Generator ─────────────────────────────────────────────────────

def generate_mock_data(symbol: str, days: int = 400) -> pd.DataFrame:
    """Generate realistic OHLCV data using geometric Brownian motion."""
    random.seed(hash(symbol) % 10000)
    np.random.seed(hash(symbol) % 10000)

    base = BASE_PRICES.get(symbol, 1000.0)
    dates = pd.date_range(end=datetime.date.today(), periods=days, freq="B")

    mu    = 0.0003          # drift
    sigma = 0.015           # volatility

    prices = [base]
    for _ in range(days - 1):
        shock = np.random.normal(mu, sigma)
        prices.append(prices[-1] * math.exp(shock))

    df = pd.DataFrame({"date": dates, "close": prices})
    df["open"]   = df["close"].shift(1).fillna(base) * (1 + np.random.normal(0, 0.003, days))
    df["high"]   = df[["open", "close"]].max(axis=1) * (1 + abs(np.random.normal(0, 0.005, days)))
    df["low"]    = df[["open", "close"]].min(axis=1) * (1 - abs(np.random.normal(0, 0.005, days)))
    df["volume"] = (np.random.randint(500_000, 5_000_000, days)).tolist()
    df["symbol"] = symbol
    return df


# ─── yfinance Fetch ──────────────────────────────────────────────────────────

def fetch_yfinance(symbol: str, period: str = "1y") -> pd.DataFrame | None:
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty:
            return None
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"stock splits": "splits", "capital gains": "cap_gains"})
        df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
        df["symbol"] = symbol
        df = df[["symbol", "date", "open", "high", "low", "close", "volume"]]
        return df
    except Exception as e:
        print(f"[yfinance] Failed for {symbol}: {e}")
        return None


# ─── Metric Computation ──────────────────────────────────────────────────────

def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add daily_return, 7-day MA, and volatility score."""
    df = df.sort_values("date").copy()

    # Daily return
    df["daily_return"] = (df["close"] - df["open"]) / df["open"]

    # 7-day moving average of close
    df["moving_avg_7"] = df["close"].rolling(window=7, min_periods=1).mean().round(2)

    # Volatility score: rolling 14-day std of daily returns (annualised, scaled 0–100)
    df["volatility_score"] = (
        df["daily_return"].rolling(window=14, min_periods=1).std() * math.sqrt(252) * 100
    ).round(4)

    return df


# ─── Ingestion Entry Point ───────────────────────────────────────────────────

def ingest_all_stocks():
    conn = get_db_connection()

    # Upsert company list
    conn.executemany(
        "INSERT OR IGNORE INTO companies (symbol, name, sector) VALUES (?, ?, ?)",
        [(c["symbol"], c["name"], c["sector"]) for c in COMPANIES],
    )
    conn.commit()

    for company in COMPANIES:
        symbol = company["symbol"]
        print(f"[Ingest] Processing {symbol} ...")

        # Check if we already have recent data
        last = conn.execute(
            "SELECT MAX(date) AS last_date FROM stock_data WHERE symbol = ?", (symbol,)
        ).fetchone()["last_date"]

        today_str = str(datetime.date.today())
        if last == today_str:
            print(f"[Ingest] {symbol} already up to date.")
            continue

        # Try yfinance first, fall back to mock
        df = fetch_yfinance(symbol)
        if df is None or df.empty:
            print(f"[Ingest] Using mock data for {symbol}")
            raw = generate_mock_data(symbol)
            raw["date"] = raw["date"].astype(str)
            df = raw[["symbol", "date", "open", "high", "low", "close", "volume"]]

        # Handle missing values
        df = df.dropna(subset=["close"])
        df["open"]   = df["open"].fillna(df["close"])
        df["high"]   = df["high"].fillna(df["close"])
        df["low"]    = df["low"].fillna(df["close"])
        df["volume"] = df["volume"].fillna(0).astype(int)

        # Compute metrics
        df = compute_metrics(df)

        # Round floats
        for col in ["open", "high", "low", "close", "moving_avg_7"]:
            df[col] = df[col].round(2)
        df["daily_return"] = df["daily_return"].round(6)

        # Upsert rows
        rows = df[[
            "symbol", "date", "open", "high", "low", "close", "volume",
            "daily_return", "moving_avg_7", "volatility_score"
        ]].to_dict(orient="records")

        conn.executemany(
            """
            INSERT INTO stock_data
                (symbol, date, open, high, low, close, volume,
                 daily_return, moving_avg_7, volatility_score)
            VALUES
                (:symbol, :date, :open, :high, :low, :close, :volume,
                 :daily_return, :moving_avg_7, :volatility_score)
            ON CONFLICT(symbol, date) DO UPDATE SET
                open=excluded.open, high=excluded.high,
                low=excluded.low,   close=excluded.close,
                volume=excluded.volume,
                daily_return=excluded.daily_return,
                moving_avg_7=excluded.moving_avg_7,
                volatility_score=excluded.volatility_score
            """,
            rows,
        )
        conn.commit()
        print(f"[Ingest] {symbol}: {len(rows)} rows saved.")

    conn.close()
    print("[Ingest] All stocks processed.")
