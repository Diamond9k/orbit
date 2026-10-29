"""Seal the conversation between the user's browser and this machine, so Orbit relays
envelopes it cannot open.

Both ends hold one fresh key pair per session. Each posts a `hello` envelope with its public
key through Orbit's relay. From the two public keys and the session number both ends derive the
same two keys, one per direction, and from then on every message is an AES-GCM `msg` envelope.
Orbit stores and forwards the envelopes as opaque text and learns their length and timing,
nothing else. The same construction lives in orbit/static/seal.js for the browser; the two must
stay in step, and tests/test_seal.py checks that they do.

What this protects against, exactly:
  - Orbit reading or altering the conversation in flight or from its database. Yes.
  - Orbit swapping in its own key during the hello exchange (an active attack). No, unless the
    host's key is checked against something Orbit does not control: an attestation report from
    enclave hardware (the `att` field, see docs/PRIVACY.md) or a fingerprint compared out of band.
    The `att` field carries `{"kind": "none"}` until a real attester exists.
  - The host's machine reading the conversation. No. The model runs there in plain text.

Construction: ECDH on P-256, HKDF-SHA256, AES-256-GCM. The nonce is the per-direction message
counter, so it never repeats within one key; the counter is also authenticated as associated
data, so a replayed or reordered envelope is rejected. A new `hello` from the user (a new
browser tab) starts a new epoch with new keys and counters. P-256 and AES-GCM are chosen over
newer curves because every browser's WebCrypto has had them for years.
"""
import base64
import hashlib
import json

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

VERSION = 1
LABEL = b"orbit-seal-v1"
CURVE = ec.SECP256R1()
ROLES = ("user", "host")


class SealError(ValueError):
    pass


def _b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def _b64d(text: str) -> bytes:
    try:
        return base64.b64decode(text, validate=True)
    except (ValueError, TypeError) as e:
        raise SealError("bad base64") from e


def parse(body):
    """The envelope in `body`, or None if the body is not one (plain text, an older program)."""
    if not isinstance(body, str) or not body.startswith("{"):
        return None
    try:
        env = json.loads(body)
    except (ValueError, RecursionError):  # not JSON, or nested too deep to be anything but hostile
        return None
    if not isinstance(env, dict) or env.get("v") != VERSION or env.get("t") not in ("hello", "msg"):
        return None
    if env.get("from") not in ROLES:
        return None
    return env


class Sealer:
    """One end of a sealed session. `role` is "user" (the browser) or "host" (this machine)."""

    def __init__(self, session_id, role):
        if role not in ROLES:
            raise SealError("role must be user or host")
        self.session_id = int(session_id)
        self.role = role
        self.peer = "host" if role == "user" else "user"
        self._private = ec.generate_private_key(CURVE)
        self.public_raw = self._private.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        self.epoch = None
        self._send_key = self._recv_key = None
        self.sent = 0
        self.received = 0

    @property
    def ready(self):
        return self._send_key is not None

    def hello(self, attestation=None):
        """The envelope that offers this end's public key. Post it through the relay."""
        env = {"v": VERSION, "t": "hello", "from": self.role, "pk": _b64e(self.public_raw),
               "att": attestation if attestation is not None else {"kind": "none"}}
        return json.dumps(env, separators=(",", ":"))

    def accept(self, envelope):
        """Take the other end's hello and derive the keys for a new epoch. Returns the attestation
        object it carried (for the caller to show or check; this code does not verify it)."""
        env = parse(envelope) if isinstance(envelope, str) else envelope
        if env is None or env.get("t") != "hello" or env.get("from") != self.peer:
            raise SealError("not a hello from the other end")
        peer_raw = _b64d(env.get("pk", ""))
        try:
            peer_key = ec.EllipticCurvePublicKey.from_encoded_point(CURVE, peer_raw)
        except ValueError as e:
            raise SealError("bad public key") from e
        shared = self._private.exchange(ec.ECDH(), peer_key)
        user_pk, host_pk = (self.public_raw, peer_raw) if self.role == "user" else (peer_raw, self.public_raw)
        salt = hashlib.sha256(LABEL + self.session_id.to_bytes(8, "big") + user_pk + host_pk).digest()
        okm = HKDF(algorithm=hashes.SHA256(), length=64, salt=salt, info=LABEL + b" keys").derive(shared)
        user_to_host, host_to_user = okm[:32], okm[32:]
        if self.role == "user":
            self._send_key, self._recv_key = user_to_host, host_to_user
        else:
            self._send_key, self._recv_key = host_to_user, user_to_host
        self.epoch = salt[:8].hex()
        self.sent = self.received = 0
        return env.get("att")

    def _aad(self, sender, n):
        return f"orbit-seal-v1|session:{self.session_id}|epoch:{self.epoch}|from:{sender}|n:{n}".encode()

    def seal(self, text):
        """Plain text in, `msg` envelope out."""
        if not self.ready:
            raise SealError("no keys yet: exchange hellos first")
        n = self.sent + 1
        ct = AESGCM(self._send_key).encrypt(n.to_bytes(12, "big"), text.encode(), self._aad(self.role, n))
        self.sent = n
        return json.dumps({"v": VERSION, "t": "msg", "from": self.role, "n": n, "ct": _b64e(ct)},
                          separators=(",", ":"))

    def unseal(self, envelope):
        """`msg` envelope from the other end in, plain text out. Rejects anything out of order."""
        if not self.ready:
            raise SealError("no keys yet: exchange hellos first")
        env = parse(envelope) if isinstance(envelope, str) else envelope
        if env is None or env.get("t") != "msg" or env.get("from") != self.peer:
            raise SealError("not a sealed message from the other end")
        n = env.get("n")
        if not isinstance(n, int) or isinstance(n, bool) or n != self.received + 1:
            # The field is untrusted text; it is not echoed, so the error always prints on any console.
            shown = n if isinstance(n, int) and not isinstance(n, bool) else "(not a number)"
            raise SealError(f"message {shown} out of order, expected {self.received + 1}")
        try:
            text = AESGCM(self._recv_key).decrypt(n.to_bytes(12, "big"), _b64d(env.get("ct", "")),
                                                  self._aad(self.peer, n))
        except InvalidTag as e:
            raise SealError("the seal does not match: altered, or sealed with other keys") from e
        self.received = n
        return text.decode()
