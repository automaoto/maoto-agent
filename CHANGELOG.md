## Maoto Agent - Release Notes

This document details changes made in the latest release of the Maoto Agent Python package.

### New Features

* **feat(agent):** Complete rewrite of the Maoto Agent using FastAPI for enhanced performance and efficiency.  The old asynchronous GraphQL client is replaced with a synchronous HTTPX client. This provides simpler usage for most use-cases, and enables full integration with the MCP.  
* **feat(mcp):**  Added support for the Marketplace Capability Provider (MCP).  The `maoto-agent` now includes a fully-functional MCP server that can easily integrate with various language models and tools. See documentation for more details on how to register and use tools in your agent.
* **feat(types):** Improved type definitions for enhanced type safety and better code readability.  Significant type-hints added.
* **feat(settings):** Introduced `AgentSettings` and `MCPSettings` for flexible configuration of the agent and MCP server.
* **feat(docs):** Significant overhaul of the documentation, including a new Quick Start guide and comprehensive API reference.  The documentation is now hosted at https://docs.maoto.world.
* **feat(README):** Revamped the README to be more appealing and informative, including installation instructions, key features, documentation link, and badges.
* **feat(CI/CD):** Added a new GitHub Actions workflow for automatic release notes generation and improved testing.  New workflows for testing and automatic release notes.

### Changed

* **refactor(agent):** The entire Maoto Agent class was replaced with a FastAPI application.  All previous methods have been rewritten to utilise the FastAPI framework.
* **chore(structure):**  Reorganized the project structure for better modularity and maintainability.  The project is now setup using `hatch`.
* **chore(dependencies):** Updated and modernized various dependencies for improved performance and security.  Many dependencies were upgraded.
* **chore(logging):** Switched from `logging` library to `loguru` for better logging flexibility and ease of use.
* **chore(testing):** Updated testing to utilize `ruff`.
* **chore(versioning):** Updated versioning.

### Removed

* **remove(agent):** Removed the old asynchronous GraphQL client and related code.
* **remove(Outdated Code):** Removed obsolete and redundant code.


### Other Changes

* **deps:** Updated dependency versions for various packages.
* **docs:** Updated documentation to reflect the changes made in this release. Added new sections and improved existing ones.
* **chore:** Updated project structure and file organization.
* **test:** Improved test coverage and added new tests.
* **assets:** Added new logo, coverage badge and partner logos.  Created image reformatting script.

### Upgrade Steps

* **ACTION REQUIRED:** Due to the significant changes introduced in this release, users will need to review the updated documentation and adjust their code accordingly.  The API has been significantly changed, requiring adaptations in your agent code.


### Breaking Changes

* **BREAKING CHANGE:** The Maoto Agent class has been completely refactored, rendering previous code incompatible.   All methods have been rewritten.  Refer to the updated documentation for the new API.  The old GraphQL client based approach has been entirely removed.
* **BREAKING CHANGE:** Project structure changed.  Update your import statements.




