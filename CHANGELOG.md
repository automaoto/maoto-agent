## Release Notes

### Added

* **workflow:** Added a new workflow `Versioner` to handle versioning and tagging of releases.  This workflow allows for creating beta and release tags, incrementing versions (major, minor, patch, beta counter), and pushing the new tags to the remote repository.
* **workflow:** Added a `Test` workflow that checks for commits containing "CHANGELOG" in their message. If found, it prints a message indicating that the workflow was triggered by a CHANGELOG commit.
* **workflow:** Added workflow `lint-and-format` that triggers automatically after a successful run of the `Test` workflow.
* **workflow:** Added workflow `release` that triggers automatically after a successful run of the `Lint and Format` workflow and the `Versioner` workflow, only for pushes to tags.

### Changed

* **workflow:** The `release_notes` workflow now triggers on pushes to the `main` branch instead of `master`.
* **workflow:** The `release` workflow trigger changed from `push` events with tags to `workflow_run` events where `Test` workflow was completed successfully.  Manual triggers via `workflow_dispatch` are now only allowed to push to PyPI.
* **workflow:** The `release` workflow now only publishes to PyPI if the trigger is from a tag push.  Manual PyPI publishing is enabled via `workflow_dispatch`.
* **workflow:** Removed the commented-out `prepare-conda-forge` job from the `release` workflow.


### Removed

* **workflow:** Removed `workflow_dispatch` trigger from `release` workflow.

### Fixed


### Security


### Other Changes

* **workflow:** Updated the `actions/checkout` action in the `Test` workflow and  `Versioner` workflow from v3 to v4.  `persist-credentials` and `fetch-depth` parameters added to `release` workflow.


