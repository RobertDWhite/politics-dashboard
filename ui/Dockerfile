FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
ARG VITE_NITTER_EMBED_BASE=""
ENV VITE_NITTER_EMBED_BASE=$VITE_NITTER_EMBED_BASE
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine
# nginx-unprivileged runs envsubst over /etc/nginx/templates/*.template at start.
COPY --from=builder /app/dist /usr/share/nginx/html
COPY default.conf.template /etc/nginx/templates/default.conf.template
ENV API_UPSTREAM=http://api:8000 \
    NGINX_RESOLVER="127.0.0.11 8.8.8.8"
EXPOSE 8080
