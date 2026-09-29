/* PVA Academy — VA Foundations
   Final Assessment: 20 questions, one at a time, answers saved in this
   browser, score shown only after submission, 16/20 to pass, retake allowed.
   The answer key is not stored as readable letters: each question carries a
   hash of its correct option, compared at submission. (A static site cannot
   make this tamper-proof; it keeps answers out of plain view.) */
(function () {
  'use strict';
  var P = window.PVAVAF;
  var QS = window.VAF_ASSESSMENT || [];
  var SALT = window.VAF_SALT || '';
  var ROOT = document.body.getAttribute('data-root') || '../';
  var ID = P.FINAL_ID;
  var ACADEMY = 'https://probinsiyanongva.org/';
  function $(s) { return document.querySelector(s); }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  function fnv(str) {
    var bytes = new TextEncoder().encode(str);
    var h = 2166136261;
    for (var i = 0; i < bytes.length; i++) { h ^= bytes[i]; h = Math.imul(h, 16777619) >>> 0; }
    return ('00000000' + h.toString(16)).slice(-8);
  }
  function answerOf(n) { var v = P.getDraft(ID, 'a:' + n); return typeof v === 'number' ? v : null; }
  function answeredCount() { return QS.filter(function (q) { return answerOf(q.n) !== null; }).length; }
  function plain(h) {
    var d = document.createElement('div'); d.innerHTML = h;
    var t = Array.prototype.map.call(d.querySelectorAll('p'), function (p) { return p.textContent.trim(); }).join(' ') || d.textContent.trim();
    return t.length > 150 ? t.slice(0, t.lastIndexOf(' ', 147)) + '…' : t;
  }

  var pos = 0;

  function show(el) { ['#assessIntro', '#assessRunner', '#assessResult'].forEach(function (s) { $(s).classList.toggle('hidden', s !== el); }); }

  function renderChrome() { P.renderProgressBar(ID); P.renderLessonNav(ID, ROOT); }

  /* ---------- intro / gate ---------- */
  function renderIntro() {
    renderChrome();
    var gate = $('#gate'), start = $('#startBtn');
    var missing = P.LESSONS.filter(function (l) { return !P.isComplete(l.id); });
    if (missing.length) {
      gate.innerHTML = '<strong>Complete all 8 lessons first.</strong> The Final Assessment opens once every lesson is marked complete. Still to mark complete:' +
        '<ul class="gate-list">' + missing.map(function (l) { return '<li><a href="' + ROOT + l.id + '/">Lesson ' + l.num + ': ' + esc(l.title) + '</a></li>'; }).join('') + '</ul>';
      gate.classList.remove('hidden');
      start.disabled = true;
      start.textContent = 'Start the assessment';
    } else {
      gate.classList.add('hidden');
      start.disabled = false;
      var a = P.assessment();
      start.textContent = answeredCount() > 0 && !a.submitted ? 'Continue the assessment (' + answeredCount() + ' of 20 answered)' : 'Start the assessment';
    }
    var a2 = P.assessment();
    if (a2.submitted && a2.attempts.length) { renderResult(a2.attempts[a2.attempts.length - 1].score); return; }
    show('#assessIntro');
    renderCompletion();
  }

  /* ---------- runner ---------- */
  function renderQuestion() {
    var q = QS[pos];
    var picked = answerOf(q.n);
    var dots = QS.map(function (qq, i) {
      var cls = 'q-dot' + (answerOf(qq.n) !== null ? ' answered' : '') + (i === pos ? ' current' : '');
      return '<button type="button" class="' + cls + '" data-go="' + i + '" aria-label="Question ' + qq.n + (answerOf(qq.n) !== null ? ', answered' : ', not answered') + '">' + qq.n + '</button>';
    }).join('');
    var opts = q.options.map(function (o, i) {
      return '<label class="choice"><input type="radio" name="q' + q.n + '" value="' + i + '"' + (picked === i ? ' checked' : '') + '><span><strong>' + 'ABCD'[i] + '.</strong> ' + o + '</span></label>';
    }).join('');
    var last = pos === QS.length - 1;
    $('#assessRunner').innerHTML =
      '<div class="assess-progress">Question ' + q.n + ' of ' + QS.length + ' · ' + answeredCount() + ' answered</div>' +
      '<div class="q-dots" aria-label="Jump to a question">' + dots + '</div>' +
      '<div class="assess-q" id="qText">' + q.html + '</div>' +
      '<div class="choice-group" role="radiogroup" aria-labelledby="qText">' + opts + '</div>' +
      '<p class="saved-note" id="qSaved">' + (picked !== null ? 'Answer saved in this browser.' : '') + '</p>' +
      '<div class="assess-nav"><button type="button" class="btn secondary" id="prevQ"' + (pos === 0 ? ' disabled' : '') + '>← Previous</button>' +
      (last ? '<button type="button" class="btn gold" id="reviewBtn">Review and submit</button>' : '<button type="button" class="btn" id="nextQ">Next →</button>') + '</div>';
    document.querySelectorAll('#assessRunner input[type=radio]').forEach(function (inp) {
      inp.addEventListener('change', function () {
        P.setDraft(ID, 'a:' + q.n, parseInt(inp.value, 10));
        P.setDraft(ID, 'pos', pos);
        $('#qSaved').textContent = 'Answer saved in this browser.';
        var dot = document.querySelector('.q-dot[data-go="' + pos + '"]'); if (dot) dot.classList.add('answered');
        document.querySelector('.assess-progress').textContent = 'Question ' + q.n + ' of ' + QS.length + ' · ' + answeredCount() + ' answered';
      });
    });
    document.querySelectorAll('.q-dot').forEach(function (b) { b.addEventListener('click', function () { go(parseInt(b.getAttribute('data-go'), 10)); }); });
    $('#prevQ').addEventListener('click', function () { go(pos - 1); });
    if (last) $('#reviewBtn').addEventListener('click', renderReview);
    else $('#nextQ').addEventListener('click', function () { go(pos + 1); });
    show('#assessRunner');
  }
  function go(i) { pos = Math.max(0, Math.min(QS.length - 1, i)); P.setDraft(ID, 'pos', pos); renderQuestion(); $('#assessRunner').scrollIntoView({ block: 'start' }); }

  function renderReview() {
    var missing = QS.filter(function (q) { return answerOf(q.n) === null; });
    var html = '<div class="section-label">Review</div><h2>Ready to submit?</h2>' +
      '<p>You have answered <strong>' + answeredCount() + ' of ' + QS.length + '</strong> questions.</p>';
    if (missing.length) {
      html += '<div class="callout"><strong>Not answered yet:</strong> ' + missing.map(function (q) {
        return '<button type="button" class="btn subtle small-btn" data-go="' + (q.n - 1) + '">Question ' + q.n + '</button>';
      }).join(' ') + '<br><span class="small">Unanswered questions count as incorrect.</span></div>';
    }
    html += '<p class="small">Your score appears after you submit. You need 16 of 20 to pass.</p>' +
      '<div class="assess-nav"><button type="button" class="btn secondary" id="backToQs">← Back to the questions</button>' +
      '<button type="button" class="btn gold" id="submitBtn">Submit my answers</button></div>';
    $('#assessRunner').innerHTML = html;
    document.querySelectorAll('#assessRunner [data-go]').forEach(function (b) { b.addEventListener('click', function () { go(parseInt(b.getAttribute('data-go'), 10)); }); });
    $('#backToQs').addEventListener('click', function () { renderQuestion(); });
    $('#submitBtn').addEventListener('click', submit);
    show('#assessRunner');
  }

  function score() {
    return QS.reduce(function (s, q) {
      var a = answerOf(q.n);
      return s + (a !== null && fnv(SALT + '|' + q.n + '|' + a) === q.k ? 1 : 0);
    }, 0);
  }

  function submit() {
    var missing = QS.length - answeredCount();
    if (missing && !confirm(missing + ' question(s) are not answered and will count as incorrect. Submit anyway?')) return;
    var s = score();
    P.recordAttempt(s);
    renderChrome();
    renderResult(s);
  }

  /* ---------- result ---------- */
  function renderResult(s) {
    var passed = s >= P.PASS_MARK;
    var missed = QS.filter(function (q) { var a = answerOf(q.n); return a === null || fnv(SALT + '|' + q.n + '|' + a) !== q.k; });
    var html = '<div class="section-label">Final Assessment result</div>' +
      '<div class="result-box ' + (passed ? 'pass' : 'retake') + '">' +
      '<div class="stamp ' + (passed ? 'passed' : 'progress') + '">' + (passed ? 'Passed' : 'Retake recommended') + '</div>' +
      '<div class="result-score">' + s + ' / ' + QS.length + '</div>' +
      '<p style="margin:0">' + (passed
        ? 'You passed. You needed 16 of 20.'
        : 'You needed 16 of 20 to pass. Review the lessons below, then retake the assessment when you are ready.') + '</p></div>';
    if (missed.length) {
      html += '<h3>Worth reviewing</h3><p class="small">These questions did not match the course. Go back to the lesson shown, then try again.</p><ul class="review-list">' +
        missed.map(function (q) {
          var lesson = (q.review.match(/\d+/) || [null])[0];
          var link = lesson ? ' <a href="' + ROOT + 'lesson-' + lesson + '/">' + esc(q.review) + '</a>' : '';
          return '<li><strong>Question ' + q.n + ':</strong> ' + esc(plain(q.html)) + '<br><span class="small">Review:</span>' + link + '</li>';
        }).join('') + '</ul>';
    } else {
      html += '<p>Every answer matched the course.</p>';
    }
    var attempts = P.assessment().attempts.length;
    html += '<p class="small">Attempts so far: ' + attempts + '.</p><div class="hero-actions">' +
      (passed ? '<a class="btn" href="' + ROOT + '">Back to VA Foundations home</a><button type="button" class="btn subtle" id="retakeBtn">Retake anyway</button>'
              : '<button type="button" class="btn" id="retakeBtn">Retake the assessment</button><a class="btn secondary" href="' + ROOT + '">Back to VA Foundations home</a>') + '</div>';
    $('#assessResult').innerHTML = html;
    $('#retakeBtn').addEventListener('click', function () {
      if (!confirm('Start a new attempt? Your current answers will be cleared. ' + (P.hasPassed() ? 'Your pass stays recorded.' : ''))) return;
      P.resetAttempt(); pos = 0; renderChrome(); renderQuestion();
    });
    show('#assessResult');
    renderCompletion();
    $('#assessResult').scrollIntoView({ block: 'start' });
  }

  function renderCompletion() {
    var comp = $('#completion');
    if (P.courseComplete()) {
      comp.innerHTML = '<div class="completion-icon">✓</div><h2>VA Foundations Complete</h2>' +
        '<p><strong>PVA Academy — VA Foundations</strong></p><p>You finished all 8 lessons and passed the Final Assessment.</p>' +
        '<div class="completion-card-note"><strong>This is a completion acknowledgment, not a certification or competency credential.</strong> It is saved in this browser only.<br><br>' +
        'Your next step depends on your starting point. Lesson 8 lists where to go next.</div>' +
        '<div class="hero-actions"><a class="btn" href="' + ACADEMY + '">Back to PVA Academy</a><a class="btn secondary" href="' + ROOT + 'lesson-8/">Review Lesson 8</a>' +
        '<button type="button" class="btn gold" onclick="window.print()">Print this screen</button></div>';
      comp.classList.remove('hidden');
    } else if (P.hasPassed()) {
      comp.innerHTML = '<p><strong>You passed the Final Assessment.</strong> VA Foundations is complete once all 8 lessons are also marked complete.</p><div class="hero-actions"><a class="btn" href="' + ROOT + '">Go to the course map</a></div>';
      comp.classList.remove('hidden');
    } else comp.classList.add('hidden');
  }

  $('#startBtn').addEventListener('click', function () {
    var saved = P.getDraft(ID, 'pos');
    pos = typeof saved === 'number' ? Math.max(0, Math.min(QS.length - 1, saved)) : 0;
    renderQuestion();
  });

  renderIntro();
})();
