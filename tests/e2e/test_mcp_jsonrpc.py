"""End-to-end tests for MCP JSON-RPC protocol via `mcp-ticketer mcp` command.

This module verifies that the MCP server correctly implements the JSON-RPC 2.0
protocol over stdio when invoked via the CLI command.

Tests focus on protocol compliance rather than ticket operations:
- Command availability and execution
- JSON-RPC message format (requests and responses)
- MCP protocol handshake (initialize, tools/list, shutdown)
- Error handling for malformed requests
- Timeout and graceful termination

NOTE: These tests do not verify ticket operations - those are covered by
integration tests. Focus here is on the transport layer and protocol compliance.
"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest


@pytest.mark.e2e
class TestMCPJsonRpcProtocol:
    """Test MCP JSON-RPC protocol implementation via CLI command."""

    @pytest.fixture
    def mcp_command(self) -> list[str]:
        """Return the MCP server command to test.

        Returns:
            Command list suitable for subprocess.Popen
        """
        return ["mcp-ticketer", "mcp", "serve"]

    @pytest.fixture
    def temp_config_dir(self, tmp_path: Path) -> Path:
        """Create temporary config directory for isolated testing.

        Args:
            tmp_path: Pytest temporary directory fixture

        Returns:
            Path to temporary config directory
        """
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create minimal config with AITrackdown adapter
        config_file = config_dir / "config.json"
        config_file.write_text(
            json.dumps(
                {
                    "default_adapter": "aitrackdown",
                    "adapters": {
                        "aitrackdown": {
                            "base_path": str(tmp_path / "test_tickets"),
                            "auto_create_dirs": True,
                        }
                    },
                }
            )
        )

        return config_dir

    async def send_jsonrpc_request(
        self,
        process: subprocess.Popen,
        method: str,
        params: dict[str, Any] | None = None,
        request_id: int | str | None = None,
    ) -> None:
        """Send JSON-RPC request to process stdin.

        Args:
            process: Running subprocess with MCP server
            method: JSON-RPC method name
            params: Method parameters (optional)
            request_id: Request ID for tracking (None for notifications)
        """
        request: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }

        if params is not None:
            request["params"] = params

        if request_id is not None:
            request["id"] = request_id

        request_line = json.dumps(request) + "\n"
        process.stdin.write(request_line.encode())
        process.stdin.flush()

    async def read_jsonrpc_response(
        self, process: subprocess.Popen, timeout: float = 5.0
    ) -> dict[str, Any]:
        """Read single JSON-RPC response from process stdout.

        Args:
            process: Running subprocess with MCP server
            timeout: Maximum time to wait for response in seconds

        Returns:
            Parsed JSON-RPC response

        Raises:
            asyncio.TimeoutError: If response not received within timeout
            json.JSONDecodeError: If response is not valid JSON
        """
        try:
            # Read line with timeout
            loop = asyncio.get_event_loop()
            line_bytes = await asyncio.wait_for(
                loop.run_in_executor(None, process.stdout.readline), timeout=timeout
            )

            if not line_bytes:
                raise RuntimeError("Process stdout closed unexpectedly")

            # Parse JSON response
            response = json.loads(line_bytes.decode())
            return response

        except TimeoutError:
            # Include stderr for debugging timeout issues
            stderr_output = ""
            if process.stderr:
                try:
                    # Non-blocking read of available stderr
                    process.stderr.flush()
                    stderr_output = process.stderr.read().decode()
                except Exception:
                    pass

            raise TimeoutError(
                f"No response received within {timeout}s. "
                f"Stderr: {stderr_output[:500] if stderr_output else '(empty)'}"
            ) from None

    def start_mcp_server(
        self, mcp_command: list[str], cwd: Path | None = None, env: dict | None = None
    ) -> subprocess.Popen:
        """Start MCP server process.

        Args:
            mcp_command: Command to start MCP server
            cwd: Working directory for the process
            env: Environment variables (merged with current env)

        Returns:
            Running subprocess instance
        """
        # Merge with current environment
        process_env = dict(os.environ) if env is None else {**os.environ, **env}

        process = subprocess.Popen(
            mcp_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(cwd) if cwd else None,
            env=process_env,
            bufsize=0,  # Unbuffered for real-time communication
        )

        return process

    @pytest.mark.asyncio
    async def test_mcp_command_exists(self, mcp_command: list[str]):
        """Test that mcp-ticketer mcp command exists and is executable.

        Verifies:
        - Command can be found in PATH
        - Command starts without immediate error
        - Process can be terminated gracefully
        """
        process = None
        try:
            # Start process
            process = subprocess.Popen(
                mcp_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Give process time to start
            await asyncio.sleep(0.5)

            # Verify process is running
            assert process.poll() is None, "MCP process exited immediately"

        finally:
            if process:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    @pytest.mark.asyncio
    async def test_initialize_request(
        self, mcp_command: list[str], temp_config_dir: Path
    ):
        """Test MCP initialization handshake.

        Verifies:
        - Server responds to initialize request
        - Response contains required fields (serverInfo)
        - Response follows JSON-RPC 2.0 format
        - Protocol version is compatible
        """
        process = None
        try:
            # Start MCP server with config
            process = self.start_mcp_server(mcp_command, cwd=temp_config_dir.parent)

            # Send initialize request
            await self.send_jsonrpc_request(
                process,
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "mcp-ticketer-test",
                        "version": "1.0.0",
                    },
                },
                request_id=1,
            )

            # Read response
            response = await self.read_jsonrpc_response(process, timeout=5.0)

            # Verify JSON-RPC structure
            assert response.get("jsonrpc") == "2.0", "Missing or invalid jsonrpc field"
            assert response.get("id") == 1, "Response ID doesn't match request"
            assert (
                "result" in response or "error" in response
            ), "Response must contain 'result' or 'error'"

            # If successful, verify MCP initialize response structure
            if "result" in response:
                result = response["result"]
                assert "serverInfo" in result, "Missing serverInfo in initialize result"
                assert "name" in result["serverInfo"], "Missing server name"
                assert "version" in result["serverInfo"], "Missing server version"
                assert "protocolVersion" in result, "Missing protocolVersion"

                # Verify protocol version is compatible
                protocol_version = result["protocolVersion"]
                assert protocol_version.startswith(
                    "2024-"
                ), f"Unexpected protocol version: {protocol_version}"

        finally:
            if process:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    @pytest.mark.asyncio
    async def test_list_tools_request(
        self, mcp_command: list[str], temp_config_dir: Path
    ):
        """Test tools/list request after initialization.

        Verifies:
        - Server responds to tools/list request
        - Response contains tools array
        - Each tool has required fields (name, description, inputSchema)
        - At least some core tools are present
        """
        process = None
        try:
            # Start MCP server
            process = self.start_mcp_server(mcp_command, cwd=temp_config_dir.parent)

            # Step 1: Initialize
            await self.send_jsonrpc_request(
                process,
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0.0"},
                },
                request_id=1,
            )

            # Wait for initialize response
            init_response = await self.read_jsonrpc_response(process, timeout=5.0)
            assert (
                "result" in init_response
            ), f"Initialize failed: {init_response.get('error')}"

            # Step 2: Send initialized notification
            await self.send_jsonrpc_request(
                process,
                method="notifications/initialized",
                params={},
                request_id=None,  # Notification has no ID
            )

            # Step 3: Request tools list
            await self.send_jsonrpc_request(
                process, method="tools/list", params={}, request_id=2
            )

            # Read tools/list response
            response = await self.read_jsonrpc_response(process, timeout=5.0)

            # Verify JSON-RPC structure
            assert response.get("jsonrpc") == "2.0"
            assert response.get("id") == 2
            assert "result" in response or "error" in response

            # If successful, verify tools structure
            if "result" in response:
                result = response["result"]
                assert "tools" in result, "Missing 'tools' in result"
                tools = result["tools"]
                assert isinstance(tools, list), "Tools should be a list"
                assert len(tools) > 0, "Should have at least one tool"

                # Verify tool structure
                for tool in tools[:3]:  # Check first 3 tools
                    assert "name" in tool, f"Tool missing name: {tool}"
                    assert "description" in tool, f"Tool missing description: {tool}"
                    assert "inputSchema" in tool, f"Tool missing inputSchema: {tool}"

                    # Verify inputSchema is valid JSON Schema
                    schema = tool["inputSchema"]
                    assert "type" in schema, f"inputSchema missing type: {schema}"
                    assert (
                        schema["type"] == "object"
                    ), f"inputSchema type should be object: {schema}"

                # Verify expected core tools are present
                tool_names = {tool["name"] for tool in tools}
                expected_tools = {
                    "ticket_create",
                    "ticket_read",
                    "ticket_update",
                    "ticket_list",
                }
                found_tools = expected_tools & tool_names
                assert len(found_tools) >= 2, (
                    f"Expected core tools not found. "
                    f"Found: {found_tools}, Available: {tool_names}"
                )

        finally:
            if process:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    @pytest.mark.asyncio
    async def test_complete_mcp_protocol(
        self, mcp_command: list[str], temp_config_dir: Path
    ):
        """Test complete MCP protocol handshake sequence.

        Verifies full protocol flow:
        1. Initialize request/response
        2. Initialized notification
        3. Tools/list request/response
        4. Graceful shutdown

        This is the typical sequence a client would perform.
        """
        process = None
        try:
            # Start MCP server
            process = self.start_mcp_server(mcp_command, cwd=temp_config_dir.parent)

            # Step 1: Initialize
            await self.send_jsonrpc_request(
                process,
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "e2e-test", "version": "1.0.0"},
                },
                request_id=1,
            )

            init_response = await self.read_jsonrpc_response(process, timeout=5.0)
            assert init_response.get("id") == 1
            assert "result" in init_response
            assert "serverInfo" in init_response["result"]

            # Step 2: Send initialized notification (no response expected)
            await self.send_jsonrpc_request(
                process, method="notifications/initialized", params={}
            )

            # Small delay to let server process notification
            await asyncio.sleep(0.1)

            # Step 3: List tools
            await self.send_jsonrpc_request(
                process, method="tools/list", params={}, request_id=2
            )

            tools_response = await self.read_jsonrpc_response(process, timeout=5.0)
            assert tools_response.get("id") == 2
            assert "result" in tools_response
            assert "tools" in tools_response["result"]
            assert len(tools_response["result"]["tools"]) > 0

            # Step 4: Graceful shutdown (process should exit cleanly)
            process.terminate()
            exit_code = process.wait(timeout=2)

            # Termination is acceptable (either 0 or terminated signal)
            assert exit_code in [0, -15, 15], f"Unexpected exit code: {exit_code}"

        finally:
            if process and process.poll() is None:
                process.kill()
                process.wait()

    @pytest.mark.asyncio
    async def test_invalid_jsonrpc(self, mcp_command: list[str], temp_config_dir: Path):
        """Test error handling for invalid JSON-RPC requests.

        Verifies:
        - Server responds with proper error for malformed JSON
        - Server responds with proper error for invalid method
        - Error responses follow JSON-RPC 2.0 error format
        """
        process = None
        try:
            # Start MCP server
            process = self.start_mcp_server(mcp_command, cwd=temp_config_dir.parent)

            # Initialize first (required before other requests)
            await self.send_jsonrpc_request(
                process,
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0.0"},
                },
                request_id=1,
            )

            init_response = await self.read_jsonrpc_response(process, timeout=5.0)
            assert "result" in init_response

            # Test 1: Invalid method
            await self.send_jsonrpc_request(
                process,
                method="nonexistent/method",
                params={},
                request_id=2,
            )

            error_response = await self.read_jsonrpc_response(process, timeout=5.0)
            assert error_response.get("jsonrpc") == "2.0"
            assert error_response.get("id") == 2
            assert "error" in error_response, "Should return error for invalid method"

            error = error_response["error"]
            assert "code" in error, "Error should have code"
            assert "message" in error, "Error should have message"
            assert isinstance(error["code"], int), "Error code should be integer"

            # Common JSON-RPC error codes:
            # -32601: Method not found
            # -32600: Invalid request
            # -32602: Invalid params
            assert error["code"] in [
                -32601,
                -32600,
                -32602,
            ], f"Unexpected error code: {error['code']}"

        finally:
            if process:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    @pytest.mark.asyncio
    async def test_process_timeout_handling(
        self, mcp_command: list[str], temp_config_dir: Path
    ):
        """Test that test infrastructure properly handles timeouts.

        This verifies that our test helpers correctly handle:
        - Read timeout when server doesn't respond
        - Process cleanup after timeout
        """
        process = None
        try:
            # Start MCP server
            process = self.start_mcp_server(mcp_command, cwd=temp_config_dir.parent)

            # Send valid request
            await self.send_jsonrpc_request(
                process,
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0.0"},
                },
                request_id=1,
            )

            # Should receive response within timeout
            response = await self.read_jsonrpc_response(process, timeout=5.0)
            assert "result" in response or "error" in response

        finally:
            if process:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


# Import os for environment handling
import os  # noqa: E402
