import pytest
from src.agent import LLMClient, default_registry

def test_llm_client_mock_mode_initialization():
    client = LLMClient(mock_mode=True)
    assert client.mock_mode is True


def test_llm_client_mock_predefined_responses():
    client = LLMClient(mock_mode=True)
    client.add_mock_response(
        content="Test content response",
        tool_calls=[]
    )
    client.add_mock_response(
        content=None,
        tool_calls=[{"name": "calculate", "arguments": {"operation": "subtract", "a": 9500, "b": 8000}}]
    )

    resp1 = client.generate(messages=[{"role": "user", "content": "Hello"}])
    assert resp1["content"] == "Test content response"
    assert resp1["tool_calls"] == []

    resp2 = client.generate(messages=[{"role": "user", "content": "Calculate variance"}])
    assert resp2["content"] is None
    assert len(resp2["tool_calls"]) == 1
    assert resp2["tool_calls"][0]["name"] == "calculate"


def test_llm_client_custom_mock_handler():
    client = LLMClient(mock_mode=True)

    def custom_handler(messages, tools):
        return {
            "content": "Handled dynamically",
            "tool_calls": [],
            "raw_response": "custom"
        }

    client.set_mock_handler(custom_handler)
    resp = client.generate(messages=[{"role": "user", "content": "Any question"}])
    assert resp["content"] == "Handled dynamically"


def test_llm_client_fallback_keyword_matching():
    client = LLMClient(mock_mode=True)
    schemas = default_registry.get_schemas()

    # Query mentioning employee
    resp_emp = client.generate(
        messages=[{"role": "user", "content": "Get details for employee EMP001"}],
        tools=schemas
    )
    assert len(resp_emp["tool_calls"]) == 1
    assert resp_emp["tool_calls"][0]["name"] == "get_employee_details"
