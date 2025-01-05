## Build locally with PyPi
This command will install the package in editable mode, meaning that any changes you make to the source code will be immediately reflected when you import and use the package in your other programs.
```bash
export SETUPTOOLS_SCM_PRETEND_VERSION=1000.0.0a1
pip install -e .
```

## Create a Git Tag for Versioning
```bash
git tag v<version>
```
```bash
git push origin main --tags
```
### If action failed, remove old tage by:
```bash
git tag -d v<version>
```
```bash
git push origin :refs/tags/v<version>
```

