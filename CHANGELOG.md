# Release Notes

## 0.2.0

### New Features

* **feat(mcp):** Add optional MCP support.  Install with `pip install "maoto-agent[mcp]"`.  Includes an MCP inspector for testing.
* **feat(agent):** Add optional `agent_url` setting to `AgentSettings` for flexible webhook URLs. Can be set via environment variable `MAOTO_AGENT_URL`.
* **feat(app):** Add favicon to the application.
* **feat(app):** Serve static files from `/static` and include a default `/favicon.ico`.
* **feat(response):** Include `provider_id` field in `IntentResponse` and `OfferCallResponse`.
* **feat(offer):** Add `solver_id` field to `NewOffer` and `NewSkill` (replaces `resolver_id`).
* **feat(offer):** Add field validator to `NewOffer.params` and `NewSkill.params` to ensure it's a dict.
* **feat(query_params):** Add field validator to  `LoginUserRequest.query_params`, `RegisterUserRequest.query_params`, and `EmailVerif.query_params` to ensure they are dicts.
* **feat(offercall):** Add `provider_id` field to `NewOfferCall` and include field validator to `NewOfferCall.args` to ensure it's a dict.
* **feat(agent):** Update `_request` to return `None` when `result_type` is `None`


### Changed

* **change(agent):**  Improve error handling in `_request` for better detail and clarity in HTTP errors.
* **chore(agent):** Use `safe_urljoin` in `_request` to correctly handle base URL and routes.
* **change(agent):** Rename `resolver_id` to `solver_id` across all relevant types and endpoints.
* **chore(agent):** Update `send_newoffercall` to take `NewOfferCall` as an argument.
* **chore(agent):**  Refactor `send_response` to handle multiple response types.
* **chore(agent):** Simplify `unregister` to accept either object or id/solver_id parameters.
* **change(domain):** Update `domain_pa` to `assistant.maoto.world`.
* **chore(agent):**  Refactor `send_intent` to handle `NewIntent` objects more cleanly.
* **chore(agent):** Change `unregister` route to use `GET` method.
* **chore(settings):** Change the `mcp_describe_all_responses` and `mcp_describe_full_response_schema` default values to `True` in `MCPSettings`.
* **chore(mcp):** Rename `server` property to `mcp` in `MCPServer` class.
* **chore(mcp):** Rename `add_tool` function to `tool` in `MCPServer` class.
* **chore(mcp):** Add `refresh` function to `MCPServer` class.
* **chore(mcp):** Add `include_operations`, `exclude_operations`, `include_tags`, and `exclude_tags` to `MCPSettings`.
* **chore(mcp):** Add documentation to `__init__.py`.
* **chore(app):**  Refactor handler registration to use `async` functions.
* **chore(gitignore):** Add `*.wrkbranch` to `.gitignore`.


### Deprecated

* **deprecate(agent):**  The `register_handler` function now uses `async` functions for event handling.

### Removed

* **remove(agent):** Remove unnecessary `input` and `type_ref` parameters in `unregister` and `refund_offercall` methods.


### Fixed

* **fix(agent):**  Resolve error in handling `bool` results in `_request`.
* **fix(agent):**  Fix potential race condition in the `unregister` function.



### Other Changes

* **docs:** Add DEV readme with instructions on using ruff.
* **docs:** Update README with instructions for using the MCP inspector and installation using the `[mcp]` extra.
* **dev:** Add `git-rebase-wrk.sh.sh` script for managing branches and rebasing.



