from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

from .mcp_settings import MCPSettings


class MCPServer:
    def __init__(self, app: FastAPI):
        """
        Initialize the MCP server with the given FastAPI app.

        Parameters
        ----------
        app : FastAPI
            The FastAPI application to mount the MCP server to
        settings : MCPSettings, optional
            MCP-specific settings. If not provided, will use default settings.
        """

        self._settings = MCPSettings()

        # Create the MCP server
        self._mcp = FastApiMCP(
            app,
            name=str(self._settings.name),
            description=str(self._settings.description),
            #base_url=self._settings.agent.url_mp,
            describe_all_responses=self._settings.describe_all_responses,
            describe_full_response_schema=self._settings.describe_full_response_schema,
            #include_operations=self._settings.include_operations,
            #exclude_operations=self._settings.exclude_operations,
            #include_tags=self._settings.include_tags,
            #exclude_tags=self._settings.exclude_tags,
        )

        # Mount the MCP server
        self._mcp.mount()

    def add_tool(self, func):
        """
        Add a custom tool to the MCP server.

        Parameters
        ----------
        func : callable
            The function to add as a tool
        """
        return self._mcp.tool()(func)

    def refresh(self):
        """
        Refresh the MCP server to include any new endpoints that were added
        after the server was created.
        """
        self._mcp.setup_server()

    @property
    def mcp(self) -> FastApiMCP:
        """Get the underlying FastApiMCP instance."""
        return self._mcp

    @property
    def settings(self) -> MCPSettings:
        """Get the MCP settings instance."""
        return self._settings
