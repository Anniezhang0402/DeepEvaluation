"""
Top-level DeepEval facade.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from .gateway import LLMGateway, DEFAULT_ENSEMBLE
from .data import Query, Report
from .metrics import (
    PresentationMetric, #评估报告表达是否清楚、结构是否合理、是否符合用户需求
    ConsistencyMetric,  #评估报告内部是否自洽、是否有前后矛盾
    CoverageMetric,     #评估报告是否覆盖checklist中的要点
    CitationAssociationMetric,   #评估引用是否和对应claims关联正确
    DepthMetric,    #评估分析深度
    CitationAccuracyMetric,   #评估引用内容本身是否正确
)

TABLE1_METRICS = [
    "presentation",
    "consistency",
    "coverage",
    "citation_association",
]

class DeepEval:
    
    def __init__(
        self,
        gateway: LLMGateway,
        ensemble: Optional[List[str]] = None,
        eval_date: Optional[str] = None,
    ):
        self.gateway = gateway
        self.ensemble = ensemble or list(DEFAULT_ENSEMBLE)
        self.eval_date = eval_date

        self.presentation = PresentationMetric(
            gateway,
            self.ensemble,
        )

        self.consistency = ConsistencyMetric(
            gateway,
            self.ensemble,
        )

        self.coverage = CoverageMetric(
            gateway,
            self.ensemble,
        )

        self.citation_assoc = CitationAssociationMetric(
            gateway,
            self.ensemble,
        )

        self.depth = DepthMetric(
            gateway,
            self.ensemble
        )


    def run_table1(
        self,
        queries: List[Query],
        reports: Dict[str, Report],
    ) -> Dict[str, float]:
        
        acc = {
            m: []
            for m in TABLE1_METRICS
        }

        for q in queries:
            report = reports.get(q.qid)
            if report is None:
                continue

            acc["presentation"].append(
                self.presentation.score(
                    q,
                    report,
                    self.eval_date,
                ).score
            )

            acc["consistency"].append(
                self.consistency.score(
                    q,
                    report,
                    self.eval_date,
                ).score
            )

            acc["coverage"].append(
                self.coverage.score(
                    q,
                    report,
                    self.eval_date,
                ).score 
            )

            acc["citation_association"].append(
                self.citation_assoc.score(
                    q,
                    report,
                    self.eval_date,
                ).score
            )

        return {
            m: (
                sum(v) / len(v)
                if v
                else 0.0
            )
            for m, v in acc.items()
        }

    
    def run_depth(
        self,
        queries: List[Query],
        candidate_reports: Dict[str, Report],
        baseline_reports: Dict[str, Report],
    ) -> Dict[str, object]:
        """
        Pairwise depth win rate of candidate vs baseline over shared queries.
        """
        outcomes = []

        for q in queries:
            cand = candidate_reports.get(q.qid)
            base = baseline_reports.get(q.qid)
            if cand is None or base is None:
                continue
            outcomes.append(
                self.depth.compare(
                    q,
                    cand,
                    base,
                    self.eval_date,
                )
            )

        return {
            "win_rate": self.depth.win_rate(outcomes),
            "n": len(outcomes),
            "wins": sum(
                1
                for o in outcomes
                if o.outcome == "win"
            ),
            "losses": sum(
                1
                for o in outcomes
                if o.outcome == "lose"
            ),
            "ties": sum(
                1
                for o in outcomes
                if o.outcome == "tie"
            ),
        }


    def run_citation_accuracy(
        self,
        queries: List[Query],
        reports: Dict[str, Report],
        fetcher=None,
        judge_model: str = "gpt-5",
    ) -> Dict[str, object]:
        """
        Average E1/E2/E3 per report for a system.
        Needs a fetcher.
        """

        metric = CitationAccuracyMetric(
            self.gateway,
            fetcher=fetcher,
            judge_model=judge_model,
        )

        e1=0
        e2=0
        e3=0
        n=0
        per_report = []

        for q in queries:
            report = reports.get(q.qid)
            if report is None:
                continue
            r = metric.score(
                query=q,
                report=report,
            )

            e1 += r.e1
            e2 += r.e2
            e3 += r.e3 
            n += 1
            per_report.append(r)
        return {
            "avg_e1": (
                e1 / n
                if n
                else 0.0
            ),

            "avg_e2": (
                e2 / n
                if n
                else 0.0
            ),

            "avg_e3": (
                e3 / n
                if n
                else 0.0
            ),

            "avg_total": (
                (e1 + e2 + e3) / n 
                if n
                else 0.0
            ),

            "per_report": per_report,
        }

    
    @staticmethod
    def system_average(
        grid_row: Dict[str, float]
    ) -> float:
        """
        Average of a system's four Table-1 metrics.
        """
        vals = list(
            grid_row.values()
        )
        return (
            sum(vals) / len(vals)
            if vals
            else 0.0
        )



