# MCP Server Troubleshooting Guide

## Common Issues and Solutions

### 1. Server Disconnection Error

**Symptoms**: Claude Desktop shows "portfolio-backtester server disconnected" error.

**Potential Causes & Solutions**:

#### A. Database Connection Issues
- **Issue**: Database file permissions or connection problems
- **Check**:
  ```bash
  ls -la data/portfolio.db
  python3 -c "from utils.database import SessionLocal; print('DB OK')"
  ```
- **Solution**: Ensure database file is readable/writable

#### B. Python Path Issues
- **Issue**: Module import failures due to incorrect PYTHONPATH
- **Check**: Verify PYTHONPATH in claude_desktop_config.json
- **Solution**: Ensure PYTHONPATH points to project root

#### C. Missing Dependencies
- **Issue**: Required packages not installed
- **Check**:
  ```bash
  /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -c "import fastmcp; print('FastMCP OK')"
  ```
- **Solution**: Install requirements:
  ```bash
  pip install -r mcp_server/requirements.txt
  ```

#### D. Python Version Compatibility
- **Issue**: Python version mismatch
- **Check**: Verify Python 3.12 is available at specified path
- **Solution**: Update python path in claude_desktop_config.json

### 2. Testing MCP Server

#### Manual Test
```bash
python3 mcp_server/test_server.py
```

#### Direct Server Start
```bash
PYTHONPATH=/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester \
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
mcp_server/portfolio_mcp_server.py
```

### 3. Configuration Verification

#### Check claude_desktop_config.json
```json
{
  "mcpServers": {
    "portfolio-backtester": {
      "command": "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
      "args": [
        "/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester/mcp_server/portfolio_mcp_server.py"
      ],
      "cwd": "/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester",
      "env": {
        "PYTHONPATH": "/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester"
      }
    }
  }
}
```

### 4. Recent Fixes Applied

#### Fixed Variable Name Conflict in Data Service
- **Issue**: `'Ticker' object has no attribute 'replace'` errors
- **Location**: `services/data_service.py:106-131`
- **Fix**: Renamed `ticker` variable to `ticker_obj` to avoid conflict

#### Improved Database Session Management
- **Issue**: Generator object used instead of database engine
- **Location**: `mcp_server/portfolio_mcp_server.py:44-68`
- **Fix**: Added proper `get_db_session()` function and connectivity test

#### Updated Requirements
- **Issue**: Incorrect MCP SDK dependency
- **Fix**: Updated requirements.txt to use `fastmcp>=2.12.0`

### 5. Monitoring and Logs

#### Check Application Logs
```bash
tail -f logs/portfolio_app.log
tail -f logs/portfolio_errors.log
```

#### Check MCP Server Logs
```bash
tail -f mcp_server/logs/portfolio_app.log
tail -f mcp_server/logs/portfolio_errors.log
```

### 6. Performance Considerations

#### Deprecation Warnings
- Current warnings about Google protobuf are harmless
- These warnings appear during import but don't affect functionality

#### Database Performance
- SQLite WAL mode enabled for concurrent access
- Connection pooling through SQLAlchemy

### 7. Environment Requirements

- Python 3.12 (as specified in config)
- FastMCP 2.12.2+
- SQLAlchemy 2.0+
- All dependencies in requirements.txt

### 8. Quick Health Check Commands

```bash
# Test imports
python3 -c "from mcp_server.portfolio_mcp_server import mcp; print('Server imports OK')"

# Test database
python3 -c "from utils.database import SessionLocal; s=SessionLocal(); print('DB session OK'); s.close()"

# Test server startup
python3 mcp_server/test_server.py

# Test configuration
python3 -c "import json; print(json.load(open('mcp_server/claude_desktop_config.json')))"
```

## Recent Update: Claude Desktop Compatibility Fix

### Issue: FastMCP Logo Interfering with Claude Desktop
**Problem**: FastMCP displays a banner/logo on startup that interferes with Claude Desktop's MCP protocol communication.

**Solution**: Created a wrapper script to suppress FastMCP output:
- **Wrapper Script**: `mcp_server/server_wrapper.py`
- **Updated Configuration**: Uses wrapper instead of direct server execution
- **Output Suppression**: Redirects stderr to /dev/null during startup

### Updated Configuration
```json
{
  "mcpServers": {
    "portfolio-backtester": {
      "command": "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
      "args": [
        "/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester/mcp_server/server_wrapper.py"
      ],
      "cwd": "/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester",
      "env": {
        "PYTHONPATH": "/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester"
      }
    }
  }
}
```

### Alternative Server Option
If the wrapper approach doesn't work, a standard MCP server implementation is available:
- **Alternative Server**: `mcp_server/portfolio_mcp_server_standard.py`
- **Standard MCP SDK**: Uses official MCP protocol implementation
- **No Output Pollution**: Cleaner communication with Claude Desktop

## Status: UPDATED ✅

As of 2025-09-21 20:30, the MCP server has been updated for Claude Desktop compatibility:
- ✅ Database connectivity test passed (10 portfolios found)
- ✅ Server initialization successful
- ✅ FastMCP output suppression implemented
- ✅ Wrapper script created for Claude Desktop compatibility
- ✅ Alternative standard MCP server available
- ✅ All imports and dependencies resolved

### Try These Solutions in Order:
1. **Primary**: Use updated configuration with wrapper script
2. **Fallback**: Switch to standard MCP server if needed
3. **Debug**: Check logs and run test scripts for diagnostics