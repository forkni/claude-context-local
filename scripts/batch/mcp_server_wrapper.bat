@echo off
setlocal
REM MCP Server Wrapper - Ensures correct working directory for module loading
pushd "%~dp0..\.." || (echo ERROR: Failed to change directory & exit /b 1)
"%~dp0..\..\.venv\Scripts\python.exe" -m mcp_server.server %*
popd
endlocal