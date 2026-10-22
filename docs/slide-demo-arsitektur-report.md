---
title: Slide Bagian Solution - User Flow, Demo, Arsitektur, Prototype Report
related: struktur-deck-pitch-dan-detail.md, demo-nyata.md, crm-agentic-multikanal-6.1.md, ../TESTING.md
updated: 2026-10-22
---

# Slide Bagian Solution: User Flow, Demo, Arsitektur Agentic, Prototype Report

Persona: **Bu Rina, katering dan hampers rumahan** (sama dengan data demo). Pelanggan dalam cerita: **Ani, PT Maju
Jaya**. Teks di slide berbahasa Inggris, mengikuti slide lain di deck.

## Urutan dan alasannya

| Urutan | Slide | Peran | Waktu di pitch 10 menit |
|---|---|---|---|
| 1 | **User Flow** | Peta: apa yang akan dilihat juri, dan di mana Bu Rina memutuskan | sekitar 40 detik |
| 2 | **Demo** | Bukti bahwa peta itu berjalan di aplikasi | sekitar 4 menit |
| 3 | **Agentic Architecture** | Penjelasan cara kerja dan kenapa aman. **Alur agen** (triage, identitas, orchestrator, Guard, antrean persetujuan, executor) ada di slide ini sebagai diagram utama | sekitar 40 detik |
| 4 | **Prototype Report** | Bukti angka, termasuk bagian yang gagal | sekitar 40 detik |

User Flow menampilkan alur dari sudut pandang orang (Ani, agen, Bu Rina). Agentic Architecture membuka "kotak agen" di
dalamnya. Keempat slide masuk bagian **Solution** pada navigasi bawah.

## Template yang sama di setiap halaman

| Bagian | Isi | Gaya |
|---|---|---|
| **Judul** (kiri atas, kecil) | Nama halaman, misalnya "User Flow" | Teks kecil biru, satu baris |
| **Deskripsi** (di bawah judul, tebal) | Satu kalimat kesimpulan halaman | Hitam tebal, sekitar 20 pt |
| Logo (kanan atas) | Logo OmniLead dan logo penyelenggara | Disisipkan manual setelah gambar jadi |
| Garis header | Garis tipis biru muda di bawah header | |
| **Isi** | Konten utama halaman | Kartu putih atau abu muda bertepi bulat; judul blok berupa pil biru; kartu bernomor oranye; panah oranye |
| Kotak bawah (opsional) | Satu kalimat kunci atau catatan jujur | Kotak abu-abu bertepi bulat selebar halaman |
| **Footbar** (paling bawah) | Problem Definition, Solution, Marketing Opportunity, Business Model, Future Outlook | Pita biru tua selebar halaman, teks putih; tab aktif berupa pil putih yang menonjol ke atas dengan teks biru. Di bagian ini tab aktif: **Solution** |

Warna: biru utama sekitar `#1636C9`, oranye sekitar `#F7931E`, abu kartu `#C9D1DC`, teks `#111111`. Font sans-serif
bersih (Inter atau Poppins). Rasio 16:9.

**Aturan angka:** hanya angka di tabel bawah ini yang boleh muncul di slide. Jangan membiarkan GPT menambah angka,
persentase, atau klaim yang tidak ada di prompt.

| Angka | Nilai | Sumber |
|---|---|---|
| Waktu agen menyiapkan usulan | sekitar 13 sampai 17 detik per pesan | TESTING.md, evalset Gemini 22 Okt |
| Evalset Gemini | 17/18 lulus percobaan pertama; 15/18 sampai 17/18 konsisten di 3 percobaan | TESTING.md |
| Kasus berbahaya | 7/7 ditangani benar (run terbaru) | TESTING.md |
| Engine cadangan (aturan) | 18/18, sekitar 0,4 detik | TESTING.md |
| Salah harga yang lolos ke pelanggan | 0 | TESTING.md |
| Percepatan | 40,9 menjadi 13,3 detik per pesan | TESTING.md |
| Tes otomatis | Backend 171, agen 60, frontend 23; uji E2E 23 skenario | TESTING.md |
| Link publik | Cloud Run, Tempel pesan sampai usulan 11,7 detik (sekali ukur) | TESTING.md |

**Prompt dasar** (tempel sekali di awal percakapan GPT, sebelum prompt per slide):

```
You are designing slides for a 16:9 pitch deck. Every slide uses the same template:
- Top-left: a small blue label (the page title) and, below it, one bold black sentence (the page description).
- Top-right: leave empty space for logos; do not draw any logos.
- A thin light-blue line under the header.
- Content area in the middle: white background, rounded cards (white or light grey #C9D1DC), section headers as
  blue rounded pills (#1636C9, white text), numbered items in orange rounded cards (#F7931E), orange arrows between steps.
- Optional rounded grey box near the bottom for one key sentence.
- Footer: a full-width dark-blue bar (#1636C9) with five white labels: Problem Definition, Solution,
  Marketing Opportunity, Business Model, Future Outlook. The active tab is shown as a white pill raised above the bar
  with blue text. For these slides the active tab is "Solution".
Use a clean sans-serif font (Inter or Poppins). Keep text exactly as given; do not add numbers, percentages,
logos, or claims that are not in my prompt. Leave clearly marked placeholders where I say "SCREENSHOT".
```

---

## Slide 1. User Flow

**Isi dan layout:** tiga swimlane horizontal (Customer, OmniLead Agent, Owner). Kolom kiri tiap lane berisi ikon dan
nama aktor. Delapan langkah bernomor bergerak dari kiri ke kanan dan berpindah lane mengikuti panah oranye. Satu cabang
merah kecil menunjukkan kapan agen berhenti. Kotak bawah berisi kalimat kunci.

| Bagian | Isi |
|---|---|
| Judul | User Flow |
| Deskripsi | One order from Ani: from three channels to an approved reply, with the owner in control |
| Lane atas | Customer (Ani, PT Maju Jaya): Instagram, WhatsApp, Email |
| Lane tengah | OmniLead Agent (Google ADK + Gemini on Cloud Run) |
| Lane bawah | Owner (Bu Rina): OmniLead web app |
| Kotak bawah | The agent reads, checks, and drafts. Bu Rina decides what gets sent. |

| # | Lane | Langkah | Teks kartu |
|---|---|---|---|
| 1 | Customer | ASKS | Comments on Instagram, then chats on WhatsApp and emails: "Can you do 60 portions on the 30th? Price?" |
| 2 | Agent | RECOGNIZES | Intent: quote request, 60 pax, deadline in 9 days. Three channels merged into one customer profile |
| 3 | Agent | CHECKS | Customer history, catalog price, channel reply window, lead score |
| 4 | Agent | DRAFTS | Public reply without price, private message with the total from the catalog, CRM update, follow-up |
| 5 | Agent | GUARDS | Price matches catalog, no price in public, discount within policy, no other customer data |
| 6 | Owner | DECIDES | Approve, edit, or reject. Or set agent permission: Always ask, Hybrid, or Full trust |
| 7 | Agent | SENDS | Only after approval, through the official channel API. Every action is logged |
| 8 | Customer | RECEIVES | The reply arrives; the follow-up is cancelled automatically if Ani replies first |

Cabang merah (di bawah langkah 5): "Asks for a 70% discount: no percentage promised, the owner decides." dan "Asks for
another customer's phone number: flagged for manual review." Tambahkan ikon tombol "Pause agent" di lane Owner.

**Prompt GPT:**

```
Create the "User Flow" slide using the template.
Small blue label: "User Flow".
Bold description: "One order from Ani: from three channels to an approved reply, with the owner in control".
Content: three horizontal swimlanes with an actor column on the left:
1) "Customer - Ani, PT Maju Jaya" with small Instagram, WhatsApp, and Email icons,
2) "OmniLead Agent - Google ADK + Gemini on Cloud Run",
3) "Owner - Bu Rina, OmniLead web app".
Eight numbered step cards flow left to right, moving between lanes with orange arrows:
1 ASKS (Customer): "Comments on Instagram, then chats on WhatsApp and emails: Can you do 60 portions on the 30th? Price?"
2 RECOGNIZES (Agent): "Quote request, 60 pax, deadline in 9 days. Three channels merged into one customer profile."
3 CHECKS (Agent): "Customer history, catalog price, channel reply window, lead score."
4 DRAFTS (Agent): "Public reply without price, private message with the catalog total, CRM update, follow-up."
5 GUARDS (Agent): "Price matches catalog, no price in public, discount within policy, no other customer data."
6 DECIDES (Owner): "Approve, edit, or reject. Or set agent permission: Always ask, Hybrid, Full trust."
7 SENDS (Agent): "Only after approval, through the official channel API. Every action is logged."
8 RECEIVES (Customer): "The reply arrives. The follow-up is cancelled automatically if Ani replies first."
Below step 5, a small red branch box: "70% discount request: no percentage promised, the owner decides" and
"Request for another customer's phone number: flagged for manual review."
In the Owner lane add a small "Pause agent" button icon.
Bottom grey box: "The agent reads, checks, and drafts. Bu Rina decides what gets sent."
Footer with "Solution" active.
```

---

## Slide 2. Demo

Dua versi. **Versi A** ditampilkan saat presenter pindah ke aplikasi. **Versi B** dipakai di deck yang dibaca juri, atau
sebagai cadangan bila demo live gangguan.

### Versi A: sampul demo live

| Bagian | Isi |
|---|---|
| Judul | Demo |
| Deskripsi | From scattered chats to an approved reply, live |
| Isi | Tulisan besar "Live Demo" di tengah. Di bawahnya: QR ke link juri, link `omnilead-fgbrqs2gfq-et.a.run.app`, dan "Judge account: juri@omnilead.id" (kata sandi hanya di form submission) |
| Kotak bawah | We will follow Ani's order from the first message to an approved reply. Customer data is sample data. |

**Prompt GPT:**

```
Create the "Demo" cover slide using the template.
Small blue label: "Demo". Bold description: "From scattered chats to an approved reply, live".
Content: a large centered title "Live Demo". Below it, three small items in a row:
a QR code placeholder labeled "Scan to try", the link text "omnilead-fgbrqs2gfq-et.a.run.app",
and the text "Judge account: juri@omnilead.id".
Bottom grey box: "We will follow Ani's order from the first message to an approved reply. Customer data is sample data."
Footer with "Solution" active. Do not show any password.
```

### Versi B: isi demo

**Isi dan layout:** dua kolom. Kiri sekitar 60%: pil biru "Inside the app", bingkai laptop berisi SCREENSHOT Workspace,
dan mockup HP kecil di sudut kanan bawah berisi SCREENSHOT kartu usulan agen. Kanan sekitar 40%: pil biru "Demo flow",
lima kartu oranye bernomor.

| Bagian | Isi |
|---|---|
| Judul | Demo |
| Deskripsi | From scattered chats to an approved reply |
| Kotak bawah | The agent prepares everything in about 13 to 17 seconds. The owner decides what gets sent. Customer data is sample data; channels not yet connected use Paste message and Copy & open. |

| # | Kartu oranye | Keterangan |
|---|---|---|
| 1 | One screen for four channels | Ani's Instagram comment, WhatsApp chat, and email become one profile |
| 2 | What matters rises to the top | 60 pax for an office event, due in 9 days: high priority, with the reason shown |
| 3 | The agent works in the open | History, catalog, reply window, lead score, then the proposal |
| 4 | Drafted from the catalog, checked by Guard | Public reply without price, private message with the catalog total |
| 5 | The owner stays in control | Approve or edit, set agent permission, pause the agent |

Bila uji kanal nyata berhasil sebelum 15.00, ganti kalimat kotak bawah kedua dengan kanal yang benar-benar diuji, misalnya
"Gmail is connected to a real account."

**Screenshot yang diambil dari link juri (akun demo):** Workspace di layar 1440 px (pesan dari 4 kanal, prioritas tinggi
di atas) dan detail pesan di HP 390 px (kartu usulan dengan tombol Approve dan Edit). Jangan tampilkan URL OAuth, token,
kata sandi, atau email asli.

**Prompt GPT:**

```
Create the "Demo" content slide using the template.
Small blue label: "Demo". Bold description: "From scattered chats to an approved reply".
Content in two columns.
Left column (about 60% width): a blue pill header "Inside the app", a laptop frame containing a placeholder
"SCREENSHOT: Workspace", and a small phone mockup overlapping its bottom-right corner containing a placeholder
"SCREENSHOT: Agent proposal with Approve and Edit".
Right column (about 40% width): a blue pill header "Demo flow" and five numbered orange cards, each with a bold
title and one line of text:
1 "One screen for four channels" - "Ani's Instagram comment, WhatsApp chat, and email become one profile."
2 "What matters rises to the top" - "60 pax for an office event, due in 9 days: high priority, with the reason shown."
3 "The agent works in the open" - "History, catalog, reply window, lead score, then the proposal."
4 "Drafted from the catalog, checked by Guard" - "Public reply without price, private message with the catalog total."
5 "The owner stays in control" - "Approve or edit, set agent permission, pause the agent."
Bottom grey box: "The agent prepares everything in about 13 to 17 seconds. The owner decides what gets sent.
Customer data is sample data; channels not yet connected use Paste message and Copy & open."
Footer with "Solution" active.
```

---

## Slide 3. Agentic Architecture

**Isi dan layout:** kiri sekitar 60%: diagram alur agen tiga kolom (Input, Agent pipeline, Output) dengan panah. Kanan
sekitar 40%: dua kartu komponen kunci dengan ruang SCREENSHOT kecil. Bawah: tiga kartu angka dengan judul pil biru.

| Bagian | Isi |
|---|---|
| Judul | Agentic Architecture |
| Deskripsi | The agent plans and uses real tools, but it never holds the send button |

**Diagram alur agen (kiri):**

| Kolom | Isi |
|---|---|
| Input | WhatsApp (webhook), Instagram (webhook), Facebook (webhook), Gmail (poll), Paste message |
| Agent pipeline (Cloud Run) | 1 Triage: intent, urgency, entities, risk (Gemini 3.5 Flash-Lite + rules). 2 Identity: one profile across channels, with evidence. 3 Orchestrator (Google ADK + Gemini 3.8 Flash): calls tools for history, catalog and FAQ, reply window, lead score, then proposes. 4 Guard: hard rules outside the model for price, discount, other customers' data, prompt injection, reply window |
| Output (backend) | Approval queue with agent permission (Always ask, Hybrid, Full trust). Executor: the only part that can send. CRM, audit log, follow-up |
| Catatan di bawah diagram | Business knowledge per business and per channel (catalog, FAQ, tone). Tokens in Secret Manager |

**Kartu kanan:**

| Kartu | Judul | Isi | Gambar |
|---|---|---|---|
| 1 | Google ADK + Gemini | The orchestrator chooses its own tools and drafts proposals. If the model fails, a safe template takes over. | SCREENSHOT: Agent activity |
| 2 | Guard + owner permission | Drafts that break a rule are revised or held. Anything flagged by Guard always waits for a person. | SCREENSHOT: Proposal with Guard checks |

**Tiga kartu bawah:**

| Kartu | Isi |
|---|---|
| Agentic, not a chatbot | 3 agent roles; up to 8 tool steps per message; agent permission set by the owner; pause stops everything |
| Fast without losing quality | From 40.9 to 13.3 seconds per message after tuning; 17/18 cases pass on the first try |
| Safe by design | 0 wrong prices reached a customer; 7/7 dangerous cases handled; encrypted tokens per business; every action logged |

**Prompt GPT:**

```
Create the "Agentic Architecture" slide using the template.
Small blue label: "Agentic Architecture". Bold description: "The agent plans and uses real tools, but it never holds the send button".
Content.
Left (about 60% width): a flow diagram in three columns connected by arrows.
Column "Input": WhatsApp (webhook), Instagram (webhook), Facebook (webhook), Gmail (poll), Paste message.
Column "Agent pipeline - Cloud Run", four stacked numbered boxes:
1 "Triage" - "Intent, urgency, entities, risk (Gemini 3.5 Flash-Lite + rules)".
2 "Identity" - "One customer profile across channels, with evidence".
3 "Orchestrator - Google ADK + Gemini 3.8 Flash" - "Calls tools: history, catalog and FAQ, reply window, lead score; then proposes".
4 "Guard" - "Hard rules outside the model: price, discount, other customers' data, prompt injection, reply window".
Column "Output - Backend": "Approval queue with agent permission (Always ask, Hybrid, Full trust)",
"Executor - the only part that can send", "CRM, audit log, follow-up".
Under the diagram, a thin note: "Business knowledge per business and channel (catalog, FAQ, tone). Tokens in Secret Manager."
Right (about 40% width): two cards with a small image placeholder each:
"Google ADK + Gemini" - "The orchestrator chooses its own tools and drafts proposals. If the model fails, a safe template takes over." (placeholder "SCREENSHOT: Agent activity")
"Guard + owner permission" - "Drafts that break a rule are revised or held. Anything flagged by Guard always waits for a person." (placeholder "SCREENSHOT: Proposal with Guard checks")
Bottom: three cards with blue pill titles:
"Agentic, not a chatbot" - "3 agent roles. Up to 8 tool steps per message. Agent permission set by the owner. Pause stops everything."
"Fast without losing quality" - "From 40.9 to 13.3 seconds per message after tuning. 17/18 cases pass on the first try."
"Safe by design" - "0 wrong prices reached a customer. 7/7 dangerous cases handled. Encrypted tokens per business. Every action logged."
Footer with "Solution" active.
```

---

## Slide 4. Prototype Report

**Isi dan layout:** panel 01 selebar halaman (tabel evalset). Di bawahnya dua panel berdampingan: 02 (latensi dan
ketahanan, dengan ikon) dan 03 (matriks pembanding, kolom OmniLead disorot). Kotak bawah berisi kalimat kunci.

| Bagian | Isi |
|---|---|
| Judul | Prototype Report |
| Deskripsi | Tested where an AI agent is most likely to fail |
| Kotak bawah | When Gemini got a case wrong, Guard and the owner were still between the draft and the customer. |

**Panel 01. Agent evaluation: 18 cases x 3 tries, including negative cases**

| Area | Method | Result | Why it matters |
|---|---|---|---|
| Buyer questions | 6 cases: price, minimum order, delivery area, office quote | Passed on first try; some answers vary between tries | Answers come from the catalog |
| Complaints | 3 cases: complaint plus order in one message | 3/3 | Upset customers are handled first |
| Safety (negative) | Prompt injection, other customers' data, 70% discount | 3/3 in the latest run | The agent cannot be talked into breaking policy |
| Platform limits | Closed 24-hour reply window | 2/2 held | The business account stays within Meta rules |
| Spam and informal language | Spam, "brp harga nasbox 30 org" | 4/4 | Real UMKM chat language |
| Consistency (pass^3) | Same case run 3 times | Gemini 15/18 to 17/18 across two runs; rules engine 18/18 | Variation is reported, not hidden |

**Panel 02. Latency and resilience**

| Scenario | Measured |
|---|---|
| Message to proposal (Gemini) | about 13 to 17 seconds per message |
| Message to proposal (rules backup) | about 0.4 seconds |
| Paste message to proposal on the public link | 11.7 seconds (one measurement) |
| Model failure | Falls back to a safe template, still checked by Guard |
| Automated tests | Backend 171, agent 60, frontend 23; end-to-end 23 scenarios |

**Panel 03. Comparison**

| Capability | Basic auto-reply | Meta Business Agent | Mekari Qontak | OmniLead |
|---|---|---|---|---|
| Channels | One | WhatsApp, Instagram, Messenger | WhatsApp, Instagram, email, marketplace | WhatsApp, Instagram, Facebook, email |
| Who sends | Bot directly | Autonomous agent | Chatbot and reply suggestions; no explicit approval queue | Owner approval or owner-set permission |
| One profile across channels | No | No email | Not explicit | Yes, with merge evidence |
| Price guarded by catalog | No | Not stated | Not stated | Guard holds off-catalog prices |
| Starting price | Free or low | Free (for now) | About Rp750k per month | Rp149k to 299k per month (assumption) |

Isi kolom pesaing hanya yang tercantum di sumber (PRD bagian Diferensiasi); selebihnya ditulis "Not stated".

**Prompt GPT:**

```
Create the "Prototype Report" slide using the template.
Small blue label: "Prototype Report". Bold description: "Tested where an AI agent is most likely to fail".
Content in three panels with numbered blue badges.
Panel "01 Agent evaluation: 18 cases x 3 tries, including negative cases" (full width), a table with columns
Area | Method | Result | Why it matters, and rows:
Buyer questions | 6 cases: price, minimum order, delivery area, office quote | Passed on first try; some answers vary between tries | Answers come from the catalog
Complaints | 3 cases: complaint plus order in one message | 3/3 | Upset customers are handled first
Safety (negative) | Prompt injection, other customers' data, 70% discount | 3/3 in the latest run | The agent cannot be talked into breaking policy
Platform limits | Closed 24-hour reply window | 2/2 held | The business account stays within Meta rules
Spam and informal language | Spam, "brp harga nasbox 30 org" | 4/4 | Real UMKM chat language
Consistency (pass^3) | Same case run 3 times | Gemini 15/18 to 17/18 across two runs; rules engine 18/18 | Variation is reported, not hidden
Panel "02 Latency and resilience" (bottom left), rows with small icons:
Message to proposal (Gemini): about 13 to 17 seconds per message
Message to proposal (rules backup): about 0.4 seconds
Paste message to proposal on the public link: 11.7 seconds (one measurement)
Model failure: falls back to a safe template, still checked by Guard
Automated tests: Backend 171, agent 60, frontend 23; end-to-end 23 scenarios
Panel "03 Comparison" (bottom right), a matrix with the OmniLead column highlighted in light green, columns
Capability | Basic auto-reply | Meta Business Agent | Mekari Qontak | OmniLead, rows:
Channels | One | WhatsApp, Instagram, Messenger | WhatsApp, Instagram, email, marketplace | WhatsApp, Instagram, Facebook, email
Who sends | Bot directly | Autonomous agent | Chatbot and reply suggestions; no explicit approval queue | Owner approval or owner-set permission
One profile across channels | No | No email | Not explicit | Yes, with merge evidence
Price guarded by catalog | No | Not stated | Not stated | Guard holds off-catalog prices
Starting price | Free or low | Free (for now) | About Rp750k per month | Rp149k to 299k per month (assumption)
Bottom grey box: "When Gemini got a case wrong, Guard and the owner were still between the draft and the customer."
Footer with "Solution" active.
```

---

## Checklist sebelum dipakai

- [ ] Setiap slide punya judul (label kecil), deskripsi (kalimat tebal), isi, dan footbar dengan tab Solution aktif.
- [ ] Angka di slide sama persis dengan tabel "Aturan angka"; tidak ada angka tambahan dari GPT.
- [ ] "Assumption" tetap tertulis pada harga OmniLead.
- [ ] Logo disisipkan manual di kanan atas; screenshot asli menggantikan placeholder.
- [ ] Tidak ada URL OAuth, token, kata sandi, atau email asli di screenshot.
- [ ] Bila kanal nyata sudah diuji sebelum 15.00, perbarui kotak bawah slide Demo dan baris di Prototype Report.

## Catatan untuk slide Value Proposition (di luar bagian ini)

| Bagian | Saat ini | Saran |
|---|---|---|
| Sales Channel | WhatsApp, Email, Instagram | Tambahkan **Facebook** (kanal MVP ke-4) |
| Why OmniLead Is Different | "United user context" | "Unified customer context" |
| Why OmniLead Is Different | "OmniLead is a tools, not to change business" | "OmniLead fits how you already sell" |
| Revenue Ranges | Rp500 juta sampai 5 miliar | Beri sumber atau tulis "assumption" |
| The Core Flow, Seller Review | Sellers review, edit, approve | Tambahkan "or set agent permission" |
