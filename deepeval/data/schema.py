from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

DOMAINS = (

    "Science & Technology",

    "Economy & Business",

    "Health & Wellbeing",

    "Law & Governance",

    "Society & Culture",

    "Education & Knowledge",

    "Media & Entertainment",

)

TASK_CATEGORIES = (

    "Market Analysis",

    "Literature Review",

    "Top Rankings",

    "Technical Support",

    "Policy & Regulation",

    "Competitive Analysis",

    "Pros & Cons",

    "Wide Info Search",

    "Topic Exploration",

    "Decision Support",

)

@dataclass
class ChecklistItem:
    cid: str
    text: str 

    @classmethod
    def from_dict(cls, d: dict) -> "ChecklistItem":
        
        return cls(
            cid=str(
                d.get("cid", d.get("id", ""))
            ),
            text=d["text"]
        )

@dataclass
class Query:
    qid: str
    text: str
    domain: Optional[str] = None
    category: Optional[str] = None
    checklist: List[ChecklistItem] = field(
        default_factory=list
    )

    @classmethod 
    def from_dict(cls, d: dict) -> "Query":

        return cls(
            qid=str(d["qid"]),
            text=d["text"],
            domain=d.get("domain"),
            category=d.get("category"),
            checklist=[
                ChecklistItem.from_dict(c)
                for c in d.get("checklist", [])
            ],
        )

    def render(
        self,
        eval_date: Optional[str] = None
    ) -> str:

        if eval_date and "{{date}}" in self.text:
            return self.text.replace(
                "{{date}}",
                eval_date
            )

        return self.text

@dataclass
class Report:
    qid: str
    system: str
    content: str

    @classmethod
    def from_dict(
        cls,
        d: dict 
    ) -> "Report":

        return cls(
           qid=str(d["qid"]),
           system=d.get(
            "system",
            "unknown"
           ),
           content=d["content"],
        )