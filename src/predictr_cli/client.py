"""HTTP client for the predictr.io API with retry/backoff."""

from __future__ import annotations

import sys
from typing import Any, Iterator, Optional

import httpx
from tenacity import (
    RetryError,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from predictr_cli.config import Config, ConfigError


class APIError(Exception):
    """Raised when the API returns a non-success response we won't retry."""

    def __init__(self, status_code: int, message: str, body: Any = None):
        super().__init__(f"API {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.body = body


# 4xx errors we deliberately do not retry — they won't get better.
_NO_RETRY_STATUSES = {400, 401, 403, 404, 405, 409, 422}


class _RetryableHTTPError(Exception):
    """Internal: signals tenacity should retry the request."""


class Client:
    """Thin wrapper around httpx with retry logic and predictr.io conventions.

    Most callers should use the resource methods (get_json/post_json/...)
    rather than .request() directly, since they handle JSON encoding,
    error mapping, and retry consistently.
    """

    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.api_url.rstrip("/")
        header_name, header_value = config.require_auth()
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={header_name: header_value, "Accept": "application/json"},
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # --------------------------------------------------------------------- #
    # Public helpers — most commands call these.
    # --------------------------------------------------------------------- #

    def get(self, path: str, **kwargs: Any) -> Any:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, json: Any = None, **kwargs: Any) -> Any:
        return self._request("POST", path, json=json, **kwargs)

    def post_file(
        self,
        path: str,
        file_path: str,
        *,
        field_name: str = "file",
        form_data: Optional[dict[str, Any]] = None,
    ) -> Any:
        """POST a multipart upload from a local file.

        The whole file is read into memory before sending so that retries
        on transient failures can replay the same payload. Use --no-retry
        for very large uploads if memory is a concern.

        `form_data` is sent alongside the file as additional multipart fields.
        """
        with open(file_path, "rb") as fh:
            content = fh.read()
        filename = file_path.split("/")[-1]
        files = {field_name: (filename, content)}
        return self._request("POST", path, files=files, data=form_data)

    def put(self, path: str, json: Any = None, **kwargs: Any) -> Any:
        return self._request("PUT", path, json=json, **kwargs)

    def patch(self, path: str, json: Any = None, **kwargs: Any) -> Any:
        return self._request("PATCH", path, json=json, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self._request("DELETE", path, **kwargs)

    # --------------------------------------------------------------------- #
    # Pagination — predictr.io uses x-page-token (request) / x-next-page (response).
    # --------------------------------------------------------------------- #

    def get_page(
        self,
        path: str,
        *,
        page_token: Optional[str] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> tuple[Any, Optional[str]]:
        """Fetch one page of a list endpoint and return (body, next_page_token)."""
        extra_headers = {"x-page-token": page_token} if page_token else None
        body, response_headers = self._request_full(
            "GET", path, params=params, extra_headers=extra_headers
        )
        return body, response_headers.get("x-next-page") if response_headers else None

    def paginate(
        self,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
    ) -> Iterator[Any]:
        """Yield items from every page of a list endpoint, until exhausted."""
        page_token: Optional[str] = None
        while True:
            body, next_token = self.get_page(
                path, page_token=page_token, params=params
            )
            if isinstance(body, list):
                yield from body
            elif body is not None:
                yield body
            if not next_token:
                return
            page_token = next_token

    # --------------------------------------------------------------------- #
    # Internal
    # --------------------------------------------------------------------- #

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make an HTTP request with retry, returning parsed JSON or None."""
        body, _ = self._request_full(method, path, **kwargs)
        return body

    def _request_full(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Optional[dict[str, Any]] = None,
        files: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> tuple[Any, Optional[httpx.Headers]]:
        """Make an HTTP request with retry; return (parsed_body, response_headers)."""

        def _attempt() -> httpx.Response:
            if self.config.verbose:
                print(f"→ {method} {self.base_url}{path}", file=sys.stderr)
            try:
                response = self._client.request(
                    method,
                    path,
                    json=json,
                    params=params,
                    files=files,
                    data=data,
                    headers=extra_headers,
                )
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                raise _RetryableHTTPError(f"network error: {exc}") from exc

            if response.status_code >= 500 or response.status_code == 429:
                raise _RetryableHTTPError(
                    f"server returned {response.status_code}: {response.text[:200]}"
                )
            return response

        if self.config.no_retry or self.config.max_retries <= 0:
            try:
                response = _attempt()
            except _RetryableHTTPError as exc:
                raise APIError(0, str(exc)) from exc
        else:
            retryer = Retrying(
                stop=stop_after_attempt(self.config.max_retries + 1),
                wait=wait_exponential(multiplier=1, min=1, max=8),
                retry=retry_if_exception_type(_RetryableHTTPError),
                reraise=False,
            )
            try:
                response = retryer(_attempt)
            except RetryError as exc:
                raise APIError(0, f"retries exhausted: {exc.last_attempt.exception()}") from exc

        # Map non-retryable error responses to APIError
        if response.status_code in _NO_RETRY_STATUSES or 400 <= response.status_code < 500:
            try:
                body = response.json()
                message = body.get("message") or body.get("error") or response.text
            except (ValueError, AttributeError):
                body = response.text
                message = response.text or response.reason_phrase
            raise APIError(response.status_code, message, body=body)

        # Parse a successful response. 204 No Content → None.
        if response.status_code == 204 or not response.content:
            return None, response.headers
        try:
            return response.json(), response.headers
        except ValueError:
            # Not all endpoints return JSON; return the raw text.
            return response.text, response.headers


def make_client(config: Config) -> Client:
    """Create a Client, validating auth is configured."""
    # require_auth() will raise ConfigError before we open a connection.
    config.require_auth()
    return Client(config)


# Re-exported so command modules can catch it without importing config too.
__all__ = ["APIError", "Client", "ConfigError", "make_client"]
