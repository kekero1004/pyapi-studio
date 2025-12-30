"""HTTP Request Executor for PyAPI Studio"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum
from datetime import datetime
import asyncio
import httpx


class HttpMethod(Enum):
    """HTTP 메서드"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class RequestConfig:
    """HTTP 요청 설정"""
    method: HttpMethod
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    body_type: str = "none"  # none, json, form, raw, binary
    timeout: float = 30.0
    verify_ssl: bool = True
    follow_redirects: bool = True
    auth: Optional[dict[str, Any]] = None


@dataclass
class ResponseData:
    """HTTP 응답 데이터"""
    status_code: int
    headers: dict[str, str]
    body: bytes
    elapsed_ms: float
    size_bytes: int
    cookies: dict[str, str]
    redirect_history: list[str]
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def body_text(self) -> str:
        return self.body.decode('utf-8', errors='replace')

    def body_json(self) -> Any:
        import orjson
        return orjson.loads(self.body)

    def to_dict(self) -> dict:
        """직렬화용 딕셔너리 변환"""
        return {
            "status_code": self.status_code,
            "headers": self.headers,
            "body": self.body_text,
            "elapsed_ms": self.elapsed_ms,
            "size_bytes": self.size_bytes,
            "cookies": self.cookies,
            "redirect_history": self.redirect_history,
            "timestamp": self.timestamp.isoformat()
        }


class IRequestExecutor(ABC):
    """요청 실행기 인터페이스"""

    @abstractmethod
    async def execute(self, config: RequestConfig) -> ResponseData:
        pass

    @abstractmethod
    def cancel(self) -> None:
        pass


class HttpxRequestExecutor(IRequestExecutor):
    """httpx 기반 요청 실행기 구현"""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._current_task: Optional[asyncio.Task] = None

    async def _get_client(self, verify_ssl: bool = True) -> httpx.AsyncClient:
        """클라이언트 반환 (요청마다 새로 생성하여 SSL 설정 반영)"""
        return httpx.AsyncClient(
            http2=True,
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            verify=verify_ssl
        )

    async def execute(self, config: RequestConfig) -> ResponseData:
        """HTTP 요청 실행"""
        client = await self._get_client(config.verify_ssl)

        try:
            # 요청 옵션 구성
            request_kwargs = {
                "method": config.method.value,
                "url": config.url,
                "headers": config.headers.copy(),
                "params": config.params,
                "timeout": config.timeout,
                "follow_redirects": config.follow_redirects,
            }

            # Body 처리
            if config.body and config.body_type != "none":
                if config.body_type == "json":
                    request_kwargs["content"] = config.body.encode('utf-8')
                    if "Content-Type" not in request_kwargs["headers"]:
                        request_kwargs["headers"]["Content-Type"] = "application/json"
                elif config.body_type == "form":
                    request_kwargs["data"] = self._parse_form_data(config.body)
                elif config.body_type == "urlencoded":
                    request_kwargs["data"] = self._parse_form_data(config.body)
                    if "Content-Type" not in request_kwargs["headers"]:
                        request_kwargs["headers"]["Content-Type"] = "application/x-www-form-urlencoded"
                else:
                    request_kwargs["content"] = config.body.encode('utf-8')

            # 인증 처리
            if config.auth:
                auth = self._build_auth(config.auth, request_kwargs["headers"])
                if auth:
                    request_kwargs["auth"] = auth

            # 요청 실행
            start_time = datetime.now()
            response = await client.request(**request_kwargs)
            elapsed = (datetime.now() - start_time).total_seconds() * 1000

            return ResponseData(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=response.content,
                elapsed_ms=elapsed,
                size_bytes=len(response.content),
                cookies={k: v for k, v in response.cookies.items()},
                redirect_history=[str(r.url) for r in response.history]
            )
        finally:
            await client.aclose()

    def cancel(self) -> None:
        """현재 요청 취소"""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()

    def _parse_form_data(self, body: str) -> dict:
        """Form data 파싱"""
        try:
            import json
            return json.loads(body)
        except:
            # key=value&key2=value2 형식 파싱
            result = {}
            for pair in body.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    result[key] = value
            return result

    def _build_auth(self, auth_config: dict, headers: dict) -> Optional[httpx.Auth]:
        """인증 객체 생성"""
        auth_type = auth_config.get("type")
        
        if auth_type == "basic":
            return httpx.BasicAuth(
                auth_config.get("username", ""),
                auth_config.get("password", "")
            )
        elif auth_type == "bearer":
            token = auth_config.get("token", "")
            headers["Authorization"] = f"Bearer {token}"
            return None
        elif auth_type == "api_key":
            key = auth_config.get("key", "")
            value = auth_config.get("value", "")
            add_to = auth_config.get("add_to", "header")
            if add_to == "header":
                headers[key] = value
            return None
        
        return None
