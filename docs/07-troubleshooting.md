# Troubleshooting

Common issues, debug commands, and recovery procedures for the toolbox stack.

---

## Common Issues

### Container Won't Start

**Symptoms:** Container shows `Restarting`, `Exited`, or never reaches `healthy` status.

**Steps:**

```bash
# 1. Check the container status
docker ps -a --filter "name=toolbox-<service>"

# 2. Read the container logs (last 100 lines)
docker logs toolbox-<service> --tail 100

# 3. Check if the container is being OOM-killed
dmesg | grep -i "oom" | tail -10

# 4. Verify the environment variables are set
docker inspect toolbox-<service> --format '{{range .Config.Env}}{{println .}}{{end}}'

# 5. Check if dependent services are running
docker ps --filter "name=toolbox-postgres" --filter "name=toolbox-redis"
```

**Common causes:**

| Error in Logs                              | Cause                                        | Fix                                         |
|--------------------------------------------|----------------------------------------------|---------------------------------------------|
| `POSTGRES_PASSWORD is required`            | Missing environment variable                 | Set the variable in Coolify and redeploy    |
| `connection refused` to postgres:5432      | PostgreSQL not running or not healthy yet    | Wait for postgres to be healthy, then restart the dependent service |
| `ECONNREFUSED` to redis:6379              | Redis not running                            | Start the core-data stack first             |
| `no such network: toolbox`                 | Docker network not created                   | Run `docker network create toolbox`         |
| `port already in use`                      | Another container or process using the port  | Stop the conflicting container              |
| `OOM killed`                               | Insufficient memory                          | Increase server RAM or reduce service limits |

### Service Can't Connect to PostgreSQL

**Symptoms:** Service logs show `connection refused`, `FATAL: password authentication failed`, or `database does not exist`.

```bash
# Verify PostgreSQL is healthy
docker exec toolbox-postgres pg_isready -U toolbox

# Verify the database exists
docker exec toolbox-postgres psql -U toolbox -c "\l"

# Verify the password works
docker exec toolbox-postgres psql -U toolbox -c "SELECT 1;"

# Check if the service is on the toolbox network
docker network inspect toolbox --format '{{range .Containers}}{{.Name}} {{end}}' | tr ' ' '\n' | grep toolbox-

# Test connectivity from the failing service
docker exec toolbox-<service> sh -c "nc -zv postgres 5432 2>&1 || echo 'Cannot reach postgres'"
```

**Fixes:**

- **Wrong password:** Ensure the service's `POSTGRES_PASSWORD` matches what PostgreSQL was initialized with. PostgreSQL sets the password only on first startup (when the volume is empty). If you changed the password in the env file but the volume already exists, you need to either `ALTER USER` inside PostgreSQL or delete the volume and reinitialize.
- **Database doesn't exist:** The init script (`compose/init-scripts/postgres/01-create-databases.sql`) only runs on the first start. If you added PostgreSQL after the volume was created, run the SQL manually:

```bash
docker exec toolbox-postgres psql -U toolbox -c "CREATE DATABASE <dbname>;"
```

- **Not on the network:** Ensure the service's compose file references the `toolbox` external network and Coolify is configured to attach the resource to it.

### Service Can't Connect to Redis

**Symptoms:** Service logs show `NOAUTH`, `connection refused`, or `ERR invalid password`.

```bash
# Verify Redis is healthy
docker exec toolbox-redis redis-cli -a "$REDIS_PASSWORD" ping

# Check which Redis DB each service uses
# PostHog: DB 1, Sentry/Snuba: DB 2, Infisical: DB 3
docker exec toolbox-redis redis-cli -a "$REDIS_PASSWORD" INFO keyspace
```

**Fixes:**

- **Wrong password:** Same issue as PostgreSQL -- Redis sets the password from the command flag. If the password in the env file doesn't match the running Redis, restart Redis with the correct password.
- **Wrong Redis DB:** PostHog uses DB 1, Sentry uses DB 2, Infisical uses DB 3. Check the connection URLs in the compose files.

### Coolify Deployment Fails

**Symptoms:** Deployment stuck at "Building" or shows an error in the Coolify UI.

```bash
# Check Coolify's own logs
docker logs coolify --tail 100

# Check the Coolify API status
curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/teams" | jq .

# List all services and their status
curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/services" | jq '.[] | {uuid, name, status}'

# Check if the GitHub App is still connected
curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/sources" | jq '.[].name'
```

**Common causes:**

- **GitHub App disconnected:** Reauthorize the GitHub App in Coolify UI > Sources.
- **Rate limiting:** GitHub API rate limits can cause failures. Wait and retry.
- **Compose file syntax error:** Validate the compose file locally: `docker compose -f compose/<file>.yml config`
- **Coolify internal error:** Restart Coolify: `docker restart coolify`

### TLS Certificate Issues

**Symptoms:** Browser shows "Connection not secure" or certificate errors.

Coolify uses Traefik with Let's Encrypt for automatic TLS certificate provisioning.

```bash
# Verify DNS points to the server
dig +short grafana.example.com

# Check if ports 80 and 443 are open
ss -tlnp | grep -E ':80|:443'

# Check Traefik logs (Coolify runs Traefik internally)
docker logs coolify-proxy --tail 50 2>&1 | grep -i "acme\|certificate\|error"
```

**Fixes:**

- **DNS not pointing to server:** Update DNS records and wait for propagation.
- **Ports 80/443 blocked:** Ensure the firewall allows both ports. Let's Encrypt requires port 80 for HTTP-01 challenges.
- **Rate limited by Let's Encrypt:** Let's Encrypt has a limit of ~50 certificates per domain per week. Wait and retry.
- **Certificate renewal:** Coolify auto-renews certificates via Let's Encrypt. If a certificate expires, restart Coolify's proxy: `docker restart coolify-proxy`

### High Memory Usage

These services are the most memory-hungry:

| Service                    | Typical Usage    | Why                                          |
|----------------------------|------------------|----------------------------------------------|
| PostHog ClickHouse         | 2-4 GB           | In-memory columnar processing                |
| Sentry ClickHouse          | 2-4 GB           | Same as above                                |
| PostHog Kafka              | 512 MB - 1 GB    | JVM heap for event buffering                 |
| Sentry Kafka               | 512 MB - 1 GB    | JVM heap for event buffering                 |
| PostHog Web + Workers      | 1-2 GB           | Django + Celery workers                      |
| Sentry Web + Workers       | 1-2 GB           | Django + Celery workers                      |

```bash
# Check memory usage per container
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}" \
  $(docker ps --filter "name=toolbox-" --format "{{.Names}}") | sort -k3 -t'%' -rn

# Check system memory
free -h

# Check for OOM events
dmesg | grep -i "out of memory" | tail -5
```

**Fixes:**

- **Reduce ClickHouse memory:** Add `max_memory_usage` settings in ClickHouse config.
- **Reduce Kafka heap:** Set `KAFKA_HEAP_OPTS=-Xmx512m -Xms256m` in the Kafka environment.
- **Reduce Redis memory:** The compose already caps Redis at 512 MB via `maxmemory`.
- **Add swap (temporary):** `sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile`

### Disk Space Issues

**Symptoms:** Services fail with "no space left on device" errors.

```bash
# Check overall disk usage
df -h /

# Check Docker disk usage
docker system df

# Find the largest volumes
du -sh /var/lib/docker/volumes/toolbox_* 2>/dev/null | sort -hr

# Find the largest containers (writable layer)
docker ps -s --format "table {{.Names}}\t{{.Size}}" --filter "name=toolbox-" | sort -k2 -hr
```

**Where data accumulates:**

| Location                                  | Service          | Growth Rate | Cleanup Strategy                     |
|-------------------------------------------|------------------|-------------|--------------------------------------|
| `toolbox_posthog_clickhouse_data`         | PostHog          | Fast        | Reduce event retention in PostHog settings |
| `toolbox_sentry_clickhouse_data`          | Sentry           | Fast        | Reduce `SENTRY_EVENT_RETENTION_DAYS` |
| `toolbox_prometheus_data`                 | Prometheus       | Medium      | Already 30d retention; reduce if needed |
| `toolbox_loki_data`                       | Loki             | Medium      | Already 30d retention; reduce if needed |
| `toolbox_minio_data`                      | MinIO            | Varies      | Clean up unused buckets and objects  |
| `toolbox_posthog_kafka_data`              | Kafka            | Medium      | Already 24h retention; usually self-cleaning |
| Docker images                             | All              | On upgrades | `docker image prune -f`             |

**Cleanup commands:**

```bash
# Remove unused Docker images
docker image prune -f

# Remove dangling volumes (not attached to any container)
docker volume prune -f

# Remove old Prometheus data manually (if needed)
# WARNING: This deletes metrics data
docker exec toolbox-prometheus promtool tsdb clean --min-block-duration 168h /prometheus

# Clean Docker build cache
docker builder prune -f
```

---

## Useful Debug Commands

### Container Logs

```bash
# Real-time logs
docker logs -f toolbox-<service>

# Last 200 lines
docker logs toolbox-<service> --tail 200

# Logs since a specific time
docker logs toolbox-<service> --since "2025-01-15T10:00:00"

# Logs from the last 2 hours
docker logs toolbox-<service> --since 2h

# Search logs for errors
docker logs toolbox-<service> 2>&1 | grep -i "error\|exception\|fatal"
```

### Execute Commands Inside Containers

```bash
# Open a shell in a container
docker exec -it toolbox-<service> sh
# Or bash (if available)
docker exec -it toolbox-<service> bash

# Run a specific command
docker exec toolbox-postgres psql -U toolbox -c "SELECT version();"
docker exec toolbox-redis redis-cli -a "$REDIS_PASSWORD" INFO server
docker exec toolbox-minio mc ls local/
```

### Network Inspection

```bash
# List all containers on the toolbox network
docker network inspect toolbox --format '{{range .Containers}}{{.Name}} ({{.IPv4Address}}){{"\n"}}{{end}}'

# Test connectivity between containers
docker exec toolbox-grafana wget -qO- --timeout=3 http://prometheus:9090/-/healthy

# DNS resolution inside a container
docker exec toolbox-grafana nslookup postgres
```

### Resource Usage

```bash
# Live stats for all toolbox containers
docker stats --filter "name=toolbox-"

# Snapshot of resource usage
docker stats --no-stream --filter "name=toolbox-"

# Check container restart count
docker inspect --format '{{.RestartCount}} restarts: {{.Name}}' $(docker ps -aq --filter "name=toolbox-")
```

---

## How to Reset a Service

If a service is in a broken state and you need to start fresh:

> **Warning:** Resetting a service deletes its data. Back up first if the data is important.

### Reset Steps

```bash
# 1. Stop the service
docker stop toolbox-<service>

# 2. Remove the container
docker rm toolbox-<service>

# 3. Delete the volume (THIS DELETES ALL DATA)
docker volume rm toolbox_<service>_data

# 4. Redeploy via Coolify
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$SERVICE_UUID/restart" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"
```

### Reset PostgreSQL (Nuclear Option)

This resets all PostgreSQL data, which affects Grafana, Sentry, Unleash, PostHog, and Infisical:

```bash
# DANGER: This deletes ALL relational data for ALL services
docker stop toolbox-postgres
docker rm toolbox-postgres
docker volume rm toolbox_postgres_data

# Redeploy core-data stack
# The init script will recreate all databases on first start
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$CORE_DATA_UUID/restart" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"

# After PostgreSQL is healthy, restart all dependent services:
# Sentry needs: docker exec toolbox-sentry sentry upgrade
# PostHog needs: first-run wizard
# Other services: just restart them
```

### Reset a Single Database (Safer)

To reset just one service's database without affecting others:

```bash
# Drop and recreate the database (e.g., Sentry)
docker exec toolbox-postgres psql -U toolbox -c "DROP DATABASE IF EXISTS sentry;"
docker exec toolbox-postgres psql -U toolbox -c "CREATE DATABASE sentry;"
docker exec toolbox-postgres psql -U toolbox -c "GRANT ALL PRIVILEGES ON DATABASE sentry TO toolbox;"

# Restart the service so it reinitializes
docker restart toolbox-sentry

# For Sentry specifically, run the upgrade/migration again
docker exec -it toolbox-sentry sentry upgrade
```

---

## How to Check Coolify API Status

```bash
# Check if the Coolify API is reachable
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/teams"

# List all services and their status
curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/services" | jq '.[] | {name, status}'

# Check Coolify containers
docker ps --filter "name=coolify"

# Restart Coolify if it's not responding
docker restart coolify
```

---

## Official Documentation Links

Quick reference for each service's official documentation:

| Service       | Docs URL                                                   |
|---------------|------------------------------------------------------------|
| PostgreSQL    | https://www.postgresql.org/docs/16/                        |
| Redis         | https://redis.io/docs/                                     |
| MinIO         | https://min.io/docs/minio/linux/                           |
| Prometheus    | https://prometheus.io/docs/                                |
| Grafana       | https://grafana.com/docs/grafana/latest/                   |
| Loki          | https://grafana.com/docs/loki/latest/                      |
| Tempo         | https://grafana.com/docs/tempo/latest/                     |
| Alertmanager  | https://prometheus.io/docs/alerting/latest/alertmanager/   |
| PostHog       | https://posthog.com/docs/self-host                         |
| Sentry        | https://develop.sentry.dev/self-hosted/                    |
| Unleash       | https://docs.getunleash.io/                                |
| Uptime Kuma   | https://github.com/louislam/uptime-kuma/wiki               |
| Meilisearch   | https://www.meilisearch.com/docs                           |
| Qdrant        | https://qdrant.tech/documentation/                         |
| Infisical     | https://infisical.com/docs                                 |
| Coolify       | https://coolify.io/docs                                    |
| Docker        | https://docs.docker.com/                                   |

---

## Support Channels

If you cannot resolve an issue with this guide, try these resources:

### Service-Specific Communities

- **Coolify:** [GitHub Discussions](https://github.com/coollabsio/coolify/discussions), [Discord](https://discord.gg/coolify)
- **PostHog:** [GitHub Issues](https://github.com/PostHog/posthog/issues), [Community Slack](https://posthog.com/community)
- **Sentry:** [GitHub Issues](https://github.com/getsentry/self-hosted/issues), [Discord](https://discord.gg/sentry)
- **Unleash:** [GitHub Discussions](https://github.com/Unleash/unleash/discussions), [Slack](https://slack.unleash.run/)
- **Grafana/Loki/Tempo:** [GitHub Issues](https://github.com/grafana/grafana/issues), [Community Forum](https://community.grafana.com/)
- **Meilisearch:** [GitHub Discussions](https://github.com/meilisearch/meilisearch/discussions), [Discord](https://discord.gg/meilisearch)
- **Qdrant:** [GitHub Issues](https://github.com/qdrant/qdrant/issues), [Discord](https://discord.gg/qdrant)
- **Infisical:** [GitHub Issues](https://github.com/Infisical/infisical/issues), [Slack](https://infisical.com/slack)
- **Uptime Kuma:** [GitHub Issues](https://github.com/louislam/uptime-kuma/issues)

### General Troubleshooting Steps

1. **Read the container logs.** 90% of issues are explained in the error output.
2. **Check environment variables.** Missing or incorrect env vars are the most common deployment issue.
3. **Verify the network.** All services must be on the `toolbox` Docker network.
4. **Check resource limits.** Memory and disk are the most common bottlenecks.
5. **Restart the service.** Many transient issues resolve with a container restart.
6. **Check Coolify.** If a Coolify-managed deployment fails, the Coolify UI deployment logs show the error.
7. **Search the issue tracker.** Most errors have been seen before by other self-hosters.
