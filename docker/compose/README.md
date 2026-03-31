# Compose Layout

The canonical compose files live here:

- `docker-compose.yml` - main deployment stack
- `docker-compose.dev.yml` - local build override
- `docker-compose.dashboard.yml` - dashboard/monitoring stack

Use `--project-directory .` when invoking them from the repo root so bind mounts
continue to resolve against the project root:

```bash
docker compose --project-directory . -f docker/compose/docker-compose.yml up -d
```

