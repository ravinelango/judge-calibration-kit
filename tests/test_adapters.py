"""Unit tests for the OpenAI and Anthropic judge adapters.

No network and no real SDKs: fake `openai` / `anthropic` modules are injected into
sys.modules so we can check the request each adapter sends and how it parses replies.
"""

import sys
import types

import pytest

from judge_calibration.dataset import Example
from judge_calibration.judges import AnthropicJudge, OpenAIJudge, get_judge


def ex():
    return Example(id="1", input="What is 2+2?", output="It is 4.", human_label="pass")


class _Recorder:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.reply


@pytest.fixture
def fake_openai(monkeypatch):
    recorder = _Recorder(None)

    class FakeOpenAI:
        def __init__(self):
            self.chat = types.SimpleNamespace(completions=recorder)

    mod = types.ModuleType("openai")
    mod.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", mod)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def set_reply(text):
        msg = types.SimpleNamespace(content=text)
        recorder.reply = types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    recorder.set_reply = set_reply
    return recorder


@pytest.fixture
def fake_anthropic(monkeypatch):
    recorder = _Recorder(None)

    class FakeAnthropic:
        def __init__(self):
            self.messages = recorder

    mod = types.ModuleType("anthropic")
    mod.Anthropic = FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", mod)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def set_reply(text):
        recorder.reply = types.SimpleNamespace(content=[types.SimpleNamespace(text=text)])

    recorder.set_reply = set_reply
    return recorder


def test_openai_adapter_sends_deterministic_request_and_parses(fake_openai):
    fake_openai.set_reply("FAIL: the arithmetic is wrong")
    judge = OpenAIJudge("gpt-test")
    verdict = judge.judge(ex())

    assert judge.name == "openai:gpt-test"
    assert verdict.label == "fail" and "arithmetic" in verdict.reason
    call = fake_openai.calls[0]
    assert call["model"] == "gpt-test" and call["temperature"] == 0
    assert "What is 2+2?" in call["messages"][0]["content"]


def test_openai_adapter_uses_custom_template(fake_openai):
    fake_openai.set_reply("PASS: fine")
    OpenAIJudge(prompt_template="Grade only this: {output}").judge(ex())
    assert fake_openai.calls[0]["messages"][0]["content"] == "Grade only this: It is 4."


def test_openai_adapter_none_content_is_a_parse_error(fake_openai):
    fake_openai.set_reply(None)
    with pytest.raises(ValueError):
        OpenAIJudge().judge(ex())


def test_anthropic_adapter_sends_deterministic_request_and_parses(fake_anthropic):
    fake_anthropic.set_reply("pass - correct and concise")
    judge = AnthropicJudge("claude-test")
    verdict = judge.judge(ex())

    assert judge.name == "anthropic:claude-test"
    assert verdict.label == "pass"
    call = fake_anthropic.calls[0]
    assert call["model"] == "claude-test" and call["temperature"] == 0
    assert call["max_tokens"] == 100


def test_missing_keys_fail_fast(fake_openai, fake_anthropic, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_judge("openai")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        get_judge("anthropic:claude-test")


def test_get_judge_default_models(fake_openai, fake_anthropic):
    assert get_judge("openai").name == "openai:gpt-4o-mini"
    assert get_judge("anthropic").name == "anthropic:claude-3-5-haiku-latest"
