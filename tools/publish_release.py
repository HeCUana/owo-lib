#!/usr/bin/env python3
"""Create the GitHub prerelease and upload the built artifacts."""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

OWNER = "HeCUana"
REPO = "owo-lib"
TAG = "0.14.0-beta.1+26.3"
NAME = "owo-lib 0.14.0-beta.1 (Minecraft 26.3)"
ROOT = r"C:\Users\Administrator\Desktop\mod\owo-lib-0.13.1-26.2"
LIBS = os.path.join(ROOT, "build", "libs")
NOTES = os.path.join(ROOT, "RELEASE_NOTES_0.14.0-beta.1.md")

ASSETS = [
    ("owo-lib-0.14.0-beta.1+26.3.jar", "owo-lib-0.14.0-beta.1+26.3.jar"),
    ("owo-lib-0.14.0-beta.1+26.3-sources.jar", "owo-lib-0.14.0-beta.1+26.3-sources.jar"),
]


def get_token():
    env = dict(os.environ)
    env["GCM_INTERACTIVE"] = "never"
    env["GIT_TERMINAL_PROMPT"] = "0"
    payload = b"protocol=https\nhost=github.com\n\n"
    r = subprocess.run(["git", "credential", "fill"], input=payload,
                       capture_output=True, env=env, timeout=60)
    for line in r.stdout.decode("utf-8", "replace").splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    raise SystemExit("could not obtain credentials")


TOKEN = get_token()


def api(method, url, data=None, raw=False, content_type="application/json"):
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ps",
    }
    body = data
    if data is not None:
        if raw:
            headers["Content-Type"] = content_type
        else:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = resp.read()
            if raw:
                return resp.status, payload, dict(resp.headers)
            return resp.status, (json.loads(payload.decode("utf-8")) if payload else {}), dict(resp.headers)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail).get("message", detail)
        except Exception:
            pass
        return e.code, detail, {}


def main():
    api_base = f"https://api.github.com/repos/{OWNER}/{REPO}"

    # --- release ---------------------------------------------------------
    status, existing, _ = api("GET", f"{api_base}/releases/tags/{TAG}")
    if status == 200:
        print(f"release for {TAG} already exists (id={existing['id']}), updating it")
        release_id = existing["id"]
    else:
        with open(NOTES, encoding="utf-8") as fh:
            body = fh.read()
        payload = {
            "tag_name": TAG,
            "name": NAME,
            "body": body,
            "prerelease": True,
            "draft": False,
        }
        status, created, _ = api("POST", f"{api_base}/releases", payload)
        if status not in (200, 201):
            print(f"ERROR creating release: {status} {created}")
            return 1
        release_id = created["id"]
        print(f"created release id={release_id} tag={created['tag_name']} "
              f"prerelease={created['prerelease']}")

    # --- assets ----------------------------------------------------------
    # Remove any asset whose name does not match what we are about to publish, so that a
    # re-run never leaves a stale or mis-named download behind.
    status, current, _ = api("GET", f"{api_base}/releases/{release_id}/assets")
    wanted_names = {remote for _local, remote in ASSETS}
    if isinstance(current, list):
        for a in current:
            if a["name"] not in wanted_names:
                st, _msg, _ = api("DELETE", f"{api_base}/releases/assets/{a['id']}")
                print(f"  removed stale asset {a['name']} -> {st}")

    status, assets, _ = api("GET", f"{api_base}/releases/{release_id}/assets")
    have = {a["name"] for a in assets} if isinstance(assets, list) else set()

    for filename, asset_name in ASSETS:
        if asset_name in have:
            print(f"  asset already present: {asset_name}")
            continue
        path = os.path.join(LIBS, filename)
        if not os.path.exists(path):
            print(f"  MISSING local file: {path}")
            return 1

        # the asset name contains '+', which must be percent-encoded in the query string,
        # otherwise it is decoded as a space and GitHub stores a mangled file name
        upload_url = (f"https://uploads.github.com/repos/{OWNER}/{REPO}"
                      f"/releases/{release_id}/assets?name={urllib.parse.quote(asset_name)}")
        with open(path, "rb") as fh:
            data = fh.read()
        st, body, _ = api("POST", upload_url, data=data, raw=True,
                          content_type="application/octet-stream")
        if st not in (200, 201):
            print(f"  UPLOAD FAILED {asset_name}: {st} {body[:400]}")
            return 1
        info = json.loads(body.decode("utf-8")) if isinstance(body, bytes) else body
        print(f"  uploaded {info.get('name')}  {info.get('size')} bytes  "
              f"downloads={info.get('browser_download_url')}")

    # --- verify ----------------------------------------------------------
    status, rel, _ = api("GET", f"{api_base}/releases/tags/{TAG}")
    print(f"\n=== release ===")
    print(f"  tag        : {rel['tag_name']}")
    print(f"  name       : {rel['name']}")
    print(f"  prerelease : {rel['prerelease']}")
    print(f"  draft      : {rel['draft']}")
    print(f"  url        : {rel['html_url']}")
    print(f"  assets     : {len(rel['assets'])}")
    for a in rel["assets"]:
        print(f"     - {a['name']}  {a['size']} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
