"""Tests for the SDK client and CLI."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from aios.sdk.client import AiosClient, ChatMessage, ChatResult

# ---------------------------------------------------------------------------
# ChatMessage / ChatResult dataclasses
# ---------------------------------------------------------------------------


class TestChatDataclasses:
    def test_chat_message(self) -> None:
        m = ChatMessage(role="user", content="hello")
        assert m.role == "user"
        assert m.content == "hello"

    def test_chat_result(self) -> None:
        r = ChatResult(response="hi", agent="default", session_id="abc")
        assert r.response == "hi"
        assert r.messages == []

    def test_chat_result_with_messages(self) -> None:
        msgs = [ChatMessage(role="user", content="q"), ChatMessage(role="assistant", content="a")]
        r = ChatResult(response="a", agent="bot", session_id="s", messages=msgs)
        assert len(r.messages) == 2


# ---------------------------------------------------------------------------
# AiosClient
# ---------------------------------------------------------------------------


def _make_mock_client(**methods: MagicMock | AsyncMock) -> MagicMock:
    """Build a mock httpx.AsyncClient with given methods."""
    mock = MagicMock(spec=httpx.AsyncClient)
    for name, impl in methods.items():
        setattr(mock, name, impl)
    mock.aclose = AsyncMock()
    return mock


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


def _error_response(status_code: int = 500) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        f"{status_code}",
        request=MagicMock(),
        response=resp,
    )
    return resp


class TestAiosClient:
    def test_init_defaults(self) -> None:
        http = MagicMock(spec=httpx.AsyncClient)
        c = AiosClient(http_client=http)
        assert c.base_url == "http://localhost:8080"
        assert c._session_id is None

    def test_init_custom(self) -> None:
        http = MagicMock(spec=httpx.AsyncClient)
        c = AiosClient("http://remote:9999", timeout=60.0, http_client=http)
        assert c.base_url == "http://remote:9999"
        assert c.timeout == 60.0

    def test_strips_trailing_slash(self) -> None:
        http = MagicMock(spec=httpx.AsyncClient)
        c = AiosClient("http://localhost:8080/", http_client=http)
        assert c.base_url == "http://localhost:8080"

    def test_set_clear_session(self) -> None:
        http = MagicMock(spec=httpx.AsyncClient)
        c = AiosClient(http_client=http)
        assert c._session_id is None
        c.set_session("my-sess")
        assert c._session_id == "my-sess"
        c.clear_session()
        assert c._session_id is None


class TestAiosClientHTTP:
    @pytest.mark.asyncio
    async def test_chat_success(self) -> None:
        http = _make_mock_client(
            post=AsyncMock(return_value=_mock_response({
                "response": "Hello!",
                "agent": "default",
                "session_id": "s123",
            }))
        )
        client = AiosClient(http_client=http)
        result = await client.chat("Hi there")
        assert result.response == "Hello!"
        assert result.agent == "default"
        assert result.session_id == "s123"
        assert client._session_id == "s123"

    @pytest.mark.asyncio
    async def test_chat_with_agent_and_session(self) -> None:
        http = _make_mock_client(
            post=AsyncMock(return_value=_mock_response({
                "response": "ok",
                "agent": "researcher",
                "session_id": "s456",
            }))
        )
        client = AiosClient(http_client=http)
        result = await client.chat("test", agent="researcher", session_id="s456")
        assert result.response == "ok"
        assert result.agent == "researcher"
        # Verify payload
        call_kwargs = http.post.call_args
        assert call_kwargs[1]["json"]["agent"] == "researcher"
        assert call_kwargs[1]["json"]["session_id"] == "s456"

    @pytest.mark.asyncio
    async def test_chat_reuses_session(self) -> None:
        http = _make_mock_client(
            post=AsyncMock(return_value=_mock_response({
                "response": "ok",
                "agent": "default",
                "session_id": "auto",
            }))
        )
        client = AiosClient(http_client=http)
        await client.chat("first")
        await client.chat("second")
        # Second call should reuse session_id "auto"
        second_payload = http.post.call_args_list[1][1]["json"]
        assert second_payload["session_id"] == "auto"

    @pytest.mark.asyncio
    async def test_health(self) -> None:
        http = _make_mock_client(
            get=AsyncMock(return_value=_mock_response({
                "status": "ok", "version": "0.1.0", "agents": [], "tools": [],
            }))
        )
        client = AiosClient(http_client=http)
        data = await client.health()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_list_agents(self) -> None:
        http = _make_mock_client(
            get=AsyncMock(return_value=_mock_response([
                {"name": "default", "type": "ReActAgent"},
            ]))
        )
        client = AiosClient(http_client=http)
        agents = await client.list_agents()
        assert len(agents) == 1
        assert agents[0]["name"] == "default"

    @pytest.mark.asyncio
    async def test_list_tools(self) -> None:
        http = _make_mock_client(
            get=AsyncMock(return_value=_mock_response([]))
        )
        client = AiosClient(http_client=http)
        tools = await client.list_tools()
        assert tools == []

    @pytest.mark.asyncio
    async def test_chat_http_error(self) -> None:
        http = _make_mock_client(
            post=AsyncMock(return_value=_error_response(500))
        )
        client = AiosClient(http_client=http)
        with pytest.raises(httpx.HTTPStatusError):
            await client.chat("fail")

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """When http_client is externally provided, close() does not call aclose."""
        http = _make_mock_client()
        client = AiosClient(http_client=http)
        assert client._owned_client is False
        await client.close()
        http.aclose.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_close_owned(self) -> None:
        """When no http_client is provided, close() calls aclose on the internal client."""
        mock_http = MagicMock()
        mock_http.aclose = AsyncMock()
        with patch("aios.sdk.client.httpx.AsyncClient", return_value=mock_http):
            client = AiosClient()
            assert client._owned_client is True
            await client.close()
            mock_http.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_session_sent_when_none(self) -> None:
        http = _make_mock_client(
            post=AsyncMock(return_value=_mock_response({
                "response": "ok",
                "agent": "default",
                "session_id": "new",
            }))
        )
        client = AiosClient(http_client=http)
        await client.chat("hello")
        payload = http.post.call_args[1]["json"]
        assert "session_id" not in payload
