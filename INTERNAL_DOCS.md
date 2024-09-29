## Build locally with PyPi
This command will install the package in editable mode, meaning that any changes you make to the source code will be immediately reflected when you import and use the package in your other programs.
```bash
export SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0
pip install -e .
```
Local Build
```bash
export SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0
pip install build
```

## Build locally with Conda
TODO

## Create a Git Tag for Versioning
```bash
git tag v1.0.4
```
```bash
git push origin main --tags
```
### If action failed, remove old tage by:
```bash
git tag -d v1.0.4
```
```bash
git push origin :refs/tags/v1.0.4
```

### Version Naming Conventions

- **Alpha**: `v1.0.0a1`
- **Beta**: `v1.0.0b1`
- **Release Candidate**: `v1.0.0rc1`
- **Final Release**: `v1.0.0`

Pre-releases (beta, RC) go to **Test PyPI**; final releases go to **PyPI**.
