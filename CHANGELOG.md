## Maoto Agent Release Notes

### Changed

* **feat(agent):** Updated `url_pa` in `AgentSettings` to correctly point to the Assistant service. The domain has changed from `pa.maoto.world` to `assistant.maoto.world`.  The path is now `/assistant/` instead of `/assistant`.
* **refactor(agent):**  The `_request` method in `maoto_agent.py` now correctly handles URL construction. The `route` parameter is now appended to the base URL using string concatenation instead of an f-string. This improves flexibility and addresses potential issues with URL formatting.
* **fix(agent):** Updated `url_mp` and `url_pa` in `agent_settings.py` to use `HttpUrl` type from Pydantic for improved URL validation.  Added trailing slash to paths in `url_mp` and `url_pa` to ensure proper API endpoint addressing.



