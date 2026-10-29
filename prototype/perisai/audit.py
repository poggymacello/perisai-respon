"""Log audit berantai hash (tamper-evident).

Diadaptasi dari Kendali `kendali/audit.py` (MIT, (c) 2026 Kendali team: Poggy Macello Gultom &
Mohammad Ari Alexander Aziz). Perbedaan: tanpa web3/keccak dan tanpa jangkar on-chain; setiap entri
memuat hash SHA-256 keputusan dan hash entri sebelumnya. Mengedit, menghapus, atau menyisipkan entri
terdeteksi oleh `verify()`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

GENESIS = "0" * 64
_BODY_KEYS = ("seq", "ts", "case_id", "kind", "payload", "payload_hash")


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _entry_hash(prev: str, body: dict) -> str:
    return sha256(prev + canonical(body))


class AuditLog:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]

    def append(self, case_id: str, kind: str, payload: dict, ts: str) -> dict:
        entries = self.entries()
        prev = entries[-1]["entry_hash"] if entries else GENESIS
        body = {"seq": len(entries), "ts": ts, "case_id": case_id, "kind": kind, "payload": payload,
                "payload_hash": sha256(canonical(payload))}
        entry = {**body, "prev_hash": prev, "entry_hash": _entry_hash(prev, body)}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(canonical(entry) + "\n")
        return entry

    def verify(self) -> dict:
        problems: list[str] = []
        prev = GENESIS
        entries = self.entries()
        for i, e in enumerate(entries):
            try:
                body = {k: e[k] for k in _BODY_KEYS}
            except KeyError as exc:
                problems.append(f"entry {i}: missing field {exc}")
                break
            if e["seq"] != i:
                problems.append(f"entry {i}: sequence number {e['seq']} (entry inserted or deleted)")
            if e.get("prev_hash") != prev:
                problems.append(f"seq {e['seq']}: broken chain link")
            if _entry_hash(e.get("prev_hash", ""), body) != e.get("entry_hash"):
                problems.append(f"seq {e['seq']}: entry hash mismatch (record edited)")
            if sha256(canonical(e["payload"])) != e["payload_hash"]:
                problems.append(f"seq {e['seq']}: payload does not match its hash")
            prev = e.get("entry_hash", "")
        return {"entries": len(entries), "ok": not problems, "problems": problems,
                "head": entries[-1]["entry_hash"] if entries else GENESIS}
