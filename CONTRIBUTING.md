# Contributing

Open an issue for user-facing changes and include a small example of the workflow. For bugs, include the Python version, OS, project version, exact command or app action, and sanitized input. A minimal CSV with synthetic product names and authorized images is enough for many issues.

1. Install with `python -m pip install -e '.[web,test]'`.
2. Run `python -m pytest --cov=trade_catalog_kit`.
3. For PDF changes, regenerate with `python examples/make_examples.py`, render each affected page, and inspect photos, labels, and pagination.
4. Submit a focused pull request with the reasoning and test results. Contributions are licensed under MIT.

For security reports, use the process in [SECURITY.md](SECURITY.md).
