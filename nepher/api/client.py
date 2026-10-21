"""
Category-agnostic API client for envhub-backend.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from nepher.api.endpoints import APIEndpoints
from nepher.config import get_config
from nepher.credentials import resolve_api_key

logger = logging.getLogger(__name__)

# (connect, read) timeouts in seconds. Bundles can be several GB, and the
# backend may take a while to validate an upload before responding.
DEFAULT_TIMEOUT = (10, 30)
TRANSFER_TIMEOUT = (30, 600)
DOWNLOAD_CHUNK_SIZE = 1024 * 1024


class APIError(Exception):
    """API client error."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def _error_message(response: requests.Response, fallback: str) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text.strip() or fallback
    if isinstance(data, dict):
        for key in ("message", "detail", "error"):
            if data.get(key):
                return str(data[key])
    return fallback


class APIClient:
    """Category-agnostic API client."""

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize API client.

        Args:
            api_url: API base URL (defaults to config)
            api_key: API key or JWT token (defaults to stored credentials)
        """
        self.api_url = (api_url or get_config().get_api_url()).rstrip("/")
        self.api_key = api_key or resolve_api_key()
        self.session = requests.Session()

        if self.api_key:
            if self.api_key.startswith("nepher_"):
                # The backend verifies X-API-Key on every request, so long
                # validator runs never depend on a short-lived access token.
                self.session.headers["X-API-Key"] = self.api_key
            else:
                self.session.headers["Authorization"] = f"Bearer {self.api_key}"

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        timeout: Any = DEFAULT_TIMEOUT,
    ) -> requests.Response:
        """Make an HTTP request and raise APIError on failure."""
        url = f"{self.api_url}{endpoint}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data if not files else None,
                data=data,
                files=files,
                stream=stream,
                timeout=timeout,
            )
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {e}") from e

        if response.status_code >= 400:
            message = _error_message(response, f"HTTP {response.status_code}")
            if response.status_code == 401:
                message = f"{message} (run 'nepher login' or set NEPHER_API_KEY)"
            response.close()
            raise APIError(message, status_code=response.status_code)
        return response

    def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        return self._request("GET", APIEndpoints.HEALTH).json()

    def get_info(self) -> Dict[str, Any]:
        """Get API information."""
        return self._request("GET", APIEndpoints.INFO).json()

    def list_environments(
        self,
        category: Optional[str] = None,
        type: Optional[str] = None,
        benchmark: Optional[bool] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List environments.

        Args:
            category: Filter by category
            type: Filter by type ("usd" or "preset")
            benchmark: Filter by benchmark status
            search: Search query
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of environment dictionaries
        """
        params: Dict[str, Any] = {}
        if category:
            params["category"] = category
        if type:
            params["type"] = type
        if benchmark is not None:
            params["benchmark"] = str(benchmark).lower()
        if search:
            params["search"] = search
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        result = self._request("GET", APIEndpoints.ENVS, params=params).json()
        if isinstance(result, dict) and "environments" in result:
            return result["environments"]
        return result if isinstance(result, list) else []

    def list_eval_benchmarks(self) -> List[Dict[str, Any]]:
        """List evaluation benchmarks."""
        result = self._request("GET", APIEndpoints.ENVS_EVAL_BENCHMARKS).json()
        if isinstance(result, dict) and "environments" in result:
            return result["environments"]
        return result if isinstance(result, list) else []

    def get_environment(self, env_id: str) -> Dict[str, Any]:
        """Get environment details."""
        return self._request("GET", APIEndpoints.env(env_id)).json()

    def download_environment(self, env_id: str, dest_path: Path) -> Path:
        """
        Download environment bundle.

        The file is written to ``<dest_path>.part`` and renamed only once the
        transfer completes, so an interrupted download never looks complete.

        Raises:
            APIError: If download fails
            OSError: If file cannot be written
        """
        response = self._request(
            "GET", APIEndpoints.env_download(env_id), stream=True, timeout=TRANSFER_TIMEOUT
        )

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        part_path = dest_path.with_name(dest_path.name + ".part")
        try:
            with response, open(part_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    f.write(chunk)
            os.replace(part_path, dest_path)
        except requests.exceptions.RequestException as e:
            part_path.unlink(missing_ok=True)
            raise APIError(f"Download interrupted: {e}") from e
        except OSError as e:
            part_path.unlink(missing_ok=True)
            raise OSError(f"Cannot write downloaded file to {dest_path}: {e}") from e

        return dest_path

    def upload_environment(
        self,
        bundle_path: Path,
        category: str,
        benchmark: bool = False,
        force: bool = False,
        duplicate_policy: str = "reject",
        thumbnail: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Upload environment bundle.

        Args:
            bundle_path: Path to bundle ZIP file
            category: Environment category
            benchmark: Whether this is a benchmark environment
            force: Force upload even if duplicate exists
            duplicate_policy: Policy for duplicates ("reject", "allow", "update")
            thumbnail: Optional thumbnail image path

        Returns:
            Upload result dictionary
        """
        content_types = {".png": "image/png", ".webp": "image/webp"}
        data = {
            "category": category,
            "benchmark": str(benchmark).lower(),
            "force": str(force).lower(),
            "duplicate_policy": duplicate_policy,
        }

        with open(bundle_path, "rb") as bundle_file:
            files: Dict[str, Any] = {"bundle": (bundle_path.name, bundle_file, "application/zip")}
            if thumbnail:
                thumbnail_path = Path(thumbnail)
                content_type = content_types.get(thumbnail_path.suffix.lower(), "image/jpeg")
                with open(thumbnail_path, "rb") as thumbnail_file:
                    files["thumbnail"] = (thumbnail_path.name, thumbnail_file, content_type)
                    response = self._request(
                        "POST", APIEndpoints.ENVS, files=files, data=data, timeout=TRANSFER_TIMEOUT
                    )
            else:
                response = self._request(
                    "POST", APIEndpoints.ENVS, files=files, data=data, timeout=TRANSFER_TIMEOUT
                )
        return response.json()

    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information."""
        return self._request("GET", APIEndpoints.USERS_ME).json()


_client_instance: Optional[APIClient] = None


def get_client(api_url: Optional[str] = None, api_key: Optional[str] = None) -> APIClient:
    """Get a shared API client.

    Credentials and URL are re-resolved on every call, and the cached client
    is rebuilt when either changes. Long-running validators therefore pick up
    a rotated key or ``nepher logout`` without restarting.
    """
    global _client_instance

    url = (api_url or get_config().get_api_url()).rstrip("/")
    key = api_key or resolve_api_key()

    if (
        _client_instance is None
        or _client_instance.api_url != url
        or _client_instance.api_key != key
    ):
        if _client_instance is not None:
            logger.info("EnvHub API client settings changed; rebuilding client")
        _client_instance = APIClient(api_url=url, api_key=key)
    return _client_instance


def reset_client() -> None:
    """Drop the shared client so the next call picks up new credentials."""
    global _client_instance
    _client_instance = None
