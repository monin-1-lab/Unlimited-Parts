"""Create the PUL-Web training backlog and refresh its sprint dashboard."""
import json
import os
import re
import subprocess
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

REPO = os.environ["GITHUB_REPOSITORY"]
BASE = f"https://github.com/{REPO}"
PROJECT = "https://github.com/orgs/monin-1-lab/projects/2"
TEAM = "PUL-Web"
OWNER = "Argonaut16"
AREA = "area: PUL-Web"
MARKER = re.compile(r"<!-- pul-web:([a-z]+) -->")
COLORS = {AREA: "0969da", "данные": "fbca04", "ux": "d4c5f9",
          "Разработка": "2da44e", "Дизайн": "a475f9", "Ускоренная": "d93f0b",
          "QA: Doing": "dbab09", "QA: Done": "2da44e", "state: QA": "fbca04"}
ITEMS = [
    ("epic", "Обучение продуктам", "Epic", None, "Собрать в магазине материалы для самостоятельного изучения продуктов.", True),
    ("feature", "Осваиваем дашборды", "Feature", "epic", "Раздел обучения показывает новые и недавно просмотренные материалы и принимает запросы покупателей.", True),
    ("new", "Как клиент, я хочу просмотреть новые учебники", "Product Backlog Item", "feature", "Открыв раздел обучения, покупатель видит новые опубликованные учебники в порядке убывания даты. Из списка можно открыть выбранный материал.", True),
    ("recent", "Как клиент, я хочу видеть недавно просмотренные учебники", "Product Backlog Item", "feature", "После повторного входа покупатель видит свои последние просмотренные материалы. Один материал появляется в истории один раз.", False),
    ("request", "Как клиент, я хочу запросить новые учебные материалы", "Product Backlog Item", "feature", "Покупатель может указать тему нового учебника, отправить запрос и получить подтверждение.", False),
    ("page", "Добавить страницу для самых последних учебников", "Task", "new", "Вывести список последних публикаций и добавить переход к полному материалу.", True),
    ("query", "Оптимизация запроса к данным для последних учебников", "Task", "new", "Спроектировать выборку по дате публикации и проверить план запроса на каталоге учебников.", False),
]
INITIAL = {"new":"Approved", "recent":"Committed", "request":"Done"}
EFFORT = {"new":3, "recent":2, "request":1}


def api(path, method="GET", data=None):
    args = ["gh","api","--method",method, f"repos/{REPO}/{path}"]
    if data is not None:
        args += ["--input","-"]
    response = subprocess.run(args, input=json.dumps(data) if data is not None else None,
                              text=True, capture_output=True)
    if response.returncode:
        raise RuntimeError(f"{method} {path}: {response.stderr}")
    return json.loads(response.stdout) if response.stdout.strip() else None


def body(key, description, hours=None):
    lines = [description]
    if key in EFFORT:
        lines += ["", f"**Effort:** {EFFORT[key]}"]
    if key in {"page", "query"}:
        lines += ["", f"**Оставшаяся работа:** {hours} ч", "",
                  "**Активность:** " + ("Разработка" if key == "page" else "Дизайн")]
    if key == "new":
        lines += ["", "### PartsUnlimitedGroup", "", "**Ticket ID:** PUG-1234"]
    return "\n".join([*lines, "", f"<!-- pul-web:{key} -->"])


def scan():
    labels = quote(AREA)
    result = {}
    page = 1
    while True:
        batch = api(f"issues?state=all&per_page=100&page={page}&labels={labels}")
        for issue in batch:
            if "pull_request" in issue:
                continue
            match = MARKER.search(issue.get("body") or "")
            key = match[1] if match else f"issue-{issue['number']}"
            if key in result:
                raise ValueError("Duplicate PUL-Web issue: " + key)
            result[key] = issue
        if len(batch) < 100:
            return result
        page += 1


def seed():
    labels = {r["name"] for r in api("labels?per_page=100")}
    for name, color in COLORS.items():
        if name not in labels:
            api("labels","POST",{"name":name,"color":color})
    sprints = {s["title"]:s for s in api("milestones?state=all&per_page=100")}
    for title, due in [("Sprint 1","2026-11-20"),("Sprint 2","2026-12-09"),("Sprint 3","2026-12-25")]:
        sprint = sprints[title]
        if not sprint.get("due_on"):
            api(f"milestones/{sprint['number']}","PATCH",{"due_on":due+"T18:00:00Z"})
    rows = scan()
    for key,title,kind,parent,desc,assigned in ITEMS:
        if key not in rows:
            ls = [AREA,"type: "+kind,"state: "+INITIAL.get(key,"New")]
            if key == "new":
                ls += ["данные","ux"]
            if key in {"page","query"}:
                ls.append("Разработка" if key == "page" else "Дизайн")
            rows[key] = api("issues","POST",{"title":title, "body":body(key,desc,5 if key=="page" else 3),
                             "milestone":sprints["Sprint 2"]["number"],"labels":ls,
                             "assignees":[OWNER] if assigned else []})
        if parent:
            path = f"issues/{rows[parent]['number']}/sub_issues"
            if rows[key]["id"] not in {r["id"] for r in api(path)}:
                api(path,"POST",{"sub_issue_id":rows[key]["id"]})
    page = rows["page"]
    if "**Оставшаяся работа:** 5 ч" in page["body"]:
        rows["page"] = api(f"issues/{page['number']}","PATCH",{"body":page["body"].replace("**Оставшаяся работа:** 5 ч","**Оставшаяся работа:** 8 ч")})
    for key in ("request","recent"):
        issue = rows[key]
        label_names = [v["name"] for v in issue["labels"]]
        if "state: "+INITIAL[key] in label_names:
            path = f"issues/{issue['number']}"
            if key == "request":
                api(path,"PATCH",{"state":"closed","state_reason":"completed"})
            labels = [l for l in label_names if l != "state: "+INITIAL[key]] + ["state: QA","QA: Doing"]
            if key == "recent":
                labels.append("Ускоренная")
            rows[key] = api(path,"PATCH",{"state":"open","labels":labels})
    return rows


def query(*filters):
    return BASE+"/issues?q="+quote(" ".join(["is:issue",f'label:"{AREA}"',*filters]))


def weekdays(start,end):
    return sum((start+timedelta(days=i)).weekday()<5 for i in range((end-start).days+1))


def dashboard(rows):
    start,end = date(2026,11,23),date(2026,12,9)
    off_start,off_end = date(2026,11,30),date(2026,12,4)
    days = weekdays(start,end)
    off = weekdays(off_start,off_end)
    capacity = days-off
    def ref(r):
        return f"[#{r['number']} {r['title']}]({r['html_url']})"
    def names(r):
        return {v["name"] for v in r["labels"]}
    def text_number(r,field):
        m = re.search(r"\*\*"+field+r":\*\*\s*(\d+)",r["body"] or "")
        return int(m[1]) if m else 0
    tasks = [r for r in rows.values() if "type: Task" in names(r)]
    sprint = [r for r in rows.values() if (r.get("milestone") or {}).get("title")=="Sprint 2"]
    hours = sum(text_number(r,"Оставшаяся работа") for r in sprint if r in tasks and r["state"]=="open")
    assignees = Counter(a["login"] for r in tasks for a in r["assignees"])
    if any(not r["assignees"] for r in tasks):
        assignees["Без назначения"] = sum(not r["assignees"] for r in tasks)
    pbi = [r for r in sprint if "type: Product Backlog Item" in names(r)]
    effort = Counter()
    for r in pbi:
        stage = next((l[7:] for l in names(r) if l.startswith("state: ")),"New")
        effort[stage] += text_number(r,"Effort")
    wip = [r for r in pbi if "QA: Doing" in names(r)]
    task_query = query('label:"type: Task"')
    lines = ["# Обучение продукту", "", "Панель команды **PUL-Web** · Sprint 2 · 23 ноября — 9 декабря 2026 г.", "",
             f"[Канбан команды]({PROJECT}/views/1) · [Веб-задачи]({PROJECT}/views/2) · [Планирование Sprint 2](sprint-2.md)", "",
             "## Обзор спринта", "", "Оценка Effort отражает относительный объём пользовательских историй. Часы ниже относятся к оставшейся работе по задачам.", "",
             f"[Диаграмма Effort по стадиям]({PROJECT}/insights/2)", "",
             "| Стадия истории | Effort |","| --- | ---: |", *[f"| {s} | {v} |" for s,v in sorted(effort.items())],
             f"| **Всего** | **{sum(effort.values())}** |","", "## Ёмкость спринта", "",
             f"График разработки — 1 ч в рабочий день, понедельник–пятница. В учебном календаре с 30 ноября по 4 декабря отведено пять рабочих дней отсутствия. Из {days} рабочих дней доступны {capacity}.",
             "", "| Доступно | Осталось по задачам | Перегрузка |","| ---: | ---: | ---: |",
             f"| {capacity} ч | {hours} ч | {max(0,hours-capacity)} ч |", "",
             f"[Оставшаяся работа по исполнителям]({PROJECT}/insights/3)", "",
             "При первом планировании разработка страницы занимала 5 ч, проектирование запроса — 3 ч. После пересмотра оценка страницы выросла до 8 ч. Обе задачи включены в Sprint 2.", "",
             "## Веб-задачи — по назначению","",f"[Общий запрос в Issues]({task_query}) · [Сохранённое представление]({PROJECT}/views/2) · [Диаграмма по исполнителям]({PROJECT}/insights/1)", "",
             "| Задача | Исполнитель | Активность | Остаток |","| --- | --- | --- | ---: |"]
    for r in tasks:
        who = ", ".join(a["login"] for a in r["assignees"]) or "Без назначения"
        activity = "Разработка" if "Разработка" in names(r) else "Дизайн"
        lines.append(f"| {ref(r)} | {who} | {activity} | {text_number(r,'Оставшаяся работа')} ч |")
    lines += ["", "```mermaid","pie showData",'    title Веб-задачи — по назначению',
              *[f'    "{who}" : {n}' for who,n in sorted(assignees.items())],"```","",
              "## Канбан историй","",
              "| Дорожка | New | Approved | Committed | Утверждено QA · Doing | Утверждено QA · Done | Done |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for lane in ("Ускоренная","Обычная"):
        buckets = [[] for _ in range(6)]
        for r in pbi:
            ls = names(r)
            if ("Ускоренная" in ls)!=(lane=="Ускоренная"):
                continue
            keys = ["state: New","state: Approved","state: Committed","QA: Doing","QA: Done","state: Done"]
            for idx,k in enumerate(keys):
                if k in ls:
                    buckets[idx].append(ref(r))
                    break
        lines.append("| "+" | ".join([lane,*["<br>".join(c) or "—" for c in buckets]])+" |")
    lines += ["",f"**Незавершённая работа в QA:** {len(wip)} из 1. " + ("Лимит превышен." if len(wip)>1 else "В пределах лимита."),
              "", "**Критерий завершения QA.** Все тесты истории проходят. После проверки результата карточку перемещают из Doing в Done. В первую очередь команда берёт карточку с ускоренной дорожки.", "",
              "## Бэклог команды","", f"[Эпик и все дочерние уровни]({rows['epic']['html_url']}) · [Рабочие элементы команды]({query()}) · [Календарь спринтов]({BASE}/milestones).",
              "", "| Итерация | Период |","| --- | --- |","| Sprint 1 | 02.11–20.11.2026 |","| Sprint 2 | 23.11–09.12.2026 |","| Sprint 3 | 10.12–25.12.2026 |","",
              "## Мой Scrum", "", "Иерархия работ включает эпик, функциональность, пользовательскую историю и задачу. В каждой истории поле Ticket ID группы PartsUnlimitedGroup хранит внешний номер обращения. При создании истории используется [форма бэклога]("+BASE+"/issues/new?template=pul-backlog.yml).", ""]
    dest = Path("planning/README.md")
    dest.parent.mkdir(exist_ok=True)
    dest.write_text("\n".join(lines), encoding="utf-8")
    sprint_page = ["# Планирование Sprint 2", "", "Команда PUL-Web развивает раздел обучения интернет-магазина. В область команды входят все дочерние элементы эпика, включая задачи разработки и проектирования.", "",
                   "## Бэклог и декомпозиция", "", "| Элемент | Уровень | Родитель | Состояние при планировании |", "| --- | --- | --- | --- |"]
    for key,_,kind,parent,_,_ in ITEMS:
        sprint_page.append(f"| {ref(rows[key])} | {kind} | {ref(rows[parent]) if parent else '—'} | {INITIAL.get(key,'New')} |")
    sprint_page += ["","## Нагрузка команды","",
                    "| Задача | Активность | Первичная оценка | После уточнения | Исполнитель |","| --- | --- | ---: | ---: | --- |",
                    f"| {ref(rows['page'])} | Разработка | 5 ч | 8 ч | {OWNER} |",f"| {ref(rows['query'])} | Дизайн | 3 ч | 3 ч | Без назначения |","",
                    "При ставке 1 ч в день и пяти рабочих днях отсутствия из 13 рабочих дней спринта доступны 8 ч. Первичная оценка двух задач укладывалась в 8 ч. После уточнения требуется 11 ч, превышение составляет 3 ч. Обе задачи остаются в текущей итерации.",
                    "", "[Панель спринта и распределение задач](README.md) · [Итерации проекта]("+BASE+"/milestones)", ""]
    dest.with_name("sprint-2.md").write_text("\n".join(sprint_page),encoding="utf-8")
    print(f"PUL-Web: {len(rows)} issues, {len(tasks)} tasks, {sum(effort.values())} effort, {hours}/{capacity} hours, QA {len(wip)}/1.")


if __name__ == "__main__":
    items = scan() if os.environ.get("GITHUB_EVENT_NAME")=="issues" else seed()
    if not {r[0] for r in ITEMS}.issubset(items):
        raise ValueError("PUL-Web backlog is incomplete")
    dashboard(items)
