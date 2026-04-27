"""
JarNox Stock Data Intelligence Dashboard — Backend API
FastAPI + SQLite + yfinance
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os

from database import init_db, get_db_connection
from data_ingestion import ingest_all_stocks
from models import StockSummary, StockDataPoint, CompareResponse, CompanyInfo

app = FastAPI(
    title="JarNox Stock Intelligence Dashboard",
    description="A mini financial data platform for real-time stock insights",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.on_event("startup")
async def startup_event():
    """Initialize DB and ingest data on startup."""
    init_db()
    ingest_all_stocks()


@app.get("/", include_in_schema=False)
def serve_frontend():
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "JarNox Stock API is running. Visit /docs for API docs."}


# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/companies", response_model=list[CompanyInfo], tags=["Companies"])
def get_companies():
    """Returns a list of all available companies with metadata."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT symbol, name, sector FROM companies ORDER BY name"
    ).fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail="No companies found. Data may still be loading.")
    return [dict(r) for r in rows]


@app.get("/data/{symbol}", response_model=list[StockDataPoint], tags=["Stock Data"])
def get_stock_data(symbol: str, days: int = Query(30, ge=1, le=365)):
    """Returns last N days of stock data for a given symbol (default: 30)."""
    symbol = symbol.upper()
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT date, open, high, low, close, volume,
               daily_return, moving_avg_7, volatility_score
        FROM stock_data
        WHERE symbol = ?
        ORDER BY date DESC
        LIMIT ?
        """,
        (symbol, days),
    ).fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No data found for symbol '{symbol}'")
    return [dict(r) for r in rows]


@app.get("/summary/{symbol}", response_model=StockSummary, tags=["Stock Data"])
def get_summary(symbol: str):
    """Returns 52-week high, low, average close, and custom metrics."""
    symbol = symbol.upper()
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT
            symbol,
            MAX(high)        AS week52_high,
            MIN(low)         AS week52_low,
            ROUND(AVG(close), 2) AS avg_close,
            ROUND(AVG(daily_return) * 100, 4) AS avg_daily_return_pct,
            ROUND(AVG(volatility_score), 4)   AS avg_volatility,
            COUNT(*)         AS total_days
        FROM stock_data
        WHERE symbol = ?
          AND date >= DATE('now', '-365 days')
        """,
        (symbol,),
    ).fetchone()
    conn.close()
    if not row or row["week52_high"] is None:
        raise HTTPException(status_code=404, detail=f"No summary data for '{symbol}'")
    return dict(row)


@app.get("/compare", response_model=CompareResponse, tags=["Analysis"])
def compare_stocks(
    symbol1: str = Query(..., example="RELIANCE.NS"),
    symbol2: str = Query(..., example="TCS.NS"),
    days: int = Query(30, ge=7, le=365),
):
    """Compare performance of two stocks over N days."""
    s1, s2 = symbol1.upper(), symbol2.upper()
    conn = get_db_connection()

    def fetch(sym):
        return conn.execute(
            """
            SELECT date, close, daily_return
            FROM stock_data
            WHERE symbol = ?
            ORDER BY date ASC
            LIMIT ?
            """,
            (sym, days),
        ).fetchall()

    d1, d2 = fetch(s1), fetch(s2)
    conn.close()

    if not d1:
        raise HTTPException(status_code=404, detail=f"No data for '{s1}'")
    if not d2:
        raise HTTPException(status_code=404, detail=f"No data for '{s2}'")

    def to_series(rows):
        return {
            "dates":   [r["date"] for r in rows],
            "closes":  [r["close"] for r in rows],
            "returns": [r["daily_return"] for r in rows],
        }

    # Correlation of daily returns
    import numpy as np
    r1 = [r["daily_return"] or 0 for r in d1]
    r2 = [r["daily_return"] or 0 for r in d2]
    min_len = min(len(r1), len(r2))
    correlation = round(float(np.corrcoef(r1[:min_len], r2[:min_len])[0, 1]), 4) if min_len > 1 else None

    return {
        "symbol1": s1,
        "symbol2": s2,
        "correlation": correlation,
        "series1": to_series(d1),
        "series2": to_series(d2),
    }


@app.get("/gainers-losers", tags=["Analysis"])
def top_gainers_losers(days: int = Query(7, ge=1, le=30)):
    """Returns top 5 gainers and losers over the last N days."""
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT symbol,
               ROUND(SUM(daily_return) * 100, 2) AS total_return_pct
        FROM stock_data
        WHERE date >= DATE('now', ? || ' days')
        GROUP BY symbol
        ORDER BY total_return_pct DESC
        """,
        (f"-{days}",),
    ).fetchall()
    conn.close()

    data = [dict(r) for r in rows]
    return {
        "gainers": data[:5],
        "losers":  data[-5:][::-1],
        "period_days": days,
    }


@app.get("/sentiment", tags=["Analysis"])
def mock_sentiment():
    """Returns a mock sentiment index for each company (fun extra metric)."""
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT symbol,
               ROUND(AVG(daily_return) * 1000 + 50, 1) AS sentiment_score
        FROM stock_data
        WHERE date >= DATE('now', '-30 days')
        GROUP BY symbol
        """
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        score = max(0, min(100, r["sentiment_score"] or 50))
        label = "Bullish 🟢" if score > 55 else ("Bearish 🔴" if score < 45 else "Neutral 🟡")
        result.append({"symbol": r["symbol"], "sentiment_score": round(score, 1), "label": label})
    return result


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
