### Upgrade Steps

* No specific upgrade steps are required.


### Breaking Changes

* The workflow trigger has changed.  Previously, it triggered on completion of the "Lint and Format" and "Versioner" workflows. Now it triggers on completion of "Lint and Format" workflow and pushes with tags starting with `v*`.  This means that the `Versioner` workflow is no longer a prerequisite for release.


### New Features

* Added a new trigger for the workflow: pushing to a branch with a tag starting with `v*`.


### Bug Fixes

* No bug fixes in this release.


### Performance Improvements

* No performance improvements in this release.


### Other Changes

* Removed the `Versioner` workflow as a trigger for the release workflow.
* Commented out the `prepare-conda-forge` job.  This functionality is likely to be added back later.


