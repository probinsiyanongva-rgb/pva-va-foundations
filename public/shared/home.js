/* PVA Academy — VA Foundations
   Home page and Progress page: stamps, summary, Continue button,
   Export / Restore / Clear, completion acknowledgment. */
(function () {
  'use strict';
  var P = window.PVAVAF;
  var ROOT = document.body.getAttribute('data-root') || './';
  function $(s) { return document.querySelector(s); }

  var ACADEMY = 'https://probinsiyanongva.org/';

  function render() {
    P.renderProgressBar(null);
    P.renderLessonNav(document.body.getAttribute('data-page') === 'home' ? 'home' : null, ROOT);

    document.querySelectorAll('.lesson-row').forEach(function (row) {
      var id = row.getAttribute('data-lesson');
      var st = P.status(id);
      var stamp = row.querySelector('[data-stamp]');
      stamp.className = 'stamp';
      if (st === 'complete') { stamp.classList.add(id === P.FINAL_ID ? 'passed' : 'complete'); stamp.textContent = id === P.FINAL_ID ? 'Passed' : 'Complete'; }
      else if (st === 'progress') { stamp.classList.add('progress'); stamp.textContent = id === P.FINAL_ID ? 'Not passed yet' : 'In progress'; }
      else { stamp.textContent = 'Not started'; }
      row.classList.toggle('is-done', st === 'complete');
    });

    var done = P.lessonsDone(), passed = P.hasPassed();
    var pct = Math.round(((done + (passed ? 1 : 0)) / (P.LESSONS.length + 1)) * 100);
    var pctEl = $('#homePct'); if (pctEl) pctEl.textContent = pct + '%';
    var sum = $('#homeSummary');
    if (sum) sum.textContent = done + ' of ' + P.LESSONS.length + ' lessons complete · Final Assessment ' + (passed ? 'passed' : 'not passed yet');

    var btn = $('#continueBtn');
    if (btn) {
      var next = P.nextLesson();
      var anyStarted = P.LESSONS.some(function (l) { return P.status(l.id) !== 'none'; });
      if (P.courseComplete()) { btn.textContent = 'Review the lessons'; btn.href = ROOT + 'lesson-1/'; }
      else if (next) {
        btn.textContent = (!anyStarted && next.num === 1) ? 'Start Lesson 1' : 'Continue: Lesson ' + next.num;
        btn.href = ROOT + next.id + '/';
      } else { btn.textContent = 'Go to the Final Assessment'; btn.href = ROOT + P.FINAL_ID + '/'; }
    }

    var comp = $('#completion');
    if (comp) {
      if (P.courseComplete()) {
        comp.innerHTML = '<div class="completion-icon">✓</div><h2>VA Foundations Complete</h2>' +
          '<p><strong>PVA Academy — VA Foundations</strong></p><p>You finished all 8 lessons and passed the Final Assessment.</p>' +
          '<div class="completion-card-note"><strong>This is a completion acknowledgment, not a certification or competency credential.</strong><br><br>' +
          'Your next step depends on your starting point. Lesson 8 lists where to go next: basic computer skills, internet and Google Workspace, document or spreadsheet practice, or the next stage of the journey.</div>' +
          '<div class="hero-actions"><a class="btn" href="' + ACADEMY + '">Back to PVA Academy</a><a class="btn secondary" href="' + ROOT + 'lesson-8/">Review Lesson 8: Where do I go from here?</a></div>';
        comp.classList.remove('hidden');
      } else comp.classList.add('hidden');
    }
  }

  var exp = $('#exportBtn'), res = $('#restoreBtn'), clr = $('#clearBtn'), file = $('#restoreFile');
  if (exp) exp.addEventListener('click', function () { P.exportProgress(); });
  if (res && file) {
    res.addEventListener('click', function () { file.click(); });
    file.addEventListener('change', function (e) {
      var f = e.target.files && e.target.files[0]; e.target.value = '';
      P.restoreFromFile(f, function () { render(); var s = document.querySelector('[data-save-state]'); if (s) s.textContent = 'Progress restored in this browser.'; });
    });
  }
  if (clr) clr.addEventListener('click', function () {
    P.clearProgress(function () { render(); var s = document.querySelector('[data-save-state]'); if (s) s.textContent = 'Progress cleared.'; });
  });

  render();
})();
