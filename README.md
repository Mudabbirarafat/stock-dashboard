# 📈 JarNox — Stock Data Intelligence Dashboard

A full-stack mini financial data platform built for the JarNox internship assignment.

---

## 🗂️ Project Structure

```
stock_dashboard/
├── backend/
│   ├── main.py            # FastAPI application & all REST endpoints
│   ├── database.py        # SQLite init & connection helpers
│   ├── data_ingestion.py  # yfinance fetch + mock data + metric computation
│   └── models.py          # Pydantic response models
├── frontend/
│   └── index.html         # Single-page dashboard (vanilla JS + Chart.js)
├── data/
│   └── stocks.db          # SQLite database (auto-created on first run)
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the server

```bash
cd backend
python main.py
```

Or with uvicorn directly:

```bash
uvicorn backend.main:app --reload --port 8000
```

### 3. Open the dashboard

- **Dashboard:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

> On first startup, data is automatically fetched from **yfinance** (requires internet).  
> If the network is unavailable, realistic **mock data** is generated automatically using geometric Brownian motion — no manual steps needed.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/companies` | All available companies |
| GET | `/data/{symbol}?days=30` | Last N days of OHLCV + metrics |
| GET | `/summary/{symbol}` | 52-week high/low, avg close, volatility |
| GET | `/compare?symbol1=X&symbol2=Y&days=30` | Compare two stocks + correlation |
| GET | `/gainers-losers?days=7` | Top 5 gainers and losers |
| GET | `/sentiment` | Mock sentiment index (30-day) |

---

## 🧩 Features

### Part 1 — Data Collection & Preparation
- Fetches 1 year of daily OHLCV data via **yfinance** for 10 NSE-listed stocks
- Falls back to **mock data** (geometric Brownian motion) if offline
- Handles missing values, incorrect formats, date normalization
- Computed metrics:
  - **Daily Return** = (Close − Open) / Open
  - **7-Day Moving Average** of closing price
  - **52-Week High / Low**
  - **Volatility Score** = rolling 14-day std of daily returns × √252 (annualised)
  - **Mock Sentiment Index** = custom formula mapping returns to 0–100 scale

### Part 2 — Backend API
- **FastAPI** with automatic Swagger/OpenAPI docs at `/docs`
- **SQLite** database with WAL mode for concurrent reads
- Upsert-based ingestion (safe to re-run; no duplicates)
- Proper HTTP error codes (404 for missing symbols, etc.)
- CORS enabled for frontend–backend separation

### Part 3 — Visualization Dashboard
- Dark-themed single-page app (no framework — pure HTML + CSS + JS)
- Company sidebar with live search/filter
- **Closing Price + 7-Day MA** line chart with period selector (30D / 90D / 180D / 1Y)
- **Daily Return** bar chart (green = positive, red = negative)
- **Stock Comparison** with Pearson correlation coefficient badge
- **Top Gainers / Losers** table (7-day rolling)
- **Sentiment Index** cards with animated meter bars

---

## 📊 Covered Companies

| Symbol | Company | Sector |
|--------|---------|--------|
| RELIANCE.NS | Reliance Industries | Energy |
| TCS.NS | Tata Consultancy Services | IT |
| INFY.NS | Infosys | IT |
| HDFCBANK.NS | HDFC Bank | Finance |
| WIPRO.NS | Wipro | IT |
| ICICIBANK.NS | ICICI Bank | Finance |
| HINDUNILVR.NS | Hindustan Unilever | FMCG |
| ITC.NS | ITC Limited | FMCG |
| SBIN.NS | State Bank of India | Finance |
| BAJFINANCE.NS | Bajaj Finance | Finance |

---

## 🧪 Tech Stack

- **Language:** Python 3.11+
- **Backend:** FastAPI + Uvicorn
- **Database:** SQLite (swap to PostgreSQL by changing `DB_PATH` in `database.py`)
- **Data:** yfinance, Pandas, NumPy
- **Frontend:** Vanilla HTML/CSS/JS + Chart.js (CDN)
- **Docs:** Auto-generated Swagger UI

---

## 🔧 Configuration

To switch to **PostgreSQL**, update `database.py`:

```python
import psycopg2
conn = psycopg2.connect("postgresql://user:pass@localhost/stocks")
```

To add **more symbols**, edit the `COMPANIES` list in `data_ingestion.py`.

---

## 📦 Submission

- GitHub repo with this codebase
- Demo: run `python backend/main.py` and visit http://localhost:8000

---

*Built with ❤️ for the JarNox Software Engineering Internship Assignment.*
