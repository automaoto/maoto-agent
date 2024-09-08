## Build locally with PyPi
This command will install the package in editable mode, meaning that any changes you make to the source code will be immediately reflected when you import and use the package in your other programs.
```bash
pip install -e .
```
## Build locally with Conda
TODO

## Create a Git Tag for Versioning
```bash
git tag v1.0.2
```
```bash
git push origin main --tags
```
### If action failed, remove old tage by:
```bash
git tag -d v1.0.2
```
```bash
git push origin :refs/tags/v1.0.0
```