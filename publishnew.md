# Publishing a New Version of qcmd

This document outlines the steps to publish a new version of the qcmd package to PyPI using GitHub Actions.

## Step 1: Update Version Numbers

1. Update version in `pyproject.toml`:
   ```toml
   [project]
   name = "ibrahimiq-qcmd"
   version = "x.y.z"  # Change this to the new version
   ```

2. Update version in `qcmd_cli/__init__.py`:
   ```python
   __version__ = "x.y.z"  # Change this to the new version
   ```

3. Update version in `PYPI-README.md`:
   ```markdown
   **Version x.y.z**
   ```

4. Add what's new section in `PYPI-README.md`:
   ```markdown
   ## What's New in x.y.z
   
   - List changes here
   - Fix descriptions
   - Feature additions
   ```

## Step 2: Test Your Changes

Run unit tests to ensure everything is working:
```bash
python -m pytest tests/test_qcmd.py -v
```

Run flake8 to check for syntax errors:
```bash
flake8 qcmd_cli/qcmd.py --count --select=E9,F63,F7,F82 --show-source --statistics
```

## Step 3: Commit and Push Changes

```bash
git add qcmd_cli/__init__.py pyproject.toml PYPI-README.md
git commit -m "Bump version to x.y.z"
git push origin main
```

## Step 4: Create a GitHub Release

1. Go to your GitHub repository
2. Click on "Releases" in the right sidebar
3. Click "Create a new release"
4. Tag version: `vx.y.z` (e.g., v1.0.2)
5. Release title: `qcmd vx.y.z`
6. Description: Add release notes (similar to what's in PYPI-README.md)
7. Click "Publish release"

## Step 5: Automatic PyPI Publishing

The GitHub Actions workflow (`publish-to-pypi.yml`) will automatically:

1. Check out the code
2. Set up Python
3. Install dependencies
4. Update version from the tag
5. Build the package
6. Publish to PyPI using your stored API token

No manual upload is required! Just wait for the workflow to complete.

## Verification

After the workflow completes, verify that the new version is available on PyPI:
https://pypi.org/project/ibrahimiq-qcmd/

Users can then install the new version with:
```bash
pip install --upgrade ibrahimiq-qcmd
``` 