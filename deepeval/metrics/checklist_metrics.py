"""
Checklist-based metrics: presentation & organization and
coverage & comprehensiveness.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import EnsembleMixin, MetricResult
from . import prompts
from ..data import Query, Report


PRESENTATION_CHECKLIST: List[str] = [
    "Does the report present a clear, coherent, and logically ordered structure that directly addresses the research question?",
    "Does the report contain zero grammar and spelling errors?",
    "Does every entry in the reference list correspond to at least one in-text citation?",
    "Does every in-text citation have a corresponding entry in the reference list?",
    "Is there exactly one References/Bibliography/Sources section, with entries sorted by a single consistent scheme?",
    "Is a single, consistent citation style used throughout the entire document?",
    "Are all in-text citations placed logically at the end of a clause or sentence, without interrupting grammatical flow?",
    "If figures or tables are included, does each contain complete data or a valid visual element? (If none, pass.)",
    "Is the formatting correct and consistent (proper Markdown heading levels; valid renderable tables)?",
    "If citations are numbered, are there no skipped numbers and no duplicates?",
]


def _format_checklist(items: List[str]) -> str:
    return "\n".join(
        f"{i+1}. {t}"
        for i, t in enumerate(items)
    )


def _binary_average(evaluations: List[dict]) -> float:
    scores = []
    for e in evaluations:
        try:
            scores.append(
                1
                if int(e.get("score", 0)) >= 1
                else 0
            )
        except (TypeError, ValueError):
            scores.append(0)
    return sum(scores) / len(scores) if scores else 0.0


class PresentationMetric(EnsembleMixin):
    name = "presentation"

    def score(
        self,
        query: Query,
        report: Report,
        eval_date: Optional[str] = None,
    ) -> MetricResult:
        checklist_section = _format_checklist(PRESENTATION_CHECKLIST)
        per_judge: List[float] = []
        details: Dict[str, dict] = {}

        for model_key in self.ensemble:
            user = prompts.PRESENTATION_USER.format(
                query=query.render(eval_date),
                checklist_section=checklist_section,
                report_content=report.content,
            )

            out = self.gateway.complete_json(
                model_key,
                prompts.PRESENTATION_SYSTEM,
                user,
            )

            frac = _binary_average(out.get("evaluations", []))
            per_judge.append(frac)
            details[model_key] = out

        score = 100.0 * self._mean(per_judge)

        return MetricResult(
            metric=self.name,
            score=score,
            detail={
                "per_judge_fraction": per_judge,
                "raw": details,
            },
        )


class CoverageMetric(EnsembleMixin):
    name = "coverage"

    def score(
        self,
        query: Query,
        report: Report,
        eval_date: Optional[str] = None,
    ) -> MetricResult:
        if not query.checklist:
            return MetricResult(
                metric=self.name,
                score=0.0,
                detail={"warning": "no checklist for query"},
            )

        checklist_section = "\n".join(
            f"{i+1}. {item.text}"
            for i, item in enumerate(query.checklist)
        )

        per_judge: List[float] = []
        details: Dict[str, dict] = {}

        for model_key in self.ensemble:
            user = prompts.COVERAGE_USER.format(
                query=query.render(eval_date),
                checklist_section=checklist_section,
                report_content=report.content,
            )

            out = self.gateway.complete_json(
                model_key,
                prompts.COVERAGE_SYSTEM,
                user,
            )

            frac = _binary_average(out.get("evaluations", []))
            per_judge.append(frac)
            details[model_key] = out

        score = 100.0 * self._mean(per_judge)

        return MetricResult(
            metric=self.name,
            score=score,
            detail={
                "per_judge_fraction": per_judge,
                "raw": details,
            },
        )