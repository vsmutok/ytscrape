# Install ytscrape via pip or uv in Your Python Project

> Install ytscrape via pip or uv, verify the setup, review the three runtime dependencies (requests, pycountry, defusedxml), and configure a dev environment.

ytscrape is a pure-Python library published on [PyPI](https://pypi.org/project/ytscrape/) under the MIT license. It has a minimal footprint — three small runtime dependencies — and works on every major operating system. This page covers everything you need to get it running in your environment.

## Requirements

* **Python 3.10 or newer.** ytscrape uses modern type annotations and structural pattern features that require Python 3.10+. It is tested against CPython 3.10, 3.11, 3.12, 3.13, and 3.14.
* **Runtime dependencies** — installed automatically by pip or uv:

| Package                                                        | Purpose                                                                                              |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [`requests`](https://pypi.org/project/requests/) `>=2.28`      | All HTTP communication with YouTube's InnerTube endpoints.                                           |
| [`pycountry`](https://pypi.org/project/pycountry/) `>=22.3.5`  | Validates ISO 639-1 language codes and ISO 3166-1 country codes passed to `language=` and `region=`. |
| [`defusedxml`](https://pypi.org/project/defusedxml/) `>=0.7.1` | Safe XML parsing for transcript/caption track responses.                                             |

No browser, no driver, and no external binaries are required.

## Install the Package

=== "pip"

    ```bash
    pip install ytscrape
    ```

=== "uv"

    ```bash
    uv add ytscrape
    ```

=== "From source"

    ```bash
    git clone https://github.com/vsmutok/ytscrape
    cd ytscrape
    pip install .
    ```


!!! note

    The package name on PyPI is `ytscrape` — install it exactly as shown above. After installation a `ytscrape` console script is also registered, so you can run `ytscrape search "python" --max 10` directly from your terminal.


## Verify the Installation

Open a Python interpreter or create a small script and confirm the package imports correctly:

```python
import ytscrape

print(ytscrape.__version__)  # e.g. 0.1.4
```

You can also run the built-in CLI to confirm end-to-end connectivity:

```bash
ytscrape search "python" --filter videos --max 3
```

If the command prints video titles and URLs, ytscrape is installed and communicating with YouTube successfully.

## Optional: Development Dependencies

If you want to contribute to ytscrape or run its test suite locally, sync the full development environment using `uv`:

```bash
git clone https://github.com/vsmutok/ytscrape
cd ytscrape
uv sync --dev
```

The `dev` dependency group includes:

| Package                                                        | Purpose                                                            |
| -------------------------------------------------------------- | ------------------------------------------------------------------ |
| [`pytest`](https://pypi.org/project/pytest/) `>=9.1.1`         | Test runner — execute with `uv run pytest`.                        |
| [`ruff`](https://pypi.org/project/ruff/) `>=0.14.5`            | Linting and code formatting.                                       |
| [`bandit`](https://pypi.org/project/bandit/) `>=1.9.4`         | Static security analysis.                                          |
| [`pre-commit`](https://pypi.org/project/pre-commit/) `>=4.3.0` | Git hook runner that executes ruff and bandit before every commit. |
| [`twine`](https://pypi.org/project/twine/) `>=6.2.0`           | Package upload tooling (maintainers only).                         |

Run the full check suite with:

```bash
uv run pytest                            # run the test suite
uv run pre-commit run --all-files        # ruff + format + bandit
```

## Next Steps

With ytscrape installed, follow the [Quickstart](quickstart.md) to write your first search, metadata fetch, and comment collection in minutes.
