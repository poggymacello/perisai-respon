"""PERISAI-RESPON: asisten triase insiden offline dengan firewall kebijakan.

Prinsip: LLM mengusulkan, kebijakan memutuskan, manusia menyetujui aksi berisiko.
Pola "propose / policy decides" dan log audit berantai hash diadaptasi dari Kendali
(TIM/FinTechathon2026/kendali, MIT, (c) 2026 Kendali team: Poggy Macello Gultom & Mohammad Ari Alexander Aziz).
"""

CATEGORIES = [
    "credential_access",
    "defense_evasion",
    "lateral_movement",
    "discovery",
    "persistence",
    "execution",
    "privilege_escalation",
    "collection",
]

CATEGORY_ID = {
    "credential_access": "pencurian kredensial",
    "defense_evasion": "penghindaran pertahanan",
    "lateral_movement": "pergerakan lateral",
    "discovery": "pengintaian internal",
    "persistence": "persistensi",
    "execution": "eksekusi kode",
    "privilege_escalation": "eskalasi hak akses",
    "collection": "pengumpulan data",
}

ACTIONS = ["isolate_host", "block_ip", "escalate", "no_action"]
RISKY_ACTIONS = {"isolate_host", "block_ip"}

# Playbook tetap (dibekukan di PRAREG): kategori -> aksi yang benar.
PLAYBOOK = {
    "credential_access": "isolate_host",
    "lateral_movement": "isolate_host",
    "privilege_escalation": "isolate_host",
    "defense_evasion": "escalate",
    "discovery": "escalate",
    "persistence": "escalate",
    "execution": "escalate",
    "collection": "escalate",
}
