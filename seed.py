"""Populate the current GitHub repository from the Parts Unlimited fixture."""
import json
import os
import re
import subprocess
import time
from pathlib import Path


DATA = json.loads(Path(__file__).with_name("parts-unlimited.json").read_text(encoding="utf-8"))
REPO = os.environ["GITHUB_REPOSITORY"]
MARKER = re.compile(r"<!-- parts-unlimited:(\d+) -->")
COLORS = {"Epic": "8250df", "Feature": "0969da", "Product Backlog Item": "1a7f37",
          "Task": "c5def5", "Bug": "cf222e"}


def api(endpoint, method="GET", payload=None, pages=False):
    cmd = ["gh", "api", "--method", method, f"repos/{REPO}/{endpoint}"]
    if pages:
        cmd += ["--paginate", "--slurp"]
    if payload is not None:
        cmd += ["--input", "-"]
    if method != "GET":
        time.sleep(1.3)
    result = subprocess.run(cmd, input=json.dumps(payload) if payload is not None else None,
                            text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{method} {endpoint}: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    return [entry for page in data for entry in page] if pages else data


def imported_issues():
    issues = {}
    for row in api("issues?state=all&per_page=100", pages=True):
        match = MARKER.search(row.get("body") or "")
        if match and "pull_request" not in row:
            key = int(match[1])
            if key in issues:
                raise ValueError(f"Duplicate template ID {key}")
            issues[key] = row
    return issues


def main():
    work = [i for i in DATA["items"] if i["type"] in COLORS]
    milestones = {m["title"]: m["number"] for m in api("milestones?state=all&per_page=100", pages=True)}
    for sprint in DATA["iterations"]:
        if sprint not in milestones:
            milestones[sprint] = api("milestones", "POST", {"title": sprint})["number"]
    labels = {"type: " + k: color for k, color in COLORS.items()}
    labels.update({"state: " + i["state"]: "d8dee4" for i in work})
    known = {label["name"] for label in api("labels?per_page=100", pages=True)}
    for name, color in labels.items():
        if name not in known:
            api("labels", "POST", {"name": name, "color": color})

    issues = imported_issues()
    for item in work:
        key = item["id"]
        if key not in issues:
            lines = [item.get("description", item["title"]), "",
                     f"Исходный ID: **{key}** · Приоритет: **{item['priority']}**."]
            if "parent" in item:
                lines += ["", f"Родительская задача: #{issues[item['parent']]['number']}."]
            if item.get("tests"):
                lines += ["", "Проверки: " + ", ".join(
                    f"[{n}](https://github.com/{REPO}/blob/main/test-plan.md#tc-{n})"
                    for n in item["tests"])]
            lines += ["", f"<!-- parts-unlimited:{key} -->"]
            payload = {"title": item["title"], "body": "\n".join(lines),
                       "labels": ["type: " + item["type"], "state: " + item["state"]]}
            if "sprint" in item:
                payload["milestone"] = milestones[item["sprint"]]
            issues[key] = api("issues", "POST", payload)
        row = issues[key]
        if item["state"] == "Done" and row["state"] == "open":
            api(f"issues/{row['number']}", "PATCH", {"state": "closed", "state_reason": "completed"})
        print(f"{key} -> #{row['number']}", flush=True)

    actual = imported_issues()
    expected = {i["id"] for i in work}
    if set(actual) != expected:
        raise ValueError("The imported IDs differ from the fixture")
    closed = sum(actual[k]["state"] == "closed" for k in expected)
    report = (f"Созданный стенд содержит {len(actual)} рабочих элементов: "
              f"{len(actual) - closed} открытых, {closed} закрытых. "
              f"В шаблоне {len(DATA['iterations'])} спринтов.\n")
    print(report)
    if "GITHUB_STEP_SUMMARY" in os.environ:
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
            stream.write(report)


if __name__ == "__main__":
    main()
