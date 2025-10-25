"""MCP server constants and configuration."""

# JSON-RPC Protocol
JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"

# Server Info
SERVER_NAME = "mcp-ticketer"
SERVER_VERSION = "0.3.2"

# Status Values
STATUS_COMPLETED = "completed"
STATUS_ERROR = "error"
STATUS_NOT_IMPLEMENTED = "not_implemented"

# Error Codes
ERROR_PARSE = -32700
ERROR_INVALID_REQUEST = -32600
ERROR_METHOD_NOT_FOUND = -32601
ERROR_INVALID_PARAMS = -32602
ERROR_INTERNAL = -32603

# Default Values
DEFAULT_LIMIT = 10
DEFAULT_OFFSET = 0
DEFAULT_PRIORITY = "medium"
DEFAULT_MAX_DEPTH = 3
DEFAULT_BASE_PATH = ".aitrackdown"

# Response Messages
MSG_TICKET_NOT_FOUND = "Ticket {ticket_id} not found"
MSG_UPDATE_FAILED = "Ticket {ticket_id} not found or update failed"
MSG_TRANSITION_FAILED = "Ticket {ticket_id} not found or transition failed"
MSG_EPIC_NOT_FOUND = "Epic {epic_id} not found"
MSG_MISSING_PARENT_ID = "Tasks must have a parent_id (issue identifier)"
MSG_UNKNOWN_OPERATION = "Unknown comment operation: {operation}"
MSG_UNKNOWN_METHOD = "Method not found: {method}"
MSG_INTERNAL_ERROR = "Internal error: {error}"
MSG_NO_TICKETS_PROVIDED = "No tickets provided for bulk creation"
MSG_NO_UPDATES_PROVIDED = "No updates provided for bulk operation"
MSG_MISSING_TITLE = "Ticket {index} missing required 'title' field"
MSG_MISSING_TICKET_ID = "Update {index} missing required 'ticket_id' field"
MSG_TICKET_ID_REQUIRED = "ticket_id is required"
MSG_PR_URL_REQUIRED = "pr_url is required"
MSG_ATTACHMENT_NOT_IMPLEMENTED = "Attachment functionality not yet implemented"
MSG_PR_NOT_SUPPORTED = "PR creation not supported for adapter: {adapter}"
MSG_PR_LINK_NOT_SUPPORTED = "PR linking not supported for adapter: {adapter}"
MSG_UNKNOWN_TOOL = "Unknown tool: {tool}"
MSG_GITHUB_CONFIG_REQUIRED = "GitHub owner and repo are required for Linear PR creation"

# Attachment Alternative Messages
ATTACHMENT_ALTERNATIVES = [
    "Add file URLs in comments",
    "Use external file storage",
]
ATTACHMENT_NOT_IMPLEMENTED_REASON = (
    "File attachments require adapter-specific implementation"
)
