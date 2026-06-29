"""
This gateway gives every metric a single. provider-agnostic complete() call.
"""

from __future__ import annotations
import json
import os
import time

from dataclasses import dataclass, field
from typing import (
    Callable, Dict, List, Optional, Protocol,
)

# Model registry. 

MODELS: Dict[str, str] = {
    "gemini-2.5-pro": "google/gemini-2.5-pro",
    "gpt-5": "openai/gpt-5",
    "claude-4-sonnet": "anthropic/claude-sonnet-4",
    "gemini-2.5-flash": "google/gemini-2.5-flash",
}

DEFAULT_ENSEMBLE: List[str] = [
    "gemini-2.5-pro", "gpt-5"
]

@dataclass
class LLMResponse:
    text: str
    model: str
    raw: Optional[dict] = None

class Provider(Protocol):
    def complete(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int
    ) -> LLMResponse: ...

# Live provider
class OpenRouterProvider:
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 120
    ):
        self.api_key = api_key or os.environ.get(
            "OPENROUTER_API_KEY"
        )
        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY not set. "

                "Export it, or use MockProvider "

                "(build_gateway(mock=True)) for offline runs."

            )
        self.max_retries = max_retries
        self.timeout = timeout

    def complete(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:

        import requests

        headers = {
            "Authorization":
                f"Bearer {self.api_key}",
            "Content-Type":
                "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": user,
                },
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        last_err = None

        for attempt in range(self.max_retries):
            try:
                resp = requests.post(
                    self.BASE_URL,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                return LLMResponse(
                    text=text,
                    model=model,
                    raw=data,
                )

            except Exception as e:
                last_err = e
                time.sleep(
                    2 ** attempt
                )
        
        raise RuntimeError(
            f"Openrouter call failed after "
            f"{self.max_retries} retries: "
            f"{last_err}"
        )

# Mock provider
class MockProvider:

    def __init__(
        self,
        responder: Optional[
            Callable[[str, str, str], str]
        ] = None
    ):
        self.responder = responder or self._default_responder

    def complete(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int 
    ) -> LLMResponse:
        return LLMResponse(
            text=self.responder(
                model,
                system,
                user,
            ),
            model=model,
        )

    @staticmethod
    def _default_responder(
        model: str,
        system: str,
        user: str
    ) -> str:
        sys = system.lower()
        
        if "depth of analysis" in sys:
            return json.dumps({
                "winner": "A",
                "scores": {
                    "A": {
                        "granularity": 4,
                        "insight": 4,
                        "critique": 3,
                        "evidence": 4,
                        "density": 4,
                        "total": 19,
                    },
                    "B": {
                        "granularity": 3,
                        "insight": 2,
                        "critique": 2,
                        "evidence": 3,
                        "density": 3,
                        "total": 13,
                    },
                },

                "justification":
                    "mock: A deeper",
                
                "major_flaws": {
                    "A": [],
                    "B": ["shallow"],

                },
            })

        if "topically relevant" in sys:
            return json.dumps({
                "relevant": True,
                "reasoning":
                    "mock relevant",
            })
        
        if "substantiates a specific factual claim" in sys:
            return json.dumps({
                "supported": True,
                "reasoning":
                    "mock supported",
            })

        if (
            "factual and logical consistency" in sys
            or 
            "citation traceability" in sys 
        ):
            return json.dumps({
                "specific_issues": [ "mock issue 1", "mock issue 2",],
                "total_issues": 2,
                "score": 9,
                "reasoning":
                    "mock: two minor issues",
            })

        if (
            "binary scoring" in sys 
            or 
            "checklist criteria" in sys 
        ):
            return json.dumps({
                "evaluations": [
                    {
                        "id": 1,
                        "score": 1,
                        "justification":
                            "mock pass",
                    },
                    {
                        "id": 2,
                        "score": 0,
                        "justification":
                            "mock fail",
                    },
                ]
            })
        
        return json.dumps({
            "score": 1,
            "reasoning":
                "mock default",
        })

# The dateway itself
@dataclass 
class LLMGateway:
    provider: Provider 
    default_temperature: float = 0.0
    default_max_tokens: int = 4096

    def complete(
        self,
        model_key: str,
        system: str,
        user: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        model = MODELS.get(
            model_key,
            model_key,
        )
        return self.provider.complete(
            model=model,
            system=system,
            user=user,
            temperature=(
                self.default_temperature
                if temperature is None
                else temperature
            ),
            max_tokens=(
                self.default_max_tokens
                if max_tokens is None
                else max_tokens
            ),
        )

    def complete_json(
        self,
        model_key: str,
        system: str,
        user: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> dict:
        resp = self.complete(
            model_key, system, user, temperature, max_tokens,
        )
        return _parse_json_lenient( resp.text )

def _parse_json_lenient(
    text: str
) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = t.split(
            "```",
            2,
        )[1]
        if t.startswith("json"):
            t = t[4:]
        t = t.strip()

    try:
        return json.loads(t)
    except json.JSONDecodeError:
        start = t.find("{")
        end = t.rfind("}")
        if (
            start != -1
            and
            end != -1
            and
            end > start 
        ):
            return json.loads(
                t[start:end + 1]
            )
        raise 

def build_gateway(
    mock: bool = False,
    api_key: Optional[str] = None,
    responder: Optional[
        Callable[[str, str, str], str]
    ] = None
) -> LLMGateway:
    if mock:
        return LLMGateway(
            provider=MockProvider(
                responder=responder
            )
        )
    return LLMGateway(
        provider=OpenRouterProvider(
            api_key=api_key
        )
    )
