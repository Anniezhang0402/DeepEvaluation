from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .base import EnsembleMixin, MetricResult
from . import prompts
from ..data import Query, Report

@dataclass 
class PairOutcome:
    """Result of one candidate-vs-baseline comparison after swap-averaging."""
    candidate_total: float
    baseline_total: float 
    outcome: str

def _extract_totals(out: dict) -> tuple:
    """Pull (A_total, B_total) from a judge response, recomputing from dims if absent."""
    scores = out.get("scores", {})
    a, b = scores.get("A", {}), scores.get("B", {})

    def _total(d:dict) -> float:
        if "total" in d:
            try:
                return float(d["total"])
            except (TypeError, ValueError):
                pass 

        dims = ["granularity", "insight", "critique", "evidence", "density"]
    
    return _total(a), _total(b)

class DepthMetric(EnsembleMixin):
    """Pairwise depth with position-swap neutralization and tie-excluded win rate."""
    name = "depth"

    TIE_THRESHOLD = 1.0

    def _one_direction(
        self,
        model_key: str,
        query: Query,
        first: Report,
        second: Report,
        eval_date: Optional[str],
    ) -> tuple:
        """Score one ordering. Returns(first_total, second_total) as A,B."""

        user = prompts.DEPTH_USER.format(
            query=query.render(eval_date),
            report_a_content=first.content,
            report_b_content=second.content,
        )

        out = self.gateway.complete_json(model_key, prompts.DEPTH_SYSTEM, user)
        return _extract_totals(out)

    def compare(
        self,
        query: Query,
        candidate: Report,
        baseline: Report,
        eval_date: Optional[str] = None,
    ) -> PairOutcome:
        """
        Compare candidate vs baseline with swap-averaging across the ensemble.
        Direction 1: A=candidate, B=baseline.
        Direction 2: A=baseline,  B=candidate (swapped) -> remap back.
        Average each report's total over both directions and both judges.
        """

        cand_totals: List[float] = []
        base_totals: List[float] = []

        for model_key in self.ensemble:
            a1, b1 = self._one_direction(
                model_key,
                query,
                candidate,
                baseline,
                eval_date,
            )

            a2, b2 = self._one_direction(
                model_key,
                query,
                baseline,
                candidate,
                eval_date,
            )

            cand_totals.extend([a1, b2])
            base_totals.extend([b1, a2])
        
        cand_avg = self._mean(cand_totals)
        base_avg = self._mean(base_totals)
        diff = cand_avg - base_avg 

        if abs(diff) <= self.TIE_THRESHOLD:
            outcome = "tie"
        elif diff > 0:
            outcome = "win"
        else:
            outcome = "lose"
        
        return PairOutcome(
            candidate_total=cand_avg,
            baseline_total=base_avg,
            outcome=outcome,
        )

    @staticmethod
    def win_rate(outcomes: List[PairOutcome]) -> float:
        """win rate over a set of comparisons, ties excluded from the denominator."""
        
        wins = sum(1 for o in outcomes if o.outcome == "win")
        losses = sum(1 for o in outcomes if o.outcome == "lose")
        denom = wins + losses 
        return 100.0 * wins / denom if denom else 0.0