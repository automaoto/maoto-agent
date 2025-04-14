## Release Notes

This release includes several changes to the project's CI/CD workflows.  No functional changes to the application itself are included in this release.

### Other Changes

* **chore(ci):** Add authentication to `git push` in `versioner.yml` workflow.  This change adds the `MAOTO_AGENT` secret to authenticate git pushes to the remote repository.  This ensures that only authorized users can push tags to the repo.
* **chore(ci):** Remove `if` condition in `release.yml` workflow. The conditional statement `if: ${{ github.event.workflow_run.conclusion == 'success' }}` has been removed from the `build-pypi` job in `release.yml`. While the intention was likely to prevent publishing if linting failed, the current setup automatically handles this by tying the `release.yml` workflow to the successful completion of "Lint and Format".  Removing the extra check simplifies the workflow.


