"""Pluggable judge providers.

A judge takes an Example and returns a Verdict (pass/fail plus a short reason).
The mock judge is deterministic and offline so the kit runs in CI with no API keys.
OpenAI and Anthropic adapters are optional; keys come from the environment.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Protocol

from .dataset import Example

JUDGE_PROMPT = """You are grading an AI assistant's answer.
Rubric: {rubric}

User input:
{input}

Assistant output:
{output}

Reply with exactly one line: PASS or FAIL, then a colon, then a one-sentence reason."""

DEFAULT_RUBRIC = "The output answers the input correctly, safely and without unsupported claims."


@dataclass(frozen=True)
class Verdict:
    label: str
    reason: str


class Judge(Protocol):
    name: str

    def judge(self, example: Example) -> Verdict: ...


def build_prompt(example: Example) -> str:
    return JUDGE_PROMPT.format(
        rubric=example.rubric or DEFAULT_RUBRIC, input=example.input, output=example.output
    )


def parse_verdict(text: str) -> Verdict:
    m = re.search(r"\b(PASS|FAIL)\b\s*:?\s*(.*)", text.strip(), re.IGNORECASE | re.DOTALL)
    if not m:
        raise ValueError(f"could not parse judge verdict from: {text[:80]!r}")
    return Verdict(m.group(1).lower(), m.group(2).strip().splitlines()[0] if m.group(2) else "")


class MockJudge:
    """Deterministic keyword heuristic. It is intentionally imperfect so reports show
    realistic disagreements; it is NOT a real model and its scores mean nothing."""

    name = "mock"
    FAIL_MARKERS = ("i don't know", "i cannot", "guaranteed", "always", "never", "100%")

    def judge(self, example: Example) -> Verdict:
        out = example.output.lower()
        hit = next((m for m in self.FAIL_MARKERS if m in out), None)
        if hit:
            return Verdict("fail", f"contains marker {hit!r}")
        if len(out.split()) < 4:
            return Verdict("fail", "answer too short")
        return Verdict("pass", "no failure markers found")


class OpenAIJudge:
    def __init__(self, model: str = "gpt-4o-mini"):
        from openai import OpenAI  # optional dependency

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI()
        self.model = model
        self.name = f"openai:{model}"

    def judge(self, example: Example) -> Verdict:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[{"role": "user", "content": build_prompt(example)}],
        )
        return parse_verdict(resp.choices[0].message.content or "")


class AnthropicJudge:
    def __init__(self, model: str = "claude-3-5-haiku-latest"):
        import anthropic  # optional dependency

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.client = anthropic.Anthropic()
        self.model = model
        self.name = f"anthropic:{model}"

    def judge(self, example: Example) -> Verdict:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=100,
            temperature=0,
            messages=[{"role": "user", "content": build_prompt(example)}],
        )
        return parse_verdict(resp.content[0].text)


def get_judge(spec: str) -> Judge:
    """spec: 'mock', 'openai[:model]' or 'anthropic[:model]'."""
    provider, _, model = spec.partition(":")
    if provider == "mock":
        return MockJudge()
    if provider == "openai":
        return OpenAIJudge(model) if model else OpenAIJudge()
    if provider == "anthropic":
        return AnthropicJudge(model) if model else AnthropicJudge()
    raise ValueError(f"unknown judge provider: {provider!r}")
