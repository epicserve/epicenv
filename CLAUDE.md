# CLAUDE.md - Release Workflow

When the user says "make a release", follow this process:

### 1. Update Changelog

Edit [CHANGELOG.md](CHANGELOG.md) - add new version section at the top with today's date (YYYY-MM-DD format)

### 2. Bump Version

```bash
uv version --bump {major|minor|patch}
```

Ask user which type if not specified. This updates both `pyproject.toml` and `uv.lock`.

### 3. Commit and Tag

```bash
git add pyproject.toml uv.lock CHANGELOG.md
git commit -m "Bump version to v{VERSION}"
git tag -a "v{VERSION}" -m "Release v{VERSION}"
```

### 4. Push

```bash
git push origin main
git push origin v{VERSION}
```

### 5. Create GitHub Release

```bash
gh release create v{VERSION} --generate-notes
```

Or manually at https://github.com/epicserve/epicenv/releases/new

### 6. Verify

GitHub Actions will automatically publish to PyPI. Check:
- https://github.com/epicserve/epicenv/actions
- https://pypi.org/project/epicenv/
