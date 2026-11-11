# The Spare Parts application (a separate Next.js project) as an IntraForge service application (ADR-0018).
# Built by scripts/shop-kit/build-spareparts-image.sh from `git archive` of a committed revision of that project -- never from
# a working tree, so no .env*, data or local build output can reach the image. Production build; at run time it needs no
# internet. It is served by the IntraForge proxy under /apps/spare-parts/ and keeps its data, files, identity, audit and
# configuration in IntraForge; it has no port of its own on the host.
FROM node:24-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_BASE_PATH=/apps/spare-parts
ENV NEXT_PUBLIC_BASE_PATH=${NEXT_PUBLIC_BASE_PATH}
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# next/image is not used by this app, so the native image library (sharp/libvips) is not shipped (IntraForge policy).
# The one-off standalone -> IntraForge data migration tool, bundled to plain JavaScript (the runtime has no TypeScript runner).
RUN npm run build \
 && npx esbuild scripts/migrate-to-intraforge.mts --bundle --platform=node --format=esm --target=node24 \
      --packages=external --outfile=dist/migrate-to-intraforge.mjs \
 && npm prune --omit=dev --no-audit --no-fund && rm -rf node_modules/@img

FROM node:24-alpine
WORKDIR /app
ARG SPAREPARTS_VERSION=dev
ARG NEXT_PUBLIC_BASE_PATH=/apps/spare-parts
# next.config.ts is evaluated again by `next start`: the base path must be the same at run time as at build time.
ENV NEXT_PUBLIC_BASE_PATH=${NEXT_PUBLIC_BASE_PATH}
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0 \
    SPAREPARTS_MODE=platform \
    SPAREPARTS_VERSION=${SPAREPARTS_VERSION} \
    INTRAFORGE_INTERNAL_URL=http://backend:8000 \
    SPAREPARTS_PG_HOST=postgres-tenant \
    SPAREPARTS_PG_PORT=5432
# INTRAFORGE_SERVICE_TOKEN, SPAREPARTS_PG_PASSWORD and SPAREPARTS_PG_DATABASE come from the installation at run time.
COPY --from=build --chown=node:node /app/package.json ./package.json
COPY --from=build --chown=node:node /app/next.config.ts ./next.config.ts
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/.next ./.next
COPY --from=build --chown=node:node /app/public ./public
COPY --from=build --chown=node:node /app/dist ./dist
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:3000/apps/spare-parts/api/v1/health || exit 1
CMD ["node", "node_modules/next/dist/bin/next", "start", "--hostname", "0.0.0.0", "--port", "3000"]
