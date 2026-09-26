# The standalone "spare parts reference application" (a separate Next.js project) packaged as one more container of the shop stack.
# Built by scripts/shop-kit/build-shop-kit.sh from a COPY of that project's working tree (never from the project itself, and never
# with its .env* files: no secrets belong in an installer). Production build; at run time it needs no internet.
FROM node:24-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# next/image is not used by this app, so the native image library (sharp/libvips) is not shipped (IntraForge policy).
RUN npm run build && npm prune --omit=dev --no-audit --no-fund && rm -rf node_modules/@img

FROM node:24-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
COPY --from=build --chown=node:node /app/package.json ./package.json
COPY --from=build --chown=node:node /app/next.config.ts ./next.config.ts
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/.next ./.next
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "node_modules/next/dist/bin/next", "start", "--hostname", "0.0.0.0", "--port", "3000"]
