---
title: Deploy OmniLead ke Google Cloud
updated: 2026-10-21
---

# Deploy OmniLead ke Google Cloud

**Status:** perintah di bawah belum dijalankan terhadap project GCP sungguhan dan Dockerfile belum
diuji build (Docker daemon tidak aktif di mesin pengembang). Perlakukan sebagai titik awal, lalu
perbaiki saat dijalankan pertama kali.

Tiga service Cloud Run, `min-instances=0`, region `asia-southeast2` (atau sesuai arahan panitia):

| Service | Folder | Peran |
|---|---|---|
| `omnilead-agent` | `omnilead-agent/` | Triage, orchestrator, guard. Hanya dipanggil BE. |
| `omnilead-api` | `omnilead-be/` | REST untuk FE, webhook, executor, scheduler endpoint. |
| `omnilead-fe` | `omnilead-fe/` | UI. |

## 1. Persiapan

```bash
export PROJECT=<id-project>  REGION=asia-southeast2
gcloud config set project $PROJECT
gcloud services enable run.googleapis.com firestore.googleapis.com secretmanager.googleapis.com \
  pubsub.googleapis.com cloudscheduler.googleapis.com gmail.googleapis.com aiplatform.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com
gcloud firestore databases create --location=$REGION --type=firestore-native
```

Pasang **budget alert** di Billing sebelum lanjut. Matikan resource yang tidak perlu setelah freeze.

## 2. Secret Manager

Token tidak pernah masuk repo, deck, atau rekaman. Buat satu secret per nilai:

```bash
for s in omnilead-api-key omnilead-agent-key meta-app-secret meta-verify-token whatsapp-access-token \
         gmail-client-secret gmail-refresh-token gmail-push-token scheduler-token instagram-access-token; do
  gcloud secrets create $s --replication-policy=automatic
done
printf '%s' "<nilai>" | gcloud secrets versions add omnilead-api-key --data-file=-
```

Service account `omnilead-run@$PROJECT.iam.gserviceaccount.com` dengan peran minimal:
`roles/datastore.user`, `roles/secretmanager.secretAccessor`, `roles/aiplatform.user` (hanya untuk agen).

## 3. Agen

```bash
gcloud run deploy omnilead-agent --source omnilead-agent --region $REGION \
  --service-account omnilead-run@$PROJECT.iam.gserviceaccount.com \
  --allow-unauthenticated --min-instances 0 \
  --set-env-vars OMNILEAD_AGENT_ENGINE=adk,GOOGLE_GENAI_USE_VERTEXAI=1,GOOGLE_CLOUD_PROJECT=$PROJECT,GOOGLE_CLOUD_LOCATION=$REGION \
  --set-secrets OMNILEAD_AGENT_API_KEY=omnilead-agent-key:latest
```

`--allow-unauthenticated` karena BE memanggil agen dengan header `X-API-Key` (autentikasi aplikasi, bukan
identitas Google); `OMNILEAD_AGENT_API_KEY` wajib terisi di produksi. Agen tidak punya jalur kirim ke platform
dan tidak memegang token platform.

Uji tanpa LLM dulu: `OMNILEAD_AGENT_ENGINE=rule` (default). Cek ID model di konsol Vertex sebelum demo
(`OMNILEAD_AGENT_MODEL`, `OMNILEAD_AGENT_TRIAGE_MODEL`).

## 4. API (BE)

```bash
AGENT_URL=$(gcloud run services describe omnilead-agent --region $REGION --format 'value(status.url)')
gcloud run deploy omnilead-api --source omnilead-be --region $REGION \
  --service-account omnilead-run@$PROJECT.iam.gserviceaccount.com --allow-unauthenticated \
  --set-env-vars OMNILEAD_STORE=firestore,OMNILEAD_FIRESTORE_PROJECT=$PROJECT,OMNILEAD_AGENT_URL=$AGENT_URL,\
OMNILEAD_CORS_ORIGINS='["https://<url-fe>"]' \
  --set-secrets OMNILEAD_API_KEY=omnilead-api-key:latest,OMNILEAD_AGENT_API_KEY=omnilead-agent-key:latest,\
OMNILEAD_META_APP_SECRET=meta-app-secret:latest,OMNILEAD_META_VERIFY_TOKEN=meta-verify-token:latest,\
OMNILEAD_WHATSAPP_ACCESS_TOKEN=whatsapp-access-token:latest,OMNILEAD_SCHEDULER_TOKEN=scheduler-token:latest,\
OMNILEAD_GMAIL_CLIENT_SECRET=gmail-client-secret:latest,OMNILEAD_GMAIL_REFRESH_TOKEN=gmail-refresh-token:latest,\
OMNILEAD_GMAIL_PUSH_TOKEN=gmail-push-token:latest,OMNILEAD_INSTAGRAM_ACCESS_TOKEN=instagram-access-token:latest
```

`--allow-unauthenticated` diperlukan karena webhook Meta dan push Pub/Sub tidak membawa identitas Google.
Perlindungan ada di aplikasi: API key untuk FE, signature `X-Hub-Signature-256` untuk Meta, token di query
untuk push Gmail, dan token Bearer untuk Scheduler. Peningkatan produksi: tutup agen dari publik dan pakai
token OIDC antar-service (belum diimplementasikan; saat ini `X-API-Key`).

Isi juga `OMNILEAD_WHATSAPP_PHONE_NUMBER_ID`, `OMNILEAD_INSTAGRAM_USER_ID`, `OMNILEAD_GMAIL_CLIENT_ID`,
`OMNILEAD_GMAIL_PUBSUB_TOPIC` (nilai non-rahasia, lewat `--set-env-vars`).

## 5. Webhook dan Gmail

- **Meta (WhatsApp)**: callback `https://<api>/webhooks/whatsapp`, verify token = `meta-verify-token`.
- **Meta (Instagram)**: callback `https://<api>/webhooks/instagram`, langganan `comments` dan `messages`.
- **Gmail push**: topic Pub/Sub, beri `gmail-api-push@system.gserviceaccount.com` peran Publisher, lalu subscription
  push ke `https://<api>/webhooks/gmail?token=<gmail-push-token>`. `watch` berlaku 7 hari; perpanjang harian (langkah 6).
  Cadangan bila push macet: job polling (langkah 6).
- Refresh token Gmail mode Testing berlaku ±7 hari: ulangi OAuth tiap pagi hari demo.

## 6. Cloud Scheduler

```bash
API=$(gcloud run services describe omnilead-api --region $REGION --format 'value(status.url)')
TOKEN=$(gcloud secrets versions access latest --secret scheduler-token)
gcloud scheduler jobs create http omnilead-followups --location $REGION --schedule "*/30 * * * *" \
  --uri "$API/scheduler/followups" --http-method POST --headers "Authorization=Bearer $TOKEN"
gcloud scheduler jobs create http omnilead-gmail-watch --location $REGION --schedule "0 3 * * *" \
  --uri "$API/scheduler/gmail-watch" --http-method POST --headers "Authorization=Bearer $TOKEN"
gcloud scheduler jobs create http omnilead-gmail-poll --location $REGION --schedule "* * * * *" \
  --uri "$API/scheduler/gmail-poll" --http-method POST --headers "Authorization=Bearer $TOKEN"
```

Alternatif OIDC: isi `OMNILEAD_SCHEDULER_OIDC_AUDIENCE` dengan URL API dan buat job dengan `--oidc-service-account-email`.

## 7. FE

```bash
gcloud builds submit omnilead-fe --tag $REGION-docker.pkg.dev/$PROJECT/cloud-run-source-deploy/omnilead-fe \
  --substitutions=_API_URL=$API   # atau: docker build --build-arg NEXT_PUBLIC_API_URL=$API
gcloud run deploy omnilead-fe --image <image> --region $REGION --allow-unauthenticated
```

`NEXT_PUBLIC_API_KEY` ikut ke bundle browser. Untuk produksi, lewatkan API key lewat proxy server-side
(Next.js route handler), jangan di bundle.

## 8. Data demo dan freeze

- Reset seed: jalankan `python -m omnilead.seed` dengan `OMNILEAD_STORE=firestore` terhadap project demo.
- Checklist pagi hari demo ada di PRD (pemanasan WA/IG, login ulang Gmail, Pause mati, seed direset).
- `v1.0-freeze`: tag git, lalu matikan resource yang tidak perlu (Scheduler, instance, Pub/Sub).
