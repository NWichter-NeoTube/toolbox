# Operations Guide

Day-to-day operations, backups, upgrades, and scaling guidance for the toolbox stack.

---

## Backup Strategy

Data lives in Docker named volumes and in the databases themselves. A solid backup strategy covers all of them.

### PostgreSQL Backups

PostgreSQL holds data for Grafana, Sentry, Unleash, PostHog, and Infisical. Losing it means losing all configuration, users, and metadata for these services.

#### Manual Backup

```bash
# Dump all databases at once
docker exec toolbox-postgres pg_dumpall -U toolbox > toolbox-pg-dumpall-$(date +%Y%m%d).sql

# Or dump individual databases
for db in toolbox grafana sentry unleash posthog infisical; do
  docker exec toolbox-postgres pg_dump -U toolbox -Fc "$db" > "backup-${db}-$(date +%Y%m%d).dump"
  echo "Dumped $db"
done
```

#### Automated Backup Cron Script

Create a backup script and schedule it with cron:

```bash
#!/usr/bin/env bash
# /opt/toolbox-backups/backup-postgres.sh
set -euo pipefail

BACKUP_DIR="/opt/toolbox-backups/postgres"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p "$BACKUP_DIR"

# Dump each database
for db in toolbox grafana sentry unleash posthog infisical; do
  FILENAME="$BACKUP_DIR/${db}-${DATE}.dump"
  docker exec toolbox-postgres pg_dump -U toolbox -Fc "$db" > "$FILENAME"
  echo "$(date): Backed up $db -> $FILENAME"
done

# Clean up old backups
find "$BACKUP_DIR" -name "*.dump" -mtime +${RETENTION_DAYS} -delete
echo "$(date): Cleaned up backups older than ${RETENTION_DAYS} days"
```

Add to cron (daily at 02:00):

```bash
# Edit crontab
crontab -e

# Add this line:
0 2 * * * /opt/toolbox-backups/backup-postgres.sh >> /opt/toolbox-backups/postgres-backup.log 2>&1
```

#### Restore from Backup

```bash
# Restore a single database from custom format dump
docker exec -i toolbox-postgres pg_restore -U toolbox -d sentry --clean --if-exists < backup-sentry-20250101.dump

# Restore from plain SQL dump
docker exec -i toolbox-postgres psql -U toolbox < toolbox-pg-dumpall-20250101.sql
```

### Redis Backups

Redis is configured with `appendonly yes` in the compose file. This means it persists data to disk automatically. The `redis_data` volume contains the AOF (Append Only File) and RDB snapshots.

```bash
# Trigger a manual RDB snapshot
docker exec toolbox-redis redis-cli -a "$REDIS_PASSWORD" BGSAVE

# Copy the RDB file from the volume
docker cp toolbox-redis:/data/dump.rdb ./redis-backup-$(date +%Y%m%d).rdb
```

Automated backup cron:

```bash
#!/usr/bin/env bash
# /opt/toolbox-backups/backup-redis.sh
set -euo pipefail

BACKUP_DIR="/opt/toolbox-backups/redis"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p "$BACKUP_DIR"

docker exec toolbox-redis redis-cli -a "$REDIS_PASSWORD" BGSAVE
sleep 5  # Wait for save to complete
docker cp toolbox-redis:/data/dump.rdb "$BACKUP_DIR/redis-${DATE}.rdb"

find "$BACKUP_DIR" -name "*.rdb" -mtime +${RETENTION_DAYS} -delete
echo "$(date): Redis backup complete"
```

### MinIO Backups

Use the MinIO client (`mc`) to mirror data to a backup location:

```bash
# Install mc (MinIO client) if not already installed
curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc
chmod +x /usr/local/bin/mc

# Configure mc to connect to your MinIO instance
docker exec toolbox-minio mc alias set local http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

# Mirror all buckets to a backup directory
docker exec toolbox-minio mc mirror local/ /backup/minio/

# Or mirror from the host using a port forward or external mc
mc alias set toolbox-minio https://minio-console.example.com "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mirror toolbox-minio/ /opt/toolbox-backups/minio/
```

### ClickHouse Backups

Both PostHog and Sentry have their own ClickHouse instances. ClickHouse data can grow large, so volume snapshots are often the most practical approach.

#### Option A: Volume Snapshots

```bash
# Stop ClickHouse before snapshotting (to ensure consistency)
docker stop toolbox-posthog-clickhouse
docker run --rm -v toolbox_posthog_clickhouse_data:/source -v /opt/toolbox-backups:/backup \
  alpine tar czf /backup/posthog-clickhouse-$(date +%Y%m%d).tar.gz -C /source .
docker start toolbox-posthog-clickhouse

# Same for Sentry ClickHouse
docker stop toolbox-sentry-clickhouse
docker run --rm -v toolbox_sentry_clickhouse_data:/source -v /opt/toolbox-backups:/backup \
  alpine tar czf /backup/sentry-clickhouse-$(date +%Y%m%d).tar.gz -C /source .
docker start toolbox-sentry-clickhouse
```

#### Option B: clickhouse-backup Tool

```bash
# Install clickhouse-backup inside the ClickHouse container
docker exec toolbox-posthog-clickhouse clickhouse-backup create "backup-$(date +%Y%m%d)"
docker exec toolbox-posthog-clickhouse clickhouse-backup list
```

### Volume Backup Reference

All named volumes used by the toolbox:

| Volume Name                         | Service               | Data Type                  | Backup Priority |
|-------------------------------------|-----------------------|----------------------------|-----------------|
| `toolbox_postgres_data`             | PostgreSQL            | All relational data        | Critical        |
| `toolbox_redis_data`                | Redis                 | Cache, queues, sessions    | High            |
| `toolbox_minio_data`                | MinIO                 | Uploaded files, media      | High            |
| `toolbox_prometheus_data`           | Prometheus            | Metrics (30d retention)    | Medium          |
| `toolbox_grafana_data`              | Grafana               | Dashboards, plugins        | Medium          |
| `toolbox_loki_data`                 | Loki                  | Logs (30d retention)       | Low             |
| `toolbox_tempo_data`                | Tempo                 | Traces                     | Low             |
| `toolbox_alertmanager_data`         | Alertmanager          | Silence/inhibit state      | Low             |
| `toolbox_posthog_clickhouse_data`   | PostHog ClickHouse    | Analytics events           | High            |
| `toolbox_posthog_clickhouse_logs`   | PostHog ClickHouse    | ClickHouse logs            | Low             |
| `toolbox_posthog_kafka_data`        | PostHog Kafka         | Event queue (ephemeral)    | Low             |
| `toolbox_sentry_clickhouse_data`    | Sentry ClickHouse     | Error events               | High            |
| `toolbox_sentry_kafka_data`         | Sentry Kafka          | Event queue (ephemeral)    | Low             |
| `toolbox_uptime_kuma_data`          | Uptime Kuma           | Monitor config, history    | Medium          |
| `toolbox_meilisearch_data`          | Meilisearch           | Search indexes             | Medium          |
| `toolbox_qdrant_data`               | Qdrant                | Vector indexes             | Medium          |

#### Generic Volume Backup with tar

For any volume, you can create a compressed archive:

```bash
# Backup a volume to a tar.gz file
VOLUME_NAME="toolbox_uptime_kuma_data"
docker run --rm -v ${VOLUME_NAME}:/source -v /opt/toolbox-backups:/backup \
  alpine tar czf /backup/${VOLUME_NAME}-$(date +%Y%m%d).tar.gz -C /source .

# Restore a volume from a tar.gz file
docker run --rm -v ${VOLUME_NAME}:/target -v /opt/toolbox-backups:/backup \
  alpine sh -c "cd /target && tar xzf /backup/${VOLUME_NAME}-20250101.tar.gz"
```

#### Rsync to Remote Backup Server

For off-site backups, rsync the backup directory to a remote server:

```bash
rsync -avz --delete /opt/toolbox-backups/ backup-user@backup-server:/backups/toolbox/
```

---

## Upgrade Procedure

All services run as Docker images managed by Coolify. Upgrading a service means pulling a newer image and redeploying.

### General Upgrade Steps

1. **Check the changelog** of the service you want to upgrade for breaking changes.
2. **Back up the service's data** before upgrading (see Backup Strategy above).
3. **Update the image tag** in the compose file (or use `latest` and just redeploy).
4. **Push the change to GitHub** so Coolify picks it up.
5. **Redeploy via Coolify:**

```bash
# Redeploy a specific stack
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$SERVICE_UUID/restart" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" | jq .
```

6. **Verify the service** is healthy after the upgrade using the checks in [05-verification.md](05-verification.md).

### Service-Specific Upgrade Notes

| Service     | Notes                                                                                      |
|-------------|--------------------------------------------------------------------------------------------|
| PostgreSQL  | Minor version upgrades (16.x) are safe. Major upgrades (16 to 17) require `pg_upgrade`.   |
| Redis       | Minor upgrades are safe. Redis handles RDB/AOF format changes automatically.               |
| MinIO       | Check release notes for storage format changes. Generally safe for minor upgrades.          |
| Prometheus  | Safe for minor upgrades. Check TSDB format changes for major versions.                     |
| Grafana     | May require database migrations (runs automatically). Check plugin compatibility.           |
| Loki        | Check schema version changes. May require index migration.                                 |
| Tempo       | Check block format changes between versions.                                               |
| PostHog     | Run `docker exec toolbox-posthog python manage.py migrate` after major upgrades.           |
| Sentry      | Run `docker exec toolbox-sentry sentry upgrade` after major upgrades. Always backup first. |
| Unleash     | Database migrations run automatically on startup.                                          |
| Meilisearch | Check for breaking API changes. Index format may change between major versions.            |
| Qdrant      | Storage format is generally backward compatible. Check release notes.                      |
| Infisical   | Database migrations run automatically. Check encryption key compatibility.                 |

### Pinned vs Latest Images

The compose files use a mix of pinned versions and `latest` tags:

- **Pinned:** `postgres:16-alpine`, `redis:7-alpine`, `prom/prometheus:v2.53.0`, `grafana/grafana-oss:11.1.0`, `grafana/loki:3.1.0`, `grafana/tempo:2.5.0`, `prom/alertmanager:v0.27.0`, `clickhouse/clickhouse-server:24.3-alpine`, `bitnami/kafka:3.7`, `getmeili/meilisearch:v1.9`, `qdrant/qdrant:v1.10.1`, `louislam/uptime-kuma:1`
- **Latest:** `posthog/posthog:latest`, `getsentry/sentry:latest`, `getsentry/snuba:latest`, `unleashorg/unleash-server:latest`, `infisical/infisical:latest`, `minio/minio:latest`

To upgrade a pinned image, update the tag in the compose file and redeploy. For `latest` images, simply redeploy and Docker pulls the newest version.

---

## Secret Rotation

See [03-infisical-setup.md](03-infisical-setup.md) for the complete secret rotation procedure, including:

- How to generate new secret values
- How to update secrets in Infisical
- How to sync updated secrets to Coolify
- How to restart affected services
- Recommended rotation schedule for each secret

Quick reference -- the rotation flow:

```bash
# 1. Generate new password
NEW_PASSWORD=$(openssl rand -hex 24)

# 2. Update in Infisical
infisical secrets set --env prod --path /core-data \
  --projectId "$INFISICAL_PROJECT_ID" \
  POSTGRES_PASSWORD="$NEW_PASSWORD"

# 3. Update the actual service (e.g., PostgreSQL)
docker exec toolbox-postgres psql -U toolbox -c \
  "ALTER USER toolbox WITH PASSWORD '$NEW_PASSWORD';"

# 4. Sync to Coolify and restart all dependent services
# (see 03-infisical-setup.md for the sync script)
```

---

## Log Management

### Loki Log Retention

Loki is configured with a 30-day retention period in `configs/loki/loki.yml`. Logs older than 30 days are automatically deleted.

To change the retention period, edit `configs/loki/loki.yml`:

```yaml
limits_config:
  retention_period: 30d    # Change this value
```

Then restart Loki:

```bash
docker restart toolbox-loki
```

### Prometheus Metrics Retention

Prometheus is configured with a 30-day retention period via the `--storage.tsdb.retention.time=30d` command flag in `compose/20-observability.yml`.

To change it, update the compose file and redeploy:

```yaml
command:
  - "--storage.tsdb.retention.time=30d"   # Change this value
```

### Viewing Logs

```bash
# Real-time logs for a specific service
docker logs -f toolbox-posthog --tail 100

# All logs for the last hour
docker logs --since 1h toolbox-sentry

# Search logs via Grafana
# Open Grafana > Explore > Select Loki datasource
# Query: {container_name="toolbox-posthog"} |= "error"
```

---

## Scaling Considerations

The toolbox is designed for a single server. Here are guidelines for when you need to scale.

### When to Add More RAM

| Symptom                                        | Likely Cause                        | Action                               |
|------------------------------------------------|-------------------------------------|--------------------------------------|
| OOM kills in `dmesg` or container restarts     | Total memory exceeded               | Add RAM or move services to a second server |
| ClickHouse slow queries                        | ClickHouse needs more buffer memory | Increase server RAM to 64 GB+        |
| PostHog/Sentry event ingestion falling behind  | Kafka/ClickHouse memory pressure    | Add RAM, increase Kafka heap         |
| Redis `maxmemory` evictions                    | Cache full (512 MB default)         | Increase `maxmemory` in compose      |

### When to Add More Disk

| Symptom                           | Where Data Accumulates                     | Action                              |
|-----------------------------------|--------------------------------------------|-------------------------------------|
| Disk usage > 80%                  | ClickHouse data, Prometheus TSDB, Loki     | Add disk or reduce retention        |
| `docker system df` shows large volumes | Docker volumes                        | Prune unused volumes, images        |

Monitor disk usage:

```bash
# Total disk usage by Docker
docker system df

# Volume sizes
docker system df -v | grep toolbox

# Largest volumes
du -sh /var/lib/docker/volumes/toolbox_* 2>/dev/null | sort -hr | head -20
```

### When to Split to Multiple Servers

Consider splitting when:

- Total RAM needed exceeds 64 GB.
- CPU usage is consistently above 80%.
- You need high availability or redundancy.

**Recommended split:**

| Server 1 (Core)           | Server 2 (Analytics + Errors)       |
|---------------------------|-------------------------------------|
| PostgreSQL, Redis, MinIO  | PostHog + ClickHouse + Kafka        |
| Prometheus, Grafana, Loki | Sentry + ClickHouse + Kafka + Snuba |
| Tempo, Alertmanager       |                                     |
| Unleash, Uptime Kuma      |                                     |
| Meilisearch, Qdrant       |                                     |
| Infisical                 |                                     |

When splitting, switch from a shared Docker network to overlay networking or expose PostgreSQL/Redis ports between servers.

---

## Monitoring with Uptime Kuma

Uptime Kuma provides uptime monitoring and public status pages for all toolbox services. It runs inside the Docker network and can reach all internal services by hostname.

### Recommended Monitors

Set up these monitors in the Uptime Kuma UI (`https://status.example.com`):

| Monitor Name        | Type  | Target                                        | Interval | Notes                    |
|---------------------|-------|-----------------------------------------------|----------|--------------------------|
| PostgreSQL          | TCP   | `postgres:5432`                               | 60s      | Port check only          |
| Redis               | TCP   | `redis:6379`                                  | 60s      | Port check only          |
| MinIO S3 API        | HTTP  | `http://minio:9000/minio/health/live`         | 60s      | Health endpoint          |
| MinIO Console       | HTTP  | `https://minio-console.example.com`           | 60s      | Public URL               |
| Grafana             | HTTP  | `https://grafana.example.com/api/health`      | 60s      | Returns JSON health      |
| Prometheus          | HTTP  | `http://prometheus:9090/-/healthy`             | 60s      | Internal health          |
| Loki                | HTTP  | `http://loki:3100/ready`                      | 60s      | Readiness probe          |
| Tempo               | HTTP  | `http://tempo:3200/ready`                      | 60s      | Readiness probe          |
| Alertmanager        | HTTP  | `http://alertmanager:9093/-/healthy`           | 60s      | Internal health          |
| PostHog             | HTTP  | `https://posthog.example.com/_health`          | 60s      | Public health            |
| Sentry              | HTTP  | `https://sentry.example.com/_health/`          | 60s      | Public health            |
| Unleash             | HTTP  | `https://unleash.example.com/health`           | 60s      | Public health            |
| Meilisearch         | HTTP  | `http://meilisearch:7700/health`               | 60s      | Internal health          |
| Qdrant              | HTTP  | `http://qdrant:6333/healthz`                   | 60s      | Internal health          |
| Infisical           | HTTP  | `https://infisical.example.com/api/status`     | 60s      | Public health            |
| Coolify             | HTTP  | `https://coolify.example.com`                  | 60s      | Coolify itself           |

### Setting Up Alert Notifications

In Uptime Kuma, go to **Settings > Notifications** and add notification channels:

- **Slack:** Add a webhook URL for your ops channel.
- **Email:** Configure SMTP settings for email alerts.
- **Telegram:** Add a bot token and chat ID.

Then assign notification channels to each monitor.

### Creating a Public Status Page

1. In Uptime Kuma, go to **Status Pages**.
2. Click **+ New Status Page**.
3. Name it (e.g., "Toolbox Status").
4. Add the monitors you want to display publicly.
5. The status page is available at `https://status.example.com/status/<slug>`.

---

## Maintenance Commands

### Clean Up Docker Resources

```bash
# Remove unused images (saves disk space after upgrades)
docker image prune -f

# Remove unused volumes (CAUTION: only safe if no stopped containers need them)
docker volume prune -f

# Full cleanup (unused images, containers, networks, build cache)
docker system prune -f

# Check disk usage
docker system df
```

### Restart All Services

```bash
# Restart a single stack
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$SERVICE_UUID/restart" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"

# Or restart containers directly
docker restart toolbox-postgres toolbox-redis toolbox-minio
```

### View Resource Usage

```bash
# Live resource usage for all toolbox containers
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" \
  $(docker ps --filter "name=toolbox-" --format "{{.Names}}")
```
