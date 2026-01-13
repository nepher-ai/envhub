"""
API endpoint definitions for envhub-backend.
"""

from typing import Optional


class APIEndpoints:
    """API endpoint paths."""

    # Health & Info
    HEALTH = "/api/v1/health"
    INFO = "/"  # Root endpoint for API info

    # Environment Management
    ENVS = "/api/v1/envs/"
    ENVS_PUBLIC = "/api/v1/envs/public/"
    ENVS_BENCHMARK = "/api/v1/envs/benchmark/"
    ENVS_EVAL_BENCHMARKS = "/api/v1/envs/eval-benchmarks/"
    ENVS_PENDING = "/api/v1/envs/pending/"
    ENVS_TRASH = "/api/v1/envs/trash/"

    @staticmethod
    def env(env_id: str) -> str:
        """Get environment endpoint."""
        return f"/api/v1/envs/{env_id}"

    @staticmethod
    def env_download(env_id: str) -> str:
        """Download environment endpoint."""
        return f"/api/v1/envs/{env_id}/download"

    @staticmethod
    def env_thumbnail(env_id: str) -> str:
        """Get environment thumbnail endpoint."""
        return f"/api/v1/envs/{env_id}/thumbnail"

    @staticmethod
    def env_approve(env_id: str) -> str:
        """Approve environment endpoint."""
        return f"/api/v1/envs/{env_id}/approve"

    @staticmethod
    def env_reject(env_id: str) -> str:
        """Reject environment endpoint."""
        return f"/api/v1/envs/{env_id}/reject"

    @staticmethod
    def env_activate_evaluation(env_id: str) -> str:
        """Activate evaluation endpoint."""
        return f"/api/v1/envs/{env_id}/activate-evaluation"

    @staticmethod
    def env_deactivate_evaluation(env_id: str) -> str:
        """Deactivate evaluation endpoint."""
        return f"/api/v1/envs/{env_id}/deactivate-evaluation"

    @staticmethod
    def env_toggle_benchmark(env_id: str) -> str:
        """Toggle benchmark endpoint."""
        return f"/api/v1/envs/{env_id}/toggle-benchmark"

    @staticmethod
    def env_restore(env_id: str) -> str:
        """Restore environment endpoint."""
        return f"/api/v1/envs/{env_id}/restore"

    # Authentication
    API_KEY_LOGIN = "/api/v1/auth/api-key/login"

    # API Key Management
    API_KEYS = "/api/v1/api-keys/"

    @staticmethod
    def api_key(api_key_id: str) -> str:
        """Get/delete API key endpoint."""
        return f"/api/v1/api-keys/{api_key_id}"

    @staticmethod
    def api_key_regenerate(api_key_id: str) -> str:
        """Regenerate API key endpoint."""
        return f"/api/v1/api-keys/{api_key_id}/regenerate"

    # User Management
    USERS_ME = "/api/v1/users/me"
    USERS = "/api/v1/users/"

    @staticmethod
    def user_envhub_role(user_id: str) -> str:
        """Get/update user envhub role endpoint."""
        return f"/api/v1/users/{user_id}/envhub-role"

    @staticmethod
    def user_status(user_id: str) -> str:
        """Update user status endpoint."""
        return f"/api/v1/users/{user_id}/status"

