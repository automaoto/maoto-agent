### 0.1.0

### New Features

* Added auto release notes workflow.
* Added `set_webhook` method to `Maoto` class.  This method sets or updates the webhook URL associated with the agent's API key.  The URL can be provided as an argument or retrieved from the `MAOTO_AGENT_URL` environment variable.  Returns a boolean indicating success or failure.


### Bug Fixes

* Fixed the `send_newoffercall` method in the `Maoto` class to correctly return an `OfferCall` object.  Previously, it was returning a dictionary.
* Updated the GitHub release workflow to include a notes file.


### Other Changes

* Updated `Maoto` class to handle boolean responses to `set_webhook`.
* Removed commented-out code for conda-forge recipe preparation from the release workflow.  This functionality will be added in a future release.
=======
**New Features:**

* **feat(agent):** Added `OutsourcedMaotoAgentMethods` class for handling user and API key management.  This class includes methods for creating, deleting, and retrieving users and API keys.  It also includes methods for uploading and downloading files.
* **feat(agent):** Added `download_missing_files` method to download files only if they are missing from the specified directory.
* **feat(workflow):** Created `.github/workflows/release_notes.yml` for automated release notes generation.  This workflow uses the `lennardkorte/auto-release-notes` action.
* **feat(workflow):** Added `CHANGELOG.md` to the `sdist` build target.

**Changed:**

* **chore(project):** Updated `pyproject.toml` to include `Homepage`, `Documentation`, and `Issues` URLs under `project.urls`.
* **chore(project):** Updated `pyproject.toml` to add `CHANGELOG.md` to the files included in the source distribution (`sdist`).
* **chore(github):** Modified the GitHub Actions workflow (`release.yml`) to include `--notes-file CHANGELOG.md` in the `gh release create` command. This will now use the changelog for release notes.
* **refactor(agent):** The `send_newoffercall` method in `maoto_agent.py` now correctly returns an `OfferCall` object.  Previously, it didn't unpack the returned data properly.
* **refactor(agent):** Improved error handling and logging throughout the codebase.
* **refactor(agent):** Improved the `set_webhook` method. Now it returns the result of the mutation, and properly handles the URL input.


**Removed:**

*  Removed commented-out sections related to the `prepare-conda-forge` job in the GitHub Actions workflow.


