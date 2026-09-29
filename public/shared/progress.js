/* PVA Academy — VA Foundations
   Browser-only progress for this course.
   One localStorage key, one namespace (window.PVAVAF). Nothing is sent
   to a server or account. Pattern follows the PVA house standard used in
   Document Basics and NDIS VA Foundations. */
(function () {
  'use strict';

  var STORAGE_KEY = 'pva-va-foundations-progress';
  var BACKUP_FORMAT = 'pva-va-foundations-progress-backup';
  var BACKUP_VERSION = 1;
  var COURSE_NAME = 'PVA Academy — VA Foundations';
  var PASS_MARK = 16; // of 20 (80%)
  var TOTAL_QUESTIONS = 20;

  var LESSONS = [
    { id: 'lesson-1', num: 1, title: 'What Is a VA?' },
    { id: 'lesson-2', num: 2, title: 'What Does a VA Actually Do?' },
    { id: 'lesson-3', num: 3, title: 'Who Can Become a VA?' },
    { id: 'lesson-4', num: 4, title: 'What Do I Need to Start?' },
    { id: 'lesson-5', num: 5, title: 'What Will I Need to Learn?' },
    { id: 'lesson-6', num: 6, title: 'What Kind of VA Work Is Out There?' },
    { id: 'lesson-7', num: 7, title: 'Learn → Practice → Prove → Grow' },
    { id: 'lesson-8', num: 8, title: 'So, Where Do I Go From Here?' }
  ];
  var FINAL_ID = 'final-assessment';

  var storageOK = true;
  var state = fresh();

  function fresh() { return { _meta: { lastLesson: null, updatedAt: null } }; }

  function isPlainObject(v) { return v !== null && typeof v === 'object' && !Array.isArray(v); }

  function normalize(raw) {
    var out = fresh();
    if (!isPlainObject(raw)) return out;
    var ids = LESSONS.map(function (l) { return l.id; }).concat([FINAL_ID]);
    ids.forEach(function (id) {
      var e = raw[id];
      if (!isPlainObject(e)) return;
      var n = { complete: e.complete === true, completedAt: typeof e.completedAt === 'string' ? e.completedAt : null,
        lastStep: typeof e.lastStep === 'string' ? e.lastStep : null, drafts: {} };
      if (isPlainObject(e.drafts)) {
        Object.keys(e.drafts).forEach(function (k) {
          var v = e.drafts[k];
          if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') n.drafts[k] = v;
        });
      }
      if (id === FINAL_ID) {
        n.attempts = Array.isArray(e.attempts) ? e.attempts.filter(function (a) {
          return isPlainObject(a) && typeof a.score === 'number' && a.score >= 0 && a.score <= TOTAL_QUESTIONS;
        }).map(function (a) { return { score: a.score, passed: a.score >= PASS_MARK, at: typeof a.at === 'string' ? a.at : null }; }) : [];
        n.passed = n.attempts.some(function (a) { return a.passed; });
        n.complete = n.passed;
        n.submitted = e.submitted === true;
      }
      out[id] = n;
    });
    if (isPlainObject(raw._meta)) {
      out._meta.lastLesson = typeof raw._meta.lastLesson === 'string' ? raw._meta.lastLesson : null;
      out._meta.updatedAt = typeof raw._meta.updatedAt === 'string' ? raw._meta.updatedAt : null;
    }
    return out;
  }

  function showBanner(msg) {
    var b = document.getElementById('storageBanner');
    if (!b) return;
    var t = document.getElementById('storageBannerText');
    if (t && msg) t.textContent = msg;
    b.classList.remove('hidden');
  }

  function load() {
    try {
      var probe = '__pva_vaf_probe__';
      localStorage.setItem(probe, '1');
      localStorage.removeItem(probe);
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        try { state = normalize(JSON.parse(raw)); }
        catch (e) {
          state = fresh();
          showBanner('Your saved progress could not be read, so this page started with a fresh progress state. Check your browser storage settings if this keeps happening.');
        }
      }
    } catch (e) {
      storageOK = false;
      state = fresh();
      showBanner();
    }
  }

  function stampTime() {
    var d = new Date();
    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  }

  function persist() {
    state._meta.updatedAt = new Date().toISOString();
    if (!storageOK) { showBanner(); return false; }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      document.querySelectorAll('[data-save-state]').forEach(function (el) {
        el.textContent = 'Saved in this browser · ' + stampTime();
      });
      return true;
    } catch (e) {
      storageOK = false;
      showBanner('Your browser stopped this course from saving progress. You can continue learning, but your progress may not remain after you close or refresh this page.');
      return false;
    }
  }

  function entry(id) {
    if (!state[id]) {
      state[id] = { complete: false, completedAt: null, lastStep: null, drafts: {} };
      if (id === FINAL_ID) { state[id].attempts = []; state[id].passed = false; state[id].submitted = false; }
    }
    return state[id];
  }

  /* ---------- lesson state ---------- */
  function visit(id) { entry(id).lastStep = new Date().toISOString(); state._meta.lastLesson = id; persist(); }
  function isComplete(id) { return !!(state[id] && state[id].complete); }
  function markComplete(id) { var e = entry(id); e.complete = true; e.completedAt = new Date().toISOString(); persist(); }
  function markNotDone(id) { var e = entry(id); e.complete = false; e.completedAt = null; persist(); }
  function getDraft(id, key) { return state[id] && state[id].drafts ? state[id].drafts[key] : undefined; }
  function setDraft(id, key, value) { entry(id).drafts[key] = value; persist(); }
  function clearDrafts(id, prefix) {
    var e = entry(id);
    Object.keys(e.drafts).forEach(function (k) { if (!prefix || k.indexOf(prefix) === 0) delete e.drafts[k]; });
    persist();
  }
  function lessonsDone() { return LESSONS.filter(function (l) { return isComplete(l.id); }).length; }
  function status(id) {
    if (id === FINAL_ID) {
      var f = state[FINAL_ID];
      if (f && f.passed) return 'complete';
      if (f && (f.attempts.length || Object.keys(f.drafts).length)) return 'progress';
      return 'none';
    }
    if (isComplete(id)) return 'complete';
    var e = state[id];
    if (e && (e.lastStep || Object.keys(e.drafts || {}).length)) return 'progress';
    return 'none';
  }
  function nextLesson() {
    for (var i = 0; i < LESSONS.length; i++) if (!isComplete(LESSONS[i].id)) return LESSONS[i];
    return null;
  }

  /* ---------- assessment ---------- */
  function assessment() { return entry(FINAL_ID); }
  function recordAttempt(score) {
    var f = entry(FINAL_ID);
    var passed = score >= PASS_MARK;
    f.attempts.push({ score: score, passed: passed, at: new Date().toISOString() });
    f.submitted = true;
    if (passed) { f.passed = true; f.complete = true; if (!f.completedAt) f.completedAt = new Date().toISOString(); }
    persist();
    return passed;
  }
  function resetAttempt() { var f = entry(FINAL_ID); f.drafts = {}; f.submitted = false; persist(); }
  function hasPassed() { return !!(state[FINAL_ID] && state[FINAL_ID].passed); }
  function courseComplete() { return lessonsDone() === LESSONS.length && hasPassed(); }

  /* ---------- export / restore / clear ---------- */
  function countSaved(data) {
    var n = 0;
    Object.keys(data).forEach(function (k) { if (k !== '_meta' && data[k] && data[k].drafts) n += Object.keys(data[k].drafts).length; });
    return n;
  }
  function exportProgress() {
    var payload = {
      format: BACKUP_FORMAT, version: BACKUP_VERSION, course: COURSE_NAME, storageKey: STORAGE_KEY,
      exportedAt: new Date().toISOString(),
      note: 'Progress backup for VA Foundations only. Restore it on the VA Foundations home page or Progress page to bring your progress back in this or another browser.',
      summary: { lessonsComplete: lessonsDone(), lessonsTotal: LESSONS.length, savedItems: countSaved(state), finalAssessmentPassed: hasPassed() },
      data: state
    };
    var blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'VA-Foundations-progress-backup-' + new Date().toISOString().slice(0, 10) + '.json';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1500);
  }
  function restoreFromFile(file, done) {
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () {
      var payload;
      try { payload = JSON.parse(reader.result); }
      catch (e) { alert('This file is not a valid progress backup (it is not JSON).'); return; }
      if (!isPlainObject(payload) || typeof payload.format !== 'string') { alert('This file is not a VA Foundations progress backup.'); return; }
      if (payload.format !== BACKUP_FORMAT) { alert('Backups from other PVA courses cannot be restored here.'); return; }
      if (typeof payload.version !== 'number' || payload.version > BACKUP_VERSION) { alert('This backup was made by a newer version of the course and cannot be restored here.'); return; }
      var restored = normalize(payload.data);
      var lessons = LESSONS.filter(function (l) { return restored[l.id] && restored[l.id].complete; }).length;
      var passed = restored[FINAL_ID] && restored[FINAL_ID].passed;
      var when = payload.exportedAt ? new Date(payload.exportedAt).toLocaleString() : 'unknown date';
      var msg = 'Restore this backup?\n\nExported: ' + when + '\nLessons complete: ' + lessons + ' of ' + LESSONS.length +
        '\nFinal Assessment: ' + (passed ? 'passed' : 'not passed yet') + '\nSaved answers: ' + countSaved(restored) +
        '\n\nRestoring REPLACES the progress currently saved in this browser.\n\nPress OK to replace and restore, or Cancel.';
      if (!confirm(msg)) return;
      state = restored;
      persist();
      if (done) done();
    };
    reader.readAsText(file);
  }
  function clearProgress(done) {
    if (!confirm('Clear all saved VA Foundations progress in this browser? This cannot be undone. Other PVA courses are not affected.')) return;
    state = fresh();
    try { localStorage.removeItem(STORAGE_KEY); } catch (e) { storageOK = false; showBanner(); }
    if (done) done();
  }

  /* ---------- shared UI ---------- */
  function renderProgressBar(currentId) {
    var track = document.getElementById('progressTrack');
    if (!track) return;
    track.innerHTML = '';
    var ids = LESSONS.map(function (l) { return l.id; }).concat([FINAL_ID]);
    ids.forEach(function (id) {
      var s = document.createElement('span');
      s.className = 'progress-seg' + (status(id) === 'complete' ? ' done' : '') + (id === currentId ? ' current' : '');
      s.setAttribute('aria-hidden', 'true');
      track.appendChild(s);
    });
    var done = lessonsDone();
    var pct = Math.round(((done + (hasPassed() ? 1 : 0)) / (LESSONS.length + 1)) * 100);
    var text = courseComplete() ? 'VA Foundations complete' :
      done + ' of ' + LESSONS.length + ' lessons · Final Assessment: ' + (hasPassed() ? 'passed' : 'not passed yet');
    var t = document.getElementById('progressText'); if (t) t.textContent = text;
    var p = document.getElementById('progressPct'); if (p) p.textContent = pct + '%';
  }
  function renderLessonNav(currentId, root) {
    var nav = document.getElementById('lessonNav');
    if (!nav) return;
    nav.innerHTML = '';
    var items = [{ id: 'home', label: 'Home', href: root }].concat(
      LESSONS.map(function (l) { return { id: l.id, label: String(l.num), href: root + l.id + '/', title: 'Lesson ' + l.num + ': ' + l.title }; }),
      [{ id: FINAL_ID, label: 'Final', href: root + FINAL_ID + '/', title: 'Final Assessment' }]);
    items.forEach(function (it) {
      var a = document.createElement('a');
      a.href = it.href; a.textContent = it.label;
      a.title = it.title || 'VA Foundations home';
      if (it.id !== 'home' && status(it.id) === 'complete') a.classList.add('done');
      if (it.id === currentId) a.setAttribute('aria-current', 'page');
      nav.appendChild(a);
    });
  }

  load();

  window.PVAVAF = {
    STORAGE_KEY: STORAGE_KEY, LESSONS: LESSONS, FINAL_ID: FINAL_ID, PASS_MARK: PASS_MARK, TOTAL_QUESTIONS: TOTAL_QUESTIONS,
    storageOK: function () { return storageOK; },
    visit: visit, isComplete: isComplete, markComplete: markComplete, markNotDone: markNotDone,
    getDraft: getDraft, setDraft: setDraft, clearDrafts: clearDrafts,
    lessonsDone: lessonsDone, status: status, nextLesson: nextLesson,
    assessment: assessment, recordAttempt: recordAttempt, resetAttempt: resetAttempt, hasPassed: hasPassed, courseComplete: courseComplete,
    exportProgress: exportProgress, restoreFromFile: restoreFromFile, clearProgress: clearProgress,
    renderProgressBar: renderProgressBar, renderLessonNav: renderLessonNav,
    _state: function () { return state; }
  };
})();
