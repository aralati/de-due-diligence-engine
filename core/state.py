"""Shared LangGraph state.

LangGraph's ``StateGraph`` expects a single state type that every node
reads from and writes partial updates into. We use a ``TypedDict``
(LangGraph's native format) whose *values* are the strict Pydantic
models from ``core.schemas`` — this gives us LangGraph-native state
merging behavior AND Pydantic-level validation on every field.

Note on the fan-out/fan-in pattern (Module 5): the four analysis
agents (macro, financial, sentiment, compliance) run in parallel and
each writes to its own key. Because each agent owns a distinct key,
LangGraph's default "last write wins" reducer is safe here — there is
no concurrent-write conflict on the same field.
"""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict

from core.schemas import (
    ComplianceFlag,
    FinancialMetrics,
    InvestmentReport,
    MacroSignal,
    SentimentScore,
)


class AgentState(TypedDict, total=False):
    """The graph-wide state object threaded through every node.

    total=False: fields are populated incrementally as agents complete,
    so at any point in the graph's execution most fields are absent
    rather than None — this makes "has this agent run yet?" a simple
    ``"macro_result" in state`` check.
    """

    # --- Input, set once at graph invocation ---
    ticker: str
    company_name: str

    # --- Written by each analysis agent (parallel fan-out) ---
    macro_result: MacroSignal
    financial_result: FinancialMetrics
    sentiment_result: SentimentScore
    compliance_result: ComplianceFlag

    # --- Written by the CIO agent (fan-in) ---
    final_report: InvestmentReport

    # --- Accumulated across the whole run ---
    # `Annotated[..., add]` tells LangGraph to concatenate lists from
    # parallel branches instead of overwriting — required because
    # multiple agents may append errors concurrently.
    errors: Annotated[list[str], add]
