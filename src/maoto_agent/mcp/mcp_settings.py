from pydantic import Field
from pydantic_settings import BaseSettings

from ..agent_settings import AgentSettings


class MCPSettings():
    mount_path: str = Field(default="/mcp", description="The path to mount the MCP server at")
    name: str = Field(default="Maoto Agent MCP", description="The name of the MCP server")
    description: str = Field(
        default="MCP server for the Maoto Agent API", description="Description of the MCP server"
    )
    describe_all_responses: bool = Field(
        default=True, description="Whether to describe all responses in tool descriptions"
    )
    describe_full_response_schema: bool = Field(
        default=True, description="Whether to show full response schema in tool descriptions"
    )
    include_operations: list[str] | None = Field(
        default=None, description="List of operation IDs to include in the MCP server"
    )
    exclude_operations: list[str] | None = Field(
        default=None, description="List of operation IDs to exclude from the MCP server"
    )
    include_tags: list[str] | None = Field(
        default=None, description="List of tags to include in the MCP server"
    )
    exclude_tags: list[str] | None = Field(
        default=None, description="List of tags to exclude from the MCP server"
    )

    class Config:
        env_prefix = "MAOTO_MCP_"
        extra = "ignore"
