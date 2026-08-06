"""Unit tests for the contract layer (core.schemas / core.enums).

Run with: pytest tests/test_schemas.py -v
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from core.enums import (
    ESGCategory,
    ImpactDirection,
    MarketIndex,
    Recommendation,
    ReportingStandard,
    RiskLevel,
    SentimentLabel,
)
from core.schemas import (
    AgentMetadata,
    ComplianceFlag,
    ESGSubScore,
    FinancialMetrics,
    InvestmentReport,
    MacroSignal,
    MonteCarloResult,
    SentimentScore,
    SourceCitation,
)


def _metadata(agent_name: str = "test_agent") -> AgentMetadata:
    return AgentMetadata(
        agent_name=agent_name,
        model_used="claude-sonnet-4-6",
        confidence_score=0.85,
        execution_time_ms=1200,
        sources=[
            SourceCitation(
                source_name="Destatis",
                retrieved_at=datetime.now(timezone.utc),
                reliability_score=0.9,
            )
        ],
    )


class TestAgentMetadata:
    def test_valid_metadata(self) -> None:
        meta = _metadata()
        assert meta.confidence_score == 0.85

    def test_confidence_out_of_bounds_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AgentMetadata(
                agent_name="x",
                model_used="claude-sonnet-4-6",
                confidence_score=1.5,  # invalid: > 1.0
                execution_time_ms=100,
            )

    def test_negative_execution_time_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AgentMetadata(
                agent_name="x",
                model_used="claude-sonnet-4-6",
                confidence_score=0.5,
                execution_time_ms=-1,
            )


class TestMacroSignal:
    def test_valid_signal(self) -> None:
        signal = MacroSignal(
            metadata=_metadata("macroeconomic_agent"),
            inflation_rate_de=2.3,
            ecb_deposit_rate=3.25,
            industrial_production_index_de=-1.2,
            gdp_growth_qoq_de=0.1,
            unemployment_rate_de=6.0,
            impact_direction=ImpactDirection.NEUTRAL,
            impact_assessment="Stable inflation with mild industrial contraction; limited near-term impact.",
            macro_risk_level=RiskLevel.MEDIUM,
        )
        assert signal.macro_risk_level == RiskLevel.MEDIUM

    def test_short_impact_assessment_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MacroSignal(
                metadata=_metadata(),
                inflation_rate_de=2.3,
                ecb_deposit_rate=3.25,
                industrial_production_index_de=-1.2,
                gdp_growth_qoq_de=0.1,
                unemployment_rate_de=6.0,
                impact_direction=ImpactDirection.NEUTRAL,
                impact_assessment="too short",  # < 20 chars
                macro_risk_level=RiskLevel.MEDIUM,
            )


class TestFinancialMetrics:
    def _monte_carlo(self) -> MonteCarloResult:
        return MonteCarloResult(
            simulations_count=10_000,
            expected_return_1y_pct=7.5,
            value_at_risk_95_pct=-12.3,
            worst_case_5th_percentile_price=150.0,
            best_case_95th_percentile_price=210.0,
        )

    def test_valid_metrics(self) -> None:
        fm = FinancialMetrics(
            metadata=_metadata("financial_statement_agent"),
            ticker="SAP.DE",
            reporting_standard=ReportingStandard.IFRS,
            fiscal_year=2025,
            current_price_eur=185.4,
            pe_ratio=28.1,
            peg_ratio=1.9,
            dcf_fair_value_eur=205.0,
            revenue_growth_yoy_pct=9.2,
            ebitda_margin_pct=31.5,
            free_cash_flow_eur=6_500_000_000,
            debt_to_equity=0.45,
            monte_carlo=self._monte_carlo(),
            quant_recommendation=Recommendation.BUY,
            quant_risk_level=RiskLevel.LOW,
        )
        assert fm.ticker == "SAP.DE"

    def test_negative_price_rejected(self) -> None:
        with pytest.raises(ValidationError):
            FinancialMetrics(
                metadata=_metadata(),
                ticker="SAP.DE",
                reporting_standard=ReportingStandard.IFRS,
                fiscal_year=2025,
                current_price_eur=-1.0,  # invalid
                revenue_growth_yoy_pct=9.2,
                ebitda_margin_pct=31.5,
                free_cash_flow_eur=1.0,
                debt_to_equity=0.45,
                monte_carlo=self._monte_carlo(),
                quant_recommendation=Recommendation.BUY,
                quant_risk_level=RiskLevel.LOW,
            )

    def test_monte_carlo_requires_min_simulations(self) -> None:
        with pytest.raises(ValidationError):
            MonteCarloResult(
                simulations_count=10,  # < 1000
                expected_return_1y_pct=5.0,
                value_at_risk_95_pct=-10.0,
                worst_case_5th_percentile_price=100.0,
                best_case_95th_percentile_price=120.0,
            )


class TestSentimentScore:
    def test_sentiment_bounds(self) -> None:
        with pytest.raises(ValidationError):
            SentimentScore(
                metadata=_metadata(),
                ticker="SIE.DE",
                overall_sentiment=SentimentLabel.POSITIVE,
                sentiment_score=1.5,  # invalid: > 1.0
                news_volume_7d=42,
            )

    def test_empty_strings_stripped_from_headlines(self) -> None:
        score = SentimentScore(
            metadata=_metadata(),
            ticker="SIE.DE",
            overall_sentiment=SentimentLabel.POSITIVE,
            sentiment_score=0.6,
            news_volume_7d=42,
            key_headlines=["  Siemens beats forecast  ", "   ", "Strong order backlog"],
        )
        assert len(score.key_headlines) == 2


class TestComplianceFlag:
    def test_requires_exactly_three_esg_scores(self) -> None:
        with pytest.raises(ValidationError):
            ComplianceFlag(
                metadata=_metadata(),
                ticker="ALV.DE",
                lksg_supply_chain_risk=RiskLevel.LOW,
                esg_scores=[
                    ESGSubScore(
                        category=ESGCategory.ENVIRONMENTAL,
                        score_0_100=70.0,
                        rationale="Solid emissions reduction program.",
                    )
                ],  # only 1, needs exactly 3
                overall_compliance_risk=RiskLevel.LOW,
            )

    def test_esg_overall_score_average(self) -> None:
        flag = ComplianceFlag(
            metadata=_metadata(),
            ticker="ALV.DE",
            lksg_supply_chain_risk=RiskLevel.LOW,
            esg_scores=[
                ESGSubScore(
                    category=ESGCategory.ENVIRONMENTAL, score_0_100=60.0, rationale="Adequate reporting."
                ),
                ESGSubScore(
                    category=ESGCategory.SOCIAL, score_0_100=80.0, rationale="Strong labor practices."
                ),
                ESGSubScore(
                    category=ESGCategory.GOVERNANCE, score_0_100=70.0, rationale="Clean board structure."
                ),
            ],
            overall_compliance_risk=RiskLevel.LOW,
        )
        assert flag.esg_overall_score == pytest.approx(70.0)


class TestModelsAreImmutable:
    def test_frozen_model_rejects_mutation(self) -> None:
        meta = _metadata()
        with pytest.raises(ValidationError):
            meta.confidence_score = 0.1  # frozen=True should block this


class TestInvestmentReportRoundTrip:
    def test_full_report_serializes_to_json(self) -> None:
        """Smoke test: a fully-composed InvestmentReport must serialize
        cleanly, since this is what the FastAPI layer (Module 7) will
        return to the client."""
        monte_carlo = MonteCarloResult(
            simulations_count=10_000,
            expected_return_1y_pct=7.5,
            value_at_risk_95_pct=-12.3,
            worst_case_5th_percentile_price=150.0,
            best_case_95th_percentile_price=210.0,
        )
        report = InvestmentReport(
            ticker="SAP.DE",
            company_name="SAP SE",
            market_index=MarketIndex.DAX,
            macro=MacroSignal(
                metadata=_metadata("macroeconomic_agent"),
                inflation_rate_de=2.3,
                ecb_deposit_rate=3.25,
                industrial_production_index_de=-1.2,
                gdp_growth_qoq_de=0.1,
                unemployment_rate_de=6.0,
                impact_direction=ImpactDirection.NEUTRAL,
                impact_assessment="Stable macro backdrop, limited near-term impact on software demand.",
                macro_risk_level=RiskLevel.LOW,
            ),
            financial=FinancialMetrics(
                metadata=_metadata("financial_statement_agent"),
                ticker="SAP.DE",
                reporting_standard=ReportingStandard.IFRS,
                fiscal_year=2025,
                current_price_eur=185.4,
                revenue_growth_yoy_pct=9.2,
                ebitda_margin_pct=31.5,
                free_cash_flow_eur=6_500_000_000,
                debt_to_equity=0.45,
                monte_carlo=monte_carlo,
                quant_recommendation=Recommendation.BUY,
                quant_risk_level=RiskLevel.LOW,
            ),
            sentiment=SentimentScore(
                metadata=_metadata("market_sentiment_agent"),
                ticker="SAP.DE",
                overall_sentiment=SentimentLabel.POSITIVE,
                sentiment_score=0.4,
                news_volume_7d=58,
            ),
            compliance=ComplianceFlag(
                metadata=_metadata("risk_compliance_esg_agent"),
                ticker="SAP.DE",
                lksg_supply_chain_risk=RiskLevel.LOW,
                esg_scores=[
                    ESGSubScore(category=ESGCategory.ENVIRONMENTAL, score_0_100=75.0, rationale="Good."),
                    ESGSubScore(category=ESGCategory.SOCIAL, score_0_100=72.0, rationale="Good."),
                    ESGSubScore(category=ESGCategory.GOVERNANCE, score_0_100=80.0, rationale="Good."),
                ],
                overall_compliance_risk=RiskLevel.LOW,
            ),
            final_recommendation=Recommendation.BUY,
            final_confidence_score=0.78,
            overall_risk_level=RiskLevel.LOW,
            executive_summary="SAP shows resilient fundamentals amid a stable macro backdrop " * 2,
            full_report_markdown="# SAP SE — Investment Report\n\n" + "Details. " * 20,
        )
        payload = report.model_dump_json()
        assert "SAP.DE" in payload
