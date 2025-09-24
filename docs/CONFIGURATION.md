# MCP Ticketer Configuration Guide

Complete guide to configuring MCP Ticketer for all supported environments and use cases.

## Table of Contents

- [Configuration Overview](#configuration-overview)
- [Configuration File Format](#configuration-file-format)
- [Environment Variables](#environment-variables)
- [Adapter-Specific Configuration](#adapter-specific-configuration)
- [Advanced Configuration](#advanced-configuration)
- [Security Best Practices](#security-best-practices)
- [Multi-Project Setup](#multi-project-setup)
- [Troubleshooting Configuration](#troubleshooting-configuration)

## Configuration Overview

MCP Ticketer uses a layered configuration system with the following precedence (highest to lowest):

1. **Command-line arguments** (highest priority)
2. **Environment variables**
3. **Configuration files**
4. **Default values** (lowest priority)

### Configuration Locations

| System | Configuration Path |
|--------|--------------------|
| **Linux** | `~/.mcp-ticketer/config.json` |
| **macOS** | `~/.mcp-ticketer/config.json` |
| **Windows** | `%USERPROFILE%\.mcp-ticketer\config.json` |
| **Custom** | Set via `MCP_TICKETER_CONFIG_FILE` environment variable |

### Configuration Initialization

```bash
# Initialize default configuration
mcp-ticket init --adapter aitrackdown

# Initialize with specific options
mcp-ticket init --adapter linear --team-id YOUR_TEAM_ID

# Initialize with custom config location
export MCP_TICKETER_CONFIG_FILE=/path/to/custom/config.json
mcp-ticket init --adapter jira
```

## Configuration File Format

### Basic Structure

```json
{
  "adapter": "linear",
  "config": {
    "team_id": "team-abc123",
    "api_key": "lin_api_xxxxxxxxxxxxx"
  },
  "cache": {
    "enabled": true,
    "ttl": 300,
    "max_size": 1000
  },
  "cli": {
    "default_limit": 10,
    "output_format": "table",
    "colors": true
  },
  "mcp": {
    "server_enabled": true,
    "port": 8765,
    "host": "localhost"
  },
  "logging": {
    "level": "INFO",
    "format": "structured",
    "file": null
  }
}
```

### Configuration Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "adapter": {
      "type": "string",
      "enum": ["aitrackdown", "linear", "jira", "github"],
      "description": "Active ticket system adapter"
    },
    "config": {
      "type": "object",
      "description": "Adapter-specific configuration"
    },
    "cache": {
      "type": "object",
      "properties": {
        "enabled": {"type": "boolean", "default": true},
        "ttl": {"type": "integer", "minimum": 60, "default": 300},
        "max_size": {"type": "integer", "minimum": 10, "default": 1000},
        "cleanup_interval": {"type": "integer", "minimum": 60, "default": 300}
      }
    },
    "cli": {
      "type": "object",
      "properties": {
        "default_limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
        "output_format": {"type": "string", "enum": ["table", "json", "csv"], "default": "table"},
        "colors": {"type": "boolean", "default": true},
        "pager": {"type": "boolean", "default": false},
        "confirm_destructive": {"type": "boolean", "default": true}
      }
    },
    "mcp": {
      "type": "object",
      "properties": {
        "server_enabled": {"type": "boolean", "default": true},
        "port": {"type": "integer", "minimum": 1024, "maximum": 65535, "default": 8765},
        "host": {"type": "string", "default": "localhost"},
        "timeout": {"type": "integer", "minimum": 10, "default": 30}
      }
    },
    "logging": {
      "type": "object",
      "properties": {
        "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR"], "default": "INFO"},
        "format": {"type": "string", "enum": ["simple", "structured", "json"], "default": "structured"},
        "file": {"type": ["string", "null"], "default": null},
        "max_size": {"type": "integer", "minimum": 1024, "default": 10485760}
      }
    }
  },
  "required": ["adapter"]
}
```

## Environment Variables

### Global Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MCP_TICKETER_CONFIG_FILE` | Custom config file path | `~/.mcp-ticketer/config.json` | `/path/to/config.json` |
| `MCP_TICKETER_ADAPTER` | Default adapter type | `aitrackdown` | `linear` |
| `MCP_TICKETER_LOG_LEVEL` | Logging level | `INFO` | `DEBUG` |
| `MCP_TICKETER_CACHE_TTL` | Cache TTL in seconds | `300` | `600` |
| `MCP_TICKETER_CACHE_ENABLED` | Enable caching | `true` | `false` |
| `MCP_TICKETER_CLI_COLORS` | Enable CLI colors | `true` | `false` |

### Cache Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MCP_TICKETER_CACHE_ENABLED` | Enable caching | `true` | `false` |
| `MCP_TICKETER_CACHE_TTL` | Cache TTL (seconds) | `300` | `600` |
| `MCP_TICKETER_CACHE_MAX_SIZE` | Max cache entries | `1000` | `500` |
| `MCP_TICKETER_CACHE_CLEANUP` | Cleanup interval (seconds) | `300` | `600` |

### CLI Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MCP_TICKETER_CLI_LIMIT` | Default result limit | `10` | `25` |
| `MCP_TICKETER_CLI_FORMAT` | Output format | `table` | `json` |
| `MCP_TICKETER_CLI_COLORS` | Enable colors | `true` | `false` |
| `MCP_TICKETER_CLI_PAGER` | Enable pager | `false` | `true` |

### MCP Server Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MCP_TICKETER_SERVER_HOST` | Server host | `localhost` | `0.0.0.0` |
| `MCP_TICKETER_SERVER_PORT` | Server port | `8765` | `9000` |
| `MCP_TICKETER_SERVER_TIMEOUT` | Request timeout | `30` | `60` |

## Adapter-Specific Configuration

### AITrackdown Configuration

```json
{
  "adapter": "aitrackdown",
  "config": {
    "base_path": ".aitrackdown",
    "create_directories": true,
    "file_format": "json",
    "pretty_print": true,
    "backup": {
      "enabled": true,
      "max_backups": 10,
      "interval_minutes": 60,
      "compress": true
    },
    "indexing": {
      "enabled": true,
      "rebuild_on_startup": false,
      "full_text_search": true,
      "index_comments": true
    },
    "validation": {
      "strict_mode": false,
      "require_assignee": false,
      "max_title_length": 255,
      "allowed_tags": null
    },
    "performance": {
      "lazy_loading": true,
      "cache_file_contents": true,
      "concurrent_reads": 10
    }
  }
}
```

**Environment Variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `AITRACKDOWN_BASE_PATH` | Base directory | `.aitrackdown` |
| `AITRACKDOWN_BACKUP_ENABLED` | Enable backups | `true` |
| `AITRACKDOWN_INDEX_ENABLED` | Enable indexing | `true` |

### Linear Configuration

```json
{
  "adapter": "linear",
  "config": {
    "team_id": "team-abc123def456",
    "api_key": "lin_api_1234567890abcdef",
    "endpoint": "https://api.linear.app/graphql",
    "timeout": 30,
    "retry": {
      "max_attempts": 3,
      "backoff_factor": 2,
      "base_delay": 1
    },
    "features": {
      "use_cycles": true,
      "include_estimates": true,
      "sync_labels": true,
      "include_projects": false
    },
    "field_mapping": {
      "priority_mapping": {
        "critical": 1,
        "high": 2,
        "medium": 3,
        "low": 4
      },
      "state_mapping": {
        "open": "Todo",
        "in_progress": "In Progress",
        "ready": "Ready for Review",
        "done": "Done"
      }
    },
    "webhook": {
      "enabled": false,
      "secret": null,
      "url": null
    }
  }
}
```

**Environment Variables:**

| Variable | Description | Required |
|----------|-------------|----------|
| `LINEAR_API_KEY` | Linear API key | ✅ |
| `LINEAR_TEAM_ID` | Team identifier | ✅ |
| `LINEAR_ENDPOINT` | GraphQL endpoint | ❌ |
| `LINEAR_TIMEOUT` | Request timeout | ❌ |

### JIRA Configuration

```json
{
  "adapter": "jira",
  "config": {
    "server": "https://company.atlassian.net",
    "email": "user@company.com",
    "api_token": "ATATT3xFfGF0T...",
    "project_key": "MYPROJ",
    "issue_type": "Task",
    "verify_ssl": true,
    "timeout": 60,
    "retry": {
      "max_attempts": 3,
      "backoff_factor": 1.5,
      "status_codes": [429, 500, 502, 503, 504]
    },
    "field_mapping": {
      "priority_mapping": {
        "critical": "Highest",
        "high": "High",
        "medium": "Medium",
        "low": "Low"
      },
      "custom_fields": {
        "story_points": "customfield_10001",
        "epic_link": "customfield_10002",
        "sprint": "customfield_10003"
      }
    },
    "features": {
      "use_transitions": true,
      "include_subtasks": true,
      "sync_attachments": false,
      "track_time": false
    },
    "jql": {
      "default_filter": "project = MYPROJ AND resolution = Unresolved",
      "max_results": 50,
      "expand": ["names", "schema", "operations", "editmeta", "changelog", "renderedFields"]
    }
  }
}
```

**Environment Variables:**

| Variable | Description | Required |
|----------|-------------|----------|
| `JIRA_SERVER` | JIRA server URL | ✅ |
| `JIRA_EMAIL` | User email | ✅ |
| `JIRA_API_TOKEN` | API token | ✅ |
| `JIRA_PROJECT_KEY` | Default project | ❌ |

### GitHub Configuration

```json
{
  "adapter": "github",
  "config": {
    "owner": "myorganization",
    "repo": "myrepository",
    "token": "ghp_1234567890abcdef",
    "base_url": "https://api.github.com",
    "include_pull_requests": false,
    "timeout": 30,
    "retry": {
      "max_attempts": 3,
      "backoff_factor": 2,
      "status_codes": [403, 429, 500, 502, 503, 504]
    },
    "labels": {
      "state_labels": {
        "in_progress": "in progress",
        "ready": "ready for review",
        "tested": "needs testing",
        "blocked": "blocked"
      },
      "priority_labels": {
        "critical": "priority: critical",
        "high": "priority: high",
        "medium": "priority: medium",
        "low": "priority: low"
      },
      "type_labels": {
        "bug": "bug",
        "feature": "enhancement",
        "documentation": "documentation"
      }
    },
    "templates": {
      "enabled": true,
      "bug_report": true,
      "feature_request": true,
      "custom_template_dir": ".github/ISSUE_TEMPLATE"
    },
    "automation": {
      "auto_close": {
        "enabled": true,
        "keywords": ["fix", "fixes", "close", "closes", "resolve", "resolves"]
      },
      "auto_assign": {
        "enabled": false,
        "default_assignee": null
      }
    }
  }
}
```

**Environment Variables:**

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_TOKEN` | Personal access token | ✅ |
| `GITHUB_OWNER` | Repository owner | ✅ |
| `GITHUB_REPO` | Repository name | ✅ |
| `GITHUB_BASE_URL` | API base URL | ❌ |

## Advanced Configuration

### Performance Tuning

```json
{
  "performance": {
    "cache": {
      "enabled": true,
      "ttl": 600,
      "max_size": 2000,
      "compression": true,
      "write_through": false
    },
    "connection_pool": {
      "max_connections": 10,
      "keep_alive": true,
      "timeout": 30
    },
    "rate_limiting": {
      "enabled": true,
      "requests_per_minute": 100,
      "burst_size": 10
    },
    "async": {
      "max_concurrent": 5,
      "queue_size": 100,
      "timeout": 60
    }
  }
}
```

### Security Configuration

```json
{
  "security": {
    "encryption": {
      "enabled": true,
      "algorithm": "AES-256-GCM",
      "key_rotation": 86400
    },
    "authentication": {
      "require_2fa": false,
      "session_timeout": 3600,
      "max_failed_attempts": 5
    },
    "api_security": {
      "rate_limiting": true,
      "request_logging": true,
      "ip_whitelist": null,
      "cors_enabled": false
    },
    "data_protection": {
      "anonymize_logs": true,
      "encrypt_config": false,
      "secure_memory": true
    }
  }
}
```

### Monitoring and Observability

```json
{
  "monitoring": {
    "metrics": {
      "enabled": true,
      "endpoint": "/metrics",
      "format": "prometheus",
      "interval": 60
    },
    "tracing": {
      "enabled": false,
      "provider": "jaeger",
      "endpoint": "http://localhost:14268/api/traces"
    },
    "health_checks": {
      "enabled": true,
      "endpoint": "/health",
      "timeout": 10,
      "checks": ["adapter", "cache", "database"]
    },
    "alerting": {
      "enabled": false,
      "webhook_url": null,
      "error_threshold": 5,
      "response_time_threshold": 1000
    }
  }
}
```

### Logging Configuration

```json
{
  "logging": {
    "level": "INFO",
    "format": "structured",
    "output": {
      "console": {
        "enabled": true,
        "level": "INFO",
        "format": "human"
      },
      "file": {
        "enabled": true,
        "path": "/var/log/mcp-ticketer/app.log",
        "level": "DEBUG",
        "format": "json",
        "rotation": {
          "max_size": "100MB",
          "max_files": 5,
          "compress": true
        }
      },
      "syslog": {
        "enabled": false,
        "facility": "daemon",
        "tag": "mcp-ticketer"
      }
    },
    "filters": {
      "exclude_paths": ["/health", "/metrics"],
      "sensitive_fields": ["password", "token", "key"],
      "max_message_length": 10000
    }
  }
}
```

## Security Best Practices

### Credential Management

#### 1. Environment Variables (Recommended)

```bash
# Use environment variables for sensitive data
export LINEAR_API_KEY="lin_api_xxxxxxxxxxxxx"
export JIRA_API_TOKEN="ATATT3xFfGF0T..."
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxx"

# Store in shell profile
echo 'export LINEAR_API_KEY="lin_api_xxx"' >> ~/.bashrc
```

#### 2. System Credential Stores

**macOS Keychain:**
```bash
# Store credentials
security add-generic-password \
  -s "mcp-ticketer" \
  -a "linear-api-key" \
  -w "lin_api_xxxxxxxxxxxxx"

# Retrieve credentials
security find-generic-password \
  -s "mcp-ticketer" \
  -a "linear-api-key" \
  -w
```

**Linux Secret Service:**
```bash
# Store credentials
secret-tool store \
  --label="MCP Ticketer Linear API" \
  service mcp-ticketer \
  account linear-api-key

# Retrieve credentials
secret-tool lookup service mcp-ticketer account linear-api-key
```

**Windows Credential Manager:**
```powershell
# Store credentials
cmdkey /add:"mcp-ticketer-linear" /user:"api-key" /pass:"lin_api_xxx"

# Retrieve credentials
cmdkey /list:"mcp-ticketer-linear"
```

#### 3. Configuration File Security

```bash
# Secure configuration file permissions
chmod 600 ~/.mcp-ticketer/config.json
chown $USER:$USER ~/.mcp-ticketer/config.json

# Encrypt sensitive configuration
gpg --symmetric --cipher-algo AES256 ~/.mcp-ticketer/config.json
```

### API Token Best Practices

1. **Minimal Permissions**: Grant only required scopes/permissions
2. **Regular Rotation**: Rotate tokens every 90 days
3. **Monitoring**: Monitor token usage for anomalies
4. **Separate Tokens**: Use different tokens for different environments
5. **Expiry Management**: Set appropriate expiration dates

### Network Security

```json
{
  "network": {
    "tls": {
      "enabled": true,
      "min_version": "1.2",
      "verify_certificates": true,
      "client_certificates": false
    },
    "proxy": {
      "enabled": false,
      "http_proxy": null,
      "https_proxy": null,
      "no_proxy": ["localhost", "127.0.0.1"]
    },
    "firewall": {
      "whitelist": ["10.0.0.0/8", "192.168.0.0/16"],
      "blacklist": [],
      "default_action": "deny"
    }
  }
}
```

## Multi-Project Setup

### Project-Specific Configurations

#### Option 1: Per-Project Config Files

```bash
# Project A (Linear)
mkdir project-a/.mcp-ticketer
cat > project-a/.mcp-ticketer/config.json << EOF
{
  "adapter": "linear",
  "config": {
    "team_id": "team-project-a",
    "api_key": "${LINEAR_API_KEY}"
  }
}
EOF

# Project B (JIRA)
mkdir project-b/.mcp-ticketer
cat > project-b/.mcp-ticketer/config.json << EOF
{
  "adapter": "jira",
  "config": {
    "server": "https://company.atlassian.net",
    "email": "${JIRA_EMAIL}",
    "api_token": "${JIRA_API_TOKEN}",
    "project_key": "PROJB"
  }
}
EOF

# Use project-specific config
cd project-a
export MCP_TICKETER_CONFIG_FILE=.mcp-ticketer/config.json
mcp-ticket list
```

#### Option 2: Profile-Based Configuration

```json
{
  "profiles": {
    "development": {
      "adapter": "aitrackdown",
      "config": {
        "base_path": ".tickets-dev"
      }
    },
    "staging": {
      "adapter": "linear",
      "config": {
        "team_id": "team-staging",
        "api_key": "${LINEAR_API_KEY_STAGING}"
      }
    },
    "production": {
      "adapter": "jira",
      "config": {
        "server": "https://company.atlassian.net",
        "project_key": "PROD"
      }
    }
  },
  "active_profile": "development"
}
```

```bash
# Switch profiles
mcp-ticket config set-profile staging
mcp-ticket config set-profile production

# Use profile temporarily
MCP_TICKETER_PROFILE=staging mcp-ticket list
```

#### Option 3: Environment-Based Configuration

```bash
# Development environment
export MCP_TICKETER_ENV=development
export MCP_TICKETER_ADAPTER=aitrackdown
export AITRACKDOWN_BASE_PATH=.tickets-dev

# Staging environment
export MCP_TICKETER_ENV=staging
export MCP_TICKETER_ADAPTER=linear
export LINEAR_TEAM_ID=team-staging
export LINEAR_API_KEY=lin_api_staging_xxx

# Production environment
export MCP_TICKETER_ENV=production
export MCP_TICKETER_ADAPTER=jira
export JIRA_PROJECT_KEY=PROD
```

### Team Configuration Management

```bash
# Shared team configuration repository
git clone https://github.com/company/mcp-ticketer-configs.git
cd mcp-ticketer-configs

# Team-specific configurations
configs/
├── team-frontend/
│   ├── development.json
│   ├── staging.json
│   └── production.json
├── team-backend/
│   ├── development.json
│   ├── staging.json
│   └── production.json
└── shared/
    ├── common.json
    └── security.json

# Use team configuration
export MCP_TICKETER_CONFIG_FILE=configs/team-frontend/production.json
mcp-ticket list
```

## Troubleshooting Configuration

### Common Configuration Issues

#### 1. Configuration File Not Found

**Error**: `Configuration file not found`

**Solutions**:
```bash
# Check if config file exists
ls -la ~/.mcp-ticketer/config.json

# Initialize if missing
mcp-ticket init --adapter aitrackdown

# Check custom config path
echo $MCP_TICKETER_CONFIG_FILE
```

#### 2. Invalid JSON Format

**Error**: `Failed to parse configuration: invalid JSON`

**Solutions**:
```bash
# Validate JSON syntax
python -m json.tool ~/.mcp-ticketer/config.json

# Fix common JSON errors
# - Missing quotes around strings
# - Trailing commas
# - Unescaped characters
```

#### 3. Missing Required Fields

**Error**: `Required field 'api_key' missing`

**Solutions**:
```bash
# Check configuration schema
mcp-ticket config validate

# Add missing fields
mcp-ticket config set adapter.config.api_key "your-api-key"

# Re-run initialization
mcp-ticket init --adapter linear --api-key your-key
```

#### 4. Permission Denied

**Error**: `Permission denied accessing configuration`

**Solutions**:
```bash
# Check file permissions
ls -la ~/.mcp-ticketer/config.json

# Fix permissions
chmod 600 ~/.mcp-ticketer/config.json
chown $USER ~/.mcp-ticketer/config.json

# Check directory permissions
chmod 700 ~/.mcp-ticketer/
```

#### 5. Environment Variable Conflicts

**Error**: `Conflicting configuration values`

**Solutions**:
```bash
# Check environment variables
env | grep MCP_TICKETER
env | grep LINEAR
env | grep JIRA
env | grep GITHUB

# Clear conflicting variables
unset MCP_TICKETER_ADAPTER
unset LINEAR_API_KEY

# Use explicit configuration
mcp-ticket --config /path/to/config.json list
```

### Debugging Configuration

#### Enable Debug Logging

```bash
# Enable debug logging
export MCP_TICKETER_LOG_LEVEL=DEBUG
mcp-ticket list

# Or in configuration
{
  "logging": {
    "level": "DEBUG"
  }
}
```

#### Configuration Validation

```bash
# Validate current configuration
mcp-ticket config validate

# Show effective configuration
mcp-ticket config show

# Test adapter connection
mcp-ticket config test

# Show configuration precedence
mcp-ticket config debug
```

#### Configuration Export/Import

```bash
# Export current configuration
mcp-ticket config export > backup-config.json

# Import configuration
mcp-ticket config import < backup-config.json

# Merge configurations
mcp-ticket config merge additional-config.json
```

### Performance Troubleshooting

#### Cache Issues

```bash
# Clear cache
mcp-ticket cache clear

# Disable cache temporarily
MCP_TICKETER_CACHE_ENABLED=false mcp-ticket list

# Check cache statistics
mcp-ticket cache stats
```

#### Network Issues

```bash
# Test connectivity
mcp-ticket config test

# Use proxy
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
mcp-ticket list

# Increase timeout
{
  "config": {
    "timeout": 120
  }
}
```

### Recovery Procedures

#### Configuration Backup

```bash
# Create backup before changes
cp ~/.mcp-ticketer/config.json ~/.mcp-ticketer/config.json.backup

# Automatic backup
{
  "backup": {
    "enabled": true,
    "directory": "~/.mcp-ticketer/backups",
    "keep": 10,
    "compress": true
  }
}
```

#### Configuration Reset

```bash
# Reset to defaults
mcp-ticket config reset

# Reset specific adapter
mcp-ticket config reset --adapter linear

# Factory reset (removes all configuration)
rm -rf ~/.mcp-ticketer/
mcp-ticket init --adapter aitrackdown
```

---

This comprehensive configuration guide covers all aspects of setting up and managing MCP Ticketer. For adapter-specific details, see the [Adapters Guide](ADAPTERS.md). For security considerations, refer to the [Security Best Practices](#security-best-practices) section above.