from __future__ import annotations
from typing import Dict, List, Optional
from .base import EnsembleMixin, MetricResult, map_issues_to_score, \
    CONSISTENCY_RUBRIC, CITATION_RUBRIC
from . import prompts
from ..data import Query, Report

def _count_issues(out: dict) -> int:
    issues = out.get("specific_issues")

    if isinstance(issues, list):
        return len(issues)
    try:
        return int(out.get("total_issues", 0))
    except (TypeError, ValueError):
        return 0

# Metric 2: Factual & Logical Consistency
class ConsistencyMetric(EnsembleMixin):
    name = "consistency"

    def score(
        self,
        query: Query,
        report: Report,
        eval_date: Optional[str] = None,
    ) -> MetricResult:
        per_judge: List[float] = []
        details: Dict[str, dict] = {}

        for model_key in self.ensemble:
            user = prompts.CONSISTENCY_USER.format(
                task=query.render(eval_date),
                report=report.content,
            )

            out = self.gateway.complete_json(
                model_key,
                prompts.CONSISTENCY_SYSTEM,
                user,
            )

            n = _count_issues(out)
            
            per_judge.append(
                map_issues_to_score(
                    n,
                    CONSISTENCY_RUBRIC,
                )
            )
            details[model_key] = {
                "n_issues": n,
                "raw": out,
            }
        
        return MetricResult(
            metric=self.name,
            score=self._mean(per_judge),
            detail={
                "per_judge_score": per_judge,
                "raw": details,
            },
        )

class CitationAssociationMetric(EnsembleMixin):
    name = "citation_association"
    
    def score(
        self,
        query: Query,
        report: Report,
        eval_date: Optional[str] = None,
    ) -> MetricResult:
        per_judge: List[float] = []
        details: Dict[str, dict] = {}

        for model_key in self.ensemble:
            user = prompts.CITATION_ASSOC_USER.format(
                task=query.render(eval_date),
                report=report.content,
            ) 

            out = self.gateway.complete_json(
                model_key,
                prompts.CITATION_ASSOC_SYSTEM,
                user,
            )

            n = _count_issues(out)

            per_judge.append(
                map_issues_to_score(
                    n,
                    CITATION_RUBRIC,
                )
            )

            details[model_key] = {
                "n_uncited": n,
                "raw": out,
            }

        return MetricResult(
            metric=self.name,
            score=self._mean(per_judge),
            detail={
                "per_judge_score": per_judge,
                "raw": details,
            },
        )
