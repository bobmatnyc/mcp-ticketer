# GitHub Adapter Attachment Limitations

**Date**: 2025-11-24
**Issue**: Implementation of `get_attachments()` for GitHub adapter
**Status**: Not Implemented - By Design

## Summary

GitHub Issues do not have native attachment support in the same way as Linear, JIRA, or Asana. Attachments are handled through:
1. Markdown-embedded images and files in issue/comment bodies
2. External file hosting (GitHub Assets)
3. References to repository files

## GitHub API Attachment Model

GitHub's REST API v3 and GraphQL API do not provide:
- A dedicated attachments endpoint for issues
- Direct file upload/download APIs for issue attachments
- Metadata about files embedded in markdown

## Attachment Handling Patterns

### 1. Markdown-Embedded Assets
Files are uploaded and embedded directly in issue/comment markdown:
```markdown
![Screenshot](https://user-images.githubusercontent.com/12345/file.png)
[Document](https://github.com/owner/repo/files/12345/document.pdf)
```

These URLs are:
- Generated when uploading through GitHub UI
- Stored as part of the issue/comment body text
- Not queryable as separate entities via API

### 2. Repository File References
Issues may reference files in the repository:
```markdown
See [config.json](../config/config.json)
```

These are repository file paths, not attachments.

### 3. External Links
Issues may link to external file hosting:
```markdown
[Design Doc](https://docs.google.com/document/d/abc123)
```

## Implementation Decision

**Status**: `get_attachments()` NOT IMPLEMENTED for GitHub adapter

### Reasoning:
1. **No Native API**: GitHub Issues API has no attachment listing endpoint
2. **Parsing Complexity**: Extracting file URLs from markdown is fragile and unreliable
3. **Inconsistent URLs**: No standard format for GitHub-hosted asset URLs
4. **Authentication Issues**: Asset URLs may require session cookies, not API tokens
5. **User Expectations**: GitHub users expect attachments to be in issue text, not separate

### Alternative Approach:
Users can:
- View attachments in GitHub UI by reading issue body
- Parse markdown from `issue.body` if needed
- Use GitHub's web interface for file management

## Comparison with Other Adapters

| Adapter       | Has `get_attachments()` | API Support | Authentication |
|---------------|-------------------------|-------------|----------------|
| Linear        | ✅ Yes                  | GraphQL     | Bearer token   |
| JIRA          | ✅ Yes                  | REST API    | Basic/Token    |
| Asana         | ✅ Yes                  | REST API    | Bearer token   |
| AiTrackDown   | ✅ Yes                  | File system | N/A            |
| **GitHub**    | ❌ No                   | N/A         | N/A            |

## Future Considerations

If attachment support is needed for GitHub:
1. Implement markdown parser to extract file URLs from issue bodies
2. Add configuration for asset URL patterns
3. Handle authentication for GitHub Assets (complex)
4. Document limitations clearly to users

## Related Issues

- Linear attachment 401 errors: Fixed with proper authentication headers
- GitHub asset URLs: Requires complex session/cookie handling
- Parser approach: Would need regex/markdown parser dependency

## Conclusion

GitHub adapter does NOT implement `get_attachments()` because:
- GitHub Issues API provides no native attachment listing
- Extracting from markdown is unreliable and out of scope
- Users can view attachments through GitHub's UI

This is a platform limitation, not a bug in mcp-ticketer.

## Testing Verification

No unit tests for GitHub `get_attachments()` as method is not implemented.
This is documented as expected behavior.
