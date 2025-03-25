# Submitting to conda-forge

This document describes the process for submitting and maintaining the `maoto-agent` package on conda-forge.

## Initial Submission

1. **Fork the conda-forge/staged-recipes repository**:
   - Go to https://github.com/conda-forge/staged-recipes
   - Click the "Fork" button

2. **Create a new branch in your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/staged-recipes.git
   cd staged-recipes
   git checkout -b maoto-agent
   ```

3. **Create recipe directory**:
   ```bash
   mkdir -p recipes/maoto-agent
   ```

4. **Copy the generated recipe files**:
   - Copy the `meta.yaml` file from the workflow artifact to `recipes/maoto-agent/meta.yaml`
   - You may need to adjust some fields like license, description, and maintainers

5. **Submit a PR to conda-forge/staged-recipes**:
   ```bash
   git add recipes/maoto-agent
   git commit -m "Add maoto-agent recipe"
   git push origin maoto-agent
   ```

6. **Create PR on GitHub**:
   - Go to your fork on GitHub
   - Click "Create Pull Request"
   - Follow the guidelines in the PR template

7. **Address review feedback**:
   - Conda-forge maintainers will review your PR
   - Make any requested changes

Once merged, conda-forge-admin will create a feedstock repository automatically.

## Subsequent Updates

After the initial submission, a feedstock repository will be created at:
`https://github.com/conda-forge/maoto-agent-feedstock`

To update the package for new versions:

1. **Fork the feedstock**:
   ```bash
   git clone https://github.com/conda-forge/maoto-agent-feedstock.git
   cd maoto-agent-feedstock
   git checkout -b update-VERSION
   ```

2. **Update the recipe**:
   - Update version number in `recipe/meta.yaml`
   - Update sha256 hash if needed
   - Update dependencies if needed

3. **Submit a PR to the feedstock**:
   ```bash
   git add recipe/meta.yaml
   git commit -m "Update to version X.Y.Z"
   git push origin update-VERSION
   ```

4. **Create PR on GitHub**:
   - Go to your fork on GitHub
   - Click "Create Pull Request"

## Automatic Updates

Once established, conda-forge will often automatically detect new versions on PyPI and create PRs for you. You'll just need to review and merge these PRs.

## Notes

- Make sure the license is correctly specified (including any restrictions)
- Ensure all dependencies are available on conda-forge
- For any questions, refer to the conda-forge documentation: https://conda-forge.org/docs/ 