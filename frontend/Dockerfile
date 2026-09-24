# syntax=docker/dockerfile:1.7
#
# Task Manager frontend — multi-stage build (bun).
#
# Stages:
#   1. deps    — installs node_modules with `bun install` + cache mount
#   2. dev     — adds source for the CRA dev server (hot reload)
#   3. build   — produces a hashed production CRA bundle
#   4. runtime — nginx serving the static bundle + /api proxy
#
# Auxiliary files (start.sh, nginx.conf) live under `docker/frontend/`
# and `docker/nginx/` and are pulled in via Compose `additional_contexts`:
#
#   build:
#     context: ./frontend
#     additional_contexts:
#       infra: ./docker/frontend
#       nginx: ./docker/nginx
#
# Bun is used for installs and to drive `bun run start` / `bun run build`.
# react-scripts (CRA) is invoked through bun's node-compatible runtime —
# no code changes required in package.json.

# ----------------------------------------------------------------------------
# 1. deps — install node_modules once, cached by package.json hash
# ----------------------------------------------------------------------------
FROM oven/bun:1.4.2-alpine AS deps

WORKDIR /app

# Copy lockfiles first to maximize layer cache reuse. Both bun.lockb
# (binary) and package-lock.json are accepted — bun reads either.
COPY package.json bun.lockb* package-lock.json* ./

# BuildKit cache mount keeps the bun install cache around between builds.
RUN --mount=type=cache,target=/root/.bun/install/cache \
    bun install --frozen-lockfile || bun install


# ----------------------------------------------------------------------------
# 2. dev — used by docker-compose.yml for the CRA dev server
# ----------------------------------------------------------------------------
FROM deps AS dev

COPY . .

# CRA reads `.env` (and `.env.local`, etc.) at build time. We pick the
# right env file based on the APP_ENV build arg, default `dev`.
ARG APP_ENV=dev
ENV APP_ENV=${APP_ENV}
RUN cp .env.${APP_ENV} .env

# Pull start.sh from the named `infra` context (./docker/frontend).
COPY --from=infra start.sh /app/start.sh
RUN chmod +x /app/start.sh

ENV CHOKIDAR_USEPOLLING=true \
    WATCHPACK_POLLING=true
EXPOSE 3000
ENTRYPOINT ["/app/start.sh"]
CMD ["bun", "run", "start"]


# ----------------------------------------------------------------------------
# 3. build — compile a production bundle (no dev server, no source maps)
# ----------------------------------------------------------------------------
FROM deps AS build

COPY . .

# Same env-file selection as the dev stage. CRA picks env vars from
# `.env`, but `REACT_APP_API_URL` from the build arg below still wins
# (process.env > .env file), so the prod compose can override at deploy
# time without rebuilding the file layer.
ARG APP_ENV=prod
ENV APP_ENV=${APP_ENV}
RUN cp .env.${APP_ENV} .env

ARG REACT_APP_API_URL
# Biome (not CRA's bundled ESLint) owns lint — enforced in CI quality gate.
# CRA 5's eslint-webpack-plugin fails to resolve its rules under the modern
# Bun/Node toolchain, so it is disabled for the production build.
ENV REACT_APP_API_URL=${REACT_APP_API_URL:-} \
    GENERATE_SOURCEMAP=false \
    INLINE_RUNTIME_CHUNK=false \
    DISABLE_ESLINT_PLUGIN=true

RUN bun run build


# ----------------------------------------------------------------------------
# 4. runtime — nginx serving the bundle (production)
# ----------------------------------------------------------------------------
FROM nginx:1.29-alpine AS runtime

# Replace the default vhost with the SPA + /api proxy config from
# the `nginx` named context (./docker/nginx).
RUN rm /etc/nginx/conf.d/default.conf
COPY --from=nginx nginx.conf /etc/nginx/conf.d/default.conf

# Pull start.sh from the `infra` context too, even though today it's
# a no-op pass-through. Having an entrypoint in place makes future
# init steps (runtime config injection, vhost templating) trivial.
COPY --from=infra start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

COPY --from=build /app/build /usr/share/nginx/html

# Run nginx as non-root.
RUN touch /var/run/nginx.pid \
    && chown -R nginx:nginx /var/cache/nginx /var/run/nginx.pid /usr/share/nginx/html

USER nginx
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD wget --quiet --spider http://127.0.0.1:8080/ || exit 1

ENTRYPOINT ["/usr/local/bin/start.sh"]
CMD ["nginx", "-g", "daemon off;"]
