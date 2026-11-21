/* The session page: wait for the machine, count the minutes, carry the sealed chat.
   Reads its numbers from data- attributes on #session, so the page holds no inline script. */
(function () {
  'use strict';
  var root = document.getElementById('session');
  if (!root) return;
  var sid = Number(root.dataset.sid), phase = root.dataset.phase, sandbox = root.dataset.sandbox === '1';

  if (phase === 'starting') {
    // Ask until the machine says ready (or the session ends), then show the running page.
    (function wait() {
      fetch('/sessions/' + sid + '/messages?after=0&wait=10', {credentials: 'same-origin'})
        .then(function (r) { if (r.status === 404) { location.reload(); return {}; } if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (d) { if (d.ready || d.ended) location.reload(); else setTimeout(wait, 300); })
        .catch(function () { setTimeout(wait, 3000); });
    })();
    return;
  }
  if (phase !== 'running') return;

  // ---- the counter ----
  var started = Number(root.dataset.ready) * 1000, rate = Number(root.dataset.rate), balance = Number(root.dataset.balance);
  function tick() {
    var secs = Math.max(0, Math.floor((Date.now() - started) / 1000));
    var mins = Math.max(1, Math.ceil(secs / 60));
    var cost = Math.ceil(rate * mins / 60);
    var left = Math.max(0, Math.floor((balance - cost) * 60 / rate));
    document.getElementById('elapsed').textContent = Math.floor(secs / 60) + ':' + ('0' + secs % 60).slice(-2);
    document.getElementById('cost').textContent = '$' + (cost / 100).toFixed(2);
    document.getElementById('left').textContent = left + ' min';
    if (left <= 0 && !window.orbitReloading) { window.orbitReloading = true; setTimeout(function () { location.reload(); }, 3000); }
  }
  tick(); setInterval(tick, 1000);

  // ---- the conversation ----
  var after = 0, seen = {}, thinking = null;
  var log = document.getElementById('chat'), form = document.getElementById('say'), input = document.getElementById('msg');
  var badge = document.getElementById('seal-state'), note = document.getElementById('seal-note');
  var empty = document.getElementById('chat-empty');
  var STORE = 'orbit-seal-' + sid, WAIT_FOR_KEY_MS = 10000, loadedAt = Date.now();
  var sealer = null, state = 'waiting', lastHostHello = null, needHello = false, foreign = false;
  // Every sentence here must stay exactly true (rule 5). See docs/PRIVACY.md.
  var copy = {
    waiting: ['text-bg-secondary', "Waiting for the host's key",
      "Orbit relays this conversation and deletes it when the session ends. The host's machine runs the model and can read it."],
    sealed: ['text-bg-success', 'Sealed from Orbit',
      "Orbit relays envelopes it cannot open and deletes them when the session ends. The host's machine runs the model and can read this conversation; nothing checks that machine yet."],
    unsealed: ['text-bg-warning', 'Unsealed',
      "This host's program offered no key, so messages pass through Orbit readable until the session ends, when they are deleted. The host's machine can read them too."],
    insecure: ['text-bg-warning', 'Unsealed',
      "This page was not opened over https, so the browser cannot seal. Messages pass through Orbit readable until the session ends, when they are deleted. The host's machine can read them too."]
  };
  if (sandbox) {
    // In the sandbox the host is simulated on Orbit's own server, so "Orbit cannot open it" would be false.
    copy.sealed = ['text-bg-success', 'Sealed (sandbox)',
      "Your browser and a simulated host exchanged keys, and every message travels as a sealed envelope. The simulated host runs on Orbit's own server, so this shows how the sealing works, not the privacy it gives. With a real host the key stays on the host's machine."];
  }
  function setState(s) { state = s; badge.className = 'badge ' + copy[s][0]; badge.textContent = copy[s][1]; note.textContent = copy[s][2]; }
  function add(sender, text, extra) {
    if (empty) { empty.remove(); empty = null; }
    var d = document.createElement('div');
    d.className = 'msg msg-' + sender + (extra ? ' ' + extra : '');
    d.textContent = text;
    log.appendChild(d); log.scrollTop = log.scrollHeight;
    return d;
  }
  function keep(s) { s.export().then(function (k) { try { sessionStorage.setItem(STORE, JSON.stringify(k)); } catch (e) {} }).catch(function () {}); }
  async function sealerFor() {
    if (sealer) return sealer;
    try { var saved = sessionStorage.getItem(STORE); if (saved) sealer = await OrbitSeal.restore(sid, 'user', JSON.parse(saved)); } catch (e) { sealer = null; }
    if (!sealer) { sealer = await OrbitSeal.create(sid, 'user'); keep(sealer); }
    return sealer;
  }
  function post(body) {
    return fetch('/sessions/' + sid + '/messages', {method: 'POST', credentials: 'same-origin',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: 'body=' + encodeURIComponent(body)});
  }
  async function sendHello() {
    needHello = false;
    var r = await post(sealer.hello());
    if (r.ok) { var j = await r.json(); seen[j.id] = true; }
  }
  async function show(m) {
    if (seen[m.id]) return;
    seen[m.id] = true; after = Math.max(after, m.id);
    var env = OrbitSeal.available ? OrbitSeal.parse(m.body) : null;
    // An envelope must come from the end it names. The relay labels the sender; a mismatch is dropped.
    if (env && env.from !== m.sender) { add('system', 'A message with a wrong sender label was dropped.', 'text-secondary'); return; }
    if (env && env.t === 'hello') {
      if (env.from === 'host') {
        lastHostHello = env;
        try { await (await sealerFor()).accept(env); needHello = true; foreign = false; setState('sealed'); }
        catch (e) { add('system', 'The host offered a key this browser could not use: ' + e.message, 'text-warning'); }
      } else if (sealer && env.pk === sealer.publicB64) { needHello = false; foreign = false; }
      else { foreign = true; }  // another tab answered the host, so its key is current and ours is not
      return;
    }
    if (m.sender === 'host' && thinking) { thinking.remove(); thinking = null; }
    if (env && env.t === 'msg') {
      if (!sealer || !sealer.ready() || foreign) { add('system', 'A sealed message this tab cannot open.', 'text-secondary'); return; }
      try { add(m.sender, await sealer.unseal(env)); }
      catch (e) { add('system', 'A sealed message this tab cannot open (' + e.message + ').', 'text-secondary'); }
      return;
    }
    add(m.sender, m.body);
  }
  async function poll() {
    try {
      var r = await fetch('/sessions/' + sid + '/messages?after=' + after + '&wait=15', {credentials: 'same-origin'});
      if (r.status === 404) { location.reload(); return; }  // the session is gone: the page will say why
      if (!r.ok) throw new Error(r.status);
      var d = await r.json();
      for (var i = 0; i < d.messages.length; i++) await show(d.messages[i]);
      if (needHello && sealer && sealer.ready() && !foreign) await sendHello();
      if (state === 'waiting' && Date.now() - loadedAt > WAIT_FOR_KEY_MS) setState('unsealed');
      if (d.ended) { location.reload(); return; }
      setTimeout(poll, 100);
    } catch (e) { setTimeout(poll, 3000); }
  }
  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    var text = input.value.trim();
    if (!text) return;
    if (state === 'waiting') { add('system', "Waiting for the host's key. Try again in a moment.", 'text-secondary'); return; }
    input.value = '';
    var body = text;
    if (state === 'sealed') {
      try {
        if (foreign) { sealer = await OrbitSeal.create(sid, 'user'); keep(sealer); await sealer.accept(lastHostHello); foreign = false; await sendHello(); }
        body = await sealer.seal(text);
      } catch (err) { add('system', 'Not sent: could not seal (' + err.message + ').', 'text-warning'); return; }
    }
    try {
      var r = await post(body);
      if (!r.ok) {
        if (state === 'sealed') sealer.sent -= 1;  // the host never saw this number
        var why = r.status;
        try { why = (await r.json()).detail || why; } catch (x) {}
        add('system', 'Not sent: ' + why, 'text-warning'); return;
      }
      var ok = await r.json();
      seen[ok.id] = true;
      add('user', text);
      if (!thinking) thinking = add('host', 'Thinking…', 'text-secondary');
    } catch (err) {
      if (state === 'sealed') sealer.sent -= 1;
      add('system', 'Not sent: Orbit did not answer.', 'text-warning');
    }
  });
  setState(OrbitSeal.available ? 'waiting' : 'insecure');
  poll();
})();
