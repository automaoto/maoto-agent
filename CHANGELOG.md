## Maoto Agent Release Notes

### Changed

* **feat(agent_settings):** Updated `domain_pa` to `assistant.maoto.world`.
* **feat(agent_settings):** Changed return type of `url_mp` and `url_pa` to `HttpUrl` and added trailing slash to URLs.
* **fix(maoto_agent):** Modified URL construction in `_request` method to correctly handle routes.  The route is now appended using f"{url}{route}" instead of f"{url}/{route}".



