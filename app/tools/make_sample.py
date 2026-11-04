"""Membuat berkas data contoh SINTETIS untuk aplikasi (app/perisai_app/sampel/).

    app\\.venv\\Scripts\\python -I app\\tools\\make_sample.py

Semua host fiktif (*.batalyon.lab), IP privat fiktif, tanpa string alat serang nyata. String injeksi diambil dari
template keluarga uji D1/D2 di prototype/perisai/scenarios.py (string uji, bukan kode). Berkas fixture
prototype/tests/fixtures/contoh_wevtutil.xml disalin apa adanya.
"""

from __future__ import annotations

import base64
import json
import shutil
import sys
from pathlib import Path
from xml.sax.saxutils import escape

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from perisai_app.paths import ensure_engine_importable  # noqa: E402

ensure_engine_importable()
from perisai import scenarios  # noqa: E402

OUT = APP / "perisai_app" / "sampel"
NS = "http://schemas.microsoft.com/win/2004/08/events/event"
SYSMON = ("Microsoft-Windows-Sysmon", "Microsoft-Windows-Sysmon/Operational")
SEC = ("Microsoft-Windows-Security-Auditing", "Security")
SCM = ("Service Control Manager", "System")
PSH = ("Microsoft-Windows-PowerShell", "Microsoft-Windows-PowerShell/Operational")


def ev(src: tuple[str, str], eid: int, t: str, host: str, **data: str) -> str:
    d = "".join(f'<Data Name="{k}">{escape(v)}</Data>' for k, v in data.items())
    return (f'<Event xmlns="{NS}"><System><Provider Name="{src[0]}"/><EventID>{eid}</EventID>'
            f'<TimeCreated SystemTime="{t}"/><Channel>{src[1]}</Channel><Computer>{host}</Computer></System>'
            f"<EventData>{d}</EventData></Event>")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(APP.parent / "prototype" / "tests" / "fixtures" / "contoh_wevtutil.xml", OUT / "contoh_wevtutil.xml")

    inj_en = scenarios.DEV_FAMILIES["D1_override_en"]["tpl"].format(
        goal=scenarios.render_goal("G1", "en", {"host": "DC01", "ip": "", "url": "", "email": ""}))
    inj_id = scenarios.DEV_FAMILIES["D2_override_id"]["tpl"].format(
        goal=scenarios.render_goal("G2", "id", {"host": "", "ip": "10.10.0.53", "url": "", "email": ""}))
    b64 = base64.b64encode(inj_id.encode("utf-8")).decode()

    ops, keu, fil, dc, log5, adm = ("WS-OPS07.batalyon.lab", "WS-KEU02.batalyon.lab", "SRV-FILE01.batalyon.lab",
                                    "DC01.batalyon.lab", "WS-LOG05.batalyon.lab", "WS-ADM01.batalyon.lab")
    pub = r"C:\Users\Public"
    events = [
        # B: akses memori LSASS di workstation -> isolasi diusulkan, menunggu persetujuan
        ev(SYSMON, 10, "2026-10-29T02:41:07.2210000Z", ops, SourceImage=rf"{pub}\svc-update.exe",
           TargetImage=r"C:\Windows\system32\lsass.exe", GrantedAccess="0x1410"),
        ev(SEC, 4624, "2026-10-29T02:42:30.0000000Z", ops, TargetUserName="operator5", LogonType="3",
           IpAddress="172.16.20.51"),
        ev(SYSMON, 3, "2026-10-29T02:43:02.0000000Z", ops, Image=rf"{pub}\svc-update.exe",
           DestinationIp="172.16.20.51", DestinationPort="445"),
        # C: PowerShell tersembunyi + instruksi bahasa Inggris "isolasi DC01" di CommandLine
        ev(SYSMON, 1, "2026-10-29T04:12:44.0000000Z", keu, Image=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
           ParentImage=r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
           CommandLine=f'powershell.exe -nop -w hidden -c "Get-Date" {inj_en}'),
        ev(SYSMON, 3, "2026-10-29T04:12:50.0000000Z", keu, Image=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
           DestinationIp="172.16.30.9", DestinationPort="8080"),
        # D: layanan PsExec dipasang di server berkas -> isolasi diusulkan
        ev(SEC, 4624, "2026-10-29T06:15:02.0000000Z", fil, TargetUserName="adm.backup", LogonType="3",
           IpAddress="172.16.20.51"),
        ev(SEC, 5145, "2026-10-29T06:15:05.0000000Z", fil, ShareName=r"\\*\ADMIN$", RelativeTargetName="PSEXESVC.exe",
           IpAddress="172.16.20.51"),
        ev(SCM, 7045, "2026-10-29T06:15:07.0000000Z", fil, ServiceName="PSEXESVC",
           ImagePath=r"%SystemRoot%\PSEXESVC.exe"),
        # E: akses memori LSASS di DC01 -> aset terlindungi, tidak diisolasi otomatis
        ev(SYSMON, 10, "2026-10-29T07:02:19.0000000Z", dc, SourceImage=r"C:\ProgramData\diag\dumptool.exe",
           TargetImage=r"C:\Windows\system32\lsass.exe", GrantedAccess="0x1fffff"),
        ev(SYSMON, 1, "2026-10-29T07:02:15.0000000Z", dc, Image=r"C:\ProgramData\diag\dumptool.exe",
           ParentImage=r"C:\Windows\System32\cmd.exe", CommandLine=r"C:\ProgramData\diag\dumptool.exe /scan"),
        # F: CreateRemoteThread dari folder Public -> penghindaran pertahanan, eskalasi
        ev(SYSMON, 1, "2026-10-29T08:20:01.0000000Z", log5, Image=rf"{pub}\updater.exe",
           ParentImage=r"C:\Windows\explorer.exe", CommandLine=rf"{pub}\updater.exe /silent"),
        ev(SYSMON, 8, "2026-10-29T08:20:04.0000000Z", log5, SourceImage=rf"{pub}\updater.exe",
           TargetImage=r"C:\Windows\explorer.exe"),
        # G: pengintaian akun domain dari workstation admin
        ev(SYSMON, 1, "2026-10-29T09:05:11.0000000Z", adm, Image=r"C:\Windows\System32\whoami.exe",
           ParentImage=r"C:\Windows\System32\cmd.exe", CommandLine="whoami /all"),
        ev(SYSMON, 1, "2026-10-29T09:05:40.0000000Z", adm, Image=r"C:\Windows\System32\net.exe",
           ParentImage=r"C:\Windows\System32\cmd.exe", CommandLine='net group "Domain Admins" /domain'),
        # I: instruksi tersandi base64 di ScriptBlockText (firewall mendekode sebelum memindai)
        ev(PSH, 4104, "2026-10-29T11:03:27.0000000Z", ops,
           ScriptBlockText=f"$cfg = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{b64}'))"),
    ]
    xml = ("<!-- SINTETIS: format keluaran wevtutil /f:xml, host/IP fiktif (*.batalyon.lab), untuk demo aplikasi -->\n"
           + "\n".join(events) + "\n")
    (OUT / "contoh_batalyon.xml").write_text(xml, encoding="utf-8")

    srv = "SRV-ARSIP02.batalyon.lab"
    beats = [
        {"@timestamp": "2026-10-29T10:31:12.000Z", "winlog": {"event_id": 13, "channel": SYSMON[1], "computer_name": srv,
         "event_data": {"EventType": "SetValue", "Image": r"C:\Windows\Temp\updsvc.exe",
                        "TargetObject": r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run\UpdSvc",
                        "Details": r"C:\Windows\Temp\updsvc.exe"}}},
        {"@timestamp": "2026-10-29T10:32:40.000Z", "winlog": {"event_id": 1, "channel": SYSMON[1], "computer_name": srv,
         "event_data": {"Image": r"C:\Windows\System32\schtasks.exe", "ParentImage": r"C:\Windows\Temp\updsvc.exe",
                        "CommandLine": r'schtasks.exe /create /tn "UpdSvc" /tr C:\Windows\Temp\updsvc.exe /sc onlogon'}}},
    ]
    (OUT / "contoh_winlogbeat.json").write_text("\n".join(json.dumps(b) for b in beats) + "\n", encoding="utf-8")
    print("ditulis:", ", ".join(p.name for p in sorted(OUT.iterdir())))


if __name__ == "__main__":
    main()
