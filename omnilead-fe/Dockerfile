# Cloud Run: omnilead-fe. URL backend dan key dibaca server saat runtime.
# Belum diuji build di mesin pengembang (Docker daemon tidak aktif).
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production PORT=8080
COPY --from=build /app ./
EXPOSE 8080
CMD ["sh", "-c", "npx next start -p ${PORT}"]
