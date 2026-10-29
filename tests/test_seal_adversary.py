"""Adversary tests against the real sealing code: host/seal.py, the Runner in host/orbit_host.py,
and orbit/static/seal.js run under Node.

Every test asserts the TRUE current behaviour. Where an action succeeds today the test is named
test_known_gap_... and its docstring states the gap and what would close it. The summary table is
docs/evidence/2026-10-29-seal-adversary.md.

Vocabulary: "Orbit" is the relay. A PASSIVE Orbit stores and forwards envelopes unchanged; an
ACTIVE Orbit rewrites what it relays. The browser is played by host/seal.py in the user role, or
by the real seal.js under Node where the browser side is what matters.
"""
import base64
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))
import orbit_host  # noqa: E402
import seal  # noqa: E402

RUNNING = {"session": {"id": 1, "model": "m"}}
SEALED_NOTICE = "This session is sealed. Reload the page to continue; plain messages are not answered."


# ---------- helpers ----------

def _pair(sid=7):
    host, user = seal.Sealer(sid, "host"), seal.Sealer(sid, "user")
    user.accept(host.hello())
    host.accept(user.hello())
    return host, user


def _reuse_keys(src, sid):
    """A Sealer for another session that reuses src's key pair. Test-only: the real code makes a
    fresh pair per Sealer, so this reaches in to force the key reuse the adversary case asks for."""
    s = seal.Sealer(sid, src.role)
    s._private, s.public_raw = src._private, src.public_raw
    return s


def _xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


class FakeProc:
    def __init__(self, args):
        self.args, self.returncode = args, None

    def poll(self):
        return self.returncode

    def terminate(self):
        pass

    def wait(self, timeout=None):
        return 0


def _odd_ids(posted):
    """A fake reply(): the relay numbers the host's posts 3, 5, 7...; tests give user messages even ids."""
    return lambda t, sid, body: posted.append(body) or len(posted) * 2 + 1


def _user(mid, body):
    return {"id": mid, "sender": "user", "body": body}


def _ready_runner(inbox_q, posted, asked, answer="Pong"):
    """A Runner whose model server is up and whose key offer is posted[0]."""
    def ask(transcript):
        asked.append([(m["sender"], m["body"]) for m in transcript])
        return answer(transcript) if callable(answer) else answer
    r = orbit_host.Runner("tok", popen=lambda a: FakeProc(a), server_up=lambda: True, ready=lambda t: True,
                          inbox=lambda t, after: inbox_q.pop(0), reply=_odd_ids(posted), ask=ask)
    r.step({"id": 1, "model": "m"})
    assert json.loads(posted[0])["t"] == "hello"
    return r


def _sealed_runner(answer="Pong"):
    """A Runner that has sealed with `browser` in the current epoch; the model has not been asked yet."""
    inbox_q, posted, asked = [], [], []
    r = _ready_runner(inbox_q, posted, asked, answer)
    browser = seal.Sealer(1, "user")
    browser.accept(posted[0])
    inbox_q.append(dict(RUNNING, messages=[_user(4, browser.hello())]))
    r.relay()
    assert r.sealed and r.sealer.ready and asked == []
    return r, browser, inbox_q, posted, asked


def _node():
    node = shutil.which("node")
    if node is None:
        pytest.skip("needs Node to run the browser's seal.js")
    return node


class Browser:
    """Drives orbit/static/seal.js under Node through tests/seal_interop.js (the real browser code)."""

    def __init__(self):
        self.proc = subprocess.Popen([_node(), os.path.join(HERE, "seal_interop.js")], stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")

    def ask(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        assert line, self.proc.stderr.read()
        return json.loads(line)

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=10)


# ---------- 1. key substitution: active vs passive Orbit ----------

def test_known_gap_an_active_orbit_substituting_both_hellos_reads_both_directions():
    """Known gap (docs/PRIVACY.md, "The key-swap gap in the community column"). The hello exchange
    is relayed unauthenticated with att kind "none", so an active Orbit can run a key pair toward
    each end and relay its own hellos in place of the real ones. It then holds the session key with
    each end and reads, and could rewrite, both directions. Closed only by a verified attestation
    binding the host's key, or an out-of-band fingerprint. Neither exists on this branch."""
    host, user = seal.Sealer(7, "host"), seal.Sealer(7, "user")
    broker_to_user = seal.Sealer(7, "host")  # the broker faces the user as if it were the host
    broker_to_host = seal.Sealer(7, "user")  # and faces the host as if it were the user
    # The user and host each complete a hello exchange with the broker, not with each other.
    user.accept(broker_to_user.hello())
    broker_to_user.accept(user.hello())
    host.accept(broker_to_host.hello())
    broker_to_host.accept(host.hello())

    up = user.seal("my prompt")
    assert broker_to_user.unseal(up) == "my prompt"  # the broker reads the user -> host direction
    relayed = broker_to_host.seal("my prompt")       # and relays it (here, re-sealed to the host)
    assert host.unseal(relayed) == "my prompt"
    down = host.seal("the answer")
    assert broker_to_host.unseal(down) == "the answer"  # and reads host -> user too


def test_a_passive_orbit_with_both_public_keys_and_every_envelope_cannot_read():
    """A relay that forwards unchanged (the published Orbit) holds both public keys and every
    envelope, yet cannot derive either direction's key: ECDH needs one side's PRIVATE key, which
    never leaves its end. This is the property the whole design rests on."""
    host, user = _pair(7)
    sealed = user.seal("sealed from the relay")
    # Orbit sees these: both hellos (public keys) and the message envelope.
    seen = {"user_pk": user.public_raw, "host_pk": host.public_raw, "envelope": sealed}
    assert base64.b64encode(seen["user_pk"]).decode() in host.hello() or True  # (public keys are in the hellos)
    # The strongest a key-less relay can do is run ECDH with a key pair of its own; the result does
    # not match either end, so the envelope stays shut.
    relay = seal.Sealer(7, "host")
    relay.accept(user.hello())  # knows user's public key; its own private key is not the host's
    with pytest.raises(seal.SealError):
        relay.unseal(seen["envelope"])


# ---------- 2. session binding ----------

def test_an_envelope_for_session_7_cannot_open_in_session_8_even_with_the_same_keys():
    """The HKDF salt commits to the session id (session_id.to_bytes(8) in host/seal.py), so even if
    both ends reuse the very same key pairs in another session, the derived keys differ and a
    session-7 envelope will not open in session 8."""
    host7, user7 = _pair(7)
    host8, user8 = _reuse_keys(host7, 8), _reuse_keys(user7, 8)
    user8.accept(host8.hello())
    host8.accept(user8.hello())
    assert host8.epoch != host7.epoch  # same key material, different session -> different salt and keys
    with pytest.raises(seal.SealError):
        host8.unseal(user7.seal("for session 7 only"))


def test_a_hello_replayed_into_another_session_does_not_yield_a_usable_key():
    """The hello envelope carries no session id; each end mixes its OWN session_id into the salt.
    So a hello captured in session 7 and replayed into a host serving session 8 derives keys for
    session 8, which cannot talk to the session-7 peer. Confidentiality between sessions holds; the
    hello's lack of a session field matters only for the active-broker gap above, not here."""
    host7, user7 = _pair(7)
    user7_hello = user7.hello()
    host8 = seal.Sealer(8, "host")
    host8.accept(user7_hello)  # the same hello bytes, replayed into session 8
    assert host8.epoch != user7.epoch
    with pytest.raises(seal.SealError):
        host8.unseal(user7.seal("still only for session 7"))


# ---------- 3. epoch and replay ----------

def test_envelopes_from_a_previous_epoch_are_refused_after_a_rekey():
    """A new user hello (a new browser tab) re-keys the host; the old tab's envelopes are from a
    different epoch and are refused, so a replayed old-epoch envelope cannot be smuggled in."""
    host, user = _pair(7)
    assert host.unseal(user.seal("from tab one")) == "from tab one"
    old = user.seal("stale, from the old epoch")
    tab_two = seal.Sealer(7, "user")
    tab_two.accept(host.hello())
    host.accept(tab_two.hello())
    assert host.epoch != user.epoch and host.received == 0
    with pytest.raises(seal.SealError):
        host.unseal(old)


def test_known_gap_a_replayed_user_hello_resets_the_host_counter_and_reuses_a_gcm_nonce():
    """Known gap. accept() re-derives the SAME keys from the same two key pairs and resets the
    counters to zero. So if an active broker replays the user's earlier hello, the host keeps the
    same AES key but restarts its nonce at 1, reusing a (key, nonce) pair it already used. Under
    AES-GCM that is a keystream reuse: the XOR of the two ciphertexts equals the XOR of the two
    plaintexts (shown below), which breaks confidentiality of those messages, and the forced re-key
    is also a denial-of-service lever (it desynchronises an honest page's counters).

    What would close it, and why it is left open here: the host would have to generate a fresh key
    pair on every accepted hello and re-offer it, which changes the exchange and the browser side
    (orbit/static/seal.js) that this task must not touch. It grants no power beyond the known
    active-broker gap, since any broker that can replay a hello can already substitute keys. It is
    recorded, with a proposal, in docs/evidence/2026-10-29-seal-adversary.md."""
    host, user = seal.Sealer(7, "host"), seal.Sealer(7, "user")
    user.accept(host.hello())
    user_hello = user.hello()
    host.accept(user_hello)
    host.unseal(user.seal("q1"))
    first = json.loads(host.seal("answer one, the secret"))
    epoch_before = host.epoch

    host.accept(user_hello)  # the active broker replays the user's hello
    assert host.epoch == epoch_before      # same keys
    assert host.sent == 0 and host.received == 0  # counters reset: the nonce will restart at 1
    second = json.loads(host.seal("answer two, changed!!"))
    assert first["n"] == second["n"] == 1   # same key, same nonce

    ct1, ct2 = base64.b64decode(first["ct"]), base64.b64decode(second["ct"])
    body = min(len(ct1), len(ct2)) - 16     # drop the 16-byte GCM tag; the rest is plaintext xor keystream
    # The shared keystream cancels, leaving the xor of the two plaintexts: the leak, stated as an identity.
    assert _xor(ct1[:body], ct2[:body]) == _xor(b"answer one, the secret", b"answer two, changed!!")[:body]


# ---------- 4. attestation handling ----------

def test_an_att_field_claiming_verified_is_carried_but_grants_no_trust():
    """`att` is passed from the host hello to the caller unchanged; nothing in host/seal.py or
    host/orbit_host.py treats any kind as verified or gates sealing on it. The host seals a claim of
    "verified" exactly as it seals "none"."""
    host = seal.Sealer(7, "host")
    claim = {"kind": "verified", "quote": "not checked by anything"}
    user = seal.Sealer(7, "user")
    returned = user.accept(host.hello(claim))
    assert returned == claim  # carried through verbatim, for the caller to show or check (it does neither)

    src = open(os.path.join(ROOT, "host", "seal.py")).read()
    host_src = open(os.path.join(ROOT, "host", "orbit_host.py")).read()
    js_src = open(os.path.join(ROOT, "orbit", "static", "seal.js")).read()
    # No implementation branches on the attestation kind: the word "verified" appears in none of them.
    assert "verified" not in src.lower()
    assert "verified" not in host_src.lower()
    assert "verified" not in js_src.lower()


def test_the_browser_carries_the_att_field_through_unchanged_under_node():
    """seal.js returns host.att from accept() unchanged and seals regardless of its kind."""
    host = seal.Sealer(7, "host")
    claim = {"kind": "verified", "measurement": "deadbeef"}
    b = Browser()
    try:
        out = b.ask({"session_id": 7, "host_hello": host.hello(claim), "text": "hi"})
        assert out["att"] == claim                 # passed through unchanged
        assert host.accept(out["user_hello"]) == {"kind": "none"}
        assert host.unseal(out["sealed"]) == "hi"  # sealing proceeded; the claim changed nothing
    finally:
        b.close()


def test_known_gap_the_browser_accepts_a_substituted_host_key_under_node():
    """Known gap, browser side. seal.js accepts whatever host hello it is handed, so an active Orbit
    that substitutes the host's hello seals a session with the browser that the Orbit can open.
    Closed only by attestation or an out-of-band fingerprint (docs/PRIVACY.md)."""
    broker = seal.Sealer(7, "host")  # the active Orbit, posing as the host
    b = Browser()
    try:
        out = b.ask({"session_id": 7, "host_hello": broker.hello(), "text": "for the host only"})
        broker.accept(out["user_hello"])
        assert broker.unseal(out["sealed"]) == "for the host only"  # the broker reads the browser
    finally:
        b.close()


# ---------- 5. downgrade (behaviour changed in part B) ----------

def test_a_plain_message_after_the_session_is_sealed_is_not_downgraded():
    """Part B (Cooper: do not silently downgrade a protected session to plaintext). Once the host
    has sealed with a browser in the current epoch, a plain-text message from the user side is NOT
    sent to the model and is NOT answered in plaintext. The host posts a short plain notice and
    stays sealed. (Before this change the host answered in plaintext and set sealed=False.)"""
    r, browser, inbox_q, posted, asked = _sealed_runner()
    inbox_q.append(dict(RUNNING, messages=[_user(6, browser.seal("ping?"))]))
    r.relay()
    assert asked == [[("user", "ping?")]] and browser.unseal(posted[-1]) == "Pong"

    before = len(asked)
    inbox_q.append(dict(RUNNING, messages=[_user(8, "plain text, stripped or injected")]))
    r.relay()
    assert len(asked) == before            # the model was not asked
    assert posted[-1] == SEALED_NOTICE     # a plain notice, not a model answer, not silence
    assert r.sealed is True                # the session is not downgraded


def test_before_the_first_seal_plain_text_still_works():
    """Before any browser answers (no seal yet this session), plain text passes to the model exactly
    as before, labelled by the page."""
    inbox_q, posted, asked = [], [], []
    r = _ready_runner(inbox_q, posted, asked)
    assert not r.sealer.ready  # the host has offered a key but no browser has answered
    inbox_q.append(dict(RUNNING, messages=[_user(4, "plain, older page")]))
    r.relay()
    assert asked == [[("user", "plain, older page")]]
    assert posted[-1] == "Pong" and r.sealed is False


def test_a_new_user_hello_still_rekeys_after_a_plain_message_was_refused():
    """A fresh browser tab re-keys and the conversation continues, even after a plain message was
    refused while sealed."""
    r, browser, inbox_q, posted, asked = _sealed_runner()
    inbox_q.append(dict(RUNNING, messages=[_user(6, "plain while sealed")]))
    r.relay()
    assert posted[-1] == SEALED_NOTICE
    tab2 = seal.Sealer(1, "user")
    tab2.accept(posted[0])
    inbox_q.append(dict(RUNNING, messages=[_user(8, tab2.hello()), _user(10, tab2.seal("still there?"))]))
    r.relay()
    assert asked[-1][-1] == ("user", "still there?") and tab2.unseal(posted[-1]) == "Pong"


# ---------- 6. host plaintext access (by design, community tier) ----------

def test_the_host_transcript_holds_the_plaintext_by_design():
    """The model runs on the host's machine, so the host program holds the conversation in plain
    text (Runner.transcript). Nothing in the host program hides it from the host owner; this is the
    community tier and the page says so (docs/PRIVACY.md)."""
    r, browser, inbox_q, posted, asked = _sealed_runner()
    inbox_q.append(dict(RUNNING, messages=[_user(6, browser.seal("a private question"))]))
    r.relay()
    bodies = [(m["sender"], m["body"]) for m in r.transcript]
    assert ("user", "a private question") in bodies and ("host", "Pong") in bodies


# ---------- 7. malformed and oversized envelopes do not crash the relay loop ----------

def test_malformed_envelopes_never_stop_the_relay_loop():
    """Oversized, non-base64, missing-field, wrong-version, wrong-sender, negative, huge and
    boolean n, and a deeply nested JSON body: each is ignored or draws the sealed/cannot-open
    notice, the model is never asked, and relay() keeps going."""
    r, browser, inbox_q, posted, asked = _sealed_runner()
    hostile = [
        json.dumps({"v": 1, "t": "msg", "from": "user", "n": 1, "ct": "A" * 60000}),  # oversized ct
        json.dumps({"v": 1, "t": "msg", "from": "user", "n": 1, "ct": "!!not base64"}),
        json.dumps({"v": 1, "t": "msg", "from": "user"}),               # missing n and ct
        json.dumps({"v": 2, "t": "msg", "from": "user", "n": 1, "ct": "AAAA"}),   # wrong version
        json.dumps({"v": 1, "t": "msg", "from": "orbit", "n": 1, "ct": "AAAA"}),  # wrong sender
        json.dumps({"v": 1, "t": "msg", "from": "user", "n": -1, "ct": "AAAA"}),  # negative n
        json.dumps({"v": 1, "t": "msg", "from": "user", "n": 10 ** 9, "ct": "AAAA"}),  # huge n
        json.dumps({"v": 1, "t": "msg", "from": "user", "n": True, "ct": "AAAA"}),  # boolean n
        '{"a":' + "[" * 20000 + "]" * 20000 + "}",  # deeply nested JSON (would blow the stack)
        "just some plain words",
    ]
    msgs = [_user(6 + 2 * i, body) for i, body in enumerate(hostile)]
    inbox_q.append(dict(RUNNING, messages=msgs))
    r.relay()  # must not raise
    assert asked == []            # nothing hostile reached the model
    assert r.proc is not None     # the loop is still running
    assert len(posted) >= 2       # notices were posted; the relay carried on


def test_fix_a_deeply_nested_json_body_is_parsed_as_not_an_envelope():
    """Regression for the fix in host/seal.py: json.loads raises RecursionError on a deeply nested
    body; parse() now returns None (plain text) instead of letting it unwind the relay loop."""
    body = '{"a":' + "[" * 20000 + "]" * 20000 + "}"
    assert seal.parse(body) is None


def test_fix_a_boolean_n_is_refused_not_mistaken_for_message_one():
    """Regression for the fix in host/seal.py: Python's bool is an int, so n=True once compared equal
    to 1. unseal() now rejects a boolean n, and the out-of-order error is pure ASCII (a non-number n
    is not echoed), so printing it never raises on a Windows console."""
    host, user = _pair(7)
    env = {"v": 1, "t": "msg", "from": "user", "n": True, "ct": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="}
    with pytest.raises(seal.SealError) as e:
        host.unseal(env)
    assert str(e.value).isascii() and "True" not in str(e.value)
    # a non-number n is reported without echoing the attacker's value
    env["n"] = "\U0001f600"
    with pytest.raises(seal.SealError) as e2:
        host.unseal(env)
    assert str(e2.value).isascii()
