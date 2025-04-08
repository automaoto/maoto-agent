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


