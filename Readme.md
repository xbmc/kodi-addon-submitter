# Kodi Addon Submitter

This is a command line script for automating submission of addons for
[Kodi Mediacenter](https://kodi.tv) to the official addon repository.
The utility automates the steps for preparing and creating addon submission
pull requests to one of the addon repositories: `xbmc/repo-plugins` or
`xbmc/repo-scripts`. It is meant for use primarily in CI/CD pipelines,
for example with GitHub Actions.

The script is compatible with Python 2.7 and 3+.


## Prerequisites

- Your addon files must have one of the following formats
  - Your addon files must be located in the root directory inside your Git repository.
    That is, your Git repo for the addon must have the following layout:
    ```
    /<git-repo-directory>/
    |
    |
    +--/resources/
    |  |
    |  ...
    +--addon.xml
    +--fanart.jpg
    +--icon.png
    |
    +--.gitignore
    +--.github/workflows/submit.yml
    +--Readme.md
    ```
    To avoid polluting your addon submission with unnecessary files, such as `.gitignore` and workflow files,
    those can be excluded by using git-archive and setting the [export-ignore attribute]
    (https://git-scm.com/docs/gitattributes#_creating_an_archive).
  - Your addon files must be located in a separate addon directory, e.g.
   `/plugin.video.example` inside your Git repository. That is, your Git repo for
    the addon must have the following layout:
    ```
    /<git-repo-directory>/
    |
    +--/plugin.video.example/
    |  |
    |  +--/resources/
    |  |  |
    |  |  ...
    |  +--addon.xml
    |  +--fanart.jpg
    |  +--icon.png
    |
    +--.gitignore
    +--.github/workflows/submit.yml
    +--Readme.md
    ```
- Fork the necessary addon repository -- `xbmc/repo-plugins` or
  `xbmc/repo-scripts` -- into your GitHub account.
- Define the following environment variables in your CI environment:
  - `GH_USERNAME`: your GitHub username.
  - `GH_TOKEN`: your GitHub access token with at least `public_repo` scope.
  - `EMAIL`: your email
- It is strongly recommended to have `<news>` section in your `addon.xml`
  that describes the changes made in the latest version being submitted.
  The contents of the `<news>` tag will be automatically added to
  a pull request message.

## Installation

The Addon Submitter utility is installed from this repository with pip:

```bash
pip install git+https://github.com/romanvm/kodi-addon-submitter.git
```

## Usage

Run `submit-addon` script with the following options:

- `addon_id` (positional): your addon ID, e.g. `plugin.video.example`.
- `-z`, `--zip` (optional): create a versioned installable ZIP for the addon.
  It can be used, e.g, if you are deploying your addon to GitHub Releases.
- `-r`, `--repo`: addon repo, e.g. `repo-plugins` or `repo-scripts`.
- `-b`, `--branch`: addon repo branch, that corresponds to a Kodi version
  codename, e.g. `krypton` or `leia`.
- `--push-branch`: create an addon branch in your repo fork.
- `--pull-request`: create a pull request for the addon submission in the Kodi
  repository. With this option the script will create/update an addon branch,
  as with `--push-branch` option, and then create a pull request in the respective
  official Kodi addon repository, if it does not exist. If the pull request
  already exists, the script will simply update the addon branch in your
  repository fork.
- `-s`, `--subdirectory`: Addon is stored in its own directory within the git repo
- `-m`, `--matrix`: Submit a Python 2/3 compatible addon to `matrix` branch
  in addition to the target branch. This can be used if you want to update
  a Python 2/3 compatible addon both in `matrix` (Kodi 19.x) and a lower
  branch at the same time. Do not use this option if you want to submit
  a Python 3 addon only to `matrix` branch. Use `-b` option for this.

Example:
```bash
submit-addon -r repo-plugins -b leia --pull-request plugin.video.example
```

## Example GitHub Actions Workflow

```yaml
name: Submit Kodi Addon

on:
  push:
    tags:
      - '*'

jobs:
  submit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'

      - name: Install addon submitter
        run: pip install git+https://github.com/romanvm/kodi-addon-submitter.git

      - name: Create release ZIP
        run: submit-addon -z plugin.video.example

      - name: Publish release assets
        uses: softprops/action-gh-release@v2
        with:
          files: '*.zip'

      - name: Submit to Kodi addon repository
        env:
          GH_USERNAME: ${{ secrets.GH_USERNAME }}
          GH_TOKEN: ${{ secrets.GH_TOKEN }}
          EMAIL: ${{ secrets.EMAIL }}
        run: submit-addon -r repo-plugins -b leia --pull-request plugin.video.example
```
This config automatically publishes your addon to the "Releases" section of your
addon repository and creates a pull request in the official Kodi addon repository
when a new git tag is pushed to your addon repository. So with this config simply
run
```bash
git tag <version number>
git push --tags
```
to submit your addon. Everything else will be done automatically by GitHub Actions.

`GH_USERNAME` must be the username that owns the fork targeted by `GH_TOKEN`.
Using `${{ github.actor }}` can fail when the workflow actor is different from the
token owner.
