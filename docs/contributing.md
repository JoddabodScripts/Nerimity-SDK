# Contributing

Contributions to nerimity-sdk and its docs are welcome.

---

## SDK development

### Setup

```
git clone https://github.com/JoddabodScripts/Nerimity-SDK
cd Nerimity-SDK
pip install -e ".[redis,sqlite,cron,watch]"
```

The `-e` flag installs in editable mode — changes to the source take effect immediately without reinstalling.

### Running tests

```
pytest
```

### Code style

The project uses `ruff` for linting:

```
pip install ruff
ruff check .
ruff format .
```

---

## Docs development

### Setup

```
pip install mkdocs-material
```

### Preview locally

```
mkdocs serve
```

Opens a live-reloading preview at `http://localhost:8000`.

### Build

```
mkdocs build
```

Output goes to `site/`.

---

## Submitting changes

1. Fork the repo on GitHub
2. Create a branch: `git checkout -b my-change`
3. Make your changes
4. Push and open a Pull Request against `master`

For bug fixes and small improvements, a PR is enough. For larger changes (new features, API changes), open an issue first to discuss.

---

## Adding a contrib plugin

1. Create `nerimity_sdk_contrib/your_plugin.py` with a class inheriting `PluginBase`
2. Import and re-export it in `nerimity_sdk_contrib/__init__.py`
3. Add it to the table in `docs/plugins.md`
4. Add it to the `nerimity_sdk_contrib/README.md`

See [Writing a plugin](plugins.md#writing-a-plugin) for the plugin API.

---

## Reporting bugs

Open an issue on [GitHub](https://github.com/JoddabodScripts/Nerimity-SDK/issues) with:
- What you expected to happen
- What actually happened
- A minimal code example that reproduces it
- Your Python version and SDK version (`nerimity version`)
