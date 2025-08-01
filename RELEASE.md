# Release Process

* Make sure that the code is in a good shape, all tests are passed, etc.
* Rebase on `master` / merge `master` into your branch, to avoid potential conflicts.
* Open `VERSION.txt`, increment the file content, e.g. `20.6.22`.
* Run `make format`.
* Run `towncrier create <num>.(bugfix|feature|doc|removal|misc) --edit` to create a new changelog entry.
* Run `towncrier` to update `CHANGELOG.md` from the changelog entries.
* Open `CHANGELOG.md`, make sure that the generated file content looks good. Fix it if needed.
* Commit changed `__init__.py`, `CHANGELOD.md` and deleted change pieces in `CHANGELOG.D`. Use `Release 1.2.3` commit message
* Push commited changes on github and create a pull request against the `master` branch.
* Wait for CircleCI checks finish, make sure that all tests are passed.
* Restart CI failed jobs in case of failed flaky tests.
* After CI is green make a git tag on a `master` branch. For version `20.6.22` the tag should be `v20.6.22` (`git tag -a v20.6.22 -m "Release 20.6.22"`).
* Push a new tag, e.g. `git push origin v20.6.22`.
* Make sure that CI is green. Restart a job for tagged commit if a flaky test is encountered.
* Open PyPI (https://pypi.org/project/apolo-sdk/ and https://pypi.org/project/apolo-cli/),
  make sure that a new release is published and all needed files are awailable for downloading
  (https://pypi.org/project/apolo-sdk/#files and https://pypi.org/project/apolo-cli/#files).
* Increment version to next alpha, e.g. `__version__ = 20.6.23a0`. Commit this change to master and push on github.
* Publish a new version announcement on `product` slack channel.
