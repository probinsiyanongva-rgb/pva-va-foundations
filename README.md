# PVA Academy — VA Foundations (standalone module) v1.0

The front door of the PVA Beginner VA Journey (Stage 1: Explore).
8 lessons + a 20-question Final Assessment. No login. Progress is saved in the
learner's browser only (`pva-va-foundations-progress`), with Export / Restore / Clear.

Live URL (after Cloudflare connection): `https://pva-va-foundations.probinsiyanongva.workers.dev/`

## Structure

- `public/` — the only folder Cloudflare serves (see `wrangler.jsonc`)
  - `index.html` — course home: journey map, progress, course map, backup tools
  - `lesson-1/` … `lesson-8/` — lessons with activities and Quick Checks
  - `final-assessment/` — 20 questions, 16/20 (80%) to pass, retake allowed
  - `progress/` — progress list, Export / Restore / Clear
  - `shared/` — `course.css` (Document Basics design tokens), `progress.js`,
    `lesson.js`, `home.js`, `assessment.js`, generated `quick-checks.js` and
    `assessment-data.js`
- `tools/build.py` — builds `public/` from the approved Markdown (needs the private files)
- `tools/qa.py` — end-to-end browser QA (Playwright); runs without the private files
- `wrangler.jsonc` — Cloudflare Workers Static Assets config

## Content source and tooling

The approved learner content is kept out of this public repository on purpose,
because the course Markdown contains the Final Assessment answer key:

- `tools/source/PVA_VA_Foundations_Revised_Course.md`
- `tools/source/VA_Foundations_Quick_Checks.md` (approved 29 Sep 2026)

**Rebuilding needs the private files.** Copy them into `tools/source/` locally,
then run `python3 tools/build.py`. Without them, the script stops with a message
explaining what is missing. `public/` is already built, so you only need this
when the content changes.

**Browser QA does not need the private files.** From a clean clone:

```text
python3 -m http.server 8765 --bind 127.0.0.1 -d public
python3 tools/qa.py
```

`qa.py` works out the Final Assessment answers from the published hashes, so it
can test 15/20 (retake) and 16/20 (pass) without the answer key file. It needs
Python with Playwright and Chromium installed.

The answer key is not stored as readable letters in the site: each question
carries a hash of its correct option. A static site cannot make this
tamper-proof; it keeps the answers out of plain view.

## Cloudflare deployment

Workers & Pages → Create → Import a repository → `pva-va-foundations`.

```text
Build command: (blank)
Deploy command: npx wrangler deploy
```

Then enable the `workers.dev` route under **Domains** if the dashboard shows
"No URLs enabled".

## Rules

- Completion = all 8 lessons marked complete **and** Final Assessment passed.
- Completion is an acknowledgment, not a certification. No portfolio-portal route.
- Mark as done is never gated; the Final Assessment opens after all 8 lessons.
- The module does not depend on code, styles or login from the main site, and the
  main site loads nothing from it.
- Links out of the module: "← PVA Academy" goes to `https://probinsiyanongva.org/`
  (same tab). Lesson 8 also links to the other PVA courses
  the lessons name: Computer & Laptop Basics, Internet, Email & Google Workspace,
  Document Basics and Spreadsheet Basics.
