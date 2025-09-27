@echo off
REM MCP Server Wrapper - Ensures correct working directory for module loading
cd /d "%~dp0..\.."
"%~dp0..\..\.venv\Scripts\python.exe" -m mcp_server.server %*