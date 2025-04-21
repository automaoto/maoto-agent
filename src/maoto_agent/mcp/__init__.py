"""
MCP (Model Context Protocol) integration for Maoto Agent.

This module provides integration with FastAPI-MCP to expose FastAPI endpoints
as MCP tools. To use this functionality, install the package with MCP support:

    pip install "maoto-agent[mcp]"

This will install the required dependencies:
- fastapi-mcp>=0.1.7
- mcp>=1.6.0

To inspect and test your MCP tools, you can use the MCP inspector:

1. Start your FastAPI application with MCP enabled:
    ```python
    from maoto_agent.maoto_agent import Maoto
    from maoto_agent.mcp import MCPServer
    from pydantic import SecretStr

    # Create the FastAPI app with required API key
    app = Maoto(apikey=SecretStr("your-api-key-here"))  # Replace with your actual API key
    mcp = MCPServer(app)
    ```

2. Run your application using the correct module path and class name:
    ```bash
    # Set the API key as an environment variable, the below is just an example
    export MAOTO_APIKEY="your-api-key-here"
    uvicorn src.maoto_agent.maoto_agent:Maoto --reload
    ```

3. Open the MCP inspector in your browser:
    ```bash
    # use the correct path based on the app created
    npx @modelcontextprotocol/inspector python -m src.maoto_agent.mcp.server
    ```

The inspector provides a web interface to:
- View all available MCP tools
- Test tools with different parameters
- View tool documentation and schemas
- Monitor tool execution
"""

from .mcp_settings import MCPSettings
from .server import MCPServer

__all__ = ["MCPSettings", "MCPServer"]
