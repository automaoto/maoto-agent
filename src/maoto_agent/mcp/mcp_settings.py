from pydantic import Field

from ..agent_settings import AgentSettings


class MCPSettings(AgentSettings):
    """
    MCP-specific settings that extend the base AgentSettings.
    """
    mcp_mount_path: str = Field(
        default="/mcp",
        description="The path to mount the MCP server at"
    )
    mcp_name: str = Field(
        default="Maoto Agent MCP",
        description="The name of the MCP server"
    )
    mcp_description: str = Field(
        default="MCP server for the Maoto Agent API",
        description="Description of the MCP server"
    )
    mcp_describe_all_responses: bool = Field(
        default=False,
        description="Whether to describe all responses in tool descriptions"
    )
    mcp_describe_full_response_schema: bool = Field(
        default=False,
        description="Whether to show full response schema in tool descriptions"
    )

    class Config:
        env_prefix = "MAOTO_MCP_"
        extra = "ignore"
