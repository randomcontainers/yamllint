# yamllint

Container images with [yamllint](https://github.com/adrienverge/yamllint), the linter that checks YAML files for syntax errors and duplicate keys and for formatting problems such as wrong indentation, long lines and trailing spaces. yamllint is installed from PyPI into a virtual environment on Ubuntu or Alpine. The images are rebuilt when yamllint publishes a release and when the base image changes, for `linux/amd64` and `linux/arm64`.

This is an unofficial build, not affiliated with or endorsed by the yamllint project. Report problems with the image in this repository and problems with yamllint itself in the [yamllint issue tracker](https://github.com/adrienverge/yamllint/issues).

## Quick start

Check every `.yaml` and `.yml` file in the current directory and below:

```sh
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" ghcr.io/randomcontainers/yamllint .
```

The same images can also be pulled as `randomcontainers.com/yamllint`.

yamllint exits with 1 when it finds an error. Warnings are printed but leave the exit code at 0 unless you pass `--strict`, which makes it exit with 2. `-f parsable` prints one `file:line:column: [level] message (rule)` line per problem:

```sh
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" \
  ghcr.io/randomcontainers/yamllint --strict -f parsable .
```

Check a single file from standard input, without mounting anything:

```sh
docker run --rm -i ghcr.io/randomcontainers/yamllint - < config.yaml
```

With nothing mounted at `/work` there is no `.yamllint` to read, so the file is checked with the `default` preset unless you pass `-d` or mount the directory that holds your configuration.

The output has colors only when the container has a terminal (`docker run -t`). In a GitHub Actions workflow, pass `-f github` to print the problems as workflow commands, which show up as annotations:

```sh
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" \
  ghcr.io/randomcontainers/yamllint -f github .
```

yamllint picks that format by itself only when `GITHUB_ACTIONS` and `GITHUB_WORKFLOW` are set, and `docker run` does not pass them into the container unless you add `-e GITHUB_ACTIONS -e GITHUB_WORKFLOW`.

## Configuration

yamllint reads `.yamllint`, `.yamllint.yaml` or `.yamllint.yml` from the working directory `/work` or the nearest directory above it, so mount the directory that holds the file, usually the root of your repository. Without one it uses the `default` preset. Other ways to pass a configuration:

- `-c path/to/config.yaml`, with the file under `/work`.
- `-d relaxed` for the lenient preset, which turns most formatting rules into warnings and disables a few, such as `document-start` and `truthy`.
- `-d` with inline YAML, such as `-d "{extends: default, rules: {line-length: disable}}"`.

The [yamllint documentation](https://yamllint.readthedocs.io/en/stable/configuration.html) describes the rules and their options. Paths in `ignore` use `.gitignore` syntax, and `ignore-from-file: .gitignore` reuses the repository's own ignore file.

The images have no language locales, so the `key-ordering` rule always sorts keys by code point. On Ubuntu the only locale is `C.UTF-8`, and a `locale` setting such as `en_US.UTF-8` makes yamllint stop with an error, so leave the option out or set it to `C.UTF-8`.

## What is in the image

- `yamllint` in `/usr/local/bin`, linked from a virtual environment in `/usr/local/lib/yamllint` that uses the distro's `python3`.
- Its dependencies PyYAML, which parses the files, and pathspec, which matches the `ignore` patterns. Both are installed from `requirements.lock`.
- pip, which stays in the virtual environment.

## Default or slim

yamllint's default image adds no other tools, so `latest` and `slim` are the same image, with the contents listed above. Use `latest` to run it and the `slim` tags as a base for your own image.

## Tags

`<version>` is a yamllint release such as `1.38.0`. `<minor>` and `<major>` are its shorter forms, `1.38` and `1`, and follow the newest release in that series. Each row lists the default tag and its `slim` twin, which point to the same image.

| Tags | Base |
|---|---|
| `latest`, `slim` | Ubuntu |
| `<version>`, `<version>-slim` | Ubuntu |
| `<minor>`, `<minor>-slim`, `<major>`, `<major>-slim` | Ubuntu |
| `ubuntu`, `slim-ubuntu` | Ubuntu |
| `<version>-ubuntu`, `<version>-slim-ubuntu` | Ubuntu |
| `<minor>-ubuntu`, `<minor>-slim-ubuntu`, `<major>-ubuntu`, `<major>-slim-ubuntu` | Ubuntu |
| `<version>-ubuntu26.04`, `<version>-slim-ubuntu26.04` | Ubuntu 26.04 |
| `alpine`, `slim-alpine` | Alpine |
| `<version>-alpine`, `<version>-slim-alpine` | Alpine |
| `<minor>-alpine`, `<minor>-slim-alpine`, `<major>-alpine`, `<major>-slim-alpine` | Alpine |
| `<version>-alpine3.24`, `<version>-slim-alpine3.24` | Alpine 3.24 |

The images are currently built on Ubuntu 26.04 and Alpine 3.24. Tags without a distro version move to the next distro release when the project does; tags ending in `ubuntu26.04` or `alpine3.24` stay on that release and are no longer rebuilt once the project moves to the next one. Every tag of the current yamllint version, including the exact version, is rebuilt in place (see [Updates](#updates)), so pin a digest when you need the same bytes every time.

## Platforms

`linux/amd64` and `linux/arm64`, for both Ubuntu and Alpine. Both are built natively on GitHub-hosted runners, without emulation. The same `requirements.lock` is installed on all four combinations of distro and architecture. yamllint and pathspec are pure Python; PyYAML comes as a glibc (`manylinux`) wheel on Ubuntu and a musl (`musllinux`) wheel on Alpine.

## Files and permissions

The working directory is `/work`. The image runs as UID 1000, and any other UID works too: `HOME` is then `/`, and caches go to `/cache`, which anyone can write to. yamllint only reads files, so the mount can be read-only (`-v "$PWD:/work:ro"`). It can read only the files its UID has access to, so run it as your own user:

| Runtime | Flag |
|---|---|
| Docker on Linux (rootful), GitHub Actions | `--user "$(id -u):$(id -g)"` |
| Rootless Podman | `--userns=keep-id` |
| Rootless Docker | `--user 0:0` (root in the container is your user on the host) |
| Docker Desktop on macOS or Windows | none, file ownership is mapped for you |

## Extending the slim image

Use a `slim` tag as the base for your own image. `slim`, `slim-ubuntu` and `slim-alpine` follow new yamllint releases and are rebuilt when its locked Python dependencies or the distro change. yamllint runs from a virtual environment in `/usr/local/lib/yamllint`; the `python3` on `PATH` is the distro's interpreter and cannot import yamllint. The distro packages yamllint needs are listed in `/usr/local/share/randomcontainers/yamllint/runtime-deps`. Switch to root to install more, then back:

```dockerfile
FROM ghcr.io/randomcontainers/yamllint:slim-ubuntu@sha256:...
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*
USER 1000:1000
```

On Alpine, use `apk add --no-cache git`. The entrypoint is `["tini", "--", "yamllint"]`; set your own `ENTRYPOINT` if your image runs a script. To pick up new yamllint releases and base image fixes, let Dependabot or Renovate update the digest in your `FROM` line.

## Verifying

Each image has a build provenance attestation from this repository's GitHub Actions run, signed by the shared build workflow in `randomcontainers/ci`:

```sh
gh attestation verify oci://ghcr.io/randomcontainers/yamllint:latest \
  --repo randomcontainers/yamllint --signer-repo randomcontainers/ci
```

Each platform image also carries an SPDX SBOM that lists the distro and Python packages in it with their versions:

```sh
docker buildx imagetools inspect ghcr.io/randomcontainers/yamllint:latest --format '{{ json .SBOM }}'
```

yamllint and its Python dependencies are installed from [`requirements.lock`](requirements.lock), which pins every package to a version and its SHA-256 hashes, and pip refuses anything else. The URL and hash of each installed wheel are in `/usr/local/share/randomcontainers/yamllint/source`, and the installed versions in `buildinfo` next to it.

## Updates

The project checks [yamllint on PyPI](https://pypi.org/project/yamllint/) every 15 minutes. A release is picked up once it is 24 hours old and PyPI holds a provenance attestation showing it was published from the [adrienverge/yamllint](https://github.com/adrienverge/yamllint) repository. The new version and a regenerated `requirements.lock` are then committed together and the images are rebuilt. Only the newest release is built; tags of older versions stay as they were last built. Dependency versions in the lock must have been on PyPI for at least 7 days. The lock is also regenerated weekly at the same yamllint version, so new pathspec releases reach the current tags between yamllint releases. When a new lock would change the PyYAML version, the update, including a new yamllint release, waits until the libyaml license files are refreshed by hand (see [Building](#building)).

The images of the current version are also rebuilt when the Ubuntu or Alpine base image changes and at least every 7 days, so distro security fixes reach the current tags.

## Building

```sh
docker build -f Dockerfile.ubuntu --target slim --build-arg VERSION=<version> -t yamllint:local .
```

Use `Dockerfile.alpine` for the Alpine image. `<version>` must be the version pinned in `requirements.lock`; the build stops otherwise.

The command that produced `requirements.lock` is on its second line; it resolves for Python 3.14, the version on both bases. To regenerate the lock at the version in `package.yml`, run `rc lock requirements.lock` in this directory. `rc` is the command-line tool of [randomcontainers/ci](https://github.com/randomcontainers/ci), and it needs uv on `PATH`. If a new lock changes the PyYAML version, run `python3 scripts/bundled-licenses.py` to refresh `licenses/`. The build fails until those files match the installed PyYAML.

## Licenses

yamllint is licensed under the [GNU General Public License, version 3 or later](https://github.com/adrienverge/yamllint/blob/master/LICENSE) (GPL-3.0-or-later). It is pure Python, so the installed files are its source, and the wheel it was installed from is named in `/usr/local/share/randomcontainers/yamllint/source`. The image adds PyYAML (MIT), pathspec (MPL-2.0) and pip (MIT), which includes packages under the Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MIT, MPL-2.0 and PSF-2.0 licenses. The complete SPDX expression is in the image's `org.opencontainers.image.licenses` label, and each package's license files are in `/usr/local/share/randomcontainers/yamllint/licenses/`.

PyYAML's extension module links a static build of libyaml (MIT). The PyYAML wheel includes only PyYAML's own license, so this repository adds libyaml's license file in [`licenses/`](licenses/), and the image has it in `/usr/local/share/randomcontainers/yamllint/licenses/PyYAML/bundled/libyaml/`. The `SOURCES` file there names the PyYAML source release and the libyaml source archive with their SHA-256.

The files in this repository are available under the MIT license, see [LICENSE](LICENSE).

## Requesting a tool

To suggest another tool, use the [Request a tool](https://github.com/randomcontainers/.github/issues/new?template=tool-request.yml) form.
