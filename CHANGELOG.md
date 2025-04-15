## Maoto Agent Release Notes

This release includes several improvements and bug fixes.

### Changed

* **deps:** Downgraded `loguru` from `>=0.7.3` to `>=0.7.0` in `meta.yaml` and `pyproject.toml`.
* **build:** Removed `setuptools` dependency from `pyproject.toml`.
* **core:** Replaced `pkg_resources.get_distribution` with `importlib.metadata.version` for version retrieval in `maoto_agent.py`.
* **workflows:** Modified GitHub Actions workflow to trigger on push and pull requests to the `main` branch. The workflow now runs on `push` and `pull_request` events targeting the `main` branch.


### Added

* **metadata:** Added additional classifiers to `meta.yaml` and `pyproject.toml` for improved package discoverability.  These classifiers provide more detailed information about the package's intended audience and topic.

### Other Changes

* **docs:** Updated documentation to reflect changes.  *(Note:  Specific documentation updates aren't detailed in the diffs provided.)*



