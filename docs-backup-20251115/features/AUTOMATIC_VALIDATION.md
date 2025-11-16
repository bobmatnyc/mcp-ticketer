# Automatic Configuration Validation

## Overview

The `mcp-ticketer init` command now includes automatic validation of adapter credentials after configuration is saved. This ensures your setup is working before you try to create tickets.

## How It Works

### 1. Configuration Save
First, the init command saves your adapter configuration to `.mcp-ticketer/config.json`

### 2. Automatic Validation
The command then validates your credentials by:
- Checking API key format (where applicable)
- Testing authentication with the adapter service
- Verifying access to teams/projects/repositories

### 3. Validation Results

#### ✅ Valid Configuration
If validation passes, you'll see:
```
🔍 Validating configuration...
✓ Configuration validated successfully!
```

Setup proceeds to show next steps.

#### ❌ Invalid Configuration
If issues are detected, you'll see:
```
🔍 Validating configuration...
⚠️  Configuration validation found issues:
  ❌ Invalid Linear API key format (should start with 'lin_api_')

What would you like to do?
1. Re-enter configuration values (fix issues)
2. Continue anyway (skip validation)
3. Exit (fix manually later)
```

### 4. User Options

**Option 1: Re-enter Configuration**
- Prompts you to enter credentials again
- Runs validation after each retry
- You get up to 3 retry attempts
- If validation still fails after 3 retries, setup completes with the last configuration

**Option 2: Continue Anyway**
- Skips validation and completes setup
- Useful if you want to configure manually later
- You can run `mcp-ticketer doctor` to validate later

**Option 3: Exit**
- Exits without completing setup
- Configuration is saved but not validated
- Run `mcp-ticketer doctor` when you're ready to test

### 5. Exit Anytime
Press Ctrl+C at any prompt to cancel the entire init process.

## Validation Checks by Adapter

### Linear
- ✅ API key starts with `lin_api_`
- ✅ API authentication successful
- ✅ Team access verified

### JIRA
- ✅ Server URL accessible
- ✅ API token authentication successful
- ✅ Project access verified (if project specified)

### GitHub
- ✅ Token format valid
- ✅ Repository accessible
- ✅ Authentication successful

### AITrackdown
- ✅ Configuration structure valid
- ℹ️ No credentials needed (local file system)

## Examples

### Example 1: Valid Configuration
```bash
$ mcp-ticketer init --adapter linear
Enter your Linear API key: lin_api_1234...
Team URL, key, or ID: ENG

✓ Initialized with linear adapter
🔍 Validating configuration...
✓ Configuration validated successfully!

🎉 Setup Complete!
```

### Example 2: Invalid Credentials → Retry → Success
```bash
$ mcp-ticketer init --adapter linear
Enter your Linear API key: bad_key

✓ Initialized with linear adapter
🔍 Validating configuration...
⚠️  Configuration validation found issues:
  ❌ Invalid Linear API key format (should start with 'lin_api_')

What would you like to do?
1. Re-enter configuration values (fix issues)
2. Continue anyway (skip validation)
3. Exit (fix manually later)
Select option (1-3) [1]: 1

Retry 1/3 - Re-entering configuration...
Enter your Linear API key: lin_api_correct_key_here

🔍 Validating configuration...
✓ Configuration validated successfully!

🎉 Setup Complete!
```

### Example 3: Continue Anyway
```bash
$ mcp-ticketer init --adapter github
Enter GitHub token: ghp_temporary_testing_token

✓ Initialized with github adapter
🔍 Validating configuration...
⚠️  Configuration validation found issues:
  ❌ GitHub authentication failed

What would you like to do?
Select option (1-3) [1]: 2

⚠️  Continuing with potentially invalid configuration.
You can validate later with: mcp-ticketer doctor

🎉 Setup Complete!
```

## Manual Validation

You can always manually validate your configuration later:

```bash
mcp-ticketer doctor
```

The doctor command runs comprehensive diagnostics including credential validation.

## Troubleshooting

### Validation Always Fails
- Double-check your credentials in the adapter's web interface
- Verify network connectivity to the adapter service
- Check if your API key has the necessary permissions
- Try running `mcp-ticketer doctor` for more detailed diagnostics

### Want to Skip Validation
- Select option 2 (Continue anyway) when prompted
- Or use environment variables and the adapter will auto-detect valid credentials

### Configuration Saved But Not Validated
- If you exit during validation, config is saved
- Run `mcp-ticketer doctor` to validate later
- Or run `mcp-ticketer init` again to reconfigure

## Benefits

✅ **Catch issues early**: Know immediately if credentials are invalid
✅ **Interactive fixes**: Correct mistakes without starting over
✅ **Flexible workflow**: Skip validation if needed
✅ **Clear feedback**: Specific error messages for each issue
✅ **Automated**: No need to remember to run `doctor` command

## Performance

Validation typically takes:
- Linear: 4-5 seconds (includes retry logic)
- JIRA: ~1 second
- GitHub: ~1 second
- AITrackdown: Instant (no network calls)
