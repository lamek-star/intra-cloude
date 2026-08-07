# Docker Build Contexts

The backend and frontend each own their `Dockerfile` and `.dockerignore`
directly (`apps/backend/Dockerfile`, `apps/frontend/Dockerfile`) since
`docker-compose.yml` builds each with its own directory as build context —
keeping a Dockerfile next to the code it packages avoids an extra layer of
indirection for what are, so far, two independent single-stage-per-service
builds.

This directory is reserved for infrastructure that's genuinely shared
across build contexts (e.g. a common base image, if one becomes justified)
— nothing here yet, and nothing should be added here speculatively.
