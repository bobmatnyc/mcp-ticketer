# MCP-Ticketer Product Requirements Document

## Executive Summary

### Purpose
MCP-Ticketer is a universal ticketing abstraction layer designed for AI coding agents, providing a unified interface to multiple ticketing systems through the Model Context Protocol (MCP) or direct API access. It enables seamless integration with various project management and issue tracking platforms while maintaining consistency and simplicity for AI agents.

### Primary Users
- AI coding agents and assistants (Claude, GPT, etc.)
- Agentic development tools and workflows
- Development teams using AI-augmented processes
- CI/CD pipelines with AI-driven task management

### Key Value Proposition
- **Single Interface**: One API to rule all ticketing systems
- **AI-Optimized**: Designed specifically for agentic interactions
- **Extensible**: Adapter pattern allows easy addition of new platforms
- **Cached & Fast**: Async operations with intelligent caching
- **Type-Safe**: Full typing support for reliable integrations

## System Architecture

### Technology Stack
- **Language**: Python 3.13+
- **Architecture Pattern**: Service-Oriented Architecture (SOA) with Dependency Injection (DI)
- **Design Pattern**: Adapter pattern for platform integrations
- **Async Framework**: asyncio for concurrent operations
- **Caching**: Redis-compatible caching layer
- **API Gateway**: MCP JSON-RPC and REST/GraphQL endpoints

### Core Components

#### 1. Universal Abstraction Layer
- Platform-agnostic ticket models
- Unified state machine
- Common operations interface
- Field mapping engine

#### 2. Platform Adapters
- Individual adapter per ticketing system
- Bidirectional data transformation
- Platform-specific optimizations
- Authentication management

#### 3. MCP Gateway
- JSON-RPC server implementation
- Tool registration and discovery
- Session management
- Error handling and retries

#### 4. Caching Layer
- Async cache operations
- TTL-based invalidation
- Write-through caching
- Batch operation support

## Core Requirements

### Universal Data Model

#### Entity Hierarchy
Based on ai-trackdown-pytools' proven model:

```
Epic (EP-XXXX)
  ├── Issue (ISS-XXXX)
  │   ├── Task (TSK-XXXX)
  │   └── Bug (BUG-XXXX)
  └── Pull Request (PR-XXXX)
      └── Comment (CMT-XXXX)
```

#### Core Ticket Properties
```python
class UniversalTicket:
    # Identification
    id: str              # Platform-specific ID
    universal_id: str    # MCP-Ticketer UUID
    type: TicketType     # epic, issue, task, bug, pr, comment
    prefix: str          # EP, ISS, TSK, BUG, PR, CMT

    # Content
    title: str
    description: str

    # Relationships
    parent: Optional[str]
    children: List[str]
    dependencies: List[str]
    blocks: List[str]

    # State
    status: TicketStatus
    priority: Priority
    severity: Optional[BugSeverity]  # For bugs only

    # Assignment
    assignees: List[str]
    creator: str

    # Metadata
    tags: List[str]
    labels: List[str]
    custom_fields: Dict[str, Any]

    # Timestamps
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime]

    # Effort
    estimated_hours: Optional[float]
    actual_hours: Optional[float]
    story_points: Optional[int]
```

#### State Machine Abstraction

Universal states mapped to platform-specific states:

```yaml
Universal States:
  - open         # New, unstarted work
  - in_progress  # Active development
  - blocked      # Waiting on dependency
  - ready        # Ready for review/testing
  - completed    # Work finished
  - cancelled    # Work abandoned
  - closed       # Archived/resolved

Platform Mappings:
  ai-trackdown:
    open: open
    in_progress: in_progress
    blocked: blocked
    ready: completed
    completed: completed
    cancelled: cancelled
    closed: closed

  Linear:
    open: Todo
    in_progress: In Progress
    blocked: Blocked
    ready: In Review
    completed: Done
    cancelled: Cancelled
    closed: Closed

  JIRA:
    open: To Do
    in_progress: In Progress
    blocked: Blocked
    ready: Code Review
    completed: Done
    cancelled: Won't Fix
    closed: Closed
```

### Supported Systems (Priority Order)

#### 1. ai-trackdown-pytools (Reference Implementation)
- **Status**: Primary reference model
- **Storage**: File-based (.aitrackdown/ directory structure)
- **Features**:
  - Hierarchical ticket structure (EP→ISS→TSK)
  - Built-in workflow states
  - File-based persistence
  - Git-friendly storage
- **Integration**: Direct Python API access

#### 2. Linear (GraphQL)
- **Status**: Priority integration
- **API**: GraphQL API v2
- **Features**:
  - Teams and projects
  - Cycles and milestones
  - Custom workflows
  - Real-time webhooks
- **Authentication**: API key or OAuth 2.0

#### 3. JIRA (REST)
- **Status**: Enterprise priority
- **API**: REST API v3
- **Features**:
  - Complex workflows
  - Custom fields
  - Agile boards
  - JQL queries
- **Authentication**: API token or OAuth 2.0

#### 4. GitHub Issues (REST/GraphQL)
- **Status**: Open-source priority
- **API**: REST v3 + GraphQL v4
- **Features**:
  - Labels and milestones
  - Projects (v2)
  - Pull request integration
  - Actions integration
- **Authentication**: Personal access token or GitHub App

#### 5. Asana (Future)
- **Status**: Planned
- **API**: REST API
- **Features**:
  - Projects and portfolios
  - Custom fields
  - Timeline view
  - Forms integration

### CLI Interface (`mcp-ticket`)

#### Command Structure
```bash
# Initialize configuration
mcp-ticket init [--adapter ai-trackdown|linear|jira|github]

# Authentication
mcp-ticket auth login [--adapter ADAPTER]
mcp-ticket auth status
mcp-ticket auth logout

# Ticket Operations
mcp-ticket create [epic|issue|task|bug|pr] --title "..." --description "..."
mcp-ticket list [--type TYPE] [--status STATUS] [--assignee USER]
mcp-ticket show TICKET_ID [--format json|yaml|markdown]
mcp-ticket update TICKET_ID [--status STATUS] [--assignee USER]
mcp-ticket delete TICKET_ID [--force]

# Workflow Operations
mcp-ticket transition TICKET_ID NEW_STATUS
mcp-ticket block TICKET_ID BLOCKING_ID
mcp-ticket unblock TICKET_ID
mcp-ticket assign TICKET_ID USER
mcp-ticket link PARENT_ID CHILD_ID

# Search and Query
mcp-ticket search "query" [--type TYPE] [--status STATUS]
mcp-ticket query --jql "..." # For JIRA
mcp-ticket query --graphql "..." # For Linear/GitHub

# Batch Operations
mcp-ticket batch create --from-file tickets.yaml
mcp-ticket batch update --query "..." --set-status STATUS
mcp-ticket batch export --format csv|json --output file

# Configuration Management
mcp-ticket config set KEY VALUE
mcp-ticket config get KEY
mcp-ticket config list
mcp-ticket config adapters  # List available adapters

# System Management
mcp-ticket status  # Show system status
mcp-ticket health  # Health check all adapters
mcp-ticket sync    # Sync with remote systems
mcp-ticket cache clear
```

### MCP Integration

#### JSON-RPC Methods
```json
{
  "methods": {
    "ticket.create": {
      "params": {
        "type": "string",
        "title": "string",
        "description": "string",
        "parent": "string?",
        "assignees": "string[]?",
        "tags": "string[]?",
        "priority": "string?",
        "due_date": "string?"
      }
    },
    "ticket.list": {
      "params": {
        "type": "string?",
        "status": "string?",
        "assignee": "string?",
        "parent": "string?",
        "limit": "number?",
        "offset": "number?"
      }
    },
    "ticket.get": {
      "params": {
        "id": "string",
        "include_children": "boolean?"
      }
    },
    "ticket.update": {
      "params": {
        "id": "string",
        "updates": "object"
      }
    },
    "ticket.transition": {
      "params": {
        "id": "string",
        "status": "string"
      }
    },
    "ticket.search": {
      "params": {
        "query": "string",
        "type": "string?",
        "limit": "number?"
      }
    },
    "ticket.batch": {
      "params": {
        "operations": "array"
      }
    },
    "system.status": {},
    "system.adapters": {},
    "system.health": {
      "params": {
        "adapter": "string?"
      }
    }
  }
}
```

#### Tool Definitions
```yaml
tools:
  - name: create_ticket
    description: Create a new ticket in the tracking system
    parameters:
      type: required, enum[epic, issue, task, bug, pr]
      title: required, string
      description: optional, string
      parent: optional, string (ticket ID)

  - name: update_ticket
    description: Update an existing ticket
    parameters:
      id: required, string
      status: optional, enum
      assignees: optional, array

  - name: search_tickets
    description: Search for tickets
    parameters:
      query: required, string
      filters: optional, object
```

### Performance Requirements

#### Response Time Targets
- **Cached operations**: < 50ms
- **Single ticket operations**: < 100ms
- **List operations** (up to 100 items): < 200ms
- **Search operations**: < 500ms
- **Batch operations** (up to 50 items): < 1000ms

#### Scalability
- Support 10,000+ tickets per project
- Handle 100+ concurrent AI agent connections
- Process 1000+ operations per minute
- Cache hit ratio > 80% for read operations

#### Optimization Strategies
- **Async everywhere**: All I/O operations async
- **Connection pooling**: Reuse HTTP/database connections
- **Batch API calls**: Group operations when possible
- **Smart caching**: Predictive cache warming
- **Rate limit handling**: Automatic backoff and retry
- **Pagination**: Automatic handling of large result sets

### State & Workflow Management

#### Workflow Definition Schema
```yaml
workflows:
  default:
    states:
      - open
      - in_progress
      - blocked
      - ready
      - completed
      - cancelled
    transitions:
      open:
        - in_progress
        - blocked
        - cancelled
      in_progress:
        - blocked
        - ready
        - completed
        - cancelled
      blocked:
        - in_progress
        - cancelled
      ready:
        - in_progress
        - completed
        - cancelled
      completed: []
      cancelled: []

  custom_dev:
    inherits: default
    states:
      - testing  # Additional state
    transitions:
      ready:
        - testing
      testing:
        - completed
        - in_progress
```

#### Conflict Resolution
- **Optimistic locking**: Version-based conflict detection
- **Merge strategies**: Last-write-wins, manual resolution
- **Audit trail**: Full history of all changes
- **Rollback support**: Undo recent operations

### API Design

#### REST API Endpoints
```
BASE URL: https://api.mcp-ticketer.io/v1

# Tickets
GET    /tickets              # List tickets
POST   /tickets              # Create ticket
GET    /tickets/{id}         # Get ticket
PATCH  /tickets/{id}         # Update ticket
DELETE /tickets/{id}         # Delete ticket

# Relationships
POST   /tickets/{id}/children      # Add child
DELETE /tickets/{id}/children/{childId}  # Remove child
POST   /tickets/{id}/dependencies  # Add dependency
DELETE /tickets/{id}/dependencies/{depId}  # Remove dependency

# Workflow
POST   /tickets/{id}/transition    # Change status
POST   /tickets/{id}/assign        # Assign user
POST   /tickets/{id}/block         # Block ticket
DELETE /tickets/{id}/block         # Unblock ticket

# Search
POST   /search                # Search tickets
GET    /search/saved          # List saved searches
POST   /search/saved          # Save search

# Batch
POST   /batch                 # Batch operations

# System
GET    /status                # System status
GET    /health                # Health check
GET    /adapters              # List adapters
POST   /sync                  # Trigger sync
```

#### GraphQL Schema
```graphql
type Query {
  ticket(id: ID!): Ticket
  tickets(
    type: TicketType
    status: TicketStatus
    assignee: String
    parent: ID
    first: Int
    after: String
  ): TicketConnection!

  search(
    query: String!
    type: TicketType
    first: Int
  ): TicketConnection!

  me: User
  adapters: [Adapter!]!
  systemStatus: SystemStatus!
}

type Mutation {
  createTicket(input: CreateTicketInput!): Ticket!
  updateTicket(id: ID!, input: UpdateTicketInput!): Ticket!
  deleteTicket(id: ID!): Boolean!

  transitionTicket(id: ID!, status: TicketStatus!): Ticket!
  assignTicket(id: ID!, assignees: [String!]!): Ticket!
  blockTicket(id: ID!, blockingId: ID!): Ticket!
  unblockTicket(id: ID!): Ticket!

  batch(operations: [BatchOperation!]!): BatchResult!
}

type Subscription {
  ticketUpdated(id: ID): Ticket!
  ticketCreated(type: TicketType): Ticket!
  statusChanged(ticketId: ID): StatusChange!
}
```

#### WebSocket Events
```javascript
// Real-time updates
ws.on('ticket:created', (ticket) => {})
ws.on('ticket:updated', (ticket) => {})
ws.on('ticket:deleted', (id) => {})
ws.on('ticket:transitioned', (id, oldStatus, newStatus) => {})

// Subscriptions
ws.send('subscribe', { event: 'ticket:*', filters: { type: 'task' }})
ws.send('unsubscribe', { subscriptionId: '...' })
```

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Core data models and abstractions
- [ ] ai-trackdown-pytools adapter
- [ ] Basic CLI interface
- [ ] Unit test framework

### Phase 2: MCP Integration (Weeks 3-4)
- [ ] MCP server implementation
- [ ] JSON-RPC method handlers
- [ ] Authentication framework
- [ ] Error handling and logging

### Phase 3: Linear Adapter (Weeks 5-6)
- [ ] Linear GraphQL client
- [ ] Data transformation layer
- [ ] Webhook support
- [ ] Integration tests

### Phase 4: JIRA Adapter (Weeks 7-8)
- [ ] JIRA REST client
- [ ] Custom field mapping
- [ ] JQL query support
- [ ] Enterprise features

### Phase 5: GitHub Adapter (Weeks 9-10)
- [ ] GitHub REST/GraphQL client
- [ ] Issues and Projects integration
- [ ] Actions workflow triggers
- [ ] PR automation

### Phase 6: Performance & Polish (Weeks 11-12)
- [ ] Caching layer implementation
- [ ] Performance optimization
- [ ] Documentation and examples
- [ ] Production deployment

## Success Metrics

### Technical Metrics
- API response time < 100ms (p95)
- Cache hit ratio > 80%
- Test coverage > 90%
- Zero critical security vulnerabilities
- 99.9% uptime SLA

### User Metrics
- AI agent adoption rate > 50%
- Reduction in context switching by 75%
- Support for 5+ ticketing platforms
- Active community contributors > 10
- GitHub stars > 1000 (within 6 months)

### Business Metrics
- Time to integrate new platform < 1 week
- Support ticket reduction by 60%
- Developer productivity increase by 30%
- Enterprise customer adoption > 5

## Security Considerations

### Authentication & Authorization
- OAuth 2.0 / API key management
- Secure credential storage (keyring/vault)
- Role-based access control (RBAC)
- Audit logging for all operations

### Data Protection
- Encryption in transit (TLS 1.3+)
- Encryption at rest for sensitive data
- PII handling compliance
- GDPR/CCPA compliance

### API Security
- Rate limiting per client
- DDoS protection
- Input validation and sanitization
- SQL injection prevention

## Appendix

### A. ai-trackdown-pytools Reference

#### Data Model Structure
- **Prefixes**: EP (Epic), ISS (Issue), TSK (Task), BUG (Bug), PR (Pull Request), CMT (Comment)
- **Storage**: File-based in `.aitrackdown/` directory
- **Format**: YAML/JSON files with metadata
- **Indexing**: Local search index for fast queries

#### State Transitions
```
Task States:
  open → in_progress → completed
  open → blocked → in_progress
  * → cancelled

Issue States:
  open → in_progress → completed
  open → blocked → in_progress
  * → cancelled

Bug States:
  open → in_progress → completed
  open → blocked → in_progress
  completed → closed
  * → cancelled

Epic States:
  open → in_progress → completed
  open → blocked → in_progress
  * → cancelled

PR States:
  draft → open → ready → merged
  draft → open → closed
  open → closed
```

#### CLI Commands Summary
- `aitrackdown init`: Initialize project
- `aitrackdown create [task|issue|epic|pr]`: Create tickets
- `aitrackdown list [--status STATUS]`: List tickets
- `aitrackdown show TICKET_ID`: Show details
- `aitrackdown update TICKET_ID`: Update ticket
- `aitrackdown transition TICKET_ID STATUS`: Change status
- `aitrackdown search "query"`: Search tickets
- `aitrackdown sync`: Sync with remote

### B. Platform Comparison Matrix

| Feature | ai-trackdown | Linear | JIRA | GitHub | Asana |
|---------|--------------|--------|------|--------|--------|
| Hierarchical Structure | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| Custom Fields | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| Workflow Customization | ⚠️ | ✅ | ✅ | ❌ | ⚠️ |
| Real-time Updates | ❌ | ✅ | ✅ | ✅ | ✅ |
| File Attachments | ✅ | ✅ | ✅ | ✅ | ✅ |
| API Rate Limits | N/A | 1000/min | 50/min | 5000/hr | 1500/min |
| Webhooks | ❌ | ✅ | ✅ | ✅ | ✅ |
| Batch Operations | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| Search Capabilities | Local | GraphQL | JQL | GraphQL | Text |
| Offline Support | ✅ | ❌ | ❌ | ❌ | ❌ |

### C. Error Codes and Handling

```python
class MCPTicketerError(Exception):
    """Base exception for MCP-Ticketer"""

class AdapterError(MCPTicketerError):
    """Adapter-specific errors"""
    CODES = {
        'AUTH_FAILED': 1001,
        'RATE_LIMITED': 1002,
        'API_ERROR': 1003,
        'NETWORK_ERROR': 1004,
    }

class ValidationError(MCPTicketerError):
    """Data validation errors"""
    CODES = {
        'INVALID_TYPE': 2001,
        'INVALID_STATUS': 2002,
        'MISSING_FIELD': 2003,
        'INVALID_TRANSITION': 2004,
    }

class CacheError(MCPTicketerError):
    """Cache operation errors"""
    CODES = {
        'CACHE_MISS': 3001,
        'CACHE_EXPIRED': 3002,
        'CACHE_FULL': 3003,
    }
```

### D. Configuration Schema

```yaml
# ~/.mcp-ticketer/config.yaml
version: 1.0

default_adapter: ai-trackdown

adapters:
  ai-trackdown:
    type: file
    project_root: ./.aitrackdown
    auto_index: true

  linear:
    type: api
    api_key: ${LINEAR_API_KEY}
    team_id: "TEAM-123"
    workspace: "my-workspace"

  jira:
    type: api
    instance_url: https://company.atlassian.net
    email: user@company.com
    api_token: ${JIRA_API_TOKEN}
    project_key: "PROJ"

  github:
    type: api
    token: ${GITHUB_TOKEN}
    owner: "organization"
    repo: "repository"

cache:
  type: redis
  host: localhost
  port: 6379
  ttl: 3600
  max_size: 1000

mcp:
  server:
    host: 0.0.0.0
    port: 3000
  auth:
    enabled: true
    type: api_key

logging:
  level: INFO
  file: ~/.mcp-ticketer/logs/mcp-ticketer.log
  max_size: 10MB
  max_files: 5
```

## Conclusion

MCP-Ticketer represents a critical infrastructure component for the AI-augmented development ecosystem. By providing a universal abstraction layer over disparate ticketing systems, it enables AI agents to seamlessly integrate with existing project management workflows while maintaining simplicity and performance.

The system's design, rooted in the proven ai-trackdown-pytools model and extended with modern architectural patterns, ensures both immediate utility and long-term extensibility. The focus on AI-first design, performance optimization, and developer experience positions MCP-Ticketer as the definitive solution for agentic ticketing integration.

---

*Document Version: 1.0.0*
*Last Updated: 2025-09-23*
*Status: Draft for Review*