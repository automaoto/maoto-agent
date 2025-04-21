## maoto-agent 0.1.1 Release Notes

### New Features

* **feat(mcp):** Add support for Model Context Protocol (MCP) via the `maoto-agent[mcp]` extra.  This allows exposing FastAPI endpoints as MCP tools.  Includes an MCP inspector for testing and viewing tools.  (Requires installing `fastapi-mcp` and `mcp`.)
* **feat(agent_url):** Add `agent_url` parameter to `AgentSettings` for flexible webhook URL configuration. Now you can set the URL for the webhook either using environment variables or the `agent_url` parameter.

### Changed

* **chore(README):**  Improved README.md with  installation instructions for MCP support, using the MCP inspector, and improved descriptions of features. Added checkmarks to the key features list.
* **chore(domain_pa):** Updated the `domain_pa` in `AgentSettings` from `"pa.maoto.world"` to `"assistant.maoto.world"`.
* **chore(url_mp & url_pa):** Updated `url_mp` and `url_pa` in `AgentSettings` to use `HttpUrl` type and added trailing slashes for consistency.
* **chore(app_types):** Updated `NewOffer`, `NewSkill`, `NewOfferCall`, `LoginUserRequest` and `RegisterUserRequest` classes to handle `json` input properly for fields `params` and `query_params`. This improves compatibility and avoids parsing errors.
* **chore(maoto_agent):** Updated the `register` function to handle potential exceptions from HTTP requests more gracefully and provides more informative error messages.  It uses `safe_urljoin` to handle URL joining and adds an additional check for unsupported types.
* **chore(maoto_agent):** Improved logging and error handling in the `_request` method, including more detailed error reporting for HTTP status errors and error message formatting.
* **chore(maoto_agent):** Updated `unregister` method to accept either an object or ID for flexibility. The endpoint now accepts both 'id' and 'solver_id' parameters to unregister based on different criteria.
* **chore(maoto_agent):** The `send_intent` function now uses the class name as the route for improved clarity.
* **chore(maoto_agent):** Refactored error handling in `_request`, providing more detailed information about HTTP errors. Also included `_safe_urljoin` to properly handle URL concatenation.
* **chore(maoto_agent):** Added `/favicon.ico` endpoint serving a favicon.ico file.
* **chore(maoto_agent):**  Added static file serving to serve the icons in the static directory. The `register_handler` function now includes a description for each supported event type in the documentation.



### Added

* **feat(static):** Added `static` directory with `favicon.ico` for improved branding.
* **feat(mcp_settings):** Added `mcp_include_operations`, `mcp_exclude_operations`, `mcp_include_tags`, and `mcp_exclude_tags` to `MCPSettings` for more fine-grained control over which endpoints are exposed as MCP tools. Default values for `mcp_describe_all_responses` and `mcp_describe_full_response_schema` are set to `True`.

### Deprecated

* None

### Removed

* None

### Fixed

* None

### Security

* None

### Other Changes

* **deps:** Updated dependencies to include: `fastapi_mcp>=0.1.7`, `mcp>=1.6.0` (required for MCP support).  The project now uses `importlib.resources` instead of `importlib_resources` for improved compatibility and clarity.
* **docs(app_types):** Improved the documentation of the type hints to enhance code clarity.



