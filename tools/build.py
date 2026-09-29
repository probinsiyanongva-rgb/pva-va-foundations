#!/usr/bin/env python3
"""Build the VA Foundations standalone module from the approved Markdown.

Source of truth: tools/source/PVA_VA_Foundations_Revised_Course.md
Quick Checks:    tools/source/VA_Foundations_Quick_Checks.md (approved 29 Sep 2026)

tools/source/ is private (not in the public repo): the course Markdown contains
the Final Assessment answer key.

Output: public/  (the only folder Cloudflare serves; see wrangler.jsonc)

Run:  python3 tools/build.py
The script never rewrites lesson wording. It converts Markdown to HTML and
turns the lesson activities into interactive, browser-saved components.
"""
import html
import json
import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tools" / "source" / "PVA_VA_Foundations_Revised_Course.md"
QC_SRC = ROOT / "tools" / "source" / "VA_Foundations_Quick_Checks.md"
OUT = ROOT / "public"
ACADEMY_URL = "https://probinsiyanongva.org/"
VERSION = "1.0"

# Courses the lessons mention by name -> where they live today.
COURSE_LINKS = {
    "Computer & Laptop Basics": "https://probinsiyanongva.org/computer-basics/",
    "Internet, Email & Google Workspace": "https://probinsiyanongva.org/internet-workspace-basics/",
    "Document Basics": "https://pva-document-basics.probinsiyanongva.workers.dev/",
    "Spreadsheet Basics": "https://pva-spreadsheet-basics.probinsiyanongva.workers.dev/",
}

LESSON_TITLES = {}
esc = lambda s: html.escape(s, quote=True)


def md(text: str) -> str:
    out = markdown.markdown(text, extensions=["tables", "sane_lists"])
    out = out.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    return out


def inline(text: str) -> str:
    """Render a short inline fragment (no wrapping <p>)."""
    h = md(text.strip())
    return re.sub(r"^<p>(.*)</p>$", r"\1", h, flags=re.S)


def blocks(text: str):
    return [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]


def strip_rules(text: str) -> str:
    return re.sub(r"^\s*---\s*$", "", text, flags=re.M).strip()


# ---------------------------------------------------------------- parsing
def split_top(src: str):
    """Split by top-level '# ' headings -> list of (title, body)."""
    parts = re.split(r"^# (.+)$", src, flags=re.M)
    out = []
    for i in range(1, len(parts), 2):
        out.append((parts[i].strip(), parts[i + 1]))
    return out


def split_h2(body: str):
    parts = re.split(r"^## (.+)$", body, flags=re.M)
    intro = strip_rules(parts[0])
    secs = []
    for i in range(1, len(parts), 2):
        secs.append((parts[i].strip(), strip_rules(parts[i + 1])))
    return intro, secs


# ---------------------------------------------------------------- flows
def flow_step(head_block: str, detail_block: str):
    lines = [l.strip() for l in head_block.splitlines() if l.strip()]
    name = re.sub(r"^#+\s*", "", lines[0]).strip("* ").strip()
    sub = lines[1].strip("* ").strip() if len(lines) > 1 else ""
    detail_lines = [l.strip() for l in detail_block.splitlines() if l.strip()]
    here = detail_block.strip() == "You are here."
    return {"name": name, "sub": sub, "detail": " · ".join(detail_lines), "here": here}


def parse_flow(text: str):
    parts = re.split(r"\n\s*↓\s*\n", "\n" + text + "\n")
    if len(parts) < 2:
        return None
    steps, intro, trailing = [], [], []
    b0 = blocks(parts[0])
    intro, steps = b0[:-2], [flow_step(b0[-2], b0[-1])]
    for mid in parts[1:-1]:
        b = blocks(mid)
        assert len(b) == 2, f"unexpected flow block: {mid!r}"
        steps.append(flow_step(b[0], b[1]))
    bl = blocks(parts[-1])
    steps.append(flow_step(bl[0], bl[1]))
    trailing = bl[2:]
    return intro, steps, trailing


def render_flow(steps):
    items = []
    for s in steps:
        cls = ' class="here"' if s["here"] else ""
        tag = '<span class="here-tag">You are here</span>' if s["here"] else ""
        sub = f'<div class="flow-sub">{esc(s["sub"])}</div>' if s["sub"] else ""
        det = "" if s["here"] else (f'<div class="flow-detail">{inline(s["detail"])}</div>' if s["detail"] else "")
        items.append(f'<li{cls}><div class="flow-name">{esc(s["name"])}{tag}</div>{sub}{det}</li>')
    return '<ol class="flow">' + "".join(items) + "</ol>"


# ---------------------------------------------------------------- activities
def graded_item(key, qlabel, question_html, options, correct, good="", try_msg=""):
    opts = "".join(
        f'<label class="choice"><input type="radio" name="{esc(key)}" value="{i}"><span>{inline(o)}</span></label>'
        for i, o in enumerate(options)
    )
    return (
        f'<div class="act-item act-graded" data-key="{esc(key)}" data-correct="{correct}" '
        f'data-good="{esc(good)}" data-try="{esc(try_msg)}">'
        f'<div class="act-q"><span class="q-num">{esc(qlabel)}</span><br>{question_html}</div>'
        f'<div class="choice-group" role="radiogroup">{opts}</div>'
        f'<div class="feedback" aria-live="polite"></div></div>'
    )


def self_choice(key, label, options, note_label):
    opts = "".join(
        f'<label class="choice"><input type="radio" name="{esc(key)}" value="{esc(o)}"><span>{esc(o)}</span></label>'
        for o in options
    )
    return (f'<div class="choice-row self-choice" role="radiogroup" aria-label="{esc(label)}" '
            f'data-key="{esc(key)}" data-note-label="{esc(note_label)}">{opts}</div>')


def text_field(key, label, rows=3, single=False):
    fid = "f-" + re.sub(r"[^a-z0-9]+", "-", key.lower())
    if single:
        field = f'<input class="response" type="text" id="{fid}" data-key="{esc(key)}" data-note-label="{esc(label)}">'
    else:
        field = f'<textarea class="response" id="{fid}" rows="{rows}" data-key="{esc(key)}" data-note-label="{esc(label)}"></textarea>'
    return (f'<label class="field-label" for="{fid}">{esc(label)}</label>{field}'
            f'<p class="saved-note" data-for="{fid}" aria-live="polite"></p>')


ACT_PREFIX = re.compile(r"^(Activity\s*[—:]\s*|\d+\.\s*)")


def activity_wrap(title, inner, resettable=False):
    reset = ('<div class="hero-actions" style="margin:4px 0 12px"><button type="button" class="btn subtle small-btn" '
             'data-reset-activity>Reset this activity</button></div>') if resettable else ""
    heading = esc(ACT_PREFIX.sub("", title))
    return (f'<section class="activity"><div class="activity-title">Activity</div>'
            f'<h2>{heading}</h2>{inner}{reset}</section>')


def act_l1(title, text):
    intro, rest = text.split("### Scenario 1", 1)
    rest = "### Scenario 1" + rest
    items = []
    for m in re.finditer(r"### (Scenario \d+)\s*\n(.*?)(?=\n### |\Z)", rest, flags=re.S):
        label, body = m.group(1), m.group(2).strip()
        b = blocks(body)
        situation, ask, answer = b[0], b[1].strip("* "), " ".join(b[2:])
        correct = 0 if answer.startswith("Yes") else 1
        q = f"<p>{inline(situation)}</p><p><strong>{esc(ask)}</strong></p>"
        items.append(graded_item("act:" + label.lower().replace(" ", "-"), label, q, ["Yes", "No"], correct,
                                 good=answer, try_msg=answer))
    return activity_wrap(title, md(intro) + "".join(items), resettable=True)


def act_l2(title, text):
    intro, rest = text.split("### Question 1", 1)
    rest = "### Question 1" + rest
    items = []
    for m in re.finditer(r"### (Question \d+)\s*\n(.*?)(?=\n### |\Z)", rest, flags=re.S):
        label, body = m.group(1), m.group(2).strip()
        b = blocks(body)
        opts, qtext, ans = [], [], None
        for blk in b:
            mo = re.match(r"^([A-D])\.\s+(.*)$", blk, flags=re.S)
            ma = re.match(r"^\*\*Answer:\s*([A-D])\*\*$", blk)
            if ma:
                ans = "ABCD".index(ma.group(1))
            elif mo:
                opts.append(mo.group(2).strip())
            else:
                qtext.append(blk)
        assert ans is not None and opts
        q = "".join(f"<p>{inline(t)}</p>" for t in qtext)
        good = "That's the step the lesson recommends."
        try_msg = "The lesson's answer is: " + opts[ans]
        items.append(graded_item("act:" + label.lower().replace(" ", "-"), label, q, opts, ans, good, try_msg))
    return activity_wrap(title, md(intro) + "".join(items), resettable=True)


def act_l3(title, text):
    b = blocks(text)
    # intro blocks until the numbered list
    out, idx = [], 0
    while not re.match(r"^1\.\s", b[idx]):
        out.append(md(b[idx])); idx += 1
    statements = re.findall(r"^\d+\.\s+(.*)$", b[idx], flags=re.M)
    choices = ["Yes", "Some", "Need Practice"]
    rows = []
    for i, s in enumerate(statements, 1):
        rows.append(f'<div class="act-item"><p class="act-q">{i}. {esc(s)}</p>'
                    f'{self_choice(f"resp:can-{i}", s, choices, f"{i}. {s}")}</div>')
    tail = "".join(md(x) for x in b[idx + 1:])
    return activity_wrap(title, "".join(out) + "".join(rows) + tail)


def act_l4(title, text):
    items = []
    for m in re.finditer(r"### (.+?)\s*\n(.*?)(?=\n### |\Z)", "\n" + text, flags=re.S):
        area, body = m.group(1).strip(), m.group(2).strip()
        b = blocks(body)
        question, opts = b[0], [o.strip() for o in b[1].strip("* ").split(" / ")]
        items.append(f'<div class="act-item"><p class="act-q"><span class="q-num">{esc(area)}</span><br>{esc(question)}</p>'
                     f'{self_choice("resp:setup-" + area.lower(), question, opts, f"{area}: {question}")}</div>')
    intro = '<p>Choose the answer that fits your situation today. There is no score. Your choices are saved in this browser.</p>'
    return activity_wrap(title, intro + "".join(items))


def act_l5(title, text):
    b = blocks(text)
    pre, table, post = [], None, []
    for blk in b:
        if blk.startswith("|"):
            table = blk
        elif table is None:
            pre.append(blk)
        else:
            post.append(blk)
    rows = [r for r in table.splitlines()[2:] if r.strip()]
    trs = []
    for r in rows:
        cells = [c.strip() for c in r.strip("|").split("|")]
        area, opts = cells[0], [o.strip() for o in cells[1].split(" / ")]
        key = "resp:map-" + re.sub(r"[^a-z0-9]+", "-", area.lower()).strip("-")
        trs.append(f'<tr><td><strong>{esc(area)}</strong></td><td>{self_choice(key, area, opts, area)}</td></tr>')
    tbl = ('<div class="table-wrap"><table class="fill-table"><thead><tr><th>Area</th><th>My Starting Point</th></tr></thead>'
           f'<tbody>{"".join(trs)}</tbody></table></div>')
    return activity_wrap(title, "".join(md(x) for x in pre) + tbl + "".join(md(x) for x in post))


def act_l6(title, text):
    first = text.index("### A.")
    intro, rest = text[:first], text[first:]
    # trailing text after the last statement block
    items, tail = [], ""
    parts = re.split(r"^### ([A-F])\.\s*$", rest, flags=re.M)
    for i in range(1, len(parts), 2):
        letter, body = parts[i], parts[i + 1].strip()
        b = blocks(body)
        statement = b[0]
        m = re.match(r"^(Possible areas?):\s*\n\*\*(.+?)\*\*$", b[1], flags=re.S)
        assert m, f"L6 activity block {letter} not in expected format"
        label, areas = m.group(1), m.group(2).strip()
        if len(b) > 2:
            tail = "\n\n".join(b[2:])
        key = f"resp:interest-{letter.lower()}"
        items.append(
            f'<div class="act-item pick" data-key="{key}" data-note-label="{esc(letter + ". " + statement.strip(chr(8220) + chr(8221) + chr(34)))}">'
            f'<label class="choice"><input type="checkbox"><span><strong>{letter}.</strong> {inline(statement)}</span></label>'
            f'<div class="area-reveal">{esc(label)}: <strong>{esc(areas)}</strong></div></div>')
    note = '<p class="small">Tick the statements that sound worth exploring. Each one shows the areas it points to.</p>'
    return activity_wrap(title, md(intro) + note + "".join(items) + md(tail))


def act_l7(title, text):
    b = blocks(text)
    # intro: blocks before first "### Learn"
    idx = next(i for i, x in enumerate(b) if x.startswith("### Learn"))
    intro = "".join(md(x) for x in b[:idx])
    fields = [text_field("resp:skill", "The skill I'm thinking about", single=True)]
    i = idx
    while i < len(b) and b[i].startswith("### "):
        step = b[i][4:].strip()
        prompt = b[i + 1]
        fields.append(text_field(f"resp:{step.lower()}", f"{step} — {prompt}", rows=2))
        i += 2
    tail = "".join(md(x) for x in b[i:])
    return activity_wrap(title, intro + "".join(fields) + tail)


def act_l8(title, text):
    b = blocks(text)
    idx = next(i for i, x in enumerate(b) if x.startswith("### 1."))
    intro = "".join(md(x) for x in b[:idx])
    fields, i = [], idx
    while i < len(b) and b[i].startswith("### "):
        prompt = b[i][4:].strip()
        n = re.match(r"(\d+)\.", prompt).group(1)
        fields.append(text_field(f"resp:next-{n}", prompt, rows=2))
        i += 2  # skip the "> ____" line
    tail = "".join(md(x) for x in b[i:])
    return activity_wrap(title.replace("10. ", ""), intro + "".join(fields) + tail)


ACTIVITIES = {
    (1, "Activity — Could This Be VA Work?"): act_l1,
    (2, "Activity — Follow the Task"): act_l2,
    (3, "Activity — What Can I Already Do?"): act_l3,
    (4, "A Quick Setup Check"): act_l4,
    (5, "Activity: Build Your Learning Map"): act_l5,
    (6, "Activity: What Sounds Interesting?"): act_l6,
    (7, "Activity: Where Are You?"): act_l7,
    (8, "10. Your Next Step"): act_l8,
}


# ---------------------------------------------------------------- page chrome
def head(title, root):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#1B4332">
<title>{esc(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}shared/course.css">
</head>"""


def chrome_top(root):
    return f"""<a class="skip-link" href="#main-content">Skip to course content</a>
<header class="route-bar"><div class="route-inner"><a class="home-btn" href="{ACADEMY_URL}" aria-label="Back to PVA Academy home page">← PVA Academy</a><div class="route-title"><a href="{root}">VA Foundations</a></div><div class="route-tag">STAGE 1 · EXPLORE</div></div></header>
<div class="progress-wrap"><div class="progress-inner"><div class="progress-label"><span id="progressText">Getting started</span><span id="progressPct">0%</span></div><div class="progress-track" id="progressTrack"></div></div></div>"""


STORAGE_BANNER = """<div class="storage-banner hidden" id="storageBanner" role="status" aria-live="polite"><strong>Progress can't be saved in this browser.</strong><br><span id="storageBannerText">You can continue learning, but your progress may not remain after you close or refresh this page. If you are using private browsing or have blocked site data, try a normal browser window.</span></div>"""

FOOTER = f'<footer><span class="footer-mark">PVA Academy</span> · Practical. Valuable. Authentic. · VA Foundations v{VERSION}</footer>'

WARNINGS = """<ul>
<li>Your saved progress may not be available if you switch to another device or browser.</li>
<li>Clearing your browser's site data may remove your saved progress.</li>
<li>Private or incognito browsing may prevent your saved progress from being available later.</li>
<li>You are responsible for keeping a backup. Use <strong>Export Progress</strong> to save a backup file.</li>
</ul>"""

PROGRESS_TOOLS = """<div class="progress-tools"><button class="btn subtle" type="button" id="exportBtn">Export Progress</button><button class="btn subtle" type="button" id="restoreBtn">Restore Progress</button><button class="btn subtle" type="button" id="clearBtn">Clear Progress</button><span class="save-state" data-save-state>Progress is saved in this browser.</span><input id="restoreFile" type="file" accept="application/json,.json" hidden></div>"""


# ---------------------------------------------------------------- lessons
def build_lesson(num, title, body, qc_purpose):
    root = "../"
    intro, secs = split_h2(body)
    parts, next_block = [], ""
    if intro:
        parts.append(md(intro))
    for stitle, stext in secs:
        if stitle == title:  # duplicated title heading inside the lesson
            parts.append(md(stext)); continue
        if (num, stitle) in ACTIVITIES:
            parts.append(ACTIVITIES[(num, stitle)](stitle, stext)); continue
        if stitle == "Quick Check":
            m = re.search(r"\*\*Purpose:\*\*\s*(.+)", stext)
            qc_purpose[f"lesson-{num}"] = m.group(1).strip() if m else ""
            continue
        if stitle in ("Next Lesson", "Next Step"):
            b = blocks(stext)
            heading = b[0].lstrip("# ").strip()
            texts = [x for x in b[1:] if not x.startswith("**Complete the Final")]
            if num < 8:
                href, label = f"../lesson-{num + 1}/", f"Go to Lesson {num + 1} →"
            else:
                href, label = "../final-assessment/", "Go to the Final Assessment →"
            next_block = (f'<section class="card"><div class="connection-title">{esc(stitle)}</div>'
                          f'<h2>{esc(heading)}</h2>{"".join(md(x) for x in texts)}'
                          f'<div class="hero-actions"><a class="btn" href="{href}">{label}</a></div></section>')
            continue
        if stitle in ("Key Takeaway", "What You Should Know After This Lesson"):
            parts.append(f'<div class="takeaway-title">{esc(stitle)}</div><div class="key-idea">{md(stext)}</div>')
            continue
        if stitle in ("Learn to Work", "Find Your Direction"):
            parts.append(f'<div class="tip"><div class="section-label">Next stage in the journey</div>'
                         f'<h3 style="margin-top:0">{esc(stitle)}</h3>{md(stext)}</div>')
            continue
        flow = parse_flow(stext) if "↓" in stext else None
        if flow:
            fi, steps, ft = flow
            parts.append(f"<h2>{esc(stitle)}</h2>" + "".join(md(x) for x in fi) + render_flow(steps) + "".join(md(x) for x in ft))
            continue
        parts.append(f"<h2>{esc(stitle)}</h2>{md(stext)}")

    content = "\n".join(parts)
    if num == 8:
        for name, url in COURSE_LINKS.items():
            h = f"<h3>{esc(name)}</h3>"
            if h in content:
                content = content.replace(h, h + f'<p><a class="btn secondary small-btn" href="{url}">Open {esc(name)} →</a></p>', 1)

    prev_link = (f'<a class="prev" href="../lesson-{num - 1}/"><span class="pager-dir">← Previous</span><span class="pager-title">Lesson {num - 1}: {esc(LESSON_TITLES[num - 1])}</span></a>'
                 if num > 1 else '<a class="prev" href="../"><span class="pager-dir">← Back</span><span class="pager-title">VA Foundations home</span></a>')
    next_link = (f'<a class="next" href="../lesson-{num + 1}/"><span class="pager-dir">Next →</span><span class="pager-title">Lesson {num + 1}: {esc(LESSON_TITLES[num + 1])}</span></a>'
                 if num < 8 else '<a class="next" href="../final-assessment/"><span class="pager-dir">Next →</span><span class="pager-title">Final Assessment</span></a>')

    page = f"""{head(f"Lesson {num}: {title} — VA Foundations | PVA Academy", root)}
<body data-lesson-id="lesson-{num}" data-root="{root}">
{chrome_top(root)}
<main id="main-content">
{STORAGE_BANNER}
<nav class="lesson-nav" id="lessonNav" aria-label="Course lessons"></nav>
<article class="card lesson" id="lessonCard">
<div class="lesson-head"><div class="lesson-num">{num}</div><div class="lesson-title-wrap"><div class="section-label">Lesson {num} of 8</div><h1>{esc(title)}</h1><span class="done-stamp">✓ Completed</span></div></div>
<div class="lesson-body">
{content}
</div>
<section class="quick-check" id="quickCheck" aria-label="Quick Check"></section>
<div class="lesson-footer"><span class="next-hint">Finished this lesson? Marking it complete is saved in this browser.</span><div class="footer-actions"><button class="btn" type="button" id="markBtn">Mark Lesson {num} complete</button><button class="btn subtle" type="button" id="notDoneBtn" disabled>Mark as not done</button></div></div>
<div class="tip hidden" id="donePanel" role="status"><strong>Lesson {num} is marked complete.</strong> <span class="small">It's saved in this browser.</span><div class="hero-actions" style="margin-top:10px"><button class="btn secondary small-btn" type="button" id="notesBtn">Download my Lesson {num} notes (.txt)</button></div></div>
</article>
{next_block}
<nav class="pager" aria-label="Lesson navigation">{prev_link}{next_link}</nav>
{FOOTER}
</main>
<script src="{root}shared/progress.js"></script>
<script src="{root}shared/quick-checks.js"></script>
<script src="{root}shared/lesson.js"></script>
</body>
</html>
"""
    d = OUT / f"lesson-{num}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(page, encoding="utf-8")


# ---------------------------------------------------------------- quick checks
def parse_quick_checks(purposes):
    src = QC_SRC.read_text(encoding="utf-8")
    data = {}
    for m in re.finditer(r"^## Lesson (\d+) — .*?$(.*?)(?=^## |\Z)", src, flags=re.M | re.S):
        num, body = int(m.group(1)), m.group(2)
        qs = []
        for q in re.finditer(r"^\*\*(\d+\.\d+)\*\*\s+(.+?)$(.*?)(?=^\*\*\d+\.\d+\*\*|\Z)", body, flags=re.M | re.S):
            qid, qtext, rest = q.group(1), q.group(2).strip(), q.group(3)
            opts, answer = [], None
            for om in re.finditer(r"^- [A-D]\.\s+(✅\s*)?(.+)$", rest, flags=re.M):
                if om.group(1):
                    answer = len(opts)
                opts.append(om.group(2).strip())
            ex = re.search(r"^\*Explanation:\*\s*(.+)$", rest, flags=re.M)
            assert answer is not None and len(opts) >= 3, qid
            qs.append({"id": qid, "q": qtext, "options": opts, "answer": answer, "explain": ex.group(1).strip() if ex else ""})
        data[f"lesson-{num}"] = {"purpose": purposes.get(f"lesson-{num}", ""), "questions": qs}
    return data


# ---------------------------------------------------------------- assessment
def fnv(s: str) -> str:
    h = 2166136261
    for ch in s.encode("utf-8"):
        h ^= ch
        h = (h * 16777619) & 0xFFFFFFFF
    return format(h, "08x")


SALT = "pva-vaf-2026"


def parse_assessment(body):
    _, secs = split_h2(body)
    qs = []
    for stitle, stext in secs:
        m = re.match(r"Question (\d+)$", stitle)
        if not m:
            continue
        n = int(m.group(1))
        b = blocks(stext)
        qtext, opts, ans = [], [], None
        for blk in b:
            ma = re.match(r"^\*\*Correct answer:\s*([A-D])\*\*$", blk)
            if ma:
                ans = "ABCD".index(ma.group(1)); continue
            if re.match(r"^A\.\s", blk):
                opts = [re.sub(r"^[A-D]\.\s+", "", l.strip()) for l in blk.splitlines() if l.strip()]
                continue
            qtext.append(blk)
        assert len(opts) == 4 and ans is not None, n
        qs.append({"n": n, "html": "".join(md(t) for t in qtext), "options": [inline(o) for o in opts], "ans": ans})
    return qs


def parse_answer_lessons(src):
    lessons = {}
    for m in re.finditer(r"^\|\s*(\d+)\s*\|\s*[A-D]\s*\|\s*(Lessons? [^|]+?)\s*\|", src, flags=re.M):
        lessons[int(m.group(1))] = m.group(2).strip()
    return lessons


def build_assessment(qs, lesson_refs):
    root = "../"
    public_qs = []
    for q in qs:
        public_qs.append({
            "n": q["n"], "html": q["html"], "options": q["options"],
            # Hashed so the answer letters are not readable in the page source.
            "k": fnv(f'{SALT}|{q["n"]}|{q["ans"]}'),
            "review": lesson_refs.get(q["n"], ""),
        })
    data_js = "window.VAF_ASSESSMENT = " + json.dumps(public_qs, ensure_ascii=False, indent=1) + ";\nwindow.VAF_SALT = " + json.dumps(SALT) + ";\n"
    (OUT / "shared" / "assessment-data.js").write_text(data_js, encoding="utf-8")

    page = f"""{head("Final Assessment — VA Foundations | PVA Academy", root)}
<body data-root="{root}">
{chrome_top(root)}
<main id="main-content">
{STORAGE_BANNER}
<nav class="lesson-nav" id="lessonNav" aria-label="Course lessons"></nav>
<section class="card" id="assessIntro">
<div class="section-label">Final Assessment</div><div class="folder-tab">20 questions · Multiple choice</div>
<h1 style="font:700 clamp(1.7rem,4vw,2.3rem)/1.15 Fraunces,Georgia,serif;color:var(--green);margin:0 0 10px">VA Foundations — Final Assessment</h1>
<p>This assessment checks your understanding of the basic concepts covered in VA Foundations.</p>
<p>Read each question carefully and choose the <strong>best answer</strong>.</p>
<p>The assessment focuses on understanding VA work, not memorizing exact wording from the lessons.</p>
<div class="key-idea"><strong>How it works</strong><ul style="margin:.4em 0 0">
<li>20 multiple-choice questions, one at a time. Your answers are saved in this browser as you go.</li>
<li>You need <strong>16 of 20 (80%)</strong> to pass.</li>
<li>Your score appears after you submit. If you score below 16, you can review the suggested lessons and retake it.</li>
<li>VA Foundations is complete when all 8 lessons are marked complete and you pass this assessment.</li>
</ul></div>
<div id="gate" class="callout hidden"></div>
<div class="hero-actions"><button class="btn" type="button" id="startBtn">Start the assessment</button></div>
</section>
<section class="card hidden" id="assessRunner" aria-live="polite"></section>
<section class="card hidden" id="assessResult"></section>
<section class="completion hidden" id="completion"></section>
{FOOTER}
</main>
<script src="{root}shared/progress.js"></script>
<script src="{root}shared/assessment-data.js"></script>
<script src="{root}shared/assessment.js"></script>
</body>
</html>
"""
    d = OUT / "final-assessment"
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(page, encoding="utf-8")


# ---------------------------------------------------------------- home + progress
def course_purpose(body):
    intro, _ = split_h2(body)
    return intro


def build_home(purpose_md, journey_steps):
    root = "./"
    b = blocks(purpose_md)
    # Course purpose from the Markdown, addressed to the learner.
    purpose_html = "".join(md(x.replace("The learner should finish the course understanding:",
                                        "By the end of this course, you should understand:")) for x in b)
    rows = "".join(
        f'<li><a class="lesson-row" data-lesson="lesson-{n}" href="lesson-{n}/"><span class="lesson-num">{n}</span>'
        f'<span class="row-text"><span class="row-title">{esc(t)}</span><span class="row-sub">Lesson {n} of 8</span></span>'
        f'<span class="stamp" data-stamp>Not started</span></a></li>'
        for n, t in LESSON_TITLES.items())
    rows += ('<li><a class="lesson-row final" data-lesson="final-assessment" href="final-assessment/"><span class="lesson-num">✓</span>'
             '<span class="row-text"><span class="row-title">Final Assessment</span><span class="row-sub">20 questions · 16 of 20 to pass</span></span>'
             '<span class="stamp" data-stamp>Not started</span></a></li>')

    page = f"""{head("VA Foundations — PVA Academy", root)}
<body data-root="{root}" data-page="home">
{chrome_top(root)}
<main id="main-content">
<section class="course-header" id="top"><div class="eyebrow">PVA Academy · Beginner VA Journey · Stage 1: Explore</div><h1>VA Foundations</h1><p>Start here if you know little or nothing about Virtual Assistant work. This course gives you a clear, practical picture of the VA world before you move into specific skills.</p><div class="meta-row"><span class="meta-chip">Free</span><span class="meta-chip">Self-Paced</span><span class="meta-chip">No Login</span><span class="meta-chip">8 Lessons + Final Assessment</span></div></section>
{STORAGE_BANNER}
<div class="before-start" aria-labelledby="before-start-title"><h2 id="before-start-title">Before You Start</h2><p><strong>No login is required.</strong> You can start learning right away.</p><p>Your course progress is saved on the device and browser you are using right now. Nothing is sent to an account or a server.</p><p>For the best experience, keep using the <strong>same device and browser</strong> while you take this course.</p><p><strong>Important:</strong></p>{WARNINGS}<p class="small" style="margin-bottom:0">Your earlier VA Foundations progress on the PVA Academy site is not carried over. This version of the course starts fresh.</p></div>

<section class="card" aria-labelledby="progress-h">
<div class="section-label">Your progress</div>
<h2 id="progress-h" style="margin-bottom:6px">Where you are</h2>
<div class="progress-summary"><span class="big-pct" id="homePct">0%</span><span id="homeSummary">0 of 8 lessons complete · Final Assessment not passed yet</span></div>
<div class="hero-actions"><a class="btn" id="continueBtn" href="lesson-1/">Start Lesson 1</a><a class="btn secondary" href="progress/">Progress &amp; backup</a></div>
{PROGRESS_TOOLS}
</section>

<section class="completion hidden" id="completion"></section>

<section class="card" aria-labelledby="about-h">
<div class="section-label">About this course</div>
<h2 id="about-h">An orientation to VA work</h2>
{purpose_html}
</section>

<section class="card" aria-labelledby="journey-h">
<div class="section-label">The PVA Beginner VA Journey</div>
<h2 id="journey-h">You are in Stage 1: Explore</h2>
<p>VA Foundations is the first stage. The later stages have their own courses and learning paths. You don't have to memorize this map; Lesson 8 walks through it with you.</p>
{render_flow(journey_steps)}
</section>

<section class="card" aria-labelledby="map-h">
<div class="section-label">Course map</div><div class="folder-tab">8 lessons + Final Assessment</div>
<h2 id="map-h">Lessons</h2>
<ul class="lesson-list" id="lessonList">{rows}</ul>
</section>
{FOOTER}
</main>
<script src="{root}shared/progress.js"></script>
<script src="{root}shared/home.js"></script>
</body>
</html>
"""
    (OUT / "index.html").write_text(page, encoding="utf-8")


def build_progress_page():
    root = "../"
    rows = "".join(
        f'<li><a class="lesson-row" data-lesson="lesson-{n}" href="../lesson-{n}/"><span class="lesson-num">{n}</span>'
        f'<span class="row-text"><span class="row-title">{esc(t)}</span><span class="row-sub">Lesson {n} of 8</span></span>'
        f'<span class="stamp" data-stamp>Not started</span></a></li>' for n, t in LESSON_TITLES.items())
    rows += ('<li><a class="lesson-row final" data-lesson="final-assessment" href="../final-assessment/"><span class="lesson-num">✓</span>'
             '<span class="row-text"><span class="row-title">Final Assessment</span><span class="row-sub">20 questions · 16 of 20 to pass</span></span>'
             '<span class="stamp" data-stamp>Not started</span></a></li>')
    page = f"""{head("Progress & Backup — VA Foundations | PVA Academy", root)}
<body data-root="{root}" data-page="progress">
{chrome_top(root)}
<main id="main-content">
{STORAGE_BANNER}
<nav class="lesson-nav" id="lessonNav" aria-label="Course lessons"></nav>
<section class="card">
<div class="section-label">Progress &amp; backup</div>
<h1 style="font:700 clamp(1.7rem,4vw,2.3rem)/1.15 Fraunces,Georgia,serif;color:var(--green);margin:0 0 10px">Your VA Foundations progress</h1>
<div class="progress-summary"><span class="big-pct" id="homePct">0%</span><span id="homeSummary">0 of 8 lessons complete</span></div>
<p>Your progress is saved only in this browser, on this device. Nothing is sent to an account or a server.</p>
{WARNINGS}
{PROGRESS_TOOLS}
<p class="small"><strong>Export Progress</strong> downloads a backup file. <strong>Restore Progress</strong> loads a VA Foundations backup and <em>replaces</em> what is saved in this browser. Backups from other PVA courses can't be restored here. <strong>Clear Progress</strong> removes only VA Foundations progress.</p>
</section>
<section class="card"><div class="section-label">Course map</div><h2>Lessons</h2><ul class="lesson-list" id="lessonList">{rows}</ul></section>
{FOOTER}
</main>
<script src="{root}shared/progress.js"></script>
<script src="{root}shared/home.js"></script>
</body>
</html>
"""
    d = OUT / "progress"
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(page, encoding="utf-8")


# ---------------------------------------------------------------- main
def require_private_sources():
    missing = [f for f in (SRC, QC_SRC) if not f.exists()]
    if missing:
        names = "\n  ".join(str(f.relative_to(ROOT)) for f in missing)
        raise SystemExit(
            "Cannot build: the private course source files are missing.\n  " + names + "\n\n"
            "tools/source/ is intentionally excluded from the public repository because the\n"
            "course Markdown contains the Final Assessment answer key. Copy the approved\n"
            "source files into tools/source/ locally, then run this script again.\n"
            "The live site in public/ is already built; you only need these files to rebuild it.\n"
            "The browser QA suite (tools/qa.py) does not need them.")


def main():
    require_private_sources()
    src = SRC.read_text(encoding="utf-8")
    top = split_top(src)
    lessons, purpose, assess_body, journey = [], "", "", None
    for title, body in top:
        m = re.match(r"Lesson (\d+) — (.+)$", title)
        if m:
            lessons.append((int(m.group(1)), m.group(2).strip(), body))
        elif title == "Course Purpose":
            purpose = strip_rules(body)
        elif title == "Final Assessment":
            assess_body = body
    for n, t, _ in lessons:
        LESSON_TITLES[n] = t
    assert len(lessons) == 8

    # journey map from Lesson 8, section 9
    _, secs8 = split_h2(lessons[7][2])
    jtext = dict(secs8)["9. The PVA Beginner VA Journey"]
    _, journey, _ = parse_flow(jtext)

    qc_purpose = {}
    for n, t, body in lessons:
        build_lesson(n, t, body, qc_purpose)

    qc = parse_quick_checks(qc_purpose)
    (OUT / "shared" / "quick-checks.js").write_text(
        "/* Quick Checks — approved (tools/source/VA_Foundations_Quick_Checks.md). Not pass/fail. */\n"
        "window.VAF_QUICK_CHECKS = " + json.dumps(qc, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")

    qs = parse_assessment(assess_body)
    assert len(qs) == 20
    build_assessment(qs, parse_answer_lessons(src))
    build_home(purpose, journey)
    build_progress_page()
    print("lessons:", len(lessons), "| quick checks:", sum(len(v["questions"]) for v in qc.values()),
          "| assessment questions:", len(qs))


if __name__ == "__main__":
    main()
