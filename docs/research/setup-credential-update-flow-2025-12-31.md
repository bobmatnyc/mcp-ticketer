# Research: Setup Command Credential Update Flow

**Date**: 2025-12-31
**Issue**: #53 - Setup command should allow updating credentials without full re-init
**Researcher**: Claude Code Research Agent

## Executive Summary

The `mcp-ticketer setup` command currently prompts for default values (user, epic, tags) when keeping existing settings, but does NOT offer to update adapter credentials (API keys, tokens). This research identifies the exact location and pattern needed to add credential update prompting.

## Current Flow Analysis

### File: `src/mcp_ticketer/cli/setup_command.py`

#### Key Logic Points

**Lines 258-269: "Keep existing settings?" decision**
```python
if config_valid:
    console.print("[green]✓[/green] Configuration detected")
    console.print(f"[dim]  Adapter: {current_adapter}[/dim]")
    console.print(f"[dim]  Location: {config_path}[/dim]\n")

    # Offer to reconfigure
    if not typer.confirm(
        "Configuration already exists. Keep existing settings?", default=True
    ):
        console.print("[cyan]Re-initializing configuration...[/cyan]\n")
        force_reinit = True
        config_valid = False
```

**Lines 339-348: Default values update when config_valid=True**
```python
else:
    console.print("[green]✓ Step 1/2: Adapter already configured[/green]\n")

    # Even though adapter is configured, prompt for default values
    # This handles the case where credentials exist but defaults were never set
    _prompt_and_update_default_values(config_path, current_adapter, console)

    # Update existing MCP configurations with credentials
    _update_mcp_json_credentials(proj_path, console)
```

**Lines 496-556: `_prompt_and_update_default_values` function**
```python
def _prompt_and_update_default_values(
    config_path: Path, adapter_type: str, console: Console
) -> None:
    """Prompt user for default values and update configuration.

    This function handles the case where adapter credentials exist but
    default values (default_user, default_epic, default_project, default_tags)
    need to be set or updated.
    """
    from .configure import prompt_default_values

    try:
        # Load current config to get existing default values
        with open(config_path) as f:
            existing_config = json.load(f)

        existing_defaults = {
            "default_user": existing_config.get("default_user"),
            "default_epic": existing_config.get("default_epic"),
            "default_project": existing_config.get("default_project"),
            "default_tags": existing_config.get("default_tags"),
        }

        # Prompt for default values
        console.print("[bold]Configure Default Values[/bold] (for ticket creation)\n")
        default_values = prompt_default_values(
            adapter_type=adapter_type, existing_values=existing_defaults
        )

        # Update config with new default values
        if default_values:
            existing_config.update(default_values)
            with open(config_path, "w") as f:
                json.dump(existing_config, f, indent=2)
            console.print("\n[green]✓ Default values updated[/green]\n")
        else:
            console.print("\n[dim]No default values set[/dim]\n")
```

## Credential Prompting Patterns in `configure.py`

### Linear Credential Prompt Pattern (Lines 492-514)

```python
def prompt_new_api_key() -> dict[str, str]:
    """Re-prompt for API key on validation failure."""
    new_key = Prompt.ask("Linear API Key", password=True)
    return {"api_key": new_key}

try:
    credentials = {"api_key": final_api_key}
    api_key_validated = _validate_api_credentials(
        "linear",
        credentials,
        credential_prompter=prompt_new_api_key,
    )
    # Update final_api_key with potentially updated value
    final_api_key = credentials["api_key"]
except typer.Exit:
    # User cancelled, propagate the exit
    raise
except Exception as e:
    console.print(f"[red]Validation error: {e}[/red]")
    retry = Confirm.ask("Re-enter API key?", default=True)
    if not retry:
        raise typer.Exit(1) from None
```

### GitHub Credential Prompt Pattern (Lines 1043-1070)

```python
def prompt_new_github_token() -> dict[str, str]:
    """Re-prompt for GitHub token on validation failure."""
    console.print(
        "[dim]Create token at: https://github.com/settings/tokens/new[/dim]"
    )
    console.print(
        "[dim]Required scopes: repo (or public_repo for public repos)[/dim]"
    )
    new_token = Prompt.ask("GitHub Personal Access Token", password=True)
    return {"token": new_token}

try:
    credentials = {"token": final_token}
    github_validated = _validate_api_credentials(
        "github", credentials, credential_prompter=prompt_new_github_token
    )
    # Update final_token with potentially updated value
    final_token = credentials["token"]
except typer.Exit:
    # User cancelled, propagate the exit
    raise
```

### JIRA Credential Prompt Pattern (Lines 825-856)

```python
def prompt_new_jira_credentials() -> dict[str, str]:
    """Re-prompt for JIRA credentials on validation failure."""
    console.print(
        "[dim]Generate token at: https://id.atlassian.com/manage/api-tokens[/dim]"
    )
    new_token = Prompt.ask("JIRA API Token", password=True)
    return {"api_token": new_token}

try:
    credentials = {
        "server": final_server,
        "email": final_email,
        "api_token": final_api_token,
    }
    jira_validated = _validate_api_credentials(
        "jira",
        credentials,
        credential_prompter=prompt_new_jira_credentials,
    )
    # Update final_api_token with potentially updated value
    final_api_token = credentials["api_token"]
except typer.Exit:
    # User cancelled, propagate the exit
    raise
```

## Recommended Implementation Location

**Add new function in `setup_command.py` after line 556:**

```python
def _prompt_and_update_credentials(
    config_path: Path, adapter_type: str, console: Console
) -> None:
    """Prompt user to update adapter credentials.

    This function handles the case where adapter credentials exist but
    user wants to update the token/API key without full re-initialization.

    Args:
        config_path: Path to the configuration file (.mcp-ticketer/config.json)
        adapter_type: Type of adapter (linear, jira, github, aitrackdown)
        console: Rich console for output

    Raises:
        typer.Exit: If configuration cannot be loaded or updated
    """
    from .configure import (
        _validate_api_credentials,
        _mask_sensitive_value,
    )
    from rich.prompt import Confirm, Prompt

    try:
        # Load current config
        with open(config_path) as f:
            config = json.load(f)

        adapter_config = config.get("adapters", {}).get(adapter_type, {})

        # Ask if user wants to update credentials
        console.print("\n[bold]Update Credentials[/bold]\n")

        if not Confirm.ask("Update adapter credentials (token/API key)?", default=False):
            return

        # Adapter-specific credential prompting
        if adapter_type == "linear":
            current_key = adapter_config.get("api_key", "")
            masked = _mask_sensitive_value(current_key) if current_key else "****"

            console.print(f"[dim]Current API key: {masked}[/dim]")
            new_key = Prompt.ask("New Linear API Key (press Enter to keep current)",
                                password=True, default=current_key)

            if new_key != current_key:
                def prompt_new_api_key() -> dict[str, str]:
                    retry_key = Prompt.ask("Linear API Key", password=True)
                    return {"api_key": retry_key}

                credentials = {"api_key": new_key}
                if _validate_api_credentials("linear", credentials,
                                            credential_prompter=prompt_new_api_key):
                    adapter_config["api_key"] = credentials["api_key"]
                    console.print("[green]✓ API key updated and validated[/green]")

        elif adapter_type == "github":
            current_token = adapter_config.get("token", "")
            masked = _mask_sensitive_value(current_token) if current_token else "****"

            console.print(f"[dim]Current token: {masked}[/dim]")
            console.print("[dim]Create token at: https://github.com/settings/tokens/new[/dim]")
            new_token = Prompt.ask("New GitHub Personal Access Token (press Enter to keep current)",
                                  password=True, default=current_token)

            if new_token != current_token:
                def prompt_new_github_token() -> dict[str, str]:
                    retry_token = Prompt.ask("GitHub Personal Access Token", password=True)
                    return {"token": retry_token}

                credentials = {"token": new_token}
                if _validate_api_credentials("github", credentials,
                                            credential_prompter=prompt_new_github_token):
                    adapter_config["token"] = credentials["token"]
                    console.print("[green]✓ Token updated and validated[/green]")

        elif adapter_type == "jira":
            current_token = adapter_config.get("api_token", "")
            masked = _mask_sensitive_value(current_token) if current_token else "****"

            console.print(f"[dim]Current API token: {masked}[/dim]")
            console.print("[dim]Generate token at: https://id.atlassian.com/manage/api-tokens[/dim]")
            new_token = Prompt.ask("New JIRA API Token (press Enter to keep current)",
                                  password=True, default=current_token)

            if new_token != current_token:
                def prompt_new_jira_credentials() -> dict[str, str]:
                    retry_token = Prompt.ask("JIRA API Token", password=True)
                    return {"api_token": retry_token}

                credentials = {
                    "server": adapter_config.get("server", ""),
                    "email": adapter_config.get("email", ""),
                    "api_token": new_token,
                }
                if _validate_api_credentials("jira", credentials,
                                            credential_prompter=prompt_new_jira_credentials):
                    adapter_config["api_token"] = credentials["api_token"]
                    console.print("[green]✓ API token updated and validated[/green]")

        elif adapter_type == "aitrackdown":
            console.print("[dim]AITrackdown adapter has no credentials to update[/dim]")
            return

        # Update config file
        config["adapters"][adapter_type] = adapter_config
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

    except json.JSONDecodeError as e:
        console.print(f"[red]✗ Invalid JSON in configuration file: {e}[/red]\n")
    except OSError as e:
        console.print(f"[red]✗ Could not read/write configuration file: {e}[/red]\n")
    except Exception as e:
        console.print(f"[red]✗ Unexpected error updating credentials: {e}[/red]\n")
```

**Call new function in existing flow (line 344, right after line 344):**

```python
else:
    console.print("[green]✓ Step 1/2: Adapter already configured[/green]\n")

    # Offer to update credentials
    _prompt_and_update_credentials(config_path, current_adapter, console)

    # Even though adapter is configured, prompt for default values
    # This handles the case where credentials exist but defaults were never set
    _prompt_and_update_default_values(config_path, current_adapter, console)

    # Update existing MCP configurations with credentials
    _update_mcp_json_credentials(proj_path, console)
```

## Implementation Checklist

- [ ] Create `_prompt_and_update_credentials()` function in `setup_command.py`
- [ ] Add call to `_prompt_and_update_credentials()` at line 344 (before default values prompt)
- [ ] Import required functions from `configure.py`:
  - `_validate_api_credentials`
  - `_mask_sensitive_value`
- [ ] Import `Confirm` and `Prompt` from `rich.prompt`
- [ ] Add test coverage for credential update flow
- [ ] Update documentation to mention credential update feature

## Edge Cases to Handle

1. **Validation failure**: User enters invalid credentials multiple times
   - Current pattern: Offer retry with `credential_prompter` callback
   - Fallback: Allow saving unvalidated credentials with warning

2. **Network errors during validation**: API unreachable
   - Current pattern: Show timeout/network error, offer retry
   - Fallback: Skip validation and save with warning

3. **User cancels**: Presses Ctrl+C during credential prompt
   - Current pattern: Catch `typer.Abort` and exit gracefully
   - Keep existing credentials unchanged

4. **AITrackdown adapter**: No credentials to update
   - Show informational message and skip credential prompt

5. **Masked value comparison**: User presses Enter to keep current
   - Compare new value with unmasked current value
   - Only update if different

## Testing Strategy

1. **Unit Tests** (`tests/cli/test_setup_command.py`):
   - Test credential update prompt appears when config_valid=True
   - Test credential validation with mocked API calls
   - Test credential update saves to config file
   - Test user cancellation preserves existing credentials

2. **Integration Tests**:
   - Test full setup flow with credential update
   - Test MCP config update after credential change
   - Test validation failure and retry flow

3. **Manual Testing Scenarios**:
   - Setup with existing Linear config → update API key
   - Setup with existing GitHub config → update token
   - Setup with existing JIRA config → update API token
   - Setup with AITrackdown → verify no credential prompt

## Dependencies and Imports

**Existing imports in `setup_command.py`:**
- ✅ `json`, `subprocess`, `sys`, `Path`
- ✅ `typer`, `Console` from rich

**New imports needed:**
- ✅ `Confirm`, `Prompt` from `rich.prompt` (already imported in configure.py)
- ✅ `_validate_api_credentials` from `.configure`
- ✅ `_mask_sensitive_value` from `.configure`

## Related Functions

**Functions to reuse from `configure.py`:**
- `_validate_api_credentials()` (line 74): API validation with retry logic
- `_mask_sensitive_value()` (line 54): Mask tokens for display
- Credential prompter callbacks: Pattern used in Linear, GitHub, JIRA configs

**Existing functions in `setup_command.py`:**
- `_prompt_and_update_default_values()` (line 496): Similar pattern for default values
- `_update_mcp_json_credentials()` (line 621): Updates MCP configs with new credentials

## File Locations

**Primary file**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/setup_command.py`
**Supporting file**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/configure.py`
**Test file**: `/Users/masa/Projects/mcp-ticketer/tests/cli/test_setup_command.py`

## Issue Reference

**GitHub Issue**: #53
**Problem**: Setup command prompts for default values but not credentials when keeping existing settings
**Expected Behavior**: After user selects "Keep existing settings? Yes", offer to:
1. Update credentials (NEW - this research)
2. Update default values (EXISTING - already implemented)

## Next Steps

1. Implement `_prompt_and_update_credentials()` function
2. Add function call in existing flow (line 344)
3. Write unit tests for new functionality
4. Test manually with all adapters (Linear, GitHub, JIRA, AITrackdown)
5. Update user documentation
6. Create pull request referencing issue #53
