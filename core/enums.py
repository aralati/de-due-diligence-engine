"""Shared enumerations used across all agent output schemas.

Keeping these centralized prevents agents from inventing incompatible
string literals for the same concept (e.g. one agent using "buy" and
another using "BUY").
"""

from enum import Enum


class AgentName(str, Enum):
    """Canonical identifier for each node in the LangGraph."""

    MACROECONOMIC = "macroeconomic_agent"
    FINANCIAL_STATEMENT = "financial_statement_agent"
    MARKET_SENTIMENT = "market_sentiment_agent"
    RISK_COMPLIANCE_ESG = "risk_compliance_esg_agent"
    CHIEF_INVESTMENT_OFFICER = "cio_agent"


class MarketIndex(str, Enum):
    DAX = "DAX40"
    MDAX = "MDAX"


class ReportingStandard(str, Enum):
    HGB = "HGB"
    IFRS = "IFRS"


class Recommendation(str, Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ImpactDirection(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"


class SentimentLabel(str, Enum):
    VERY_NEGATIVE = "VERY_NEGATIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    POSITIVE = "POSITIVE"
    VERY_POSITIVE = "VERY_POSITIVE"


class ESGCategory(str, Enum):
    ENVIRONMENTAL = "ENVIRONMENTAL"
    SOCIAL = "SOCIAL"
    GOVERNANCE = "GOVERNANCE"
