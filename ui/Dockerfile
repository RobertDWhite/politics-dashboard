FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
ARG VITE_NITTER_EMBED_BASE=""
ENV VITE_NITTER_EMBED_BASE=$VITE_NITTER_EMBED_BASE
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
