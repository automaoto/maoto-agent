## Release Notes

### Added

* **workflow:** Added `versioner` workflow to automate version tagging.  This workflow allows for creating beta and release tags, incrementing version numbers according to user-specified criteria (major, minor, patch, or beta counter).


### Changed

* **workflow(lint):** The `lint` workflow now triggers only after a successful `Test` workflow run.
* **workflow(release):** The `release` workflow now triggers only after successful completion of the "Lint and Format" and "Versioner" workflows.  The workflow dispatch input for version has been removed.
* **workflow(release_notes):** The `release_notes` workflow trigger changed from pull requests on the `master` branch to pushes on the `main` branch.
* **workflow(test):** The `test` workflow now triggers only after a successful `Auto Release Notes` workflow run. The workflow name was changed to `changelog_job` and it now only prints a message.


### Removed

* **workflow(release):** Removed the `workflow_dispatch` trigger and its associated `version` input from the `release` workflow.
* **workflow(release):** Removed the commented-out `prepare-conda-forge` job.


### Fixed

* *(No changes in this release.)*


### Security

* *(No changes in this release.)*

### Other Changes

* *(No other changes in this release.)*


