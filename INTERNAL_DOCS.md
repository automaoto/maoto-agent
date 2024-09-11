## Build locally with PyPi
This command will install the package in editable mode, meaning that any changes you make to the source code will be immediately reflected when you import and use the package in your other programs.
```bash
pip install -e .
```
## Build locally with Conda
TODO

## Test locally

`.secrets_01`:
```bash
DEBUG=False
MAOTO_API_KEY=test_apikey_resolver
```

`.secrets_02`:
```bash
OPENAI_API_KEY=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
DEBUG=False
MAOTO_API_KEY=test_apikey_provider
```


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
git push origin :refs/tags/v1.0.2
```

# https://pyob.oxyry.com