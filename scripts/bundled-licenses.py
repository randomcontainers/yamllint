"""Collect the license file of libyaml, which PyYAML links statically.

Usage: bundled-licenses.py

PyYAML's Linux wheels link a static build of libyaml into their extension
module but include PyYAML's own license only. This reads the PyYAML version
from requirements.lock, checks in PyYAML's source release that libyaml is
still built as a static library, reads the libyaml tag the wheels are built
from in PyYAML's CI workflow at the same tag, checks that the extension
module of each Linux wheel the images install reports that libyaml version,
checks that the license file in libyaml's release archive matches the one at
that tag in libyaml's repository, and writes the file and the URLs to
licenses/pyyaml-<version>/bundled/. Run it whenever the PyYAML pin in
requirements.lock changes.
"""

import hashlib
import io
import json
import pathlib
import re
import shutil
import sys
import tarfile
import textwrap
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent

WORKFLOW = "https://raw.githubusercontent.com/yaml/pyyaml/{version}/.github/workflows/ci.yaml"
LIBYAML_REPO = "https://github.com/yaml/libyaml"
LIBYAML_ARCHIVE = "https://github.com/yaml/libyaml/releases/download/{ref}/yaml-{ref}.tar.gz"
LIBYAML_FILE = "https://raw.githubusercontent.com/yaml/libyaml/{ref}/{name}"
LICENSE_FILES = ["License"]

# The wheels installed on Ubuntu and Alpine.
PLATFORMS = (
    r"manylinux\S*_x86_64",
    r"manylinux\S*_aarch64",
    r"musllinux_\d+_\d+_x86_64",
    r"musllinux_\d+_\d+_aarch64",
)


def fetch(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def fetch_checked(item):
    data = fetch(item["url"])
    if hashlib.sha256(data).hexdigest() != item["digests"]["sha256"]:
        sys.exit(f"{item['url']} does not match its SHA-256 on PyPI")
    return data


def read(tar, path):
    try:
        return tar.extractfile(path).read()
    except KeyError:
        sys.exit(f"{path} is not in its archive")


def workflow_default(text, variable):
    """The fallback value of `VARIABLE: ${{ inputs.x || 'value' }}` in the workflow's env."""
    match = re.search(rf"^\s*{variable}:.*\|\|\s*'([^']+)'", text, re.M)
    if not match:
        sys.exit(f"PyYAML's CI workflow does not set {variable}")
    return match.group(1)


def main():
    lock = (ROOT / "requirements.lock").read_text()
    match = re.search(r"^pyyaml==([^\s;]+)", lock, re.M | re.I)
    if not match:
        sys.exit("requirements.lock does not pin pyyaml")
    pyyaml = match.group(1)
    match = re.search(r"--python-version 3\.(\d+)", lock)
    if not match:
        sys.exit("requirements.lock does not name the Python version it resolves for")
    python = f"cp3{match.group(1)}"

    release = json.loads(fetch(f"https://pypi.org/pypi/PyYAML/{pyyaml}/json"))
    sdists = [f for f in release["urls"] if f["packagetype"] == "sdist"]
    if len(sdists) != 1:
        sys.exit(f"PyYAML {pyyaml} has {len(sdists)} source releases on PyPI")
    sdist = sdists[0]
    with tarfile.open(fileobj=io.BytesIO(fetch_checked(sdist))) as tar:
        script = read(tar, f"pyyaml-{pyyaml}/packaging/build/libyaml.sh").decode()
    if "--enable-shared=no" not in script:
        sys.exit(f"PyYAML {pyyaml} packaging/build/libyaml.sh no longer builds a static libyaml")

    workflow = fetch(WORKFLOW.format(version=pyyaml)).decode()
    repo = workflow_default(workflow, "LIBYAML_REPO")
    if repo != LIBYAML_REPO:
        sys.exit(f"PyYAML {pyyaml} builds libyaml from {repo}, not {LIBYAML_REPO}")
    ref = workflow_default(workflow, "LIBYAML_REF")
    if not re.fullmatch(r"\d+\.\d+\.\d+", ref):
        sys.exit(f"PyYAML {pyyaml} builds libyaml at {ref!r}, which is not a release tag")

    # libyaml's yaml_get_version_string() returns this string, so every
    # extension module linked with that release contains it.
    marker = re.compile(rb"(?<![0-9.])" + re.escape(ref.encode()) + rb"\x00")
    for platform in PLATFORMS:
        pattern = re.compile(rf"pyyaml-{re.escape(pyyaml)}-{python}-{python}-{platform}\.whl", re.I)
        wheels = [f for f in release["urls"] if pattern.fullmatch(f["filename"])]
        if len(wheels) != 1:
            sys.exit(f"PyYAML {pyyaml} has {len(wheels)} {python} wheels for {platform}")
        with zipfile.ZipFile(io.BytesIO(fetch_checked(wheels[0]))) as wheel:
            modules = [n for n in wheel.namelist() if re.fullmatch(r"yaml/_yaml\.[^/]*\.so", n)]
            if len(modules) != 1 or not marker.search(wheel.read(modules[0])):
                sys.exit(f"{wheels[0]['filename']} does not contain libyaml {ref}")

    url = LIBYAML_ARCHIVE.format(ref=ref)
    data = fetch(url)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        texts = {name: read(tar, f"yaml-{ref}/{name}") for name in LICENSE_FILES}
    # The release archive has no published checksum, so compare its license
    # files with the ones at the tag the wheels are built from.
    for name, text in texts.items():
        if fetch(LIBYAML_FILE.format(ref=ref, name=name)) != text:
            sys.exit(f"{name} in {url} differs from {name} at libyaml tag {ref}")

    intro = (
        f"PyYAML {pyyaml} links a static build of libyaml into its extension module "
        "yaml._yaml. Its Linux wheels are built by PyYAML's CI workflow, which checks "
        f"out {LIBYAML_REPO} at the tag {ref} and configures it with "
        "--enable-shared=no (packaging/build/libyaml.sh in the PyYAML source release). "
        "The archive below is libyaml's release of that tag. libyaml is licensed under "
        "the MIT license; its license file is in the libyaml directory."
    )
    sources = [textwrap.fill(intro, 76), "", f"PyYAML {pyyaml}", f"  {sdist['url']}"]
    sources.append(f"  sha256:{sdist['digests']['sha256']}")
    sources += [f"libyaml {ref}", f"  {url}", f"  sha256:{hashlib.sha256(data).hexdigest()}"]

    base = ROOT / "licenses"
    for old in base.glob("pyyaml-*"):
        shutil.rmtree(old)
    out = base / f"pyyaml-{pyyaml}" / "bundled"
    (out / "libyaml").mkdir(parents=True)
    for name, text in texts.items():
        (out / "libyaml" / name).write_bytes(text)
    (out / "SOURCES").write_text("\n".join(sources) + "\n")
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
