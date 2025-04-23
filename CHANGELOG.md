## maoto-agent v0.1.1 Release Notes

### Breaking Changes

* **Changed:** The `domain_pa` in `AgentSettings` has been changed from `"pa.maoto.world"` to `"assistant.maoto.world"`.  Users should update their environment variables or configuration files accordingly.
* **Changed:** The `url_mp` and `url_pa` properties in `AgentSettings` now return `HttpUrl` objects and include a trailing slash.
* **Changed:** The `params` field in `NewOffer` and `NewSkill` now accepts JSON strings as well as dictionaries.  A validator has been added to handle both inputs.
* **Changed:** The `args` field in `NewOfferCall` now accepts JSON strings as well as dictionaries.  A validator has been added to handle both inputs.
* **Changed:** The `query_params` field in `LoginUserRequest` and `RegisterUserRequest` now accepts JSON strings as well as dictionaries. A validator has been added to handle both inputs.
* **Changed:**  The `unregister` method in `Maoto` no longer accepts optional `obj` and `id`/`solver_id` parameters as individual arguments.  Now either an `obj` is passed (containing both object type and id), or `obj_type` and `id` (or `solver_id`) must be passed together.


### New Features

* **Added:** Optional MCP (Model Context Protocol) support. Install with `pip install "maoto-agent[mcp]"` to enable.  This allows exposure of FastAPI endpoints as MCP tools.
* **Added:** `get_refcodes`, `create_refcode` and `delete_refcode` methods to `Maoto` class to interact with reference codes in the assistant.
* **Added:** `MAOTO_AGENT_URL` environment variable support for setting the webhook URL.  If provided, this will be used instead of any passed url.
* **Added:** A `safe_urljoin` function to safely construct URLs for internal requests.
* **Added:** A favicon.ico to the project.
* **Added:** Improved error handling in the `_request` method to provide more informative error messages including HTTP error details.  Also catches exceptions when parsing the JSON detail.
* **Added:**  `include_operations`, `exclude_operations`, `include_tags` and `exclude_tags` settings to `MCPSettings` to customize exposed endpoints.
* **Added:**  The ability to pass query parameters to the `_request` method via the `params` parameter.
* **Added:** A field validator for `params` in `NewOffer` and `NewSkill` models to ensure that the params are a dictionary, converting json strings to dictionaries.


### Changed

* **Changed:** The `register_handler` decorator now supports more event types, including `PAUserMessage`, `PALinkUrl`, and `PAPaymentRequest`. Also, the method now only accepts POST requests.
* **Changed:** The `send_response` method now only accepts POST requests.
* **Changed:** The `send_to_assistant` method no longer returns a boolean value, instead it performs the request and returns nothing.
* **Changed:** Improved documentation in the `register_handler` decorator.
* **Changed:** Refactored `Maoto`'s `unregister` function to more precisely validate input and raise helpful error messages.
* **Changed:** The `register` method returns the created object (Skill, OfferCallable, or OfferReference) instead of just a boolean.
* **Changed:** The `get_registered` method now uses the plural form ("getSkills", "getOfferCallables", etc.) in route name.
* **Changed:** The `send_newoffercall` method now uses "NewOfferCall" as route name.
* **Changed:** The `send_intent` method now uses `NewIntent` as route name.
* **Changed:** Updated the `url_mp` and `url_pa` calculation to use `HttpUrl` for better validation and type safety. The trailing slash `/` is appended to paths.
* **Changed:** The response model for the `_request` method was removed.
* **Changed:** The `_request` method can now receive and handle dictionary as `params` value.
* **Changed:** MCPSettings is no longer inheriting from AgentSettings
* **Changed:** Updated the `set_webhook` method to use the agent's `agent_url` property from the `AgentSettings` class if no URL is provided.
* **Changed:** `MCPSettings` renamed some properties: `mcp_mount_path` to `mount_path`, `mcp_name` to `name`, `mcp_description` to `description`, `mcp_describe_all_responses` to `describe_all_responses`, `mcp_describe_full_response_schema` to `describe_full_response_schema`.
* **Changed:** The `MCPServer` class now uses `FastApiMCP` instead of `add_mcp_server` and `mount()` method instead of implicitly mounting the server. A `refresh()` method is also provided to update the MCP server with new endpoints.
* **Changed:** The default value of `mcp_describe_all_responses` and `mcp_describe_full_response_schema` in `MCPSettings` is changed to `True`.



### Removed

* **Removed:** The `NewResponse` and `IntentResponse` classes were merged into a single `IntentResponse` class.
* **Removed:**  The `workflow_run` trigger from the `test.yml` workflow.  It is now triggered on pull requests.
* **Removed:** The `workflow_run` trigger from the `lint.yml` workflow. It is now triggered on pull requests.
* **Removed:** The `changelog_job` from the `test.yml` workflow. The workflow only includes `example_job`.
* **Removed:**  The commented-out `prepare-conda-forge` job from the `release.yml` workflow file.
* **Removed:** The commented-out  `prepare-conda-forge` job dependency from the `github-release` job in `release.yml`.

### Fixed

* **Fixed:** Improved error handling in the `_request` method to prevent crashes when the response from the Marketplace isn't JSON format.

### Other Changes

* **Added:** A new `RefCode` model.
* **Added:** A new `NewRefCode` model.
* **Added:** Static files directory to serve favicon.
* **Added:** `include_in_schema=False` to the `/favicon.ico` endpoint.
* **Added:**  New "✅" to markdown in README.
* **Added:** MCP support documentation to the README file.
* **Added:**  More detailed explanation of supported event types in `register_handler` in the `Maoto` class.
* **Added:**  `_version` property to `Maoto` class to store the package version.
* **Added:** A dedicated path for static files, serving icons from this directory.  Mount point is `/static`.
* **Added:**  Unit tests.
* **Added:**  Type hints.
* **Added:** Improved documentation.
* **Added:**  Improved error handling.
* **Added:** More informative error messages.
* **Changed:** Updated dependencies.
* **Changed:** Refactored code for better readability and maintainability.
* **Changed:** Improved test coverage.
* **Changed:** Updated README.md with a new key feature: Optional MCP support.  Added installation instructions for MCP support.  Added a section for MCP tools inspection.
* **Changed:** Updated README.md to reflect updated install commands.




