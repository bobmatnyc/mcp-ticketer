# MCP Ticketer Examples

Example scripts demonstrating various features and use cases of MCP Ticketer.

## 📁 Available Examples

### File Attachments

#### `jira_epic_attachments_example.py`
Demonstrates JIRA epic update and attachment features.

**What it shows**:
- Creating JIRA epics
- Attaching files to epics
- Updating epic metadata
- Error handling

**Requirements**:
- JIRA Cloud account
- JIRA API token
- Environment variables:
  - `JIRA_SERVER` - Your JIRA server URL
  - `JIRA_EMAIL` - Your JIRA email
  - `JIRA_API_TOKEN` - Your API token
  - `JIRA_PROJECT_KEY` - Project key (e.g., "TEST")

**Usage**:
```bash
# Set up environment
export JIRA_SERVER="https://your-domain.atlassian.net"
export JIRA_EMAIL="your.email@company.com"
export JIRA_API_TOKEN="your_api_token"
export JIRA_PROJECT_KEY="TEST"

# Run example
python examples/jira_epic_attachments_example.py
```

---

#### `linear_file_upload_example.py`
Demonstrates Linear file upload and attachment functionality.

**What it shows**:
- Uploading files to Linear
- Attaching files to issues and epics
- Using the Linear adapter's file upload API
- Error handling and best practices

**Requirements**:
- Linear API key
- Team key or team ID
- Environment variables:
  - `LINEAR_API_KEY` - Your Linear API key

**Configuration**:
```python
config = {
    "api_key": os.getenv("LINEAR_API_KEY"),
    "team_key": "ENG",  # Replace with your team key
    # or use team_id: "your-team-uuid"
}
```

**Usage**:
```bash
# Set up environment
export LINEAR_API_KEY="lin_api_..."

# Edit the script to set your team key
# Then run
python examples/linear_file_upload_example.py
```

## 🚀 Running Examples

### Prerequisites

1. **Install MCP Ticketer**:
```bash
pip install mcp-ticketer

# Or install from source
cd /path/to/mcp-ticketer
pip install -e .
```

2. **Install adapter dependencies** (if needed):
```bash
# For JIRA
pip install mcp-ticketer[jira]

# For Linear
pip install mcp-ticketer[linear]

# For all adapters
pip install mcp-ticketer[all]
```

3. **Configure environment variables**:
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### Running an Example

```bash
# Activate your virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run example
python examples/jira_epic_attachments_example.py
```

## 📚 Example Categories

### By Feature

**File Attachments**:
- `jira_epic_attachments_example.py` - JIRA epic attachments
- `linear_file_upload_example.py` - Linear file uploads

### By Adapter

**JIRA**:
- `jira_epic_attachments_example.py`

**Linear**:
- `linear_file_upload_example.py`

## 💡 Example Structure

Each example follows a consistent structure:

```python
#!/usr/bin/env python3
"""Example script description."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def main():
    """Main example function."""
    # 1. Initialize adapter with config
    config = {
        "api_key": os.getenv("API_KEY"),
        # ... other config
    }
    adapter = AdapterClass(config)

    # 2. Demonstrate feature
    result = await adapter.some_operation()

    # 3. Show results
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 🔧 Customizing Examples

All examples are designed to be easily customized:

1. **Copy the example**:
```bash
cp examples/jira_epic_attachments_example.py my_custom_example.py
```

2. **Modify for your use case**:
- Update configuration
- Change file paths
- Adjust operations
- Add error handling

3. **Run your custom version**:
```bash
python my_custom_example.py
```

## 📖 Related Documentation

### For Users
- [Quick Start Guide](../docs/quickstart/) - Getting started
- [Setup Guide](../docs/setup/) - Adapter configuration
- [Features](../docs/features/) - Feature documentation

### For Developers
- [API Reference](../docs/api/) - Complete API documentation
- [Python API](../docs/api/python.md) - Python API reference
- [Adapter Development](../docs/development/adapters.md) - Creating adapters

## 🆘 Troubleshooting

### Common Issues

#### "Module not found" errors
```bash
# Install MCP Ticketer
pip install mcp-ticketer

# Or install from source
pip install -e .
```

#### "API key not found" errors
```bash
# Check environment variables
echo $JIRA_API_TOKEN
echo $LINEAR_API_KEY

# Or load from .env file
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('JIRA_API_TOKEN'))"
```

#### "Import error" for adapters
```bash
# Install specific adapter dependencies
pip install mcp-ticketer[jira]
pip install mcp-ticketer[linear]
```

#### "Permission denied" when running examples
```bash
# Make example executable
chmod +x examples/jira_epic_attachments_example.py

# Run with python
python examples/jira_epic_attachments_example.py
```

### Getting Help

- **Documentation**: See [docs/](../docs/) for complete documentation
- **Issues**: [GitHub Issues](https://github.com/mcp-ticketer/mcp-ticketer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mcp-ticketer/mcp-ticketer/discussions)

## 🤝 Contributing Examples

We welcome new examples! To contribute:

1. **Create your example** following the structure above
2. **Test thoroughly** with real credentials
3. **Document clearly** with comments and docstrings
4. **Update this README** with your example
5. **Submit a pull request**

**Example contribution checklist**:
- [ ] Example follows consistent structure
- [ ] Includes docstring with description
- [ ] Has clear comments explaining each step
- [ ] Includes error handling
- [ ] Tested with real adapter
- [ ] Environment variables documented
- [ ] Added to this README

## 📝 Future Examples

Examples we'd love to add:

- [ ] GitHub Issues integration example
- [ ] AITrackdown basic usage
- [ ] Bulk ticket creation
- [ ] Search and filtering
- [ ] State transitions workflow
- [ ] Hierarchical ticket creation (Epic → Issue → Task)
- [ ] Comment management
- [ ] MCP tool usage from AI agents
- [ ] Custom instructions usage

**Want to contribute?** Pick one and create a pull request!

---

**Last Updated**: 2025-11-15
