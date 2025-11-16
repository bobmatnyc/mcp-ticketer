# Bulletproof Ticket Creation Guide

**Version**: 0.2.0+  
**Date**: 2025-10-24  
**Status**: ✅ **COMPREHENSIVE CONFIGURATION GUIDE**

## 🎯 **The Problem**

Users like Auggie are experiencing issues where MCP Ticketer creates tickets in its internal system (AITrackdown) instead of the intended external system (Linear, GitHub, JIRA). This happens because the adapter selection isn't properly configured.

## 🔧 **The Solution**

MCP Ticketer v0.2.0+ includes **bulletproof adapter selection** with multiple configuration methods and comprehensive diagnostics.

## 🚀 **Quick Fix for Auggie**

### **Step 1: Create .env.local File**
```bash
# Create .env.local file with Linear configuration
cat > .env.local << EOF
MCP_TICKETER_ADAPTER=linear
LINEAR_API_KEY=lin_api_YOUR_LINEAR_API_KEY_HERE
LINEAR_TEAM_ID=02d15669-7351-4451-9719-807576c16049
EOF
```

### **Step 2: Verify Configuration**
```bash
# Run diagnostics to check configuration
mcp-ticketer diagnose

# Test ticket creation
mcp-ticketer create "Test ticket from MCP Ticketer"

# Verify in your external system (Linear, GitHub, etc.)
```

### **Step 3: Restart MCP Client**
```bash
# Restart Auggie or your MCP client to pick up new configuration
# The .env.local file will be automatically loaded by MCP Ticketer
```

## 📋 **Complete Configuration Guide**

### **Configuration Priority (Highest to Lowest)**

1. **Command Line Arguments** (Highest Priority)
2. **.env/.env.local Files** (Recommended for MCP)
3. **Project Configuration Files**
4. **Global Configuration Files**
5. **Auto-Discovery from existing .env files**
6. **Default (aitrackdown)** (Lowest Priority)

### **Method 1: .env Files (Recommended for MCP)**

#### **Linear Configuration (.env.local)**
```bash
# .env.local
MCP_TICKETER_ADAPTER=linear
LINEAR_API_KEY=lin_api_YOUR_LINEAR_API_KEY_HERE
LINEAR_TEAM_ID=02d15669-7351-4451-9719-807576c16049

# Optional
LINEAR_TEAM_KEY=BTA  # Alternative to team ID
LINEAR_API_URL=https://api.linear.app/graphql  # Custom URL
```

#### **GitHub Configuration (.env.local)**
```bash
# .env.local
MCP_TICKETER_ADAPTER=github
GITHUB_TOKEN=ghp_your_token_here
GITHUB_OWNER=your_username
GITHUB_REPO=your_repository

# Optional
GITHUB_API_URL=https://api.github.com  # For GitHub Enterprise
```

#### **JIRA Configuration (.env.local)**
```bash
# .env.local
MCP_TICKETER_ADAPTER=jira
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_api_token

# Optional
JIRA_PROJECT_KEY=PROJ  # Default project
```

#### **AITrackdown Configuration (.env.local)**
```bash
# .env.local - this is the default
MCP_TICKETER_ADAPTER=aitrackdown
MCP_TICKETER_BASE_PATH=.aitrackdown  # Custom path
```

### **Method 2: Configuration Files**

Create `.env.local` (highest priority) or `.env` in your project:

```bash
# .env.local
MCP_TICKETER_ADAPTER=linear
LINEAR_API_KEY=lin_api_YOUR_LINEAR_API_KEY_HERE
LINEAR_TEAM_ID=02d15669-7351-4451-9719-807576c16049
```

### **Method 3: Configuration Files**

#### **Project Configuration**
Create `.mcp-ticketer/config.json`:
```json
{
  "default_adapter": "linear",
  "adapters": {
    "linear": {
      "api_key": "lin_api_YOUR_LINEAR_API_KEY_HERE",
      "team_id": "02d15669-7351-4451-9719-807576c16049"
    }
  }
}
```

#### **Global Configuration**
Create `~/.mcp-ticketer/config.json`:
```json
{
  "default_adapter": "linear",
  "adapters": {
    "linear": {
      "api_key": "lin_api_YOUR_LINEAR_API_KEY_HERE",
      "team_id": "02d15669-7351-4451-9719-807576c16049"
    }
  }
}
```

### **Method 4: Command Line**
```bash
# Override adapter for single command
mcp-ticketer --adapter linear create "Test ticket"

# Start MCP server with specific adapter
mcp-ticketer serve --adapter linear
```

## 🔍 **Diagnostics and Troubleshooting**

### **Run Diagnostics**
```bash
# Comprehensive configuration check
mcp-ticketer diagnose
```

This will show:
- ✅ Environment variables status
- ✅ Configuration files found
- ✅ Adapter discovery results
- ✅ Adapter instantiation test
- ✅ Specific recommendations

### **Common Issues and Solutions**

#### **Issue 1: Tickets Created in Wrong System**
**Symptom**: Tickets appear in AITrackdown instead of Linear/GitHub/JIRA

**Solution**:
```bash
# Check current adapter
mcp-ticketer diagnose

# Set correct adapter
export MCP_TICKETER_ADAPTER=linear  # or github, jira

# Verify
mcp-ticketer create "Test ticket"
```

#### **Issue 2: Authentication Errors**
**Symptom**: "Authentication failed" or "Invalid credentials"

**Solution**:
```bash
# Check credentials
echo $LINEAR_API_KEY  # Should show your API key
echo $LINEAR_TEAM_ID  # Should show your team ID

# Test credentials
mcp-ticketer diagnose

# Regenerate API key if needed
```

#### **Issue 3: Team Not Found**
**Symptom**: "Team with key 'XXX' not found"

**Solution**:
```bash
# Use team ID instead of team key
export LINEAR_TEAM_ID=02d15669-7351-4451-9719-807576c16049

# Or verify team key
export LINEAR_TEAM_KEY=BTA  # Your actual team key
```

#### **Issue 4: MCP Server Not Using Environment**
**Symptom**: MCP server ignores environment variables

**Solution**: MCP Ticketer v0.2.0+ automatically checks environment variables. Restart your MCP client (Claude, Auggie, etc.) after setting variables.

## 🎯 **For Auggie Specifically**

### **Quick Setup**
```bash
# 1. Set environment variables
export MCP_TICKETER_ADAPTER=linear
export LINEAR_API_KEY=lin_api_YOUR_LINEAR_API_KEY_HERE
export LINEAR_TEAM_ID=02d15669-7351-4451-9719-807576c16049

# 2. Verify configuration
mcp-ticketer diagnose

# 3. Test ticket creation
mcp-ticketer create "Test from Auggie"

# 4. Check Linear to confirm ticket appears
```

### **Permanent Setup**
Add to your shell profile (`.bashrc`, `.zshrc`, etc.):
```bash
# Linear configuration for MCP Ticketer
export MCP_TICKETER_ADAPTER=linear
export LINEAR_API_KEY=lin_api_YOUR_LINEAR_API_KEY_HERE
export LINEAR_TEAM_ID=02d15669-7351-4451-9719-807576c16049
```

### **Auggie MCP Configuration**
If using Auggie with MCP, ensure your `~/.augment/settings.json` includes the environment variables:
```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "mcp_ticketer.mcp.server"],
      "env": {
        "MCP_TICKETER_ADAPTER": "linear",
        "LINEAR_API_KEY": "lin_api_YOUR_LINEAR_API_KEY_HERE",
        "LINEAR_TEAM_ID": "02d15669-7351-4451-9719-807576c16049"
      }
    }
  }
}
```

**Note**: For Auggie, the simplified `mcp-ticketer mcp` command is available but configuration must be set in `~/.augment/settings.json` for MCP integration.

## ✅ **Verification Steps**

### **1. Check Configuration**
```bash
mcp-ticketer diagnose
```

### **2. Test Ticket Creation**
```bash
mcp-ticketer create "Test ticket - $(date)"
```

### **3. Verify in External System**
- **Linear**: Check your Linear workspace for the new ticket
- **GitHub**: Check your repository's Issues tab
- **JIRA**: Check your JIRA project

### **4. Test via MCP**
If using with AI clients (Claude, Auggie), ask them to:
```
Create a ticket titled "MCP Test - [current time]" with description "Testing MCP Ticketer configuration"
```

Then verify the ticket appears in your external system, not just in MCP Ticketer's response.

## 🚨 **Emergency Troubleshooting**

### **If Nothing Works**
```bash
# 1. Reset to defaults
unset MCP_TICKETER_ADAPTER
rm -f .env.local .env
rm -rf .mcp-ticketer

# 2. Start fresh with explicit configuration
export MCP_TICKETER_ADAPTER=linear
export LINEAR_API_KEY=your_key_here
export LINEAR_TEAM_ID=your_team_id_here

# 3. Test immediately
mcp-ticketer diagnose
mcp-ticketer create "Emergency test"

# 4. Check Linear/GitHub/JIRA for the ticket
```

### **Get Help**
```bash
# Show all available commands
mcp-ticketer --help

# Show adapter-specific help
mcp-ticketer init --help

# Run comprehensive diagnostics
mcp-ticketer diagnose

# Check version (should be 0.2.0+)
mcp-ticketer --version
```

## 🏆 **Success Indicators**

You'll know it's working when:
- ✅ `mcp-ticketer diagnose` shows green checkmarks
- ✅ `mcp-ticketer create "test"` creates tickets in your external system
- ✅ AI clients (Auggie, Claude) create tickets that appear in Linear/GitHub/JIRA
- ✅ No tickets appear in `.aitrackdown` folder (unless that's your intended adapter)

## 📞 **Support**

If you're still having issues:
1. Run `mcp-ticketer diagnose` and share the output
2. Check MCP Ticketer version: `mcp-ticketer --version` (should be 0.2.0+)
3. Verify your API credentials work with direct API calls
4. Create an issue with diagnostic output and configuration details

**MCP Ticketer v0.2.0+ makes ticket creation bulletproof!** 🚀
