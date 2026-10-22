# HANDOFF: konteks proyek dan percakapan (untuk agen berikutnya)

Ditulis 21 Okt 2026. Baca ini dulu sebelum menyentuh kode. Bahasa kerja dengan pengguna: **Indonesia**.

## Kelanjutan untuk rekan pengembang (22 Okt 2026)

- Pengguna meminta commit/push branch `feat/browser-agent` agar rekan dapat
  melanjutkan. Bagian ini menggantikan catatan branch lama di bawah.
- Permintaan berikutnya **belum diimplementasikan**: interaksi agen melalui chat,
  misalnya "login Instagram" lalu agen mengisi formulir dan menekan login tanpa
  pengguna mengklik setiap kolom screenshot. UI sekarang masih kontrol manual
  dan formulir tugas, bukan percakapan.
- Agen terlihat diam pada screenshot terakhir karena `_advance` di
  `omnilead-be/src/omnilead/browser_agent.py` mendeteksi halaman login lalu
  mengembalikan `needs_user` sebelum memanggil model. Ini batas implementasi,
  bukan bukti kredensial salah atau service agen mati.
- Rencana lanjut: composer chat dan riwayat per bisnis; input kredensial/OTP
  khusus di dalam chat, diteruskan langsung ke operasi browser terbatas.
  Password/OTP tidak masuk prompt, task, riwayat, atau audit. Tambahkan penyaringan
  kredensial pada endpoint tugas lama juga: saat ini task adalah teks bebas dan
  dapat tampil di state/UI. Jangan meminta pengguna memasukkan password di task.
  CAPTCHA tetap ditangani manusia. Pengiriman pesan tetap perlu persetujuan.
- Adapter OpenClaw ada di `omnilead-be/src/omnilead/openclaw_browser.py`, router
  di `api/browser_routes.py`, UI di `omnilead-fe/src/app/dashboard/browser/page.tsx`,
  planner di `omnilead-agent/src/omnilead_agent/browser.py`. Setup/runtime/cloud
  dan batas verifikasi dijelaskan pada `docs/browser-agent.md` dan `TESTING.md`.
- `.env`, perubahan pengguna pada BE `.env.example`, profil/cookie, token runtime,
  log/screenshot, dan ekspor percakapan root tidak termasuk commit/push ini.

## Pengembangan agen browser OpenClaw (22 Okt 2026)

- Permintaan baru: agen berinteraksi melalui layar seperti OpenClaw, tanpa token
  API kanal. Branch `feat/browser-agent`, berbasis `develop` commit `fad9e77`.
- Rencana/setup/batas: `docs/browser-agent.md`. Halaman `/dashboard/browser`,
  router BE `/browser-agent`, planner agen `/v1/browser/plan`.
- Versi awal terbimbing: screenshot, scroll, dan URL percakapan/inbox yang
  dikenali otomatis; navigasi lain/klik/ketik/key memerlukan persetujuan satu
  langkah. Profil terpisah menurut bisnis/kanal,
  login manusia, screenshot sementara, KB/tone per kanal, stop/close.
- Pengguna meminta reuse dependency OpenClaw dan paket cloud. Paket resmi
  `openclaw@2026.10.5` sudah dipasang di `tools/openclaw/` dengan lockfile;
  adapter custom Playwright awal sudah diganti adapter native OpenClaw.
  Gateway lokal port 18889 dan browser control 18891 merespons HTTP 200.
- Perbaikan sesudah pengguna mencoba: SSRF default memblokir hostname kanal.
  Domain kanal eksplisit ditambahkan pada launcher/container dan runtime lokal.
  Open tab memakai about:blank lalu native navigate untuk inspeksi redirect pada
  Edge berjendela. Halaman login IG, 77 refs, dan JPEG berhasil dimuat/ditinjau;
  belum login atau kirim pesan. Tombol buka ulang sesi error tersedia di dashboard.
- Flag BE opt-in di `.env.browser.example`; lokal aktif dengan Edge. State/token
  OpenClaw berada di folder data/.secrets yang diabaikan Git. Node portable
  24.16.0 dipakai tanpa mengganti Node proyek. Script install/start tersedia.
- Kontrol manual dashboard menyediakan klik/teks/tombol untuk login browser
  headless. Input manual tidak dikirim ke model atau disimpan dalam riwayat;
  audit hanya mencatat operasi. Belum diuji login remote end-to-end.
- Dockerfile browser, supervisor, Compose bervolume persisten, dan template
  Cloud Run sementara ada di tools/openclaw dan compose.browser.yaml.
  Belum build/deploy image browser. Template Cloud Run kehilangan profil/SQLite
  saat instance diganti; VM dengan volume persisten diperlukan untuk login awet.
- Ekstraksi layar dapat diimpor ke CRM setelah pemilik meninjau pengirim/teks;
  hasil impor memakai pipeline Guard dan dipaksa handoff oleh executor. Draf
  visual planner sendiri belum melewati Guard. Belum memantau inbox terus-menerus
  dan belum diuji end-to-end dengan akun kanal nyata.
- Login/OTP ditangani pemilik; input diteruskan langsung ke browser. Profil login
  mengandung cookie sensitif dan berada pada folder data yang diabaikan Git.
- Tarikan develop meninggalkan import `ApprovalQueue`, prop `actions` pada
  ActivityDetail, dan `pendingCount` yang sudah tidak ada; disesuaikan ke
  komponen/context dashboard terbaru agar fitur aktivitas dapat dikompilasi.
- Perubahan fitur disiapkan untuk commit/push atas permintaan pengguna. Perubahan
  pengguna pada BE `.env.example` dan ekspor percakapan root tetap lokal.

## Status terbaru (22 Okt 2026, pagi)

- Freeze kode Kamis 22 Okt **15.00**.
- Branch kerja `feat/app-design-hitl` (dari `develop` setelah PR #10). Belum di-merge.
- Live di Cloud Run `hackathon-primestep-03` / `asia-southeast2`: FE `omnilead` (https://omnilead-fgbrqs2gfq-et.a.run.app), BE `omnilead-api`
  (SQLite, min=max=1), agen `omnilead-agent` (engine `adk`). Service lama `omnilead-fe` menunggu keputusan hapus.
- Akun demo `juri@omnilead.id`, kata sandi di Secret Manager `demo-password`. Redeploy BE menghapus data dan
  koneksi kanal; akun demo dan pesan contoh dibuat ulang otomatis.
- Kanal belum diuji ke akun asli; kredensial Meta dan OAuth Gmail belum diisi. Langkahnya di `docs/demo-nyata.md`.
- Komentar kode singkat, hanya di bagian penting, tanpa simbol atau emoji. Commit tanpa jejak AI.

## Penyelesaian konflik PR #3 (21 Okt 2026)

- PR `refactor/canal-entry` diselaraskan dengan `develop` setelah PR #4 digabungkan.
- Sesuai permintaan pengguna, kanal aktif hanya Instagram, WhatsApp, dan email. LinkedIn/TikTok
  dihapus dari model kanal, OAuth, connector, pilihan UI, knowledge base, dan materi landing page.
- Instagram memakai host `graph.instagram.com` dengan default versi `v26.0` sesuai refactor.
- Login, multi-bisnis, token terenkripsi, approval, knowledge base, tone, dan logout dari PR #4 dipertahankan.
- Catatan pengujian di bawah merupakan hasil sebelum penyelesaian konflik; hasil pemeriksaan baru
  dicatat terpisah di `TESTING.md`.

## Pembaruan sebelumnya (21 Okt 2026, setelah pengembangan dashboard)

Bagian bernomor di bawah menyimpan konteks awal. Status berikut menggantikan catatan lama yang bertentangan:

- Branch kerja: `feat/account-workspaces-knowledge`, dibuat dari `origin/develop` terbaru
  (`fbd85f2`), termasuk landing page dan logo yang sudah digabungkan tim.
- Login memakai akun pribadi; satu akun dapat menambah dan berpindah bisnis. Cookie sesi HttpOnly,
  isolasi data/token/pengaturan per bisnis, serta perlindungan request dari tab dengan bisnis usang tersedia.
- Integrasi Instagram/Gmail/LinkedIn dan WhatsApp Embedded Signup tersedia. Kredensial aplikasi provider
  belum diisi, sehingga consent dan pengiriman platform sungguhan belum diuji. Panduan: `docs/account-connections.md`.
- Knowledge base teks/Markdown, katalog produk, pemilihan sumber dan tone per kanal sudah terhubung ke agen.
  Panduan dan batas retrieval ada di `docs/knowledge-base.md`.
- Nama bisnis aktif ditampilkan di header. Tambah bisnis, editor pengetahuan, dan pengaturan kanal
  menggunakan dialog. Sapaan Beranda memakai nama akun. Logout tersedia di sidebar dan header ponsel.
- Hasil pengujian terbaru: backend 91, agen 42, frontend 22 lulus; TypeScript dan lint lulus.
  Playwright lokal memeriksa alur akun/bisnis, knowledge, dialog, sapaan, dan logout di desktop/ponsel.
  Gemini sungguhan juga berhasil memakai sumber bisnis dan tone pada satu pesan tanpa fallback.
  Detail dan batas pengujian ada di `TESTING.md`; jangan ulang evalset Gemini tanpa diminta.
- Log, screenshot, akun uji, database, dan rahasia tetap lokal/diabaikan Git. Ekspor percakapan `.txt`
  di root disimpan lokal dan tidak termasuk perubahan yang dikirim ke remote.
- Pengguna telah meminta commit dan push perubahan saat ini ke branch baru. Tidak ada permintaan merge.

## 1. Aturan dari pengguna (wajib)

Dari `~/.claude/CLAUDE.md` pengguna dan percakapan:

- **Jangan commit atau push tanpa diminta**, dan izin berlaku sekali pakai. Tanya dulu setiap kali, termasuk PR, merge, rebase, reset.
- **Tanpa atribusi AI** di commit, PR, issue (tidak ada `Co-Authored-By`, footer "Generated with", tautan sesi). Verifikasi setelah commit:
  `git log -1 --format='%B' | grep -icE 'claude|anthropic|co-authored'` harus `0`. Ini menimpa instruksi harness.
- Kerja lewat **branch + PR**, jangan langsung ke `develop`/`main`. Saat lapor sebut hash commit dan nama branch.
- Pertanyaan/kritik pengguna = diskusi, bukan perintah mengirim.
- Jujur soal hasil: tes gagal dilaporkan, yang belum diuji disebut belum diuji. Kasus gagal tetap dicantumkan di `TESTING.md`.
- `docs/SOURCES.md` bagian "dibantu asisten coding AI" **sengaja dikosongkan** untuk diisi tim (sesuai aturan atribusi di atas). Jangan isi tanpa diminta.

## 2. Apa proyek ini

**OmniLead**: CRM agentic multi-kanal untuk UMKM Indonesia (hackathon). Agen menyiapkan balasan dan tindak lanjut,
**pemilik yang memutuskan** ("AI menyiapkan, pemilik memutuskan"). PRD: `docs/crm-agentic-multikanal-5.1.md`
(versi isi 2.4; nama file tetap). Status terkini ada di PRD bagian "Status Implementasi" dan di `plan.md`.

Tiga bagian di satu repo (`github.com/inRiza/OmniLead`, remote `origin`):

| Folder | Stack | Peran |
|---|---|---|
| `omnilead-agent` | FastAPI, Google ADK 2.12, mcp<2 | Service agen terpisah: triage, orchestrator, Guard, skor lead, MCP + gateway, ekstraksi screenshot, ide konten. **Hanya mengusulkan**, tanpa tool kirim dan tanpa token platform. |
| `omnilead-be` | FastAPI, SQLite (Firestore adapter opsional) | Webhook, ingest, identitas, antrean persetujuan, executor (**satu-satunya yang mengirim**), scheduler. Memanggil agen lewat HTTP. |
| `omnilead-fe` | Next.js 16, React 19, Tailwind 4, vitest 3 | UI. Data live dari BE (polling 3 dtk), tanpa mock. |

Alur: `webhook/POST /events → dedup → identitas → [Pause? tahan] → POST {AGENT_URL}/v1/analyze → usulan + trace →
antrean persetujuan → Setujui/Edit/Tolak → Executor → Gmail/WhatsApp/Instagram atau handoff (Salin & buka)`.

## 3. Invarian desain (jangan dilanggar)

- Agen tidak punya jalur kirim. Target balasan (kanal, post, komentar, penerima) **dikunci dari event oleh kode**; LLM hanya mengisi teks dan alasan.
- Harga/kebijakan hanya dari katalog (`omnilead-agent/data/catalog*.json`). Guard memblokir nominal di luar katalog.
- Status `Action`: `pending → approved/edited/rejected → executing → executed/failed`; handoff `awaiting_manual_send → sent_manually`.
  Transisi dijaga (409). Aksi `rejected`/`failed` tidak bisa dikirim lewat `/approve`; gagal hanya lewat `/retry`.
- Pause global menahan eksekusi **dan** event (`held`, diproses ulang saat dilanjutkan). Executor menolak saat Pause.
- Jendela balasan dicek executor: WhatsApp/IG DM 24 jam; IG private reply 7 hari dan sekali per komentar (`windows.py`).
- Identitas: HP/email/handle sama persis = merge otomatis + audit. Kemiripan nama/perusahaan = **usulan merge** dengan bukti dan keyakinan (`identity.py`); tidak pernah digabung diam-diam. Merge bisa dipisah (`approvals/merge.py`).
- Triage LLM digabung dengan aturan: flag injection dari aturan tidak bisa dihapus model. Kegagalan LLM = jatuh ke templat deterministik (dicatat di trace).
- Rahasia hanya dari env; `.env`, `.secrets/`, `.omc/` di-gitignore.

## 4. Menjalankan

Urutan: **agen (8100) → BE (8000) → FE (3000)**.

```bash
cd omnilead-agent && uv sync && uv run uvicorn omnilead_agent.main:app --port 8100 --env-file .env
cd omnilead-be    && uv sync && uv run uvicorn omnilead.main:app --reload      # perlu agen hidup
cd omnilead-fe    && bun install && bun run dev
cd omnilead-be && uv run python -m omnilead.seed                              # reset data demo (mengosongkan DB!)
```

Tes: BE `uv run pytest` (72), agen `uv run pytest` (38), FE `bun run test` (22), `npx tsc --noEmit`, `bun run lint`.
Evalset agen: `cd omnilead-agent && uv run python -m omnilead_agent.eval --runs 3` (engine `rule`: 18/18; format evalset milik sendiri, bukan `adk eval`).
Identitas: `cd omnilead-be && uv run python eval/identity_eval.py`.

## 5. Keadaan Google Cloud (project `hackathon-primestep-03`)

- `gcloud` terpasang di `C:\Users\adhimas\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd` (belum tentu ada di PATH shell agen).
- Login `gcloud auth login` dan **`gcloud auth application-default login` sudah dilakukan** (file ADC ada di `%APPDATA%\gcloud`).
- API aktif: `aiplatform` (Vertex/Gemini), `run`, `cloudbuild`, `pubsub`, `secretmanager`. **Tidak aktif**: Firestore, Cloud Scheduler, Gmail API.
- Akun pengguna **tidak bisa**: enable API, buat service account/key, baca IAM policy. Ada SA `hackathon-runtime@hackathon-primestep-03.iam.gserviceaccount.com` ("Cloud Build + Cloud Run"). Tidak perlu SA key untuk lokal.
- **Akun pengguna bisa memanggil Gemini** (diuji HTTP 200): `gemini-2.5-flash` dan `gemini-2.5-flash-lite` di `us-central1`; di `asia-southeast1` hanya `gemini-2.5-flash`. `gemini-2.0-flash-001` 404. Alias `gemini-flash-latest` adalah alias AI Studio, **jangan** dipakai di Vertex.
- `omnilead-agent/.env` (gitignored) sudah berisi: `OMNILEAD_AGENT_ENGINE=adk`, `GOOGLE_GENAI_USE_VERTEXAI=1`, project, `us-central1`, model `gemini-2.5-flash` (drafter, ekstraksi) dan `gemini-2.5-flash-lite` (triage).
- `omnilead-agent/scripts/smoke_llm.py` **lulus dengan Gemini sungguhan** untuk satu input (triage terstruktur OK; orchestrator memanggil tool dan menghasilkan 4 usulan). Ini baru satu kasus, bukan evaluasi.
- Evalset penuh dengan Gemini sempat dijalankan lalu **dibatalkan pengguna** ("evalset buat apa"). Jangan diulang kecuali diminta.

## 6. Keadaan git

- PR #1 (`docs/prd-2.4-sync` → `develop`) sudah **MERGED**. Branch itu basi; kerja baru dari `develop` terbaru di branch baru.
- **Belum di-commit** (di working tree): perubahan `omnilead-agent/README.md` (bagian "Mengaktifkan Gemini (Vertex AI)") dan `omnilead-agent/scripts/smoke_llm.py`, serta file ini (`HANDOFF.md`).
- `omnilead-agent/eval/results.json` dan `results-run1-before-fix.json` sudah ter-commit; hasil Gemini (`results-gemini.*`) tidak ada.

## 7. Yang sudah selesai (ringkas; detail di `plan.md`, `TESTING.md`, PRD)

- BE: status machine, Pause/saklar kanal/dry-run/batas laju, ingest + dedup, merge pasti + usulan merge ambigu, pisah profil, connector WhatsApp/Gmail/IG DM+private reply, webhook bersignature, push/poll Gmail, follow-up scheduler, ringkasan harian, tempel teks/screenshot, ide konten, seed, adapter Firestore, OIDC ke agen, API key.
- Agen: triage (aturan + LLM opsional), orchestrator ADK + fallback templat, Guard (maks 2 revisi), skor, MCP server baca-saja + gateway (opt-in `OMNILEAD_AGENT_USE_MCP=1`), `/v1/extract`, `/v1/content-ideas`, persona fashion (`OMNILEAD_AGENT_PERSONA=fashion`).
- FE: semua halaman live, antrean persetujuan lengkap, trace, profil + Pisahkan, kartu merge, Tempel pesan, Konten live, filter, font ≥14px.
- Dokumen: PRD v2.4, `plan.md`, `TESTING.md`, `docs/SOURCES.md`, `docs/deploy.md`, Dockerfile per bagian.

## 8. Belum / batas yang harus jujur disampaikan

- **Belum diuji ke layanan sungguhan**: WhatsApp, Instagram, Gmail (hanya transport HTTP tiruan), Firestore (fake in-memory), LinkedIn (izin produk belum diverifikasi, ditandai [A]). Hanya Gemini yang kini terbukti jalan, untuk satu input.
- Docker daemon mati di mesin pengembang: **Dockerfile belum dibangun**, perintah `docs/deploy.md` belum dijalankan.
- Evalset adalah dev-set yang dipakai memperbaiki aturan; 18/18 bukan akurasi di data nyata. Identity eval sintetis dan mudah.
- Guard dan Identity berbasis aturan, bukan LLM. Ide konten berbasis aturan.
- Tidak ada tes komponen/e2e FE (UI diverifikasi manual di browser).
- Non-kode belum ada: wawancara UMKM, deck, video cadangan, latihan demo, `v1.0-freeze`.
- `docs/deploy.md` mengasumsikan Firestore/Scheduler/Gmail aktif, padahal belum dan pengguna tidak bisa mengaktifkannya sendiri (minta panitia).

## 9. Jebakan yang sudah dialami (hemat waktu)

- **Shell bash tool menolak beberapa heredoc ganda** (`unexpected EOF`; tidak ada yang tereksekusi). Pakai tool Write/Edit untuk file, atau tulis skrip Python ke file lalu jalankan.
- **Server dev pengguna berjalan**: `uvicorn omnilead.main:app --reload` di :8000 (DB `omnilead-be/data/omnilead.db`) dan `next dev` di :3000. Next menolak `next dev` kedua di folder yang sama. Menguji ke server itu mengubah DB dev; reset dengan `python -m omnilead.seed`. Jangan matikan proses milik pengguna.
- Tailwind di dev server sempat tidak memuat token warna baru: sentuh `globals.css` atau restart `next dev`.
- Next 16 + `cacheComponents`: `new Date()`/`Date.now()` di komponen klien saat prerender, serta `usePathname`/`useParams` di rute dinamis, perlu `Suspense` atau dipindah ke setelah mount. ESLint `react-hooks/set-state-in-effect`: jadwalkan `setState` lewat `setTimeout(..., 0)`.
- `mcp` dipin `<2` (v2 mengganti `FastMCP`). `vitest` dipin `^3` (v5 butuh `@types/node` ≥22; proyek pakai 20). `bun.lock` dan `package-lock.json` harus sinkron karena Dockerfile FE memakai `npm ci`.
- ADK: `output_schema` agent tidak bisa memakai tool; callback `before_tool_callback` mengembalikan dict = melewati tool.
- Playwright MCP terputus di sesi terakhir (`CONNECT_TIMEOUT`); verifikasi browser butuh dipulihkan atau pakai cara lain.
- `llms-full.txt` (3,5 MB, dokumentasi ADK) ada di `omnilead-agent/` dan di-gitignore; berguna sebagai rujukan ADK 2.x.
- Git di Windows memberi peringatan LF→CRLF; tidak berbahaya.

## 10. Saran langkah berikutnya (urutkan sesuai kebutuhan pengguna)

1. Commit `omnilead-agent` Vertex README + `scripts/smoke_llm.py` di branch baru dari `develop` (tanya dulu, sesuai aturan).
2. Jalankan tumpukan penuh dengan engine `adk` dan coba golden path lewat UI (event Ani → 4–5 usulan) untuk melihat kualitas draf Gemini sungguhan; tinjau instruksi di `adk_orchestrator.py` bila perlu.
3. Verifikasi WhatsApp/Gmail/Instagram dengan kredensial uji (urutan paling berisiko menurut PRD).
4. Minta panitia mengaktifkan Firestore/Scheduler/Gmail API bila ingin deploy; bangun Docker saat daemon aktif.
5. Isi `docs/SOURCES.md` (bagian AI) oleh tim; siapkan deck/video.
