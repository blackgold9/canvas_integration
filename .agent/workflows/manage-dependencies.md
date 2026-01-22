---
description: How to manage dependencies using uv
---

This project uses `uv` for dependency management. Follow these steps to manage the environment and dependencies.

### Installation

To sync the environment with the current `pyproject.toml`:

```bash
uv sync
```

### Adding Dependencies

To add a new production dependency:

```bash
uv add <package_name>
```

To add a new development dependency:

```bash
uv add --dev <package_name>
```

### Running Commands

To run commands within the virtual environment (like `pytest`):

```bash
uv run <command>
```

Example:

```bash
uv run pytest
```

### Updating Dependencies

To update all dependencies:

```bash
uv lock --upgrade
uv sync
```
