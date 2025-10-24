#!/usr/bin/env python3
"""Test the new diagnostic MCP tools."""

import asyncio
import json
import subprocess
import sys
import time
from typing import Any, Dict


async def test_mcp_tool(tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
    """Test an MCP tool by sending a JSON-RPC request."""
    if arguments is None:
        arguments = {}
    
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    # Start MCP server process
    process = subprocess.Popen(
        ["mcp-ticketer", "serve"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Send request
        request_json = json.dumps(request) + "\n"
        stdout, stderr = process.communicate(input=request_json, timeout=10)
        
        if stderr:
            print(f"Server stderr: {stderr}")
        
        # Parse response
        if stdout.strip():
            response = json.loads(stdout.strip())
            return response
        else:
            return {"error": "No response from server"}
            
    except subprocess.TimeoutExpired:
        process.kill()
        return {"error": "Request timed out"}
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON response: {e}"}
    except Exception as e:
        return {"error": f"Request failed: {e}"}
    finally:
        if process.poll() is None:
            process.terminate()


async def main():
    """Test the diagnostic MCP tools."""
    print("🔍 Testing MCP Diagnostic Tools")
    print("=" * 50)
    
    # Test system_health tool
    print("\n1. Testing system_health tool...")
    health_response = await test_mcp_tool("system_health")
    
    if "error" in health_response:
        print(f"❌ Health check failed: {health_response['error']}")
    else:
        print("✅ Health check completed")
        if "result" in health_response:
            content = health_response["result"].get("content", [])
            if content and len(content) > 0:
                print("📊 Health Status:")
                print(content[0].get("text", "No text content"))
            else:
                print("⚠️  No content in response")
        else:
            print(f"Response: {json.dumps(health_response, indent=2)}")
    
    # Test system_diagnose tool
    print("\n2. Testing system_diagnose tool...")
    diagnose_response = await test_mcp_tool("system_diagnose", {"include_logs": False})
    
    if "error" in diagnose_response:
        print(f"❌ Diagnosis failed: {diagnose_response['error']}")
    else:
        print("✅ Diagnosis completed")
        if "result" in diagnose_response:
            content = diagnose_response["result"].get("content", [])
            if content and len(content) > 0:
                print("📋 Diagnosis Report:")
                text = content[0].get("text", "No text content")
                # Show first 500 characters
                print(text[:500] + ("..." if len(text) > 500 else ""))
            else:
                print("⚠️  No content in response")
        else:
            print(f"Response: {json.dumps(diagnose_response, indent=2)}")
    
    # Test tools/list to verify our tools are registered
    print("\n3. Testing tools/list to verify diagnostic tools are registered...")
    list_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    
    process = subprocess.Popen(
        ["mcp-ticketer", "serve"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        request_json = json.dumps(list_request) + "\n"
        stdout, stderr = process.communicate(input=request_json, timeout=10)
        
        if stdout.strip():
            response = json.loads(stdout.strip())
            if "result" in response and "tools" in response["result"]:
                tools = response["result"]["tools"]
                diagnostic_tools = [t for t in tools if t["name"] in ["system_health", "system_diagnose"]]
                
                if diagnostic_tools:
                    print(f"✅ Found {len(diagnostic_tools)} diagnostic tools:")
                    for tool in diagnostic_tools:
                        print(f"  • {tool['name']}: {tool['description']}")
                else:
                    print("❌ No diagnostic tools found in tools list")
                    print(f"Available tools: {[t['name'] for t in tools]}")
            else:
                print(f"❌ Unexpected response: {response}")
        else:
            print("❌ No response from tools/list")
            
    except Exception as e:
        print(f"❌ Tools list failed: {e}")
    finally:
        if process.poll() is None:
            process.terminate()
    
    print("\n🎉 Diagnostic tools testing complete!")


if __name__ == "__main__":
    asyncio.run(main())
