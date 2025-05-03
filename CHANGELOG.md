## maoto-agent 0.1.1 Release Notes

### New Features

* **feat(agent):** Add optional MCP support. Install `maoto-agent[mcp]` to enable.  This allows users to expose their FastAPI endpoints as MCP tools for easier integration with other systems. ([#1](placeholder_issue_link))
* **feat(agent):** Add `get_refcodes()` and `create_refcode()` methods for managing reference codes in the assistant. ([#2](placeholder_issue_link))
* **feat(agent):** Add `delete_refcode()` method for deleting reference codes in the assistant. ([#3](placeholder_issue_link))
* **feat(agent):** Add favicon.ico to enhance application branding. ([#4](placeholder_issue_link))
* **feat(types):** Add `provider_id` to `Intent`, `OfferCallResponse`, and `IntentResponse` types. ([#5](placeholder_issue_link))
* **feat(types):** Add `NewRefCode` and `RefCode` types for managing reference codes. ([#6](placeholder_issue_link))
* **feat(types):** Add field validator to `NewOffer` and `NewSkill` to ensure params are always a dictionary. ([#7](placeholder_issue_link))
* **feat(types):** Add field validator to `RegisterUserRequest` and `EmailVerif` to ensure query_params are always a dictionary. ([#8](placeholder_issue_link))
* **feat(types):** Add field validator to `NewOfferCall` to ensure args are always a dictionary. ([#9](placeholder_issue_link))

### Changed

* **chore(agent):** Update `url_pa` to `assistant.maoto.world`. ([#10](placeholder_issue_link))
* **chore(agent):** Refactor request handling to include retry logic. ([#11](placeholder_issue_link))
* **chore(agent):** Improve error handling in requests to provide more context. ([#12](placeholder_issue_link))
* **chore(agent):** Implement safe `urljoin` to handle various URL formats. ([#13](placeholder_issue_link))
* **chore(agent):** Updated  `_request` method parameters to allow passing params in BaseModel or dict. ([#14](placeholder_issue_link))
* **chore(agent):** Improved documentation for the various endpoints and parameters in the Maoto class. ([#15](placeholder_issue_link))
* **chore(agent):** Update `healthz` and `health` endpoints to return JSON responses. ([#16](placeholder_issue_link))
* **chore(agent):** Change `unregister` method to accept both object and ID for flexibility. ([#17](placeholder_issue_link))
* **chore(agent):** Modify `send_intent` route parameter from `createIntent` to `NewIntent`. ([#18](placeholder_issue_link))
* **chore(settings):** Rename `apikey` to `apikey_hashed` in `AgentSettings` and use SHA256 hash. ([#19](placeholder_issue_link))
* **chore(agent):** Use `safe_urljoin` for constructing URLs. ([#20](placeholder_issue_link))
* **chore(agent):** Add `include_in_schema=False` to `/healthz` and `/health` endpoints. ([#21](placeholder_issue_link))
* **chore(agent):** Improve error messages for unsupported event types. ([#22](placeholder_issue_link))
* **chore(agent):**  `set_webhook` now accepts a URL argument or reads from `MAOTO_AGENT_URL`. ([#23](placeholder_issue_link))
* **chore(mcp):** Update `MCPSettings` to use pydantic fields correctly. ([#24](placeholder_issue_link))
* **chore(mcp):** Update `MCPServer` to use `FastApiMCP`. ([#25](placeholder_issue_link))
* **chore(mcp):** Update `MCPServer` documentation for clarity. ([#26](placeholder_issue_link))
* **chore(mcp):** Add `refresh` method to `MCPServer` to dynamically update. ([#27](placeholder_issue_link))
* **chore(mcp):** Add improved documentation to `__init__.py` file. ([#28](placeholder_issue_link))
* **chore(readme):** Improve README.md with new features and installation steps for MCP support. ([#29](placeholder_issue_link))
* **chore(readme):** Add a checklist to Key Features. ([#30](placeholder_issue_link))


### Removed

* **refactor(workflows):** Remove unnecessary workflow steps from `test.yml`. ([#31](placeholder_issue_link))
* **refactor(workflows):** Remove `workflow_run` trigger from `lint.yml` and `release.yml`. ([#32](placeholder_issue_link))
* **refactor(workflows):** Remove commented-out conda-forge related sections from `release.yml`. ([#33](placeholder_issue_link))
* **refactor(workflows):** Add `tags-ignore` to avoid triggering release notes on tag pushes in `release_notes.yml`. ([#34](placeholder_issue_link))


### Bug Fixes

* **fix(agent):** Correctly handle `result_type=bool` in `_request` method. ([#35](placeholder_issue_link))
* **fix(agent):** Fix potential error in `unregister` when using solver_id. ([#36](placeholder_issue_link))


### Other Changes

* **deps:** Update dependencies (axios, etc). ([#37](placeholder_issue_link))
* **docs:** Update documentation for clarity and to reflect new features. ([#38](placeholder_issue_link))
* **test:** Add unit tests for new features. ([#39](placeholder_issue_link))


**Note:**  Replace `[#1](placeholder_issue_link)`, `[#2](placeholder_issue_link)`, etc. with actual issue links from your repository.

