"""End-to-end tests for MCP analysis tools graceful degradation.

This module verifies that analysis tools correctly handle scenarios with
and without optional analysis dependencies (scikit-learn, rapidfuzz, numpy):

- Tools list includes analysis tools regardless of dependencies
- Graceful error messages when dependencies are missing
- Successful operation when dependencies are available

Tests focus on protocol-level behavior via JSON-RPC over stdio.
"""

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

# Try to import ANALYSIS_AVAILABLE flag
try:
    from mcp_ticketer.mcp.server.tools.analysis_tools import ANALYSIS_AVAILABLE
except ImportError:
    ANALYSIS_AVAILABLE = False


@pytest.mark.e2e
class TestMCPAnalysisToolsGracefulDegradation:
    """Test analysis tools behavior with/without optional dependencies."""

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

    async def initialize_mcp_session(self, process: subprocess.Popen) -> dict[str, Any]:
        """Complete MCP initialization handshake.

        Args:
            process: Running MCP server process

        Returns:
            Initialize response result

        Raises:
            AssertionError: If initialization fails
        """
        # Step 1: Send initialize request
        await self.send_jsonrpc_request(
            process,
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "analysis-tools-test",
                    "version": "1.0.0",
                },
            },
            request_id=1,
        )

        # Step 2: Read initialize response
        init_response = await self.read_jsonrpc_response(process, timeout=5.0)
        assert "result" in init_response, f"Initialize failed: {init_response}"

        # Step 3: Send initialized notification
        await self.send_jsonrpc_request(
            process,
            method="notifications/initialized",
            params={},
            request_id=None,  # Notifications have no ID
        )

        # Small delay for notification processing
        await asyncio.sleep(0.1)

        return init_response["result"]

    @pytest.mark.asyncio
    async def test_tools_list_includes_analysis_tools(
        self, mcp_command: list[str], temp_config_dir: Path
    ):
        """Test that tools/list includes analysis tools regardless of dependencies.

        Verifies:
        - Analysis tools appear in tools list
        - Tools have proper schema definition
        - Expected analysis tools are present:
          * ticket_find_similar
          * ticket_find_stale
          * ticket_find_orphaned
          * ticket_cleanup_report
        """
        process = None
        try:
            # Start MCP server
            process = self.start_mcp_server(mcp_command, cwd=temp_config_dir.parent)

            # Initialize MCP session
            await self.initialize_mcp_session(process)

            # Request tools list
            await self.send_jsonrpc_request(
                process, method="tools/list", params={}, request_id=2
            )

            # Read tools/list response
            response = await self.read_jsonrpc_response(process, timeout=5.0)

            # Verify JSON-RPC structure
            assert response.get("jsonrpc") == "2.0"
            assert response.get("id") == 2
            assert "result" in response, f"Tools list failed: {response.get('error')}"

            # Extract tools
            result = response["result"]
            assert "tools" in result, "Missing 'tools' in result"
            tools = result["tools"]
            assert isinstance(tools, list), "Tools should be a list"

            # Check for analysis tools
            tool_names = {tool["name"] for tool in tools}
            expected_analysis_tools = {
                "ticket_find_similar",
                "ticket_find_stale",
                "ticket_find_orphaned",
                "ticket_cleanup_report",
            }

            found_analysis_tools = expected_analysis_tools & tool_names
            assert found_analysis_tools == expected_analysis_tools, (
                f"Not all analysis tools found. "
                f"Expected: {expected_analysis_tools}, "
                f"Found: {found_analysis_tools}, "
                f"All tools: {tool_names}"
            )

            # Verify tool structure for analysis tools
            for tool in tools:
                if tool["name"] in expected_analysis_tools:
                    assert "description" in tool, f"Tool missing description: {tool}"
                    assert "inputSchema" in tool, f"Tool missing inputSchema: {tool}"

                    # Verify inputSchema is valid JSON Schema
                    schema = tool["inputSchema"]
                    assert "type" in schema, f"inputSchema missing type: {schema}"
                    assert (
                        schema["type"] == "object"
                    ), f"inputSchema type should be object: {schema}"
                    assert (
                        "properties" in schema
                    ), f"inputSchema missing properties: {schema}"

        finally:
            if process:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    @pytest.mark.asyncio
    async def test_analysis_tools_graceful_degradation_without_dependencies(
        self, mcp_command: list[str], temp_config_dir: Path
    ):
        """Test analysis tools return helpful errors when dependencies missing.

        This test simulates an environment without scikit-learn by manipulating
        Python's import system via PYTHONPATH exclusion or module mocking.

        Verifies:
        - Tool call succeeds at protocol level (no crash)
        - Response indicates dependencies are missing
        - Response includes installation instructions
        - Server continues to operate normally
        """
        process = None
        try:
            # Create environment that blocks analysis imports
            # We'll create a stub that makes imports fail
            stub_dir = temp_config_dir.parent / "import_stub"
            stub_dir.mkdir(exist_ok=True)

            # Create a stub sklearn module that raises ImportError
            sklearn_stub = stub_dir / "sklearn"
            sklearn_stub.mkdir(exist_ok=True)
            (sklearn_stub / "__init__.py").write_text(
                "raise ImportError('sklearn not available in test')"
            )

            # Modify PYTHONPATH to prioritize stub
            test_env = dict(os.environ)
            existing_path = test_env.get("PYTHONPATH", "")
            test_env["PYTHONPATH"] = (
                f"{stub_dir}:{existing_path}" if existing_path else str(stub_dir)
            )

            # Also set MCP_TICKETER_NO_ANALYSIS flag for explicit testing
            test_env["MCP_TICKETER_NO_ANALYSIS"] = "1"

            # Start MCP server with modified environment
            process = self.start_mcp_server(
                mcp_command, cwd=temp_config_dir.parent, env=test_env
            )

            # Initialize MCP session
            await self.initialize_mcp_session(process)

            # Call ticket_find_similar tool
            await self.send_jsonrpc_request(
                process,
                method="tools/call",
                params={
                    "name": "ticket_find_similar",
                    "arguments": {"threshold": 0.8, "limit": 10},
                },
                request_id=3,
            )

            # Read response
            response = await self.read_jsonrpc_response(process, timeout=5.0)

            # Verify JSON-RPC structure
            assert response.get("jsonrpc") == "2.0"
            assert response.get("id") == 3

            # Response should succeed at protocol level
            # (even if tool reports an error in its result)
            if "error" in response:
                # Protocol-level error is acceptable but not required
                error = response["error"]
                assert "code" in error
                assert "message" in error
            else:
                # Result-level error is the expected pattern
                assert "result" in response

                # The tool should return an error status in its result
                tool_result = response["result"]
                assert "content" in tool_result

                # Parse tool content (MCP wraps tool output)
                content_items = tool_result["content"]
                assert isinstance(content_items, list)
                assert len(content_items) > 0

                # Extract actual tool response
                tool_output = json.loads(content_items[0]["text"])

                # Verify graceful error response
                assert (
                    tool_output.get("status") == "error"
                ), f"Expected error status, got: {tool_output}"
                assert "error" in tool_output or "message" in tool_output
                assert (
                    "dependencies" in tool_output.get("message", "").lower()
                    or "analysis" in tool_output.get("error", "").lower()
                )

                # Verify installation instructions are provided
                message = tool_output.get("message", "")
                assert (
                    "pip install" in message or "required_packages" in tool_output
                ), f"Missing installation instructions: {tool_output}"

            # Verify server still works - call another tool
            await self.send_jsonrpc_request(
                process, method="tools/list", params={}, request_id=4
            )

            tools_response = await self.read_jsonrpc_response(process, timeout=5.0)
            assert tools_response.get("id") == 4
            assert "result" in tools_response, "Server crashed after error"

        finally:
            if process:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not ANALYSIS_AVAILABLE,
        reason="Analysis dependencies not installed (scikit-learn, rapidfuzz, numpy)",
    )
    async def test_analysis_tools_work_with_dependencies(
        self, mcp_command: list[str], temp_config_dir: Path
    ):
        """Test analysis tools work correctly when dependencies are available.

        This test only runs when analysis dependencies are installed.

        Verifies:
        - Tool call succeeds at protocol level
        - Response indicates completion (not error)
        - Server operates normally
        - Tool returns expected data structure
        """
        process = None
        try:
            # Start MCP server (normal environment with dependencies)
            process = self.start_mcp_server(mcp_command, cwd=temp_config_dir.parent)

            # Initialize MCP session
            await self.initialize_mcp_session(process)

            # Call ticket_find_similar tool
            await self.send_jsonrpc_request(
                process,
                method="tools/call",
                params={
                    "name": "ticket_find_similar",
                    "arguments": {"threshold": 0.8, "limit": 10},
                },
                request_id=3,
            )

            # Read response
            response = await self.read_jsonrpc_response(process, timeout=10.0)

            # Verify JSON-RPC structure
            assert response.get("jsonrpc") == "2.0"
            assert response.get("id") == 3
            assert "result" in response, f"Tool call failed: {response.get('error')}"

            # Parse tool result
            tool_result = response["result"]
            assert "content" in tool_result

            content_items = tool_result["content"]
            assert isinstance(content_items, list)
            assert len(content_items) > 0

            # Extract actual tool response
            tool_output = json.loads(content_items[0]["text"])

            # Verify successful response structure
            assert tool_output.get("status") == "completed", (
                f"Expected completed status, got: {tool_output.get('status')}. "
                f"Error: {tool_output.get('error')}"
            )

            # Verify expected data structure
            # (May have no tickets, but structure should be correct)
            assert "similar_tickets" in tool_output
            assert "count" in tool_output

            # Count should be non-negative
            assert tool_output["count"] >= 0

            # If enough tickets were analyzed, should have threshold field
            if "tickets_analyzed" in tool_output:
                assert tool_output["tickets_analyzed"] >= 0
                assert "threshold" in tool_output

            # If no tickets or not enough tickets, message should explain why
            if tool_output["count"] == 0:
                assert (
                    "message" in tool_output
                    or tool_output.get("tickets_analyzed", 0) < 2
                ), "Empty result should have explanation"

            # Verify other analysis tools work too
            for tool_name in [
                "ticket_find_stale",
                "ticket_find_orphaned",
                "ticket_cleanup_report",
            ]:
                await self.send_jsonrpc_request(
                    process,
                    method="tools/call",
                    params={
                        "name": tool_name,
                        "arguments": {},
                    },
                    request_id=tool_name,
                )

                tool_response = await self.read_jsonrpc_response(process, timeout=10.0)
                assert (
                    "result" in tool_response
                ), f"{tool_name} failed: {tool_response.get('error')}"

                # Parse result
                result_content = json.loads(
                    tool_response["result"]["content"][0]["text"]
                )
                assert result_content.get("status") == "completed", (
                    f"{tool_name} returned error: " f"{result_content.get('error')}"
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
    async def test_analysis_tool_error_messages_are_helpful(
        self, mcp_command: list[str], temp_config_dir: Path
    ):
        """Test that analysis tools provide actionable error messages.

        Verifies:
        - Error messages mention the specific missing capability
        - Installation instructions are clear and actionable
        - Required package names and versions are listed
        """
        process = None
        try:
            # Create environment that blocks analysis imports
            stub_dir = temp_config_dir.parent / "import_stub"
            stub_dir.mkdir(exist_ok=True)

            # Create stubs for all analysis dependencies
            for pkg_name in ["sklearn", "rapidfuzz", "numpy"]:
                pkg_stub = stub_dir / pkg_name
                pkg_stub.mkdir(exist_ok=True)
                (pkg_stub / "__init__.py").write_text(
                    f"raise ImportError('{pkg_name} not available in test')"
                )

            # Modify environment
            test_env = dict(os.environ)
            existing_path = test_env.get("PYTHONPATH", "")
            test_env["PYTHONPATH"] = (
                f"{stub_dir}:{existing_path}" if existing_path else str(stub_dir)
            )

            # Start MCP server
            process = self.start_mcp_server(
                mcp_command, cwd=temp_config_dir.parent, env=test_env
            )

            # Initialize
            await self.initialize_mcp_session(process)

            # Test each analysis tool for helpful error messages
            analysis_tools = [
                "ticket_find_similar",
                "ticket_find_stale",
                "ticket_find_orphaned",
                "ticket_cleanup_report",
            ]

            for idx, tool_name in enumerate(analysis_tools, start=10):
                await self.send_jsonrpc_request(
                    process,
                    method="tools/call",
                    params={"name": tool_name, "arguments": {}},
                    request_id=idx,
                )

                response = await self.read_jsonrpc_response(process, timeout=5.0)
                assert response.get("id") == idx

                # Extract tool output
                if "result" in response:
                    content = response["result"]["content"]
                    tool_output = json.loads(content[0]["text"])

                    if tool_output.get("status") == "error":
                        # Verify error message quality
                        message = tool_output.get("message", "")
                        error = tool_output.get("error", "")
                        combined = f"{error} {message}".lower()

                        # Should mention analysis or dependencies
                        assert (
                            "analysis" in combined or "dependencies" in combined
                        ), f"{tool_name}: Error message not clear: {tool_output}"

                        # Should include installation command
                        assert "pip install" in message, (
                            f"{tool_name}: Missing pip install command: "
                            f"{tool_output}"
                        )

                        # Should list required packages
                        assert (
                            "required_packages" in tool_output
                            or "scikit-learn" in message
                        ), f"{tool_name}: Missing package list: {tool_output}"

        finally:
            if process:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
