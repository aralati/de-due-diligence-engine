"""Pydantic contract layer for the Multi-Agent Due Diligence Engine.

Every agent in the LangGraph reads from and writes to these schemas.
Design principles:

1. Every output schema carries an ``AgentMetadata`` block — no agent
   result exists without provenance (sources, confidence, timing).
2. Numeric fields that have a natural bound (probabilities, scores,
   percentages) are validated at the schema level, not left to agent
   discipline.
3. Nothing here talks to a network or an LLM — this module has zero
   side effects, which makes it trivially unit-testable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from core.enums import (
    ESGCategory,
    ImpactDirection,
    MarketIndex,
    Recommendation,
    ReportingStandard,
    RiskLevel,
    SentimentLabel,
)

# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

Score01 = Annotated[float, Field(ge=0.0, le=1.0)]
"""A normalized score/probability/confidence value in [0, 1]."""

Sentiment11 = Annotated[float, Field(ge=-1.0, le=1.0)]
"""A bipolar sentiment score in [-1, 1]."""


class DDEBaseModel(BaseModel):
    """Base class for every schema in the project.

    ``strict=True`` avoids silent type coercion (e.g. the string "12"
    being accepted where a float is expected) — important when data is
    ultimately produced by an LLM tool call and we want hard failures,
    not silently wrong numbers.
    """

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
        use_enum_values=True,
    )


class SourceCitation(DDEBaseModel):
    """A single data source backing a claim, for auditability."""

    source_name: str = Field(..., min_length=1, examples=["Destatis", "yfinance"])
    url: HttpUrl | None = None
    retrieved_at: datetime
    reliability_score: Score01 = Field(
        default=0.8,
        description="Subjective/heuristic trust weight for this source.",
    )


class AgentMetadata(DDEBaseModel):
    """Provenance block attached to every agent output.

    This is what lets the CIO Agent (Module 5) reason about *how much*
    to trust a given signal when resolving conflicts between agents.
    """

    agent_name: str
    model_used: str = Field(..., examples=["claude-sonnet-4-6", "gpt-4.1"])
    confidence_score: Score01
    execution_time_ms: int = Field(..., ge=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sources: list[SourceCitation] = Field(default_factory=list)
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal issues the agent hit (e.g. stale data, missing field).",
    )


# ---------------------------------------------------------------------------
# 1. Macroeconomic Agent output
# ---------------------------------------------------------------------------


class MacroSignal(DDEBaseModel):
    metadata: AgentMetadata

    inflation_rate_de: float = Field(..., description="German HICP/CPI YoY, in %.")
    ecb_deposit_rate: float = Field(..., description="Current ECB deposit facility rate, in %.")
    industrial_production_index_de: float = Field(
        ..., description="German industrial production index, YoY % change."
    )
    gdp_growth_qoq_de: float = Field(..., description="German GDP growth, QoQ, in %.")
    unemployment_rate_de: float = Field(..., ge=0.0, le=100.0)

    impact_direction: ImpactDirection
    impact_assessment: str = Field(
        ...,
        min_length=20,
        description="Free-text reasoning on how this affects the target company.",
    )
    macro_risk_level: RiskLevel


# ---------------------------------------------------------------------------
# 2. Financial Statement Agent output
# ---------------------------------------------------------------------------


class MonteCarloResult(DDEBaseModel):
    """Output of the NumPy/SciPy Monte Carlo simulation (Module 4)."""

    simulations_count: int = Field(..., ge=1000)
    expected_return_1y_pct: float
    value_at_risk_95_pct: float = Field(
        ..., description="1y 95% VaR, as a negative percentage of position value."
    )
    worst_case_5th_percentile_price: float = Field(..., gt=0)
    best_case_95th_percentile_price: float = Field(..., gt=0)


class FinancialMetrics(DDEBaseModel):
    metadata: AgentMetadata

    ticker: str = Field(..., min_length=2, examples=["SAP.DE", "ALV.DE"])
    reporting_standard: ReportingStandard
    fiscal_year: int = Field(..., ge=2000, le=2100)

    current_price_eur: float = Field(..., gt=0)
    pe_ratio: float | None = None
    peg_ratio: float | None = None
    dcf_fair_value_eur: float | None = Field(default=None, gt=0)

    revenue_growth_yoy_pct: float
    ebitda_margin_pct: float
    free_cash_flow_eur: float
    debt_to_equity: float = Field(..., ge=0.0)

    monte_carlo: MonteCarloResult

    quant_recommendation: Recommendation
    quant_risk_level: RiskLevel


# ---------------------------------------------------------------------------
# 3. Market Sentiment Agent output
# ---------------------------------------------------------------------------


class SentimentScore(DDEBaseModel):
    metadata: AgentMetadata

    ticker: str
    overall_sentiment: SentimentLabel
    sentiment_score: Sentiment11
    news_volume_7d: int = Field(..., ge=0)

    key_headlines: list[str] = Field(default_factory=list, max_length=10)
    positive_drivers: list[str] = Field(default_factory=list, max_length=10)
    negative_drivers: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("key_headlines", "positive_drivers", "negative_drivers")
    @classmethod
    def _no_empty_strings(cls, v: list[str]) -> list[str]:
        cleaned = [item.strip() for item in v if item.strip()]
        return cleaned


# ---------------------------------------------------------------------------
# 4. Risk, Compliance & ESG Agent output
# ---------------------------------------------------------------------------


class ESGSubScore(DDEBaseModel):
    category: ESGCategory
    score_0_100: float = Field(..., ge=0.0, le=100.0)
    rationale: str = Field(..., min_length=10)


class ComplianceFlag(DDEBaseModel):
    metadata: AgentMetadata

    ticker: str
    bafin_warnings: list[str] = Field(default_factory=list)
    lksg_supply_chain_risk: RiskLevel
    esg_scores: list[ESGSubScore] = Field(..., min_length=3, max_length=3)
    regulatory_concerns: list[str] = Field(default_factory=list)
    overall_compliance_risk: RiskLevel

    @property
    def esg_overall_score(self) -> float:
        return sum(s.score_0_100 for s in self.esg_scores) / len(self.esg_scores)


# ---------------------------------------------------------------------------
# 5. CIO Agent output (final synthesis)
# ---------------------------------------------------------------------------


class AgentConflict(DDEBaseModel):
    """A detected disagreement between two agents, and how the CIO resolved it.

    Example: Financial Agent says BUY on valuation grounds while Macro
    Agent flags high inflation risk for the sector — the CIO must state
    which signal it weighted more heavily, and why.
    """

    agent_a: str
    agent_b: str
    conflict_description: str = Field(..., min_length=20)
    resolution: str = Field(..., min_length=20)


class InvestmentReport(DDEBaseModel):
    """The final artifact produced by the CIO Agent — the user-facing output."""

    ticker: str
    company_name: str
    market_index: MarketIndex
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    macro: MacroSignal
    financial: FinancialMetrics
    sentiment: SentimentScore
    compliance: ComplianceFlag

    conflicts_identified: list[AgentConflict] = Field(default_factory=list)

    final_recommendation: Recommendation
    final_confidence_score: Score01
    overall_risk_level: RiskLevel

    executive_summary: str = Field(..., min_length=50)
    full_report_markdown: str = Field(..., min_length=100)
