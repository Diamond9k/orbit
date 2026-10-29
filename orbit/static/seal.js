/* Seal the conversation between this browser and the host's machine, so Orbit relays envelopes
   it cannot open. The twin of host/seal.py; the two must stay in step (tests/test_seal.py runs
   this file under Node against the Python side).

   ECDH P-256 -> HKDF-SHA256 -> two AES-256-GCM keys, one per direction. Nonce = message counter,
   also authenticated as associated data, so replays and reordering are rejected. See the Python
   file for what this does and does not protect against. Runs in the browser (WebCrypto) and in
   Node 20+ (globalThis.crypto). */
(function (root) {
  'use strict';
  var VERSION = 1, LABEL = 'orbit-seal-v1';
  var subtle = root.crypto && root.crypto.subtle;
  var enc = new TextEncoder(), dec = new TextDecoder();

  function b64e(buf) {
    var bytes = new Uint8Array(buf), s = '';
    for (var i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
    return btoa(s);
  }
  function b64d(s) {
    var bin = atob(s), out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }
  function sameBytes(a, b) {
    if (a.length !== b.length) return false;
    var diff = 0;
    for (var i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
    return diff === 0;
  }
  function concat() {
    var n = 0, i, out, off = 0;
    for (i = 0; i < arguments.length; i++) n += arguments[i].length;
    out = new Uint8Array(n);
    for (i = 0; i < arguments.length; i++) { out.set(arguments[i], off); off += arguments[i].length; }
    return out;
  }
  function be8(n) { // session number as 8 big-endian bytes (ids stay below 2^32)
    var b = new Uint8Array(8); new DataView(b.buffer).setUint32(4, n >>> 0); return b;
  }
  function be12(n) {
    var b = new Uint8Array(12); new DataView(b.buffer).setUint32(8, n >>> 0); return b;
  }
  function hex(buf) {
    var bytes = new Uint8Array(buf), s = '';
    for (var i = 0; i < bytes.length; i++) s += ('0' + bytes[i].toString(16)).slice(-2);
    return s;
  }

  function parse(body) {
    if (typeof body !== 'string' || body[0] !== '{') return null;
    var env;
    try { env = JSON.parse(body); } catch (e) { return null; }
    if (!env || typeof env !== 'object' || env.v !== VERSION) return null;
    if (env.t !== 'hello' && env.t !== 'msg') return null;
    if (env.from !== 'user' && env.from !== 'host') return null;
    return env;
  }

  function Sealer(sessionId, role, keyPair, publicRaw) {
    this.sessionId = sessionId >>> 0;
    this.role = role;
    this.peer = role === 'user' ? 'host' : 'user';
    this.keyPair = keyPair;
    this.publicRaw = publicRaw;
    this.publicB64 = b64e(publicRaw);
    this.epoch = null;
    this.sendKey = this.recvKey = null;
    this.sent = 0;
    this.received = 0;
  }

  Sealer.prototype.ready = function () { return this.sendKey !== null; };

  Sealer.prototype.hello = function (att) {
    return JSON.stringify({v: VERSION, t: 'hello', from: this.role, pk: this.publicB64, att: att || {kind: 'none'}});
  };

  Sealer.prototype.accept = async function (envelope) {
    var env = typeof envelope === 'string' ? parse(envelope) : envelope;
    if (!env || env.t !== 'hello' || env.from !== this.peer) throw new Error('not a hello from the other end');
    var peerRaw = b64d(env.pk);
    if (this.ready() && this.peerRaw && sameBytes(peerRaw, this.peerRaw)) return env.att;  // the same hello again: keep keys and counters (no nonce reuse)
    var seenB64 = b64e(peerRaw);
    if ((this.seenPeers || []).indexOf(seenB64) >= 0) throw new Error('a key from an earlier epoch of this session');  // replayed: nonces already spent
    var peerKey = await subtle.importKey('raw', peerRaw, {name: 'ECDH', namedCurve: 'P-256'}, false, []);
    var shared = new Uint8Array(await subtle.deriveBits({name: 'ECDH', public: peerKey}, this.keyPair.privateKey, 256));
    var userPk = this.role === 'user' ? this.publicRaw : peerRaw;
    var hostPk = this.role === 'user' ? peerRaw : this.publicRaw;
    var salt = new Uint8Array(await subtle.digest('SHA-256', concat(enc.encode(LABEL), be8(this.sessionId), userPk, hostPk)));
    var ikm = await subtle.importKey('raw', shared, 'HKDF', false, ['deriveBits']);
    var okm = new Uint8Array(await subtle.deriveBits({name: 'HKDF', hash: 'SHA-256', salt: salt, info: enc.encode(LABEL + ' keys')}, ikm, 512));
    var userToHost = await subtle.importKey('raw', okm.slice(0, 32), 'AES-GCM', false, ['encrypt', 'decrypt']);
    var hostToUser = await subtle.importKey('raw', okm.slice(32, 64), 'AES-GCM', false, ['encrypt', 'decrypt']);
    if (this.role === 'user') { this.sendKey = userToHost; this.recvKey = hostToUser; }
    else { this.sendKey = hostToUser; this.recvKey = userToHost; }
    this.peerRaw = peerRaw;
    this.seenPeers = (this.seenPeers || []).concat([seenB64]);
    this.epoch = hex(salt.slice(0, 8));
    this.sent = this.received = 0;
    return env.att;
  };

  Sealer.prototype.aad = function (sender, n) {
    return enc.encode('orbit-seal-v1|session:' + this.sessionId + '|epoch:' + this.epoch + '|from:' + sender + '|n:' + n);
  };

  Sealer.prototype.seal = async function (text) {
    if (!this.ready()) throw new Error('no keys yet: exchange hellos first');
    var n = this.sent + 1;
    var ct = await subtle.encrypt({name: 'AES-GCM', iv: be12(n), additionalData: this.aad(this.role, n)}, this.sendKey, enc.encode(text));
    this.sent = n;
    return JSON.stringify({v: VERSION, t: 'msg', from: this.role, n: n, ct: b64e(ct)});
  };

  /* Opens a sealed message from the other end, or one of our own from the relay's history (after a
     page reload), keeping both counters in step. */
  Sealer.prototype.unseal = async function (envelope) {
    if (!this.ready()) throw new Error('no keys yet: exchange hellos first');
    var env = typeof envelope === 'string' ? parse(envelope) : envelope;
    if (!env || env.t !== 'msg') throw new Error('not a sealed message');
    var mine = env.from === this.role, n = env.n;
    var expected = (mine ? this.sent : this.received) + 1;
    if (typeof n !== 'number' || n !== expected) throw new Error('message ' + n + ' out of order, expected ' + expected);
    var key = mine ? this.sendKey : this.recvKey;
    var pt;
    try {
      pt = await subtle.decrypt({name: 'AES-GCM', iv: be12(n), additionalData: this.aad(env.from, n)}, key, b64d(env.ct));
    } catch (e) {
      throw new Error('the seal does not match: altered, or sealed with other keys');
    }
    if (mine) this.sent = n; else this.received = n;
    return dec.decode(pt);
  };

  /* The key pair as JSON, so a tab can keep it in sessionStorage across a reload. */
  Sealer.prototype.export = async function () {
    return {priv: await subtle.exportKey('jwk', this.keyPair.privateKey), pub: await subtle.exportKey('jwk', this.keyPair.publicKey)};
  };

  async function create(sessionId, role) {
    var kp = await subtle.generateKey({name: 'ECDH', namedCurve: 'P-256'}, true, ['deriveBits']);
    var raw = new Uint8Array(await subtle.exportKey('raw', kp.publicKey));
    return new Sealer(sessionId, role, kp, raw);
  }

  async function restore(sessionId, role, saved) {
    var priv = await subtle.importKey('jwk', saved.priv, {name: 'ECDH', namedCurve: 'P-256'}, true, ['deriveBits']);
    var pub = await subtle.importKey('jwk', saved.pub, {name: 'ECDH', namedCurve: 'P-256'}, true, []);
    var raw = new Uint8Array(await subtle.exportKey('raw', pub));
    return new Sealer(sessionId, role, {privateKey: priv, publicKey: pub}, raw);
  }

  var api = {create: create, restore: restore, parse: parse, available: !!subtle};
  root.OrbitSeal = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
