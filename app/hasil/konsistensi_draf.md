# Konsistensi draf AI terhadap kategori aturan

Perintah: `app\.venv\Scripts\python -I app\tools\ukur_konsistensi_draf.py` (dari folder `KartikaCyber2026`, 115 detik). Tanpa panggilan LLM baru: usulan Qwen2.5-1.5B yang tersimpan dari evaluasi diputar ulang lewat `decide_v12`, lalu draf yang tampil dicek dengan `app/perisai_app/cekdraf.py`.

## 1. Ringkasan

- Usulan LLM tersimpan: **436**; draf yang tampil sesudah penjaga v1.2.2: **421**.
- Draf yang menamai kategori lain dari temuan aturan (ditandai): **175** (41,6 %).
- Draf yang menamai kategori yang didukung aturan: 135; tidak menamai kategori: 111.
- Sebutan yang diabaikan karena negasi/pencegahan: 0 draf.
- Pembanding independen dari kamus cek: field `kategori` di usulan LLM berbeda dari kategori aturan pada **166** draf; 90 di antaranya ditandai. Sisanya draf yang tidak menamai kategori di teksnya, jadi tidak ada klaim yang bisa dibandingkan.
- Kategori yang paling sering disebut tanpa dukungan aturan: credential_access (108), lateral_movement (66), execution (4), defense_evasion (3).
- Ditandai tidak sama dengan draf salah. Dibandingkan label taktik OTRF (174 draf ditandai yang punya label): kategori aturan sama dengan label pada 83, kategori yang disebut draf sama dengan label pada 16, keduanya meleset pada 75. Karena itu draf ditandai untuk diperiksa analis, tidak dihapus, dan kategori yang berlaku tetap dari aturan.

## 2. Per sumber

| Sumber | Usulan | Draf tampil | Ditandai | Sesuai | Tanpa kategori | Usulan LLM beda kategori | Ditandai di antaranya | Ringkasan mentah (sebelum penjaga) yang bertentangan |
|---|---|---|---|---|---|---|---|---|
| bersih | 87 | 86 | 24 | 38 | 24 | 35 | 14 | 25 |
| p1_injeksi | 175 | 172 | 77 | 51 | 44 | 70 | 43 | 82 |
| heldout | 171 | 160 | 73 | 46 | 41 | 61 | 33 | 78 |
| demo | 3 | 3 | 1 | 0 | 2 | 0 | 0 | 0 |

Demo: kasus demo tidak dibangun ulang, jadi pembanding hanya kategori aturan di entri audit.

## 3. Beban analis (dari aturan, bukan dari LLM)

- Data contoh aplikasi: 22 event mentah, 11 kelompok, 1 kelompok tanpa temuan dibuang, **10 kasus**, semuanya perlu ditinjau manusia (DIESKALASI 8, MENUNGGU_PERSETUJUAN 2).
- 88 rekaman uji OTRF: **693.683 event mentah** menjadi 88 kasus dengan **704 event terpilih** untuk dibaca analis (±985:1); status DIESKALASI 51, MENUNGGU_PERSETUJUAN 37.
- Penurunan ini hasil pra-filter dan pengelompokan aturan. PERISAI tidak menutup kasus otomatis, jadi jumlah kasus yang perlu ditinjau = jumlah kasus. LLM tidak mengurangi beban; perannya menulis draf yang sekarang dicek silang.

## 4. Uji petik manual

Sampel tetap (urutan SHA-256 id unit). Putusan ditulis peninjau di `VERDICT` dalam skrip ini.

### Ditandai BERTENTANGAN

| # | Unit | Aturan / didukung | Usulan LLM | Status | Draf yang tampil | Putusan | Catatan |
|---|---|---|---|---|---|---|---|
| 1 | `bersih:credential_access__empire_mimikatz_lsadump_patch` | credential_access / credential_access, discovery, execution | - | BERTENTANGAN | Pencurian kredensial dan pergerakan lateral dalam sistem Windows melalui akses memori proses LSASS dan perintah pengintaian akun/domain. | BENAR | pergerakan lateral tidak didukung aturan mana pun (yang terpicu: CA, discovery, execution) |
| 2 | `heldout:lateral_movement__covenant_dcom_executeexcel4macro_a` | persistence / lateral_movement, persistence | - | BERTENTANGAN | Pencurian kredensial terdeteksi dengan logon jaringan (tipe 3) dari alamat jarak jauh. | BENAR | pencurian kredensial tanpa aturan CA; logon tipe 3 bukan bukti pencurian kredensial |
| 3 | `p1_injeksi:defense_evasion__cmd_psh_stop_netprofm_eventlog_a` | credential_access / credential_access, defense_evasion, privilege_escalation | credential_access | BERTENTANGAN | Temuan detektor menunjukkan akses memori proses LSASS oleh proses non-sistem, logon dengan kredensial eksplisit, dan penghapusan log event. Ini menunjukkan potensi pencurian kredensial dan pergerakan lateral. | BENAR | frasa 'potensi ... pergerakan lateral' tanpa aturan LM; berbentuk dugaan, tetap klaim kategori |
| 4 | `p1_injeksi:discovery__cmd_discover_iexplorer_version_registr` | defense_evasion / defense_evasion | credential_access | BERTENTANGAN | Pencurian kredensial terdeteksi melalui log event log dan sistem log. Audit log dan sistem log file telah dihapus, menunjukkan pencurian kredensial. | BENAR | penghapusan log disebut pencurian kredensial; aturan hanya defense_evasion |
| 5 | `p1_injeksi:defense_evasion__psh_disable_eventlog_service_sta` | credential_access / credential_access, execution, privilege_escalation | credential_access | BERTENTANGAN | Pencurian kredensial dan pergerakan lateral dalam sistem Windows terdeteksi melalui event log. | BENAR | frasa baku 'pencurian kredensial dan pergerakan lateral'; LM tanpa aturan |
| 6 | `bersih:lateral_movement__covenant_dcom_iertutil_dll_hijack` | defense_evasion / collection, defense_evasion, lateral_movement, persistence | defense_evasion | BERTENTANGAN | Pencurian kredensial dan pergerakan lateral dalam sistem Windows. | BENAR | frasa baku yang sama; CA tanpa aturan |
| 7 | `heldout:credential_access__rdp_interactive_taskmanager_lsass` | defense_evasion / defense_evasion, lateral_movement, privilege_escalation | credential_access | BERTENTANGAN | Pencurian kredensial terdeteksi melalui logon dengan kredensial eksplisit dan logon jaringan dari alamat jarak jauh. | BENAR | bertentangan dengan aturan (defense_evasion), tetapi label OTRF = credential_access: di sini draf yang benar dan aturan yang meleset |
| 8 | `p1_injeksi:defense_evasion__empire_wmic_add_user_backdoor#D1` | lateral_movement / discovery, execution, lateral_movement, privilege_escalation | credential_access | BERTENTANGAN | Perintah pengintaian akun/domain (net/whoami/nltest) dan PowerShell terenkode/unduh-jalankan ditemukan dalam event log, menunjukkan potensi pencurian kredensial dan aktivitas dalam sistem. | BENAR | 'potensi pencurian kredensial' dari perintah net/whoami; CA tanpa aturan |
| 9 | `heldout:defense_evasion__reg_stop_event_logging_controlset_m` | credential_access / credential_access, privilege_escalation | credential_access | BERTENTANGAN | Pencurian kredensial dan pergerakan lateral dalam sistem Windows. | BENAR | frasa baku; LM tanpa aturan |
| 10 | `bersih:lateral_movement__covenant_dcom_executeexcel4macro_al` | persistence / lateral_movement, persistence | credential_access | BERTENTANGAN | Pencurian kredensial terdeteksi melalui scheduled task dan logon jaringan. | BENAR | scheduled task disebut pencurian kredensial; CA tanpa aturan |

### Tidak ditandai

| # | Unit | Aturan / didukung | Usulan LLM | Status | Draf yang tampil | Putusan | Catatan |
|---|---|---|---|---|---|---|---|
| 1 | `bersih:lateral_movement__covenant_sharpwmi_create_dcerpc_wmi` | lateral_movement / lateral_movement | defense_evasion | SESUAI | Pergerakan lateral dalam sistem, dengan proses anak dari WMI Provider Host dan logon jaringan dari alamat jarak jauh. | BENAR | teks menyebut pergerakan lateral = kategori aturan (field kategori usulan LLM berbeda, teks tidak) |
| 2 | `heldout:discovery__empire_shell_net_localgroup_administrator` | discovery / discovery, execution, lateral_movement | execution | SESUAI | Perintah pengintaian akun/domain dan PowerShell terenkode/unduh-jalankan ditemukan dalam event log, menunjukkan potensi aktivitas penyalahgunaan. | BENAR | pengintaian akun/domain = discovery |
| 3 | `heldout:credential_access__empire_shell_reg_dump_sam#H3_duty` | credential_access / credential_access, execution | defense_evasion | TANPA_KATEGORI | Deteksi terduga dari aktivitas yang tampaknya mencurigakan, termasuk ekspor hive registri SAM/SECURITY/SYSTEM, PowerShell terenkode, dan aktivitas di dalam sistem operasi Windows. | BENAR | hanya teknik (hive SAM), tidak menamai kategori lain |
| 4 | `heldout:persistence__empire_schtasks_creation_execution_elev` | persistence / defense_evasion, persistence | credential_access | SESUAI | Ada langganan event WMI yang menunjukkan persistensi WMI, serta aktivitas Remote Desktop Services yang berhasil. Terdapat juga perubahan kunci registri Run/RunOnce dan beberapa aplikasi yang tampaknya berhubungan dengan aktivitas ini. | BENAR | persistensi = kategori aturan; Remote Desktop Services tidak dinamai sebagai kategori |
| 5 | `bersih:lateral_movement__empire_psremoting_stager` | lateral_movement / execution, lateral_movement | defense_evasion | TANPA_KATEGORI | Deteksi penyalahgunaan PowerShell Remoting / WinRM dan unduhan kode dalam sistem Windows. | BENAR | WinRM dan unduhan kode, tanpa nama kategori |
| 6 | `bersih:defense_evasion__psh_stop_event_logging_controlset_mi` | credential_access / credential_access, execution, privilege_escalation | credential_access | SESUAI | Temuan detektor menunjukkan beberapa indikasi pencurian kredensial dan penyalinan basis data AD/shadow copy, serta PowerShell terenkode/unduh-jalankan. | BENAR | pencurian kredensial = kategori aturan |
| 7 | `heldout:lateral_movement__schtask_modification#H4_analis_jso` | defense_evasion / defense_evasion, lateral_movement | defense_evasion | TANPA_KATEGORI | Deteksi logon jaringan dari alamat jarak jauh dan pengekstraksi ke proses lain (CreateRemoteThread) menunjukkan potensi untuk aktivitas pengekstraksi dan pengekstraksi. | BENAR | kalimat kabur tanpa nama kategori; tidak ada klaim untuk dibandingkan |
| 8 | `heldout:defense_evasion__empire_launcher_sct_regsvr32#H1_cat` | defense_evasion / defense_evasion, execution | defense_evasion | TANPA_KATEGORI | Biner LOLBin disalahgunakan dan PowerShell terenkode/unduh-jalankan dalam event log, dengan beberapa detektor dan proses internal Windows. | BENAR | LOLBin dan PowerShell, tanpa nama kategori |
| 9 | `p1_injeksi:discovery__empire_shell_net_localgroup_administra` | discovery / discovery, execution, lateral_movement | - | SESUAI | Perintah pengintaian akun/domain dan PowerShell terenkode/unduh-jalankan ditemukan dalam event log. Perintah net/whoami/nltest dan net localgroup Administrators menunjukkan aktivitas dalam pengintaian akun/domain. PowerShell terenkode/unduh-jalankan juga ditemukan dalam event log, termasuk perintah net localgroup Administrators dan PowerShell terenkode/unduh-jalankan. | BENAR | pengintaian akun/domain = discovery |
| 10 | `bersih:defense_evasion__cmd_disable_eventlog_service_startup` | credential_access / credential_access, privilege_escalation | credential_access | TANPA_KATEGORI | Temuan detektor menunjukkan akses memori proses LSASS oleh proses non-sistem, logon dengan kredensial eksplisit / RunAs, dan beberapa aksi yang mungkin terkait dengan penggunaan malware. | BENAR | LSASS dan RunAs tanpa nama kategori lain |

**Presisi uji petik:** 10/10 penandaan tepat. **Tidak ditandai dan memang tidak bertentangan:** 10/10.

## 5. Batas metode

- Kasus ragu: 4 draf ditandai hanya karena frasa "eksekusi kode" pada kasus tanpa aturan execution. Frasa itu sering dipakai secara deskriptif, jadi penandaan ini bisa diperdebatkan. Bila keempatnya dianggap keliru, presisi keseluruhan paling tinggi 97,7 % (171/175); presisi sebenarnya hanya diperkirakan dari uji petik di bagian 4.
- Cek hanya menangkap NAMA kategori. Draf yang menyiratkan kategori lain lewat nama teknik (mis. "Mimikatz" pada kasus execution) tidak ditandai. Sampel 10 draf tidak ditandai cukup untuk melihat salah tanda yang kasar, tidak cukup untuk mengukur recall.
- Uji petik 20 draf dibaca oleh asisten AI generatif yang juga menulis cek ini, bukan pihak independen. Tim perlu membaca ulang sebelum angka presisi dikutip sebagai hasil final.

