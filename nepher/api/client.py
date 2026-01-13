"""
Category-agnostic API client for envhub-backend.
"""

import requests
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
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
            api_key: API key or JWT token (defaults to config)
        """
        config = get_config()
        self.api_url = (api_url or config.get_api_url()).rstrip("/")
        self.api_key = api_key or config.get_api_key()
        self.session = requests.Session()
        self._jwt_token: Optional[str] = None  # Cached JWT token

        if self.api_key:
            # Check if it's an API key (starts with "envhub-") or a JWT token (starts with "eyJ")
            if self.api_key.startswith("envhub-"):
                # It's an API key - we'll exchange it for a token on first authenticated request
                self._raw_api_key = self.api_key
            else:
                # Assume it's a JWT token - use it directly
                self._jwt_token = self.api_key
                self._raw_api_key = None
                self.session.headers.update({"Authorization": f"Bearer {self._jwt_token}"})
        else:
            self._raw_api_key = None

    def _ensure_jwt_token(self):
        """Exchange API key for JWT token if needed."""
        if self._raw_api_key and not self._jwt_token:
            # Exchange API key for JWT token
            # Temporarily remove auth header to make unauthenticated request
            original_auth = self.session.headers.get("Authorization")
            self.session.headers.pop("Authorization", None)
            try:
                response = self.session.post(
                    f"{self.api_url}{APIEndpoints.API_KEY_LOGIN}",
                    json={"api_key": self._raw_api_key},
                    timeout=30,
                )
                response.raise_for_status()
                login_data = response.json()
                self._jwt_token = login_data.get("access_token")
                if self._jwt_token:
                    self.session.headers.update({"Authorization": f"Bearer {self._jwt_token}"})
            except Exception:
                # Restore original auth header on error
                if original_auth:
                    self.session.headers.update({"Authorization": original_auth})
                raise

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> requests.Response:
        """
        Make HTTP request.
        
        Note: When files are provided, data should be used for form fields instead of json.
        """
        # Exchange API key for JWT token if needed (skip for login endpoint)
        if endpoint != APIEndpoints.API_KEY_LOGIN:
            self._ensure_jwt_token()
        
        url = f"{self.api_url}{endpoint}"

        try:
            # When files are present, use data for form fields (multipart/form-data)
            # When files are not present, use json for JSON body
            if files:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    files=files,
                    stream=stream,
                    timeout=30,
                )
            else:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    data=data,
                    stream=stream,
                    timeout=30,
                )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            error_msg = "API request failed"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("message", error_data.get("detail", error_msg))
                except (ValueError, KeyError):
                    error_msg = e.response.text or error_msg
            raise APIError(f"{error_msg}") from e
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
        result = response.json()
        # Backend returns EnvironmentListResponse with nested 'environments' array
        if isinstance(result, dict) and "environments" in result:
            return result["environments"]
        # Fallback for backward compatibility
        return result if isinstance(result, list) else []

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
            duplicate_policy: Policy for duplicates ("reject", "allow", "update")
            thumbnail: Optional thumbnail image path

        Returns:
            Upload result dictionary
        """
        # Open bundle file
        bundle_file = open(bundle_path, "rb")
        files = {"bundle": (bundle_path.name, bundle_file, "application/zip")}
        file_handles = [bundle_file]
        
        # Open thumbnail file with proper content type if provided
        if thumbnail:
            thumbnail_path = Path(thumbnail)
            # Determine content type from file extension
            content_type = "image/jpeg"
            if thumbnail_path.suffix.lower() == ".png":
                content_type = "image/png"
            elif thumbnail_path.suffix.lower() == ".webp":
                content_type = "image/webp"
            elif thumbnail_path.suffix.lower() in [".jpg", ".jpeg"]:
                content_type = "image/jpeg"
            
            thumbnail_file = open(thumbnail, "rb")
            files["thumbnail"] = (thumbnail_path.name, thumbnail_file, content_type)
            file_handles.append(thumbnail_file)

        # Backend expects form data (multipart/form-data), not JSON
        # Convert boolean values to strings for form data
        data = {
            "category": category,
            "benchmark": str(benchmark).lower(),
            "force": str(force).lower(),
            "duplicate_policy": duplicate_policy,
        }

        try:
            response = self._request("POST", APIEndpoints.ENVS, files=files, data=data)
            return response.json()
        finally:
            for f in file_handles:
                f.close()

    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information."""
        response = self._request("GET", APIEndpoints.USERS_ME)
        return response.json()

    # API Key Management Methods

    def api_key_login(self, api_key: str) -> Dict[str, Any]:
        """
        Exchange API key for JWT tokens.

        Args:
            api_key: API key to exchange

        Returns:
            Dictionary containing access_token, refresh_token, and user info
        """
        response = self._request(
            "POST", APIEndpoints.API_KEY_LOGIN, json={"api_key": api_key}
        )
        return response.json()

    def create_api_key(
        self,
        name: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Create a new API key.

        Args:
            name: Optional name for the API key
            expires_at: Optional expiration date

        Returns:
            Dictionary containing API key (shown only once) and metadata
        """
        data = {}
        if name:
            data["name"] = name
        if expires_at:
            data["expires_at"] = expires_at.isoformat()
        response = self._request("POST", APIEndpoints.API_KEYS, json=data)
        return response.json()

    def list_api_keys(self) -> List[Dict[str, Any]]:
        """
        List user's API keys.

        Returns:
            List of API key dictionaries (without key values)
        """
        response = self._request("GET", APIEndpoints.API_KEYS)
        return response.json()

    def get_api_key(self, api_key_id: str) -> Dict[str, Any]:
        """
        Get API key details.

        Args:
            api_key_id: API key ID

        Returns:
            API key dictionary (without key value)
        """
        response = self._request("GET", APIEndpoints.api_key(api_key_id))
        return response.json()

    def delete_api_key(self, api_key_id: str) -> None:
        """
        Delete an API key.

        Args:
            api_key_id: API key ID
        """
        self._request("DELETE", APIEndpoints.api_key(api_key_id))

    def regenerate_api_key(self, api_key_id: str) -> Dict[str, Any]:
        """
        Regenerate an API key (creates new key, deactivates old one).

        Args:
            api_key_id: API key ID to regenerate

        Returns:
            Dictionary containing new API key (shown only once) and metadata
        """
        response = self._request("POST", APIEndpoints.api_key_regenerate(api_key_id))
        return response.json()


# Global client instance
_client_instance: Optional[APIClient] = None


def get_client(api_url: Optional[str] = None, api_key: Optional[str] = None) -> APIClient:
    """Get global API client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = APIClient(api_url=api_url, api_key=api_key)
    return _client_instance

