### Upgrade Steps
* **ACTION REQUIRED**: Review changes in `OutsourcedMaotoAgentMethods.py` which has been removed.  Functionality may need to be re-implemented.
* **ACTION REQUIRED**: The workflow for generating release notes has been added. Ensure your secrets are correctly configured.
* **ACTION REQUIRED**: Verify the `verify-artifact` step in the release workflow is functioning correctly.

### Breaking Changes
* Removed `OutsourcedMaotoAgentMethods.py`.  Functionality must be reimplemented.
* The Github release workflow now requires a notes file (`artifact/output.txt`).
* The `set_webhook` function in `maoto_agent.py` now returns a boolean indicating success or failure.


### New Features
* Added a new workflow (`release_notes.yml`) to automatically generate release notes using the `lennardkorte/auto-release-notes` action.
* Added `verify-artifact` job to `release.yml` to check for the existence of the release notes file before creating the release.

### Bug Fixes
* Fixed the `send_newoffercall` function in `maoto_agent.py` to correctly handle the returned `OfferCall` object.
* The `set_webhook` function in `maoto_agent.py` now returns the result of the mutation, indicating success or failure.


### Performance Improvements
* No performance improvements in this release.

### Other Changes
* No other changes in this release.


