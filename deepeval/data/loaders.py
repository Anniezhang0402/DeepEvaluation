from __future__ import annotations

import glob
import json
import os
import re

from typing import Dict, List

from .schema import (
    Query,
    Report,
    DOMAINS,
    TASK_CATEGORIES,
)


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_queries(path: str) -> Dict[str, Query]:
    queries: Dict[str, Query] = {}

    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, "*.json")))
        for fp in files:
            d = _load_json(fp)
            for qd in (d if isinstance(d, list) else [d]):
                q = Query.from_dict(qd)
                queries[q.qid] = q
    else:
        d = _load_json(path)
        for qd in (d if isinstance(d, list) else [d]):
            q = Query.from_dict(qd)
            queries[q.qid] = q

    return queries


def load_reports(path: str) -> Dict[str, Report]:
    reports: Dict[str, Report] = {}

    if os.path.isdir(path):
        for fp in sorted(glob.glob(os.path.join(path, "*.json"))):
            d = _load_json(fp)  
            for rd in (d if isinstance(d, list) else [d]):
                r = Report.from_dict(rd)
                reports[r.qid] = r
    else:
        d = _load_json(path)
        for rd in (d if isinstance(d, list) else [d]): 
            r = Report.from_dict(rd)
            reports[r.qid] = r

    return reports


_COMPLETENESS_RE = re.compile(
    r"\b(all|every|each and every|exhaustive|complete list of)\b",
    re.IGNORECASE,
)


def validate_dataset(queries: Dict[str, Query]) -> List[str]:
    warnings: List[str] = []

    for qid, q in queries.items():
        if q.domain and q.domain not in DOMAINS:
            warnings.append(f"[{qid}] domain '{q.domain}' not in known DOMAINS")

        if q.category and q.category not in TASK_CATEGORIES:
            warnings.append(f"[{qid}] category '{q.category}' not in known TASK_CATEGORIES")

        if not q.checklist:
            warnings.append(f"[{qid}] has no checklist items")

        seen = set()

        for item in q.checklist:
            if item.cid in seen:
                warnings.append(f"[{qid}] duplicate checklist id '{item.cid}'")

            seen.add(item.cid)

            if _COMPLETENESS_RE.search(item.text):
                warnings.append(
                    f"[{qid}/{item.cid}] checklist item may demand "
                    f"unverifiable completeness (J.3 anti-pattern): "
                    f"\"{item.text[:60]}...\""
                )

    return warnings