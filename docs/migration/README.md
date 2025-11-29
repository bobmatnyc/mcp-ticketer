# Migration Guides

This directory contains migration guides for breaking changes in MCP Ticketer.

## Available Migration Guides

### Version 1.4

**[v1.4 Project Filtering Enforcement](v1.4-project-filtering.md)**
- **Breaking Change**: Mandatory project filtering for search and list operations
- **Affected Tools**: 5 tools (ticket_search, ticket_list, epic_list, get_my_tickets, ticket_search_hierarchy)
- **Impact**: High - Requires configuration change or parameter updates
- **Migration Time**: ~5 minutes
- **Status**: Current

**Quick Start**:
```python
# Set default project (recommended)
config_set_default_project(project_id='YOUR-PROJECT-ID')
```

## Migration Strategy

### Before Upgrading

1. **Review Changelog**: Check [CHANGELOG.md](../../CHANGELOG.md) for breaking changes
2. **Read Migration Guide**: Read the full guide for your target version
3. **Test in Staging**: Test migration in non-production environment first
4. **Backup Configuration**: Save copy of `.mcp-ticketer/config.json`

### During Migration

1. **Follow Guide**: Use step-by-step instructions from migration guide
2. **Verify Configuration**: Run `mcp-ticketer doctor` to validate setup
3. **Test Affected Tools**: Test all tools mentioned in migration guide
4. **Update Documentation**: Update team documentation if needed

### After Migration

1. **Monitor Errors**: Watch for error messages related to migration
2. **Update Scripts**: Update automation scripts and CI/CD pipelines
3. **Inform Team**: Notify team members of changes
4. **Report Issues**: Open GitHub issue if you encounter problems

## Getting Help

- **GitHub Issues**: https://github.com/mcp-ticketer/mcp-ticketer/issues
- **Discussions**: https://github.com/mcp-ticketer/mcp-ticketer/discussions
- **Linear Project**: https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267

## Contributing

Found an issue with a migration guide? Please open an issue or submit a pull request!

---

**Last Updated**: 2025-11-29
