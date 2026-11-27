import subprocess
import os
import re
from datetime import datetime

def _run_git(args):
    try:
        out = subprocess.check_output(
            ["git"] + args,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except Exception:
        return ""

def get_app_version():
    if os.getenv("APP_VERSION"):
        return os.getenv("APP_VERSION")
    tag = _run_git(["describe", "--tags", "--abbrev=0"])
    if tag:
        return tag.lstrip("v")
    return "1.2.1"

def get_changelog(limit=50):
    log = _run_git(["log", "-n", str(limit), "--pretty=format:%H|%ad|%s", "--date=short"])
    if not log:
        return {"current_version": get_app_version(), "changelog": []}
    releases = {}
    for line in log.splitlines():
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        _, commit_date, subject = parts
        if subject.lower().startswith(("merge", "wip", "test:")):
            continue
        m = re.match(r"^(added|add|feat|feature|fixed|fix|improved|improve|perf|launch|docs|security):\s*(.+)", subject, re.I)
        if m:
            raw_type = m.group(1).lower()
            text = m.group(2).strip()
        else:
            raw_type = "update"
            text = subject.strip()
        type_map = {"feat": "added", "feature": "added", "add": "added", "fix": "fixed", "improve": "improved", "perf": "improved"}
        item_type = type_map.get(raw_type, raw_type if raw_type in ["added", "fixed", "improved", "launch"] else "update")
        key = commit_date
        if key not in releases:
            releases[key] = {
                "version": get_app_version(),
                "date": commit_date,
                "summary": "",
                "items": []
            }
        releases[key]["items"].append({"type": item_type, "text": text})
    sorted_releases = sorted(releases.values(), key=lambda x: x["date"], reverse=True)
    if sorted_releases:
        sorted_releases[0]["version"] = get_app_version()
        sorted_releases[0]["summary"] = "Latest deploy"
    return {"current_version": get_app_version(), "changelog": sorted_releases}
