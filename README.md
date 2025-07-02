# Introduction

The repository for Apolo SDK library and Apolo CLI tool.

Please look at [SDK readme](apolo-sdk/README.md) and [CLI readme](apolo-cli/README.md) for details.

## Development Guidelines

- Update `app.rst` when modifying the SDK
- Respect `root.quiet` flag to suppress non-essential output
- Colorize output: use bold for important info, red for errors
- Update `test_shell_completion.py` when adding commands
- Use formatters for table output instead of direct formatting
- Test formatters with `rich_cmp(console)`
- Regenerate ASCII files with `pytest --rich-gen`
- Create changelog entries: `towncrier create <num>.(bugfix|feature|doc|removal|misc) --edit`
