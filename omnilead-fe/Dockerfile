# Cloud Run: omnilead-fe. URL backend dibaca server saat runtime (OMNILEAD_BACKEND_URL).
# Dependensi dipasang dengan bun sesuai bun.lock (package-lock.json tidak dipakai tim).
FROM oven/bun:1.3 AS build
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN bun run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production PORT=8080 NEXT_TELEMETRY_DISABLED=1
COPY --from=build /app ./
EXPOSE 8080
CMD ["sh", "-c", "node node_modules/next/dist/bin/next start -p ${PORT}"]
