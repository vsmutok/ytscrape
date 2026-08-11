# Contributing to ytscrape

Thanks for your interest in improving **ytscrape**. Bug reports, ideas, docs
fixes and pull requests are all welcome.

## Ways to contribute

- **Bug reports** — unexpected behaviour, parse failures, broken endpoints.
- **Feature ideas** — new InnerTube coverage, API ergonomics, CLI options.
- **Documentation** — README, examples, docstrings, this guide.
- **Code** — fixes and features with tests where it makes sense.

Please open an
[issue](https://github.com/vsmutok/ytscrape/issues) before large or breaking
changes so we can align on design.

## Development setup

Requirements: **Python 3.10+** and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/vsmutok/ytscrape
cd ytscrape
uv sync --dev
uv run pre-commit install   # optional, recommended
```

### Useful commands

```bash
uv run pytest                           # unit tests
uv run pre-commit run --all-files       # ruff + format + bandit
uv run python -m ytscrape --help        # CLI smoke check
```

The package lives under `src/ytscrape/`. Prefer extending the public `YouTube`
facade and typed models rather than exposing raw InnerTube JSON.

## Pull requests

1. Fork the repo and create a branch from `main`.
2. Keep the change focused — one concern per PR when possible.
3. Add or update tests for behaviour changes.
4. Run `uv run pytest` and `uv run pre-commit run --all-files` locally.
5. Fill in the PR template: what changed, why, and how you verified it.
6. Update `CHANGELOG.md` under an `[Unreleased]` section when the change is
   user-visible (API, CLI, behaviour, docs that users rely on).

### Style

- Match existing code style (Ruff enforces lint and format).
- Prefer clear names and small functions over clever one-liners.
- Keep public APIs typed; models stay frozen dataclasses unless there is a
  strong reason not to.
- Do not commit secrets, large binary fixtures, or live credentials.

## Issues

Use the issue templates when they fit:

- **Bug report** — steps, expected vs actual, environment, minimal snippet.
- **Feature request** — problem, proposed API, alternatives considered.

For security-sensitive reports, do not file a public issue with exploit details;
contact the maintainer privately if possible.

## Scope and responsibility

`ytscrape` talks to YouTube’s private InnerTube endpoints. Contributions should
not encourage abuse (credential stuffing, bulk harassment tooling, etc.). You
are responsible for how you use the library and for complying with applicable
terms and laws.

## License

By contributing, you agree that your contributions are licensed under the same
[MIT License](LICENSE) as the project.
