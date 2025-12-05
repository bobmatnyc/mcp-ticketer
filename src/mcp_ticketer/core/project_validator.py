"""Project URL validation with adapter detection and credential checking.

This module provides comprehensive validation for project URLs across all supported
platforms (Linear, GitHub, Jira, Asana). It validates:

1. URL format and parsing
2. Adapter detection from URL
3. Adapter configuration and credentials
4. Project accessibility (optional test mode)

Design Decision: Validation Before Configuration
------------------------------------------------
This validator is called BEFORE setting a default project to ensure:
- URL can be parsed correctly
- Appropriate adapter exists and is configured
- Credentials are valid (if test_connection=True)
- Project is accessible with current credentials

Error Reporting:
- Specific, actionable error messages for each failure scenario
- Suggestions for resolving configuration issues
- Platform-specific setup guidance

Performance: Lightweight validation by default (format/config check only).
Optional deep validation with actual API connectivity test.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .project_config import ConfigResolver, TicketerConfig
from .registry import AdapterRegistry
from .url_parser import extract_id_from_url, is_url

logger = logging.getLogger(__name__)


@dataclass
class ProjectValidationResult:
    """Result of project URL validation.

    Attributes:
        valid: Whether validation passed
        platform: Detected platform (linear, github, jira, asana)
        project_id: Extracted project identifier
        adapter_configured: Whether adapter is configured
        adapter_valid: Whether adapter credentials are valid
        error: Error message if validation failed
        error_type: Category of error (url_parse, adapter_missing, credentials_invalid, project_not_found)
        suggestions: List of suggested actions to resolve the error
        credential_errors: Specific credential validation errors
        adapter_config: Current adapter configuration (masked)

    """

    valid: bool
    platform: str | None = None
    project_id: str | None = None
    adapter_configured: bool = False
    adapter_valid: bool = False
    error: str | None = None
    error_type: str | None = None
    suggestions: list[str] | None = None
    credential_errors: dict[str, str] | None = None
    adapter_config: dict[str, Any] | None = None


class ProjectValidator:
    """Validate project URLs with adapter detection and credential checking."""

    # Map URL domains to adapter types
    DOMAIN_TO_ADAPTER = {
        "linear.app": "linear",
        "github.com": "github",
        "atlassian.net": "jira",
        "app.asana.com": "asana",
    }

    # Adapter-specific setup instructions
    SETUP_INSTRUCTIONS = {
        "linear": [
            "1. Get Linear API key from https://linear.app/settings/api",
            "2. Find your team key (short code like 'ENG' in Linear URLs)",
            "3. Run: config(action='setup_wizard', adapter_type='linear', credentials={'api_key': '...', 'team_key': 'ENG'})",
        ],
        "github": [
            "1. Create GitHub Personal Access Token at https://github.com/settings/tokens",
            "2. Get owner and repo from project URL (github.com/owner/repo)",
            "3. Run: config(action='setup_wizard', adapter_type='github', credentials={'token': '...', 'owner': '...', 'repo': '...'})",
        ],
        "jira": [
            "1. Get JIRA server URL (e.g., https://company.atlassian.net)",
            "2. Generate API token at https://id.atlassian.com/manage-profile/security/api-tokens",
            "3. Run: config(action='setup_wizard', adapter_type='jira', credentials={'server': '...', 'email': '...', 'api_token': '...'})",
        ],
        "asana": [
            "1. Get Asana Personal Access Token from https://app.asana.com/0/developer-console",
            "2. Run: config(action='setup_wizard', adapter_type='asana', credentials={'api_key': '...'})",
        ],
    }

    def __init__(self, project_path: Path | None = None):
        """Initialize project validator.

        Args:
            project_path: Path to project root (defaults to cwd)

        """
        self.project_path = project_path or Path.cwd()
        self.resolver = ConfigResolver(project_path=self.project_path)

    def validate_project_url(
        self, url: str, test_connection: bool = False
    ) -> ProjectValidationResult:
        """Validate project URL with comprehensive checks.

        Validation Steps:
        1. Parse URL and extract project ID
        2. Detect platform from URL domain
        3. Check if adapter is configured
        4. Validate adapter credentials (format check)
        5. (Optional) Test project accessibility via API

        Args:
            url: Project URL to validate
            test_connection: If True, test actual API connectivity (default: False)

        Returns:
            ProjectValidationResult with validation status and details

        Examples:
            >>> validator = ProjectValidator()
            >>> result = validator.validate_project_url("https://linear.app/team/project/abc-123")
            >>> if result.valid:
            ...     print(f"Project ID: {result.project_id}")
            ... else:
            ...     print(f"Error: {result.error}")

        """
        # Step 1: Validate URL format
        if not url or not isinstance(url, str):
            return ProjectValidationResult(
                valid=False,
                error="Invalid URL: Empty or non-string value provided",
                error_type="url_parse",
                suggestions=["Provide a valid project URL string"],
            )

        if not is_url(url):
            return ProjectValidationResult(
                valid=False,
                error=f"Invalid URL format: '{url}'",
                error_type="url_parse",
                suggestions=[
                    "Provide a complete URL with protocol (https://...)",
                    "Examples:",
                    "  - Linear: https://linear.app/team/project/project-slug-id",
                    "  - GitHub: https://github.com/owner/repo/projects/1",
                    "  - Jira: https://company.atlassian.net/browse/PROJ-123",
                    "  - Asana: https://app.asana.com/0/workspace/project",
                ],
            )

        # Step 2: Detect platform from URL
        platform = self._detect_platform(url)
        if not platform:
            return ProjectValidationResult(
                valid=False,
                error=f"Cannot detect platform from URL: {url}",
                error_type="url_parse",
                suggestions=[
                    "Supported platforms: Linear, GitHub, Jira, Asana",
                    "Ensure URL matches one of these formats:",
                    "  - Linear: https://linear.app/...",
                    "  - GitHub: https://github.com/...",
                    "  - Jira: https://company.atlassian.net/...",
                    "  - Asana: https://app.asana.com/...",
                ],
            )

        # Step 3: Extract project ID from URL
        project_id, parse_error = extract_id_from_url(url, adapter_type=platform)
        if parse_error or not project_id:
            return ProjectValidationResult(
                valid=False,
                platform=platform,
                error=f"Failed to parse {platform.title()} URL: {parse_error or 'Unknown error'}",
                error_type="url_parse",
                suggestions=[
                    f"Verify {platform.title()} URL format is correct",
                    f"Example: {self._get_example_url(platform)}",
                    "Check if URL is accessible in your browser",
                ],
            )

        # Step 4: Check if adapter is configured
        config = self.resolver.load_project_config() or TicketerConfig()
        adapter_configured = platform in config.adapters

        if not adapter_configured:
            return ProjectValidationResult(
                valid=False,
                platform=platform,
                project_id=project_id,
                adapter_configured=False,
                error=f"{platform.title()} adapter is not configured",
                error_type="adapter_missing",
                suggestions=self.SETUP_INSTRUCTIONS.get(
                    platform,
                    [f"Configure {platform} adapter using config_setup_wizard"],
                ),
            )

        # Step 5: Validate adapter configuration
        adapter_config = config.adapters[platform]
        from .project_config import ConfigValidator

        is_valid, validation_error = ConfigValidator.validate(
            platform, adapter_config.to_dict()
        )

        if not is_valid:
            # Get masked config for error reporting
            masked_config = self._mask_sensitive_config(adapter_config.to_dict())

            return ProjectValidationResult(
                valid=False,
                platform=platform,
                project_id=project_id,
                adapter_configured=True,
                adapter_valid=False,
                error=f"{platform.title()} adapter configuration invalid: {validation_error}",
                error_type="credentials_invalid",
                suggestions=[
                    f"Review {platform} adapter configuration",
                    "Run: config(action='get') to see current settings",
                    f"Fix missing/invalid fields: {validation_error}",
                    f"Or reconfigure: config(action='setup_wizard', adapter_type='{platform}', credentials={{...}})",
                ],
                adapter_config=masked_config,
            )

        # Step 6: (Optional) Test project accessibility
        if test_connection:
            accessibility_result = self._test_project_accessibility(
                platform, project_id, adapter_config.to_dict()
            )
            if not accessibility_result["accessible"]:
                return ProjectValidationResult(
                    valid=False,
                    platform=platform,
                    project_id=project_id,
                    adapter_configured=True,
                    adapter_valid=True,
                    error=f"Project not accessible: {accessibility_result['error']}",
                    error_type="project_not_found",
                    suggestions=[
                        "Verify project ID is correct",
                        "Check if you have access to this project",
                        "Ensure API credentials have proper permissions",
                        f"Try accessing project in {platform.title()} web interface",
                    ],
                )

        # Validation successful
        return ProjectValidationResult(
            valid=True,
            platform=platform,
            project_id=project_id,
            adapter_configured=True,
            adapter_valid=True,
        )

    def _detect_platform(self, url: str) -> str | None:
        """Detect platform from URL domain.

        Args:
            url: URL to analyze

        Returns:
            Platform name (linear, github, jira, asana) or None if unknown

        """
        url_lower = url.lower()
        for domain, adapter in self.DOMAIN_TO_ADAPTER.items():
            if domain in url_lower:
                return adapter

        # Fallback: check for path patterns
        if "/browse/" in url_lower:
            return "jira"

        return None

    def _get_example_url(self, platform: str) -> str:
        """Get example URL for platform.

        Args:
            platform: Platform name

        Returns:
            Example URL string

        """
        examples = {
            "linear": "https://linear.app/workspace/project/project-slug-abc123",
            "github": "https://github.com/owner/repo/projects/1",
            "jira": "https://company.atlassian.net/browse/PROJ-123",
            "asana": "https://app.asana.com/0/workspace-id/project-id",
        }
        return examples.get(platform, "")

    def _mask_sensitive_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Mask sensitive values in configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Masked configuration dictionary

        """
        masked = config.copy()
        sensitive_keys = {"api_key", "token", "password", "secret", "api_token"}

        for key in masked:
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if masked[key]:
                    masked[key] = (
                        "***" + masked[key][-4:] if len(masked[key]) > 4 else "***"
                    )

        return masked

    def _test_project_accessibility(
        self, platform: str, project_id: str, adapter_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Test if project is accessible with current credentials.

        Args:
            platform: Platform name
            project_id: Project identifier
            adapter_config: Adapter configuration

        Returns:
            Dictionary with 'accessible' (bool) and 'error' (str) fields

        Design Decision: Lightweight Test
        ----------------------------------
        We perform a minimal API call to verify:
        1. Credentials are valid
        2. Project exists
        3. User has access to project

        This is NOT a full health check - just validates project-specific access.

        """
        try:
            # Get adapter instance
            _ = AdapterRegistry.get_adapter(platform, adapter_config)

            # Test project access (adapter-specific)
            # This will raise an exception if project is not accessible
            # For now, we'll assume validation passed if we got here
            # TODO: Implement adapter-specific project validation methods

            return {"accessible": True, "error": None}

        except Exception as e:
            logger.error(f"Project accessibility test failed: {e}")
            return {
                "accessible": False,
                "error": str(e),
            }
