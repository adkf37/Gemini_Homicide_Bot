import os
from typing import Any, Optional

from google.api_core import exceptions as google_exceptions
from google.auth import exceptions as auth_exceptions


def resolve_gemini_api_key(config: Any) -> str:
    """Resolve the Gemini API key from Secret Manager or a local env var."""
    api_key_env = config.get("model.api_key_env", "GOOGLE_API_KEY")
    secret_ref_env = config.get("model.api_key_secret_ref_env", "GOOGLE_API_KEY_SECRET_REF")
    secret_ref = os.getenv(secret_ref_env) or config.get("model.api_key_secret_ref")

    if secret_ref:
        return _access_secret(
            secret_ref=secret_ref,
            version=config.get("model.api_key_secret_version", "latest"),
            project_id=_resolve_project_id(config),
        )

    api_key = os.getenv(api_key_env)
    if api_key:
        return api_key

    raise EnvironmentError(
        "Missing Gemini API key. Configure Secret Manager with "
        f"'{secret_ref_env}' or set '{api_key_env}' for local development."
    )


def _resolve_project_id(config: Any) -> Optional[str]:
    configured_project = config.get("model.api_key_secret_project")
    if configured_project:
        return configured_project

    for env_name in ("GCP_PROJECT_ID", "GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "GCP_PROJECT"):
        project_id = os.getenv(env_name)
        if project_id:
            return project_id

    return None


def _access_secret(secret_ref: str, version: str, project_id: Optional[str]) -> str:
    resource_name = _secret_resource_name(secret_ref, version, project_id)
    client = _secret_manager_client()

    try:
        response = client.access_secret_version(request={"name": resource_name})
    except auth_exceptions.DefaultCredentialsError as exc:
        raise EnvironmentError(
            "Could not authenticate to Google Secret Manager. "
            "Run with Google Application Default Credentials or set GOOGLE_API_KEY locally."
        ) from exc
    except google_exceptions.NotFound as exc:
        raise EnvironmentError(f"Gemini API key secret was not found: {resource_name}") from exc
    except google_exceptions.PermissionDenied as exc:
        raise EnvironmentError(
            f"Permission denied reading Gemini API key secret: {resource_name}"
        ) from exc

    api_key = response.payload.data.decode("UTF-8").strip()
    if not api_key:
        raise EnvironmentError(f"Gemini API key secret is empty: {resource_name}")

    return api_key


def _secret_resource_name(secret_ref: str, version: str, project_id: Optional[str]) -> str:
    if secret_ref.startswith("projects/"):
        if "/versions/" in secret_ref:
            return secret_ref
        return f"{secret_ref}/versions/{version}"

    if not project_id:
        raise EnvironmentError(
            "GOOGLE_API_KEY_SECRET_REF is a short secret name, but no Google Cloud "
            "project id was configured. Set GCP_PROJECT_ID or use a full "
            "'projects/<project>/secrets/<secret>' secret reference."
        )

    return f"projects/{project_id}/secrets/{secret_ref}/versions/{version}"


def _secret_manager_client():
    try:
        from google.cloud import secretmanager
    except ImportError as exc:
        raise EnvironmentError(
            "google-cloud-secret-manager is required when GOOGLE_API_KEY_SECRET_REF is set. "
            "Install dependencies with 'pip install -r requirements.txt'."
        ) from exc

    return secretmanager.SecretManagerServiceClient()
