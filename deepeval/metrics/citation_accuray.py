"""
Accuracy checks whether the cited page actually substantiates the claim.
    E1: URL is inaccessible / does not resolve.
    E2: URL content is irrelevant to the task topic.
    E3: URL is accessible and on-topic but does NOT support the specific claim.
"""

from __future__ import annotations 

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Protocol, Tuple

from .base import EnsembleMixin
from . import prompts
from ..data import Query, Report

# CitationAccuracyResult
@dataclass
@dataclass
class CitationAccuracyResult:
    e1: int = 0
    e2: int = 0
    e3: int = 0
    detail: dict = field(default_factory=dict)

    @property
    def total(self) -> int:
        return self.e1 + self.e2 + self.e3

_URL_RE = re.compile(r"https?://[^\s\])\"<>]+")

_NUMERIC_CITE_RE = re.compile(r"\[(\d+)\]")

def default_claim_extractor(report: Report) -> List[Tuple[str, List[str]]]:
    pairs: List[Tuple[str, List[str]]] = []
    for line in report.content.splitlines():
        urls = _URL_RE.findall(line)
        if urls:
            claim = line.strip()
            pairs.append((claim, urls))
    return pairs

class Fetcher(Protocol):
    def fetch(self, url: str) -> Optional[str]: ...

class WebFetcher:
    def __init__(self, timeout: int = 20, max_chars: int = 8000):
        self.timeout = timeout 
        self.max_chars = max_chars 
    
    def fetch(self, url: str) -> Optional[str]:
        try:
            import requests
            resp = requests.get(
                url,
                timeout=self.timeout,
                headers={
                    "User-Agent": "deepeval-repro/0.1"
                }
            )

            if resp.status_code >= 400:
                return None
            
            return resp.text[:self.max_chars]
        except Exception:
            return None

class MockWebFetcher:
    def __init__(self, pages: Optional[Dict[str, Optional[str]]] = None):
        self.pages = pages or {}

    def fetch(self, url: str) -> Optional[str]:
        return self.pages.get(url)

class CitationAccuracyMetric:
    name = "citation_accuracy"
    def __init__(
        self,
        gateway,
        fetcher: Optional[Fetcher] = None,
        claim_extractor: Optional[Callable] = None,
        judge_model: str = "gpt-5",
        relevance_excerpt_chars: int = 600,
    ):
        self.gateway = gateway
        self.fetcher = fetcher or WebFetcher()
        self.claim_extractor = claim_extractor or default_claim_extractor 
        self.judge_model = judge_model 
        self.relevance_excerpt_chars = relevance_excerpt_chars

    def score(
        self,
        query: Query,
        report: Report,
    ) -> CitationAccuracyMetric:

        pairs = self.claim_extractor(report)
        url_to_claims: Dict[str, List[str]] = {}
        
        for claim, urls in pairs:
            for u in urls:
                url_to_claims.setdefault(u, []).append(claim)

        result = CitationAccuracyResult()
        per_url: Dict[str, dict] = {}

        for url, claims in url_to_claims.items():
            content = self.fetcher.fetch(url)

            if content is None:
                result.e1 += 1
                per_url[url] = {
                    "error": "E1",
                    "claims": len(claims),
                }
                continue

            excerpt = content[:self.relevance_excerpt_chars]

            rel = self.gateway.complete_json(
                self.judge_model,
                prompts.CITATION_RELEVANCE_SYSTEM,
                prompts.CITATION_RELEVANCE_USER.format(
                    task=query.text,
                    page_excerpt=excerpt,
                ),
            )

            if not rel.get("relevant", False):
                result.e2 += 1
                per_url[url] = {
                    "error": "E2",
                    "claims": len(claims),
                }
                continue
            unsupported = 0

            for claim in claims:
                sup = self.gateway.complete_json(
                    self.judge_model,
                    prompts.CITATION_SUPPORT_SYSTEM,
                    prompts.CITATION_SUPPORT_USER.format(
                        claim=claim,
                        page_content=content,
                    ),
                )
                if not sup.get("supported", False):
                    unsupported += 1
            result.e3 += unsupported

            per_url[url] = {
                "error": None,
                "claims": len(claims),
                "unsupported": unsupported,
            }

        result.detail = {
            "per_url": per_url,
            "n_urls": len(url_to_claims),
        }

        return result




