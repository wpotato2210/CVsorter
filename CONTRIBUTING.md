# Contributing

## Import & Packaging Rules

- Use relative imports inside packages for intra-package references.
- Do not assume subfolders are importable as top-level packages.
- All code must work after `python -m pip install -e .`.
- Never rely on `sys.path` side effects for runtime behavior.
- CI must validate import integrity from the installed package environment.
