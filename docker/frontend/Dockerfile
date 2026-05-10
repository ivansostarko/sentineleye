# syntax=docker/dockerfile:1.7

# ---- Build stage ---------------------------------------------------------
FROM ghcr.io/cirruslabs/flutter:stable AS build

USER root
WORKDIR /build

COPY apps/frontend/ ./

# Same-origin runtime config: nginx proxies /api and /ws to the backend,
# so the bundled app issues relative URLs.
RUN printf '{"apiBaseUrl":"","wsBaseUrl":""}' > assets/config.json

RUN flutter pub get \
 && flutter build web --release

# ---- Runtime stage -------------------------------------------------------
FROM nginx:alpine

COPY --from=build /build/build/web /usr/share/nginx/html
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
