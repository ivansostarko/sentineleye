# Deployment

## Compose (single host)

The provided `docker-compose.yml` is suitable for a single host with up to ~20 cameras.
Pre-flight checklist:

- Set a strong `SECRET_KEY` (≥ 32 random chars).
- Set a strong `BACKEND_SERVICE_TOKEN` (separate from `SECRET_KEY`).
- Override `S3_ACCESS_KEY` / `S3_SECRET_KEY` if exposing MinIO outside the host.
- Put the host behind a reverse proxy (Caddy/Nginx) terminating TLS.
- Restrict `CORS_ORIGINS` to your real frontend origin(s).
- Schedule off-host backups of the `postgres-data` volume.

### Reverse proxy (Caddy example)

```caddy
api.example.com {
    reverse_proxy localhost:8000
}

cctv.example.com {
    reverse_proxy localhost:8080  # Flutter web build, served separately
}
```

## Kubernetes (multi-host)

Container images map 1:1 to Deployments. Recommendations:

- **backend**: Deployment with `replicas: ≥ 2`. Sticky-session (or session-affinity) on
  the Ingress for `/api/v1/ws/*` paths because WS connections are long-lived.
- **backend-worker**: Deployment with `replicas: 1` (Celery beat must be a singleton).
  Run additional plain `worker` Deployments for throughput.
- **ai-engine**: one Deployment per camera shard. Use a GPU node pool with
  `nvidia.com/gpu: 1` requests and `runtimeClassName: nvidia`.
- **recording-service**: StatefulSet if you bind PVCs per pod, or Deployment with a
  shared RWX PVC. Partition cameras across replicas (consistent hash).
- **notification-service**: Deployment with `replicas: ≥ 2`.
- **postgres**: managed (RDS / CloudSQL) or operator-driven (CrunchyData / Zalando).
- **redis**: managed or `bitnami/redis-cluster` chart.
- **MinIO**: only for self-hosted; in cloud, use S3 directly.

## GPU setup

1. Install the NVIDIA driver on the host.
2. Install the NVIDIA Container Toolkit:
   ```bash
   sudo apt install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```
3. In `docker-compose.yml`, override the `ai-engine` service:
   ```yaml
   ai-engine:
     deploy:
       resources:
         reservations:
           devices:
             - driver: nvidia
               count: 1
               capabilities: [gpu]
     environment:
       ENABLE_GPU: "true"
       YOLO_DEVICE: "cuda:0"
   ```
4. Use a CUDA base image (see comment in `docker/ai-engine/Dockerfile`) and a
   matching `torch` wheel.

## Storage sizing

A rough rule-of-thumb at 1080p H.264, 15 fps, 2 Mbps VBR:

| Cameras | Per-day  | 14-day retention |
|---------|----------|------------------|
| 4       | 86 GB    | 1.2 TB           |
| 8       | 173 GB   | 2.4 TB           |
| 16      | 345 GB   | 4.8 TB           |
| 32      | 691 GB   | 9.7 TB           |

Hybrid mode keeps the most recent N days hot (local) and offloads the rest to S3.

## Observability

- Each service exposes Prometheus metrics on `/metrics`.
- Structured JSON logs to stdout; ship via Loki/Promtail or Datadog Agent.
- Health: `/healthz` (process up) and `/readyz` (deps reachable, backend only).
- Sentry: set `SENTRY_DSN` to enable.

## Backups

- **Postgres**: nightly `pg_dump` to S3 (use `pgbackrest` for PITR in prod).
- **Recordings**: rely on S3 versioning + lifecycle policies, or a periodic
  cross-region replication rule.
- **Config**: this whole repo + your `.env` (encrypted, in a secrets manager).
