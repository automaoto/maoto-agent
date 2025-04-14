## Release Notes

This release includes improvements to the versioning workflow.

### Other Changes

* **chore(workflow):** Update versioning workflow to push tags to a private repository using a personal access token. The workflow now pushes tags to `https://x-access-token:${{ secrets.MAOTO_AGENT }}@github.com/automaoto/maoto-agent.git` instead of the public origin.  This enhances security by avoiding exposure of the token in the public repository's commit history.


