/* Plays the browser for tests/test_seal.py, using the real orbit/static/seal.js under Node.
   Line protocol on stdin/stdout, one JSON object per line:
     in  {"session_id": 7, "host_hello": "<envelope>"}   -> out {"user_hello": "...", "sealed": "...", "att": {...}}
     in  {"open": "<envelope from the host>"}            -> out {"text": "..."}
     in  {"seal": "plain text"}                          -> out {"sealed": "..."}
   Any error -> out {"error": "..."} */
'use strict';
const path = require('path');
const readline = require('readline');
const OrbitSeal = require(path.join(__dirname, '..', 'orbit', 'static', 'seal.js'));

let sealer = null;
const rl = readline.createInterface({input: process.stdin});
const queue = [];
let busy = false;

async function handle(line) {
  const req = JSON.parse(line);
  if (req.host_hello !== undefined) {
    sealer = await OrbitSeal.create(req.session_id, 'user');
    const att = await sealer.accept(req.host_hello);
    return {user_hello: sealer.hello(), sealed: await sealer.seal(req.text || 'hello from the browser'), att: att};
  }
  if (req.open !== undefined) return {text: await sealer.unseal(req.open)};
  if (req.seal !== undefined) return {sealed: await sealer.seal(req.seal)};
  throw new Error('unknown request');
}

async function drain() {
  if (busy) return;
  busy = true;
  while (queue.length) {
    const line = queue.shift();
    let out;
    try { out = await handle(line); } catch (e) { out = {error: String(e && e.message || e)}; }
    process.stdout.write(JSON.stringify(out) + '\n');
  }
  busy = false;
}

rl.on('line', function (line) { if (line.trim()) { queue.push(line); drain(); } });
rl.on('close', function () { process.exit(0); });
