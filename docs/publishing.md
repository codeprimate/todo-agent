# Publishing to PyPI

This guide covers how to publish the `todo-agent` package to the Python Package Index (PyPI). The process uses modern Python packaging tools with `pyproject.toml` configuration and a Makefile for streamlined workflows.

## Overview

Publishing a new release involves three main steps:
1. **Update the version** using git tags (automated via setuptools_scm)
2. **Create a git tag** to mark the release
3. **Run the publish command** to upload to PyPI

After initial setup, each release follows the same simple workflow using the provided Makefile.

## Release Checklist

- [ ] Run code quality checks: `ruff check .`, `ruff format .`, `mypy .`
- [ ] Run tests: `pytest`
- [ ] All code changes merged and tests passing
- [ ] Create and push git tag: `git tag vX.X.X && git push origin main && git push origin vX.X.X`
- [ ] Build and publish: `make publish`
- [ ] Verify package published at [https://pypi.org/project/todo-agent/](https://pypi.org/project/todo-agent/)

## One-Time Setup

These steps only need to be done once when setting up publishing for the first time.

### 1. Install Dependencies

Ensure all project dependencies are installed, including the publishing tools:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install build twine
```

### 2. Create PyPI Account and API Token

You need an account on PyPI to publish packages.

1. **Create an account**: [https://pypi.org/account/register/](https://pypi.org/account/register/)
2. **Generate an API token**:
   - Log in to your PyPI account
   - Navigate to "Account settings" → "API tokens"
   - Create a new token (scope it to the `todo-agent` project if desired)
   - **Important**: Copy the token immediately, as you cannot view it again

## Release Process

Follow these steps for each new release:

### Step 1: Prepare for Release

Ensure all code is ready for release:

```bash
# Run all tests
pytest

# Run code quality checks
ruff check .
ruff format .
mypy .

# Check for security issues
bandit -r todo_agent/
safety check
```

### Step 2: Create Git Tag

The project uses `setuptools_scm` for automatic version management based on git tags. Create a git tag to mark the release:

```bash
git tag v1.0.1
git push origin main
git push origin v1.0.1
```

**Note**: Replace `1.0.1` with your actual version number. Tags should follow the `v{version}` format. The version will be automatically extracted from the git tag.

### Step 3: Build and Publish to PyPI

Use the Makefile for a streamlined build and publish process:

```bash
# Full publish workflow (clean → build → check → upload)
make publish
```

This single command will:
1. Clean previous build artifacts
2. Build the package distribution files
3. Validate the built package
4. Upload to PyPI

## Makefile Targets

The project includes a Makefile with several useful targets:

- **`make clean`** - Remove build artifacts (dist/, build/, .eggs/, *.egg-info)
- **`make build`** - Build the package using `python -m build`
- **`make check`** - Validate distribution files with `twine check`
- **`make publish`** - Complete publishing workflow: clean → build → check → upload

## Version Management

This project uses `setuptools_scm` for automatic version management:

- Version is automatically determined from git tags
- No need to manually update version numbers in files
- Version follows semantic versioning: `v1.0.0`, `v1.0.1`, `v1.1.0`, etc.
- The version is written to `todo_agent/_version.py` during build

## Authentication Reference

### Interactive Authentication

When you run `make publish`, it will prompt for credentials:
- **Username**: Enter `__token__`
- **Password**: Paste your PyPI API token (including the `pypi-` prefix)

### Non-Interactive Authentication (Optional)

For automated workflows, you can set environment variables:

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD="pypi-your-token-here"
```

With these variables set, `twine` will authenticate automatically without prompting.

## Project-Specific Notes

- **Package name**: `todo-agent` (with hyphen for PyPI, underscore for import)
- **License**: GPL-3.0
- **Python versions**: 3.8+
- **Dependencies**: See `pyproject.toml` for complete list
- **Entry point**: `todo-agent` command line tool

## Quick Reference

For subsequent releases after initial setup:

1. Ensure all code changes are merged and tests are passing
2. Run code quality checks
3. Create a git tag for the new version
4. Build and publish: `make publish`
5. Verify the release on PyPI

## Troubleshooting

### Common Issues

- **Version already exists**: PyPI doesn't allow overwriting versions. Use a new version number.
- **Authentication failed**: Ensure your API token is correct and includes the `pypi-` prefix.
- **Build errors**: Check that all dependencies are installed and the project structure is correct.
- **Upload errors**: Verify the package name matches your PyPI project name exactly.

### Getting Help

- Check the [PyPI documentation](https://packaging.python.org/guides/distributing-packages-using-setuptools/)
- Review the [setuptools_scm documentation](https://github.com/pypa/setuptools_scm)
- Check the project's [GitHub repository](https://github.com/codeprimate/todo-agent) for issues