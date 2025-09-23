@echo off
REM MCP Server Wrapper - Ensures correct working directory for module loading
cd /d "F:\RD_PROJECTS\COMPONENTS\Claude-context-MCP"
"F:\RD_PROJECTS\COMPONENTS\Claude-context-MCP\.venv\Scripts\python.exe" -m mcp_server.server %*