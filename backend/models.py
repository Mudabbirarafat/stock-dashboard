"""
Pydantic response models for API type safety and auto-documentation.
"""

from pydantic import BaseModel
from typing import Optional


class CompanyInfo(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None


class StockDataPoint(BaseModel):
    date: str
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    volume: Optional[int]
    daily_return: Optional[float]
    moving_avg_7: Optional[float]
    volatility_score: Optional[float]


class StockSummary(BaseModel):
    symbol: str
    week52_high: float
    week52_low: float
    avg_close: float
    avg_daily_return_pct: Optional[float]
    avg_volatility: Optional[float]
    total_days: int


class StockSeries(BaseModel):
    dates: list[str]
    closes: list[float]
    returns: list[Optional[float]]


class CompareResponse(BaseModel):
    symbol1: str
    symbol2: str
    correlation: Optional[float]
    series1: StockSeries
    series2: StockSeries
