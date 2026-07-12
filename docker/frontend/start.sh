#!/usr/bin/env sh
#
# Task Manager frontend entrypoint.
#
# Add init steps here as the app grows (e.g. runtime config injection
# into the built bundle, nginx vhost templating from env vars, asset
# precompression). Today the frontend has nothing to bootstrap — the
# CRA dev server and the nginx static-file image are both ready to
# run as-is — so this script is a pure pass-through.

set -eu

# ----------------------------------------------------------------------------
# 1. (placeholder) runtime config injection
# ----------------------------------------------------------------------------


# ----------------------------------------------------------------------------
# 2. (placeholder) asset preprocessing
# ----------------------------------------------------------------------------


# ----------------------------------------------------------------------------
# 3. Hand off to the actual command (bun run start, nginx, …).
# ----------------------------------------------------------------------------
exec "$@"
