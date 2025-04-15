## maoto-agent - Release Notes

This release includes several improvements and bug fixes.


### Changed

* **deps:** Downgraded `loguru` from `>=0.7.3` to `>=0.7.0` in `meta.yaml` and `pyproject.toml`.
* **build:** Removed `setuptools` dependency from `pyproject.toml`.
* **chore:** Updated `classifiers` in `meta.yaml` and `pyproject.toml` to add more specific classifiers.
* **chore:** Replaced `pkg_resources.get_distribution` with `importlib.metadata.version` in `src/maoto_agent/maoto_agent.py`.

### Other Changes

* **workflow:** Modified the GitHub Actions workflow to trigger on push and pull requests to the `main` branch in `.github/workflows/release_notes.yml`.
* **docs:** Updated `README.md` (not shown in diff).
* **test:** Added more tests (not shown in diff).



