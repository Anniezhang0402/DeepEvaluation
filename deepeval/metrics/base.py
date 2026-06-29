from __future__ import annotations 
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from ..gateway import LLMGateway, DEFAULT_ENSEMBLE

@dataclass
class MetricResult:
    metric: str
    score: float
    detail: dict = field(default_factory=dict)

def map_issues_to_score(n_issues: int, rubric: List[tuple]) -> int:
    for max_issues, score in rubric:
        if n_issues <= max_issues:
            return score 
    return rubric[-1][1]

CONSISTENCY_RUBRIC = [
    (0, 100),
    (2, 90),
    (4, 80),
    (6, 70),
    (8, 60),
    (10, 50),
    (12, 40),
    (14, 30),
    (17, 20),
    (10**9, 10),
]

CITATION_RUBRIC = [
    (0, 100),
    (2, 90),
    (4, 80),
    (6, 70),
    (8, 60),
    (10, 50),
    (12, 40),
    (14, 30),
    (17, 20),
    (10**9, 10),
]

class EnsembleMixin:
    def __init__(
        self,
        gateway: LLMGateway,
        ensemble: Optional[List[str]] = None
    ):
        self.gateway = gateway 
        self.ensemble = ensemble or list(DEFAULT_ENSEMBLE)

    
    def _mean(
        self,
        values: List[float]
    ) -> float:
        return sum(values) / len(values) if values else 0.0
