"""Pluggable judge providers.

A judge takes an Example and returns a Verdict (pass/fail plus a short reason).
The mock judge is deterministic and offline so the kit runs in CI with no API keys.
OpenAI and Anthropic adapters are optional; keys come from the environment.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
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


def build_prompt(example: Example, template: str | None = None) -> str:
    return (template or JUDGE_PROMPT).format(
        rubric=example.rubric or DEFAULT_RUBRIC, input=example.input, output=example.output
    )


def load_prompt_template(path: str | os.PathLike[str]) -> str:
    """Read a judge prompt template. It must use {output}; {rubric} and {input} are optional."""
    text = Path(path).read_text(encoding="utf-8")
    if "{output}" not in text:
        raise ValueError(f"{path}: prompt template must contain the {{output}} placeholder")
    try:
        text.format(rubric="", input="", output="")
    except (KeyError, IndexError, ValueError) as exc:
        raise ValueError(
            f"{path}: prompt template may only use {{rubric}}, {{input}} and {{output}} "
            f"(escape other braces as {{{{ }}}}): {exc!r}"
        ) from exc
    return text


def parse_verdict(text: str) -> Verdict:
    m = re.search(r"\b(PASS|FAIL)\b\s*:?\s*(.*)", text.strip(), re.IGNORECASE | re.DOTALL)
    if not m:
        raise ValueError(f"could not parse judge verdict from: {text[:80]!r}")
    return Verdict(m.group(1).lower(), m.group(2).strip().splitlines()[0] if m.group(2) else "")


class MockJudge:
    """Deterministic keyword heuristic. It is intentionally imperfect so reports show
    realistic disagreements; it is NOT a real model and its scores mean nothing."""

    name = "mock"
    FAIL_MARKERS: tuple[str, ...] = (
        "i don't know", "i cannot", "guaranteed", "always", "never", "100%",
    )
    MIN_WORDS = 4

    def judge(self, example: Example) -> Verdict:
        out = example.output.lower()
        hit = next((m for m in self.FAIL_MARKERS if m in out), None)
        if hit:
            return Verdict("fail", f"contains marker {hit!r}")
        if len(out.split()) < self.MIN_WORDS:
            return Verdict("fail", "answer too short")
        return Verdict("pass", "no failure markers found")


class StrictMockJudge(MockJudge):
    """A second deterministic heuristic for offline A/B demos: more failure markers
    (absolute promises) and a higher minimum length. Also NOT a real model."""

    name = "mock:strict"
    FAIL_MARKERS = MockJudge.FAIL_MARKERS + ("every", "any time", "no questions asked")
    MIN_WORDS = 6


class OpenAIJudge:
    def __init__(self, model: str = "gpt-4o-mini", prompt_template: str | None = None):
        from openai import OpenAI  # optional dependency

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI()
        self.model = model
        self.name = f"openai:{model}"
        self.prompt_template = prompt_template

    def judge(self, example: Example) -> Verdict:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[{"role": "user", "content": build_prompt(example, self.prompt_template)}],
        )
        return parse_verdict(resp.choices[0].message.content or "")


class AnthropicJudge:
    def __init__(
        self, model: str = "claude-3-5-haiku-latest", prompt_template: str | None = None
    ):
        import anthropic  # optional dependency

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.client = anthropic.Anthropic()
        self.model = model
        self.name = f"anthropic:{model}"
        self.prompt_template = prompt_template

    def judge(self, example: Example) -> Verdict:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=100,
            temperature=0,
            messages=[{"role": "user", "content": build_prompt(example, self.prompt_template)}],
        )
        return parse_verdict(resp.content[0].text)


MOCK_VARIANTS = {"": MockJudge, "strict": StrictMockJudge}


def get_judge(spec: str, prompt_template: str | None = None) -> Judge:
    """spec: 'mock', 'mock:strict', 'openai[:model]' or 'anthropic[:model]'.

    `prompt_template` overrides JUDGE_PROMPT for model judges. Mock judges do not use a
    prompt, so passing one with a mock spec is an error rather than a silent no-op.
    """
    provider, _, model = spec.partition(":")
    if provider == "mock":
        if model not in MOCK_VARIANTS:
            raise ValueError(f"unknown mock variant: {model!r} (use 'mock' or 'mock:strict')")
        if prompt_template is not None:
            raise ValueError("mock judges ignore prompts; use openai/anthropic with --prompt-*")
        return MOCK_VARIANTS[model]()
    if provider == "openai":
        return OpenAIJudge(model or "gpt-4o-mini", prompt_template)
    if provider == "anthropic":
        return AnthropicJudge(model or "claude-3-5-haiku-latest", prompt_template)
    raise ValueError(f"unknown judge provider: {provider!r}")
