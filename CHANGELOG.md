### 0.1.0 (yyyy-mm-dd)

### New Features
* Added workflow to automatically generate release notes.  (See `.github/workflows/release_notes.yml`)
* Added `set_webhook` function to `maoto_agent.py` to set or update the webhook URL.
* Improved `set_webhook` function in `maoto_agent.py` to return the result of the mutation.

### Bug Fixes
* Fixed an issue in `maoto_agent.py` where `send_newoffercall` was not returning the created `OfferCall` object.  The created object is now correctly returned.
* Fixed the GitHub release workflow to correctly upload release notes using a notes file.


### Other Changes
* Commented out the conda-forge recipe preparation section in the release workflow.  (See `.github/workflows/release.yml`)
