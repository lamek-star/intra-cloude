# ADR-0006: Deployment Orchestration — Docker Compose First, Kubernetes Deferred

Status: Accepted
Date: 2026-08-07

## Decision

Use Docker Compose as the deployment orchestration mechanism through at
least Phase 11. Kubernetes is not adopted unless a concrete, documented
requirement (multi-node scheduling, workload isolation at a scale Compose
cannot reasonably handle) forces it, per Section 3's explicit instruction
not to introduce Kubernetes "merely for complexity or prestige."

## Context

The target deployment is a single self-hosted server (or small number of
servers) on private infrastructure, not a large multi-tenant SaaS fleet.

## Alternatives Considered

1. Kubernetes from the start (kubeadm/k3s or managed).
2. Bare-metal systemd units with no containerization.
3. (Chosen) Docker Compose, with persistent volumes, internal networks, and
   a reverse proxy, matching Section 3 and Section 23.

## Advantages

- Matches the actual deployment target (single private server/small
  cluster) without operational overhead disproportionate to that scale.
- Lower operational learning curve for the organizations this product
  targets (self-hosting without a dedicated platform team).
- Still provides isolated networks, persistent volumes, and declarative
  service definition — the properties that actually matter for this
  product's security model (Section 17).

## Disadvantages

- No built-in multi-node scheduling, rolling deployment orchestration, or
  autoscaling — acceptable trade-off at target scale; would need
  revisiting if the product needed to run across many nodes.
- Some manual work for zero-downtime deploys compared to Kubernetes-native
  patterns.

## Security Considerations

- Docker socket is never mounted into any container that doesn't
  absolutely require it, and never exposed to the public network
  (Section 17 explicitly lists the Docker socket as never-expose).
- Internal Docker networks separate data-plane services from anything
  internet-facing, per the network architecture in ARCHITECTURE.md.

## Operational Considerations

- Backup, monitoring, and restart policies are all achievable with Compose
  + host-level tooling (cron, systemd) at this scale.
- Future Kubernetes migration, if ever justified, would be a distinct,
  separately-decided project phase, not a Phase 0–11 deliverable.

## Final Recommendation

Docker Compose for all phases in this roadmap. Kubernetes remains
explicitly out of scope unless a future ADR documents a concrete forcing
requirement.
