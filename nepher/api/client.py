"""
Category-agnostic API client for envhub-backend.
"""

import requests
from pathlib import Path
from typing import List, Optional, Dict, Any
from typing import List, Optional, Dict, Any
from pathlib import Path
import requests
from nepher.config import get_config
from nepher.api.endpoints import APIEndpoints


class APIError(Exception):
    """API client error."""

    pass


class APIClient:
    """Category-agnostic API client."""

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize API client.

        Args:
            api_url: API base URL (defaults to config)
            api_key: API key (defaults to config)
        """
        config = get_config()
        self.api_url = (api_url or config.get_api_url()).rstrip("/")
        self.api_key = api_key or config.get_api_key()
        self.session = requests.Session()

        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> requests.Response:
        """Make HTTP request."""
        url = f"{self.api_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                files=files,
                stream=stream,
                timeout=30,
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            raise APIError(f"API request failed: {e.response.text}") from e
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}") from e

    def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        response = self._request("GET", APIEndpoints.HEALTH)
        return response.json()

    def get_info(self) -> Dict[str, Any]:
        """Get API information."""
        response = self._request("GET", APIEndpoints.INFO)
        return response.json()

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
        params = {}
        if category:
            params["category"] = category
        if type:
            params["type"] = type
        if benchmark is not None:
            params["benchmark"] = benchmark
        if search:
            params["search"] = search
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        response = self._request("GET", APIEndpoints.ENVS, params=params)
        return response.json()

    def get_environment(self, env_id: str) -> Dict[str, Any]:
        """Get environment details."""
        response = self._request("GET", APIEndpoints.env(env_id))
        return response.json()

    def download_environment(self, env_id: str, dest_path: Path) -> Path:
        """
        Download environment bundle.

        Args:
            env_id: Environment ID
            dest_path: Destination path for the ZIP file

        Returns:
            Path to downloaded file
        """
        response = self._request("GET", APIEndpoints.env_download(env_id), stream=True)

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

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
            duplicate_policy: Policy for duplicates ("reject", "replace", "version")
            thumbnail: Optional thumbnail image path

        Returns:
            Upload result dictionary
        """
        files = {"bundle": open(bundle_path, "rb")}
        if thumbnail:
            files["thumbnail"] = open(thumbnail, "rb")

        data = {
            "category": category,
            "benchmark": benchmark,
            "force": force,
            "duplicate_policy": duplicate_policy,
        }

        try:
            response = self._request("POST", APIEndpoints.ENVS, files=files, json=data)
            return response.json()
        finally:
            for f in files.values():
                f.close()

    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information."""
        response = self._request("GET", APIEndpoints.USERS_ME)
        return response.json()


# Global client instance
_client_instance: Optional[APIClient] = None


def get_client(api_url: Optional[str] = None, api_key: Optional[str] = None) -> APIClient:
    """Get global API client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = APIClient(api_url=api_url, api_key=api_key)
    return _client_instance

