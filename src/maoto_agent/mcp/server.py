from fastapi import FastAPI
from fastapi_mcp import add_mcp_server

from .mcp_settings import MCPSettings


class MCPServer:
    def __init__(self, app: FastAPI, settings: MCPSettings | None = None):
        """
        Initialize the MCP server with the given FastAPI app.

        Parameters
        ----------
        app : FastAPI
            The FastAPI application to mount the MCP server to
        settings : MCPSettings, optional
            MCP-specific settings. If not provided, will use default settings.
        """
        self._settings = settings or MCPSettings()

        self._server = add_mcp_server(
            app,
            mount_path=self._settings.mcp_mount_path,
            name=self._settings.mcp_name,
            description=self._settings.mcp_description,
            base_url=self._settings.url_mp,  # Inherited from AgentSettings
            describe_all_responses=self._settings.mcp_describe_all_responses,
            describe_full_response_schema=self._settings.mcp_describe_full_response_schema,
        )

    def add_tool(self, func):
        """
        Add a custom tool to the MCP server.

        Parameters
        ----------
        func : callable
            The function to add as a tool
        """
        return self._server.tool()(func)

    @property
    def server(self):
        """Get the underlying MCP server instance."""
        return self._server

    @property
    def settings(self) -> MCPSettings:
        """Get the MCP settings instance."""
        return self._settings
