"""End-to-end QA for VA Foundations. Serve public/ on :8765 first."""
import json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

B = "http://127.0.0.1:8765/"
SRC = Path(__file__).parent / "source" / "PVA_VA_Foundations_Revised_Course.md"
ANS = {int(n): "ABCD".index(a) for n, a in re.findall(r"^\|\s*(\d+)\s*\|\s*([A-D])\s*\|", SRC.read_text(), flags=re.M)}
results, errors = [], []

def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))

def ignore(msg):  # Google Fonts are blocked in the sandbox; not a site error
    return "ERR_TUNNEL_CONNECTION_FAILED" in msg or "fonts.g" in msg

with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    pg = ctx.new_page()
    pg.on("console", lambda m: (m.type == "error" and not ignore(m.text)) and errors.append(f"{pg.url}: {m.text}"))
    pg.on("pageerror", lambda e: errors.append(f"{pg.url}: {e}"))
    dialogs = []
    def on_dialog(d):
        dialogs.append(d.message); d.accept()
    pg.on("dialog", on_dialog)

    # 1. every page loads
    for u in [""] + [f"lesson-{i}/" for i in range(1, 9)] + ["final-assessment/", "progress/"]:
        r = pg.goto(B + u); pg.wait_for_timeout(150)
        check(f"loads /{u}", r.status == 200)

    # 2. internal links resolve
    hrefs = set()
    for u in [""] + [f"lesson-{i}/" for i in range(1, 9)] + ["final-assessment/", "progress/"]:
        pg.goto(B + u)
        for h in pg.eval_on_selector_all("a[href]", "els=>els.map(e=>e.href)"):
            hrefs.add(h)
    internal = [h for h in hrefs if h.startswith(B)]
    bad = [h for h in internal if pg.request.get(h.split("#")[0]).status != 200]
    check("internal links resolve", not bad, f"{len(internal)} checked, bad={bad}")
    ext = sorted(h for h in hrefs if not h.startswith(B))
    check("external links are only Academy + named PVA courses", all(("probinsiyanongva" in h) for h in ext), str(ext))

    # 3. lesson 1 activity + persistence
    pg.goto(B + "lesson-1/")
    it = pg.locator(".act-graded").first
    it.locator("label.choice").nth(0).click()
    check("L1 activity feedback shows", it.locator(".feedback.show.good").count() == 1)
    pg.reload()
    check("L1 activity answer persists", pg.locator(".act-graded").first.locator("input:checked").count() == 1)
    pg.click("[data-reset-activity]")
    check("L1 activity reset clears", pg.locator(".act-graded input:checked").count() == 0)

    # 4. quick check
    qc = pg.locator(".qc-item").first
    qc.locator("label.choice").first.click()
    check("Quick Check gives feedback", qc.locator(".feedback.show").count() == 1)
    pg.reload()
    check("Quick Check answer persists", pg.locator(".qc-item").first.locator("input:checked").count() == 1)
    check("Quick Check count L1 = 5", pg.locator(".qc-item").count() == 5)
    pg.click("#qcReset")
    check("Quick Check reset clears", pg.locator(".qc-item input:checked").count() == 0)

    # 5. mark complete / not done
    pg.click("#markBtn")
    check("Mark complete shows stamp", pg.locator("#lessonCard.is-done").count() == 1)
    pg.reload()
    check("Completion persists after reload", pg.locator("#lessonCard.is-done").count() == 1)
    pg.click("#notDoneBtn")
    check("Mark as not done works", pg.locator("#lessonCard.is-done").count() == 0)

    # 6. lesson 7 text response + notes download
    pg.goto(B + "lesson-7/")
    pg.fill("textarea.response >> nth=0", "I have used spreadsheets for store inventory.")
    pg.wait_for_timeout(700)
    pg.reload()
    check("L7 text response persists", "store inventory" in pg.input_value("textarea.response >> nth=0"))
    pg.click("#markBtn")
    with pg.expect_download() as dl:
        pg.click("#notesBtn")
    notes = Path(dl.value.path()).read_text()
    check("Notes .txt contains saved response", "store inventory" in notes and "Lesson 7" in notes)

    # 7. lesson 6 pick reveal, lesson 5 table choice
    pg.goto(B + "lesson-6/")
    pg.locator(".pick input").first.check()
    check("L6 pick reveals area", pg.locator(".area-reveal.show").count() == 1)
    pg.goto(B + "lesson-5/")
    pg.locator(".fill-table .self-choice").first.locator("label.choice").nth(1).click()
    pg.reload()
    check("L5 learning map choice persists", pg.locator(".fill-table input:checked").count() == 1)

    # 8. assessment gated before lessons done
    pg.goto(B + "final-assessment/")
    check("Assessment gated until lessons complete", pg.is_disabled("#startBtn") and pg.locator("#gate:not(.hidden)").count() == 1)
    src = pg.content()
    check("No answer key visible in assessment page", "Correct answer" not in src and "Answer Key" not in src)
    data_js = pg.request.get(B + "shared/assessment-data.js").text()
    check("Assessment data has no plain answer fields", '"ans"' not in data_js and "Correct answer" not in data_js)

    for i in range(1, 9):
        pg.goto(B + f"lesson-{i}/")
        if pg.is_enabled("#markBtn"): pg.click("#markBtn")

    # home stamps + continue
    pg.goto(B)
    check("Home shows 8 complete stamps", pg.locator(".lesson-row .stamp.complete").count() == 8)
    check("Continue points to Final Assessment", "final-assessment" in pg.get_attribute("#continueBtn", "href"))

    def take(correct_count):
        pg.goto(B + "final-assessment/")
        if pg.locator("#retakeBtn").count():
            pg.click("#retakeBtn")
        else:
            pg.click("#startBtn")
        pg.click('.q-dot[data-go="0"]')  # resume may reopen mid-way; start from Q1
        for n in range(1, 21):
            pick = ANS[n] if n <= correct_count else (ANS[n] + 1) % 4
            pg.locator("#assessRunner label.choice").nth(pick).click()
            if n < 20: pg.click("#nextQ")
        pg.click("#reviewBtn"); pg.click("#submitBtn")
        return pg.inner_text(".result-score")

    s = take(15)
    check("15/20 shows retake", s.strip() == "15 / 20" and pg.locator(".result-box.retake").count() == 1, s)
    check("15/20 does not complete the course", pg.locator("#completion:not(.hidden)").count() == 0)
    check("Result lists questions to review, not answers", pg.locator(".review-list li").count() == 5)
    # mid-attempt persistence
    pg.click("#retakeBtn"); pg.locator("#assessRunner label.choice").nth(ANS[1]).click(); pg.click("#nextQ")
    pg.reload()
    check("Answers persist mid-attempt", "1 of 20 answered" in pg.inner_text("#startBtn"))
    s = take(16)
    check("16/20 passes", s.strip() == "16 / 20" and pg.locator(".result-box.pass").count() == 1, s)
    check("Course completion shown after pass", pg.locator("#completion:not(.hidden) h2").count() == 1)
    s = take(20)
    check("20/20 scores correctly", s.strip() == "20 / 20", s)
    pg.goto(B)
    check("Home shows completion", pg.locator("#completion:not(.hidden)").count() == 1)

    # 9. export / clear / restore
    with pg.expect_download() as dl:
        pg.click("#exportBtn")
    backup = json.loads(Path(dl.value.path()).read_text())
    check("Export format correct", backup["format"] == "pva-va-foundations-progress-backup" and backup["version"] == 1
          and backup["storageKey"] == "pva-va-foundations-progress" and backup["summary"]["lessonsComplete"] == 8, dl.value.suggested_filename)
    Path("/tmp/claude-0/backup.json").write_text(json.dumps(backup))
    other = dict(backup); other["format"] = "pva-document-basics-progress-backup"
    Path("/tmp/claude-0/other.json").write_text(json.dumps(other))
    pg.evaluate("localStorage.setItem('pva-document-basics-progress-v2','{\"done\":[1]}')")
    pg.click("#clearBtn")
    check("Clear resets progress", pg.locator(".lesson-row .stamp.complete").count() == 0)
    check("Clear leaves other PVA keys", pg.evaluate("localStorage.getItem('pva-document-basics-progress-v2')") is not None)
    dialogs.clear()
    pg.set_input_files("#restoreFile", "/tmp/claude-0/other.json"); pg.wait_for_timeout(300)
    check("Other-course backup rejected", any("other PVA courses" in d for d in dialogs), str(dialogs))
    pg.set_input_files("#restoreFile", "/tmp/claude-0/backup.json"); pg.wait_for_timeout(300)
    check("Restore brings progress back", pg.locator(".lesson-row .stamp.complete").count() == 8)

    # fresh browser restore
    ctx2 = br.new_context(); pg2 = ctx2.new_page(); pg2.on("dialog", lambda d: d.accept())
    pg2.goto(B + "progress/")
    pg2.set_input_files("#restoreFile", "/tmp/claude-0/backup.json"); pg2.wait_for_timeout(300)
    check("Restore works in a fresh browser", pg2.locator(".lesson-row .stamp.complete").count() == 8)
    ctx2.close()

    # 10. storage blocked banner
    ctx3 = br.new_context()
    ctx3.add_init_script("Storage.prototype.setItem=function(){throw new Error('blocked')}")
    pg3 = ctx3.new_page()
    for u in ["", "lesson-3/", "final-assessment/"]:
        pg3.goto(B + u)
        check(f"Blocked-storage banner on /{u}", pg3.locator("#storageBanner:not(.hidden)").count() == 1)
    ctx3.close()

    # 11. responsive overflow
    for w, h in [(1280, 900), (820, 1180), (390, 844), (360, 740)]:
        c = br.new_context(viewport={"width": w, "height": h}); q = c.new_page()
        over = []
        for u in [""] + [f"lesson-{i}/" for i in range(1, 9)] + ["final-assessment/", "progress/"]:
            q.goto(B + u)
            sw = q.evaluate("document.documentElement.scrollWidth")
            if sw > w: over.append((u, sw))
        check(f"No horizontal overflow at {w}px", not over, str(over))
        c.close()
    br.close()

check("No console/page errors", not errors, "\n".join(errors[:10]))
fails = [r for r in results if not r[1]]
for n, ok, d in results:
    print(("PASS " if ok else "FAIL ") + n + (f"  [{d}]" if (d and not ok) else ""))
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
