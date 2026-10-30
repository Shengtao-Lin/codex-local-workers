"""Publish only the frozen preview tree; never stage the working repository."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
REMOTE = "https://github.com/Shengtao-Lin/codex-local-workers.git"
API = "https://api.github.com/repos/Shengtao-Lin/codex-local-workers"
BRANCH = "strata-preview"
TAG = "strata-v0.1.0-preview.1"
PRODUCT = KIT / "benchmarks/work/releases/strata-worker-0.1.0-preview.1-final"
ZIP = PRODUCT.with_name(PRODUCT.name + ".zip")
EXPECTED = "75f68311641fa727e8220fbeec571c7d33650560390c5c702ebd1bf887f10095"
BATCH = KIT / "benchmarks/work/publish/strata-preview-0.1.0-1"
REPO = BATCH / "repository"
NOTES = KIT / "docs/strata-release-notes-0.1.0-preview.1.md"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)


def git(*args, cwd=REPO):
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                            text=True, encoding="utf-8", check=False)
    if result.returncode:
        raise RuntimeError("Git operation failed: " + result.stderr[-1600:])
    return result.stdout.strip()


def verify_product():
    if hashlib.sha256(ZIP.read_bytes()).hexdigest() != EXPECTED:
        raise ValueError("Release ZIP changed")
    manifest = json.loads((PRODUCT / "manifest.json").read_text(encoding="utf-8"))
    for name, sha in manifest.items():
        path = PRODUCT / name
        if not path.resolve().is_relative_to(PRODUCT) or path.is_symlink():
            raise ValueError("Escaping product path")
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError("Product manifest drift: " + name)
    return manifest


def stage():
    verify_product()
    if BATCH.exists():
        raise FileExistsError("Publishing stage already exists; inspect, never overwrite")
    baseline = {
        "branch": git("branch", "--show-current", cwd=KIT),
        "head": git("rev-parse", "HEAD", cwd=KIT),
        "status": git("status", "--porcelain=v1", cwd=KIT),
        "remote_refs": git("ls-remote", "--heads", "--tags", "origin", cwd=KIT),
    }
    if git("ls-remote", "origin", "refs/heads/" + BRANCH, "refs/tags/" + TAG, cwd=KIT):
        raise ValueError("Release branch/tag exists; no overwrite permitted")
    REPO.mkdir(parents=True)
    for path in PRODUCT.rglob("*"):
        if path.is_file():
            destination = REPO / path.relative_to(PRODUCT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
    shutil.copyfile(NOTES, REPO / "RELEASE_NOTES.md")
    git("init", "--initial-branch=" + BRANCH)
    git("config", "core.autocrlf", "false")
    for key in ("user.name", "user.email"):
        git("config", key, git("config", key, cwd=KIT))
    git("remote", "add", "origin", REMOTE)
    git("fetch", "--no-tags", "origin", "codex/v2.1-dev")
    parent = git("rev-parse", "FETCH_HEAD")
    git("add", "--all")
    tree = git("write-tree")
    commit = git("commit-tree", tree, "-p", parent, "-m", "Release Strata Worker 0.1.0 preview 1")
    git("update-ref", "refs/heads/" + BRANCH, commit)
    git("tag", "-a", TAG, commit, "-m", "Strata Worker 0.1.0 Preview 1 (limited supervised prerelease)")
    assert git("status", "--porcelain=v1") == ""
    assert git("branch", "--show-current", cwd=KIT) == baseline["branch"]
    assert git("rev-parse", "HEAD", cwd=KIT) == baseline["head"]
    assert git("status", "--porcelain=v1", cwd=KIT) == baseline["status"]
    result = {"commit": commit, "parent": parent, "branch": BRANCH, "tag": TAG,
              "files": git("ls-tree", "-r", "--name-only", commit).splitlines(),
              "baseline": baseline, "zip_sha256": EXPECTED}
    save(BATCH / "staged.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "baseline"}, indent=2))


def push():
    staged = json.loads((BATCH / "staged.json").read_text())
    verify_product()
    assert git("rev-parse", BRANCH) == staged["commit"]
    expected_files = {p: PRODUCT / p for p in staged["files"] if p != "RELEASE_NOTES.md"}
    expected_files["RELEASE_NOTES.md"] = NOTES
    for name, path in expected_files.items():
        blob = subprocess.check_output(["git", "show", staged["commit"] + ":" + name], cwd=REPO)
        if blob != path.read_bytes():
            raise ValueError("Committed bytes differ from verified product: " + name)
    git("push", "--atomic", "origin", "refs/heads/" + BRANCH + ":refs/heads/" + BRANCH,
        "refs/tags/" + TAG + ":refs/tags/" + TAG)
    refs = git("ls-remote", "origin", "refs/heads/" + BRANCH, "refs/tags/" + TAG, "refs/tags/" + TAG + "^{}")
    assert staged["commit"] + "\trefs/heads/" + BRANCH in refs
    assert staged["commit"] + "\trefs/tags/" + TAG + "^{}" in refs
    baseline_refs = staged["baseline"]["remote_refs"]
    current = git("ls-remote", "--heads", "origin", "main", "codex/v2.1-dev")
    assert all(line in baseline_refs for line in current.splitlines())
    save(BATCH / "pushed.json", {"commit": staged["commit"], "refs": refs,
                                "main_and_dev_unchanged": True})
    print("Pushed isolated preview branch and tag; main/dev unchanged")


def credential():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}
    result = subprocess.run(["git", "credential", "fill"], cwd=KIT, env=env,
        input="protocol=https\nhost=github.com\npath=Shengtao-Lin/codex-local-workers.git\n\n",
        capture_output=True, text=True, check=False)
    # Credentials remain in process memory; never print or persist this output.
    fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    if result.returncode or not fields.get("password"):
        raise RuntimeError("GitHub release credentials unavailable; branch/tag may already be published")
    return fields["password"]


def release():
    verify_product()
    staged = json.loads((BATCH / "staged.json").read_text())
    assert (BATCH / "pushed.json").exists()
    token = credential()

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args, **_kwargs):
            raise ValueError("Authenticated redirect refused")

    opener = urllib.request.build_opener(NoRedirect())

    def api(url, method="GET", data=None, content_type="application/json"):
        if urllib.parse.urlsplit(url).hostname not in {"api.github.com", "uploads.github.com"}:
            raise ValueError("Unexpected GitHub API host")
        request = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "codex-local-workers-release",
            "Content-Type": content_type})
        with opener.open(request, timeout=90) as response:
            return json.load(response)

    lookup = API + "/releases/tags/" + TAG
    try:
        record = api(lookup)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise RuntimeError("GitHub release lookup failed: HTTP " + str(exc.code)) from None
        payload = {"tag_name": TAG, "target_commitish": staged["commit"],
            "name": "Strata Worker 0.1.0 Preview 1", "body": NOTES.read_text(encoding="utf-8"),
            "draft": False, "prerelease": True, "make_latest": "false"}
        record = api(API + "/releases", "POST", json.dumps(payload).encode())
    if record["tag_name"] != TAG or not record["prerelease"] or record["draft"]:
        raise ValueError("Unexpected release state; no existing release overwritten")
    name = "strata-worker-0.1.0-preview.1.zip"
    assets = [a for a in record["assets"] if a["name"] == name]
    if not assets:
        url = record["upload_url"].split("{", 1)[0] + "?" + urllib.parse.urlencode({"name": name})
        api(url, "POST", ZIP.read_bytes(), "application/zip")
    verified = api(lookup)
    assets = [a for a in verified["assets"] if a["name"] == name]
    if len(assets) != 1 or assets[0].get("digest") != "sha256:" + EXPECTED:
        raise ValueError("Published release asset digest is not verified")
    result = {"release_url": verified["html_url"], "asset_url": assets[0]["browser_download_url"],
        "asset_digest": assets[0]["digest"], "prerelease": True, "commit": staged["commit"],
        "branch": BRANCH, "tag": TAG, "main_and_dev_unchanged": True}
    save(BATCH / "released.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("mode", choices=["stage", "push", "release"])
    args = parser.parse_args()
    {"stage": stage, "push": push, "release": release}[args.mode]()
