.PHONY: ci-smoke

# CI smoke test to catch missing native shared libraries (e.g. libGL.so.1)
# in minimal container environments before runtime startup.
ci-smoke:
	python -m pip install -r requirements.txt
	python scripts/smoke_imports.py
