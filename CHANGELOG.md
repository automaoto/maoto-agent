### 0.1.0

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


