/* PVA Academy — VA Foundations
   Lesson page behaviour: progress bar, lesson pills, activities,
   Quick Check, Mark complete / Mark as not done, notes download.
   Requires shared/progress.js (window.PVAVAF) and shared/quick-checks.js. */
(function () {
  'use strict';
  var P = window.PVAVAF;
  var body = document.body;
  var LESSON_ID = body.getAttribute('data-lesson-id');
  var ROOT = body.getAttribute('data-root') || '../';
  var lesson = P.LESSONS.filter(function (l) { return l.id === LESSON_ID; })[0];

  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $all(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  /* ---------- header UI ---------- */
  function renderChrome() {
    P.renderProgressBar(LESSON_ID);
    P.renderLessonNav(LESSON_ID, ROOT);
    var card = $('#lessonCard');
    var done = P.isComplete(LESSON_ID);
    if (card) card.classList.toggle('is-done', done);
    var mark = $('#markBtn'), undo = $('#notDoneBtn'), panel = $('#donePanel');
    if (mark) { mark.disabled = done; mark.textContent = done ? 'Lesson ' + lesson.num + ' complete ✓' : 'Mark Lesson ' + lesson.num + ' complete'; }
    if (undo) undo.disabled = !done;
    if (panel) panel.classList.toggle('hidden', !done);
  }

  /* ---------- graded-style items (activity MCQ + Quick Check) ---------- */
  function lockItem(item, picked) {
    var correct = parseInt(item.getAttribute('data-correct'), 10);
    var ok = picked === correct;
    $all('.choice', item).forEach(function (lab) {
      var inp = $('input', lab);
      var v = parseInt(inp.value, 10);
      inp.checked = v === picked;
      inp.disabled = true;
      lab.classList.add('locked');
      lab.classList.toggle('correct', v === correct);
      lab.classList.toggle('wrong', v === picked && !ok);
    });
    var fb = $('.feedback', item);
    if (fb) {
      var good = item.getAttribute('data-good') || '';
      var tryMsg = item.getAttribute('data-try') || '';
      fb.innerHTML = ok ? '<strong>That matches the lesson.</strong> ' + good
                        : '<strong>Not quite.</strong> ' + (tryMsg || good);
      fb.className = 'feedback show ' + (ok ? 'good' : 'try');
    }
    return ok;
  }
  function unlockItem(item) {
    $all('.choice', item).forEach(function (lab) {
      var inp = $('input', lab);
      inp.checked = false; inp.disabled = false;
      lab.classList.remove('locked', 'correct', 'wrong');
    });
    var fb = $('.feedback', item); if (fb) { fb.className = 'feedback'; fb.innerHTML = ''; }
  }
  function wireGraded(item, onChange) {
    var key = item.getAttribute('data-key');
    var saved = P.getDraft(LESSON_ID, key);
    if (typeof saved === 'number') lockItem(item, saved);
    $all('input', item).forEach(function (inp) {
      inp.addEventListener('change', function () {
        var v = parseInt(inp.value, 10);
        P.setDraft(LESSON_ID, key, v);
        lockItem(item, v);
        if (onChange) onChange();
      });
    });
  }

  /* ---------- seeded shuffle so option order is stable per question ---------- */
  function seeded(str) {
    var h = 2166136261;
    for (var i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    return function () { h ^= h << 13; h ^= h >>> 17; h ^= h << 5; return ((h >>> 0) % 10000) / 10000; };
  }
  function shuffledOrder(n, seed) {
    var order = []; for (var i = 0; i < n; i++) order.push(i);
    var rnd = seeded(seed);
    for (var j = n - 1; j > 0; j--) { var k = Math.floor(rnd() * (j + 1)); var t = order[j]; order[j] = order[k]; order[k] = t; }
    return order;
  }

  /* ---------- Quick Check ---------- */
  function renderQuickCheck() {
    var box = $('#quickCheck');
    if (!box) return;
    var data = (window.VAF_QUICK_CHECKS || {})[LESSON_ID];
    if (!data || !data.questions || !data.questions.length) { box.classList.add('hidden'); return; }
    var html = '<div class="section-label">Lesson ' + lesson.num + '</div><h2>Quick Check</h2>' +
      '<p class="qc-meta">' + esc(data.purpose) + '</p>' +
      '<p class="qc-meta"><strong>' + data.questions.length + ' questions · Not pass/fail.</strong> You can mark the lesson complete whether or not you answer these. Your answers are saved in this browser.</p>';
    data.questions.forEach(function (q, qi) {
      var order = shuffledOrder(q.options.length, LESSON_ID + '|' + q.id);
      html += '<div class="act-item qc-item" data-key="qc:' + esc(q.id) + '" data-correct="' + q.answer + '" data-good="' + esc(q.explain) + '">' +
        '<p class="act-q"><span class="q-num">Question ' + (qi + 1) + ' of ' + data.questions.length + '</span><br>' + esc(q.q) + '</p>' +
        '<div class="choice-group" role="radiogroup">';
      order.forEach(function (oi) {
        html += '<label class="choice"><input type="radio" name="qc-' + esc(q.id) + '" value="' + oi + '"><span>' + esc(q.options[oi]) + '</span></label>';
      });
      html += '</div><div class="feedback" aria-live="polite"></div></div>';
    });
    html += '<p class="qc-summary" id="qcSummary" aria-live="polite"></p>' +
      '<div class="hero-actions" style="margin:0 0 14px"><button class="btn subtle small-btn" type="button" id="qcReset">Try the Quick Check again</button></div>';
    box.innerHTML = html;
    var items = $all('.qc-item', box);
    function summary() {
      var answered = 0, matched = 0;
      items.forEach(function (it) {
        var v = P.getDraft(LESSON_ID, it.getAttribute('data-key'));
        if (typeof v === 'number') { answered++; if (v === parseInt(it.getAttribute('data-correct'), 10)) matched++; }
      });
      var s = $('#qcSummary');
      s.textContent = answered === 0 ? '' : answered < items.length
        ? 'Answered ' + answered + ' of ' + items.length + '.'
        : 'Done: ' + matched + ' of ' + items.length + ' matched the lesson. If any didn’t, the explanation points you to the part worth re-reading.';
    }
    items.forEach(function (it) { wireGraded(it, summary); });
    summary();
    $('#qcReset').addEventListener('click', function () {
      P.clearDrafts(LESSON_ID, 'qc:');
      items.forEach(unlockItem);
      summary();
    });
  }

  /* ---------- activities ---------- */
  function wireActivities() {
    // graded activity items (scenario Yes/No, follow-the-task MCQ)
    $all('.act-graded').forEach(function (it) { wireGraded(it); });
    $all('[data-reset-activity]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var act = btn.closest('.activity');
        $all('.act-graded', act).forEach(function (it) {
          P.clearDrafts(LESSON_ID, it.getAttribute('data-key'));
          unlockItem(it);
        });
      });
    });
    // self-assessment radios (no right answer)
    $all('.self-choice').forEach(function (group) {
      var key = group.getAttribute('data-key');
      var saved = P.getDraft(LESSON_ID, key);
      $all('input', group).forEach(function (inp) {
        if (saved !== undefined && inp.value === saved) inp.checked = true;
        inp.addEventListener('change', function () { if (inp.checked) P.setDraft(LESSON_ID, key, inp.value); });
      });
    });
    // checkboxes with reveal
    $all('.pick').forEach(function (row) {
      var key = row.getAttribute('data-key');
      var inp = $('input', row);
      var reveal = $('.area-reveal', row);
      inp.checked = P.getDraft(LESSON_ID, key) === true;
      if (reveal) reveal.classList.toggle('show', inp.checked);
      inp.addEventListener('change', function () {
        P.setDraft(LESSON_ID, key, inp.checked);
        if (reveal) reveal.classList.toggle('show', inp.checked);
      });
    });
    // free-text responses: debounce 0.5s + blur
    $all('.response').forEach(function (ta) {
      var key = ta.getAttribute('data-key');
      var note = ta.parentNode.querySelector('.saved-note[data-for="' + ta.id + '"]');
      var saved = P.getDraft(LESSON_ID, key);
      if (typeof saved === 'string') ta.value = saved;
      var timer = null;
      function save() {
        clearTimeout(timer);
        P.setDraft(LESSON_ID, key, ta.value);
        if (note) note.textContent = P.storageOK() ? 'Saved in this browser · ' + new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : 'Not saved: this browser is blocking storage.';
      }
      ta.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(save, 500); });
      ta.addEventListener('blur', save);
    });
  }

  /* ---------- notes download ---------- */
  function buildNotes() {
    var lines = ['PVA Academy — VA Foundations', 'Lesson ' + lesson.num + ': ' + lesson.title, 'My notes · ' + new Date().toLocaleString(), ''];
    var any = false;
    $all('[data-note-label]').forEach(function (el) {
      var label = el.getAttribute('data-note-label');
      var key = el.getAttribute('data-key');
      var v = P.getDraft(LESSON_ID, key);
      var out = '';
      if (el.classList.contains('pick')) { if (v === true) out = 'Selected'; else return; }
      else if (typeof v === 'string') out = v.trim();
      if (!out) out = '(not answered)'; else any = true;
      lines.push(label); lines.push('  ' + out.replace(/\n/g, '\n  ')); lines.push('');
    });
    lines.push('Saved in this browser only. Keep this file if you want a copy of your answers.');
    return { text: lines.join('\n'), any: any };
  }
  function wireNotes() {
    var btn = $('#notesBtn');
    if (!btn) return;
    if (!$all('[data-note-label]').length) { btn.classList.add('hidden'); return; }
    btn.addEventListener('click', function () {
      var n = buildNotes();
      var blob = new Blob([n.text], { type: 'text/plain;charset=utf-8' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'VA-Foundations-Lesson-' + lesson.num + '-my-notes.txt';
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 1500);
    });
  }

  /* ---------- completion buttons ---------- */
  function wireCompletion() {
    var mark = $('#markBtn'), undo = $('#notDoneBtn');
    if (mark) mark.addEventListener('click', function () {
      P.markComplete(LESSON_ID); renderChrome();
      var panel = $('#donePanel'); if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
    if (undo) undo.addEventListener('click', function () { P.markNotDone(LESSON_ID); renderChrome(); });
  }

  P.visit(LESSON_ID);
  renderChrome();
  wireActivities();
  renderQuickCheck();
  wireCompletion();
  wireNotes();
})();
