# Documentation Standards

**Version**: 1.0  
**Last Updated**: December 2025  
**Based on**: GitFlow Analytics documentation structure and MCP Ticketer best practices

## 📚 Documentation Philosophy

Our documentation follows a **progressive disclosure** model with clear audience segmentation:

- **Users** find what they need to get started quickly with MCP Ticketer
- **Developers** can dive deep into implementation details and contribute effectively
- **Contributors** have clear guidance on project standards and development workflows
- **Maintainers** have architectural context for decisions and system design

## 🏗️ Directory Structure

```
docs/
├── README.md                    # Documentation hub and navigation
├── DOCUMENTATION-STANDARDS.md  # This file - documentation standards
├── getting-started/            # User onboarding and quick wins
├── guides/                     # Task-oriented user guides
├── examples/                   # Real-world usage examples
├── reference/                  # Technical reference material
├── developer/                  # Developer and contributor documentation
├── architecture/              # System design and architecture
├── integrations/              # Platform integrations and setup
├── deployment/                # Operations and deployment
├── configuration/             # Configuration documentation
└── _archive/                  # Historical content and deprecated docs
```

## 🎯 Content Categories

### 1. Getting Started (`getting-started/`)
**Purpose**: Help new users succeed quickly with MCP Ticketer  
**Audience**: First-time users, evaluators  
**Content**: Installation, quickstart, first ticket creation, MCP setup  
**Style**: Step-by-step, minimal prerequisites

### 2. Guides (`guides/`)
**Purpose**: Task-oriented how-to documentation  
**Audience**: Regular users, power users  
**Content**: Configuration, troubleshooting, specific features, workflows  
**Style**: Problem-solution oriented, comprehensive

### 3. Examples (`examples/`)
**Purpose**: Real-world usage scenarios  
**Audience**: All users seeking practical applications  
**Content**: Complete working examples, use cases, integration patterns  
**Style**: Copy-paste ready, well-commented

### 4. Reference (`reference/`)
**Purpose**: Complete technical specifications  
**Audience**: Integrators, advanced users  
**Content**: CLI commands, MCP tools, APIs, configuration options  
**Style**: Comprehensive, searchable, precise

### 5. Developer (`developer/`)
**Purpose**: Support contributors and maintainers  
**Audience**: Contributors, core team  
**Content**: Contributing, development setup, coding standards, release process  
**Style**: Technical, detailed, process-oriented

### 6. Architecture (`architecture/`)
**Purpose**: System design and technical decisions  
**Audience**: Architects, senior developers  
**Content**: System overview, design patterns, MCP integration, adapter architecture  
**Style**: High-level, decision-focused

### 7. Integrations (`integrations/`)
**Purpose**: Platform-specific setup and integration guides  
**Audience**: Users integrating with specific platforms  
**Content**: Linear, JIRA, GitHub setup, AI client integration, MCP configuration  
**Style**: Platform-focused, step-by-step

### 8. Deployment (`deployment/`)
**Purpose**: Production deployment and operations  
**Audience**: DevOps, system administrators  
**Content**: Installation, monitoring, scaling, security  
**Style**: Operations-focused, security-conscious

## 📋 File Naming Conventions

### Standard Patterns
- Use lowercase with hyphens: `file-name.md`
- Be descriptive but concise: `linear-setup.md` not `linear.md`
- Use consistent suffixes:
  - `-guide.md` for how-to documentation
  - `-reference.md` for technical specifications
  - `-overview.md` for high-level summaries
  - `-setup.md` for installation/configuration

### Special Files
- `README.md` - Directory index and navigation
- `CHANGELOG.md` - Version history (root only)
- `CONTRIBUTING.md` - Contribution guidelines (root only)
- `SECURITY.md` - Security policy and guidelines

## ✍️ Content Structure Standards

### Document Template
```markdown
# Title

Brief description of what this document covers.

## Prerequisites
- What users should know/have done first
- Required tools or access

## Overview
High-level summary of the topic

## Step-by-Step Instructions
1. Clear, numbered procedures
2. Include expected output
3. Provide troubleshooting for common issues

## Examples
Real-world usage scenarios with complete code

## Troubleshooting
Common issues and solutions

## See Also
- [Related Topic](../category/related-topic.md)
- [External Resource](https://example.com)

## Next Steps
Where to go next in the documentation journey
```

### Writing Style Guidelines

**Voice and Tone**:
- Use active voice: "Run the command" not "The command should be run"
- Be direct and concise
- Use "you" to address the reader
- Maintain a helpful, professional tone

**Technical Writing**:
- Define acronyms on first use (MCP = Model Context Protocol)
- Use consistent terminology throughout
- Include complete, runnable examples
- Test all code samples before committing

**Formatting**:
- Use code blocks for commands and code
- Use tables for structured data
- Use callout boxes for important information
- Include screenshots for UI elements when helpful

## 🔗 Cross-Referencing Standards

### Internal Links
- Use relative paths: `[Configuration Guide](../guides/configuration.md)`
- Link to specific sections: `[Installation](../getting-started/installation.md#prerequisites)`
- Include "See Also" sections for related topics

### External Links
- Use full URLs for external resources
- Include link text that describes the destination
- Verify links regularly for accuracy

### Navigation Aids
- Each directory must have a `README.md` index
- Include breadcrumb navigation in complex documents
- Provide clear "Next Steps" guidance

## 📊 Quality Standards

### Content Quality
- All examples must be tested and working
- Include expected output when helpful
- Update documentation with each release
- Maintain accuracy through regular reviews

### Accessibility
- Use descriptive link text
- Include alt text for images
- Maintain logical heading hierarchy
- Ensure good contrast in screenshots

### Maintenance
- Review quarterly for accuracy
- Update broken links promptly
- Archive outdated content to `_archive/`
- Keep examples current with latest version

## 🗂️ Archive Policy

### What to Archive
- Outdated documentation versions
- Deprecated feature documentation
- Historical reports and analysis
- Temporary documentation files

### Archive Structure
```
_archive/
├── old-versions/     # Previous documentation versions
├── deprecated/       # Deprecated feature docs
├── temp-files/       # Temporary documentation
└── reports/          # Historical reports and analysis
```

### Archive Process
1. Move outdated content to appropriate `_archive/` subdirectory
2. Add date suffix to archived files: `old-guide-20241201.md`
3. Update any links pointing to archived content
4. Add entry to archive index if needed

## 🚀 Implementation Guidelines

### For New Documentation
1. Determine appropriate category and directory
2. Follow naming conventions
3. Use standard document template
4. Include in directory README.md index
5. Test all examples and links

### For Existing Documentation
1. Review against these standards
2. Reorganize if in wrong category
3. Update format to match template
4. Fix broken links and outdated content
5. Archive if no longer relevant

### For Major Changes
1. Update this standards document first
2. Communicate changes to team
3. Update existing docs gradually
4. Maintain backward compatibility where possible

## 🔧 MCP Ticketer Specific Guidelines

### Adapter Documentation
- Each adapter should have setup guide in `integrations/`
- Include configuration examples and troubleshooting
- Document platform-specific features and limitations

### MCP Integration
- Document all MCP tools with examples
- Include JSON schema references where applicable
- Provide AI client integration guides

### CLI Documentation
- Include complete command examples
- Document all flags and options
- Provide expected output examples

---

**Maintainers**: Update this document when changing documentation organization or standards.

**Contributors**: Follow these standards for all documentation contributions.
