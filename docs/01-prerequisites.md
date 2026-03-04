# Prerequisites

Everything you need before deploying the toolbox stack.

---

## Server Requirements

| Resource | Minimum       | Recommended   | Notes                                           |
|----------|---------------|---------------|--------------------------------------------------|
| RAM      | 16 GB         | 32 GB         | PostHog + Sentry + ClickHouse are memory-hungry  |
| CPU      | 4 cores       | 8 cores       | ClickHouse and Kafka benefit from more cores     |
| Disk     | 100 GB SSD    | 250 GB+ SSD   | NVMe preferred; metrics/logs/events grow fast    |
| OS       | Ubuntu 22.04+ | Ubuntu 24.04  | Any Linux distro supported by Coolify works      |
| Network  | 100 Mbit/s    | 1 Gbit/s      | Sufficient bandwidth for analytics ingestion     |

> **Memory breakdown estimate** (idle/low-traffic):
> - PostgreSQL: ~512 MB
> - Redis: ~512 MB (capped at 512 MB via maxmemory)
> - MinIO: ~256 MB
> - Prometheus + Alertmanager: ~512 MB
> - Grafana: ~256 MB
> - Loki + Tempo: ~512 MB
> - PostHog + ClickHouse + Kafka: ~4-6 GB
> - Sentry + ClickHouse + Kafka + Snuba: ~4-6 GB
> - Unleash: ~256 MB
> - Uptime Kuma: ~128 MB
> - Meilisearch: ~256 MB
> - Qdrant: ~256 MB
> - Infisical: ~256 MB
> - Coolify itself: ~1 GB
>
> **Total baseline: ~13-16 GB**. With traffic and indexing, memory usage grows significantly.

---

## Coolify

Coolify must be installed and reachable on the server before deploying the toolbox.

### Install Coolify

If Coolify is not yet installed, run the official installer:

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

After installation, Coolify is available at `http://<server-ip>:8000`. Complete the initial setup wizard (create admin account, configure server).

### Verify Coolify Is Running

```bash
# Check Coolify containers
docker ps --filter "name=coolify"

# Verify the UI is reachable
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000
# Expected: 200 or 302
```

---

## Docker and Docker Compose v2

Coolify installs Docker as part of its setup. Verify both are available:

```bash
# Docker
docker --version
# Expected: Docker version 24.x or newer

# Docker Compose v2 (plugin, not standalone)
docker compose version
# Expected: Docker Compose version v2.x.x
```

If Docker Compose v2 is missing:

```bash
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

---

## Domain Names

You need a domain (e.g., `example.com`) with DNS records pointing to your server's public IP address. Each public-facing service gets its own subdomain.

### Required Subdomains

| Subdomain                      | Service        | Notes                              |
|--------------------------------|----------------|------------------------------------|
| `coolify.example.com`          | Coolify UI     | Already configured during install  |
| `grafana.example.com`          | Grafana        | Dashboards and monitoring          |
| `sentry.example.com`           | Sentry         | Error tracking                     |
| `posthog.example.com`          | PostHog        | Product analytics                  |
| `unleash.example.com`          | Unleash        | Feature flags                      |
| `status.example.com`           | Uptime Kuma    | Public status page                 |
| `infisical.example.com`        | Infisical      | Secrets management                 |
| `minio-console.example.com`    | MinIO Console  | Object storage UI                  |

Replace `example.com` with your actual domain throughout this documentation.

### DNS Records to Create

Create **A records** for each subdomain pointing to your server's public IPv4 address. If your server also has an IPv6 address, add **AAAA records** as well.

```
# Example DNS zone file entries (replace 203.0.113.10 with your server IP)

coolify.example.com.        A    203.0.113.10
grafana.example.com.        A    203.0.113.10
sentry.example.com.         A    203.0.113.10
posthog.example.com.        A    203.0.113.10
unleash.example.com.        A    203.0.113.10
status.example.com.         A    203.0.113.10
infisical.example.com.      A    203.0.113.10
minio-console.example.com.  A    203.0.113.10
```

Alternatively, you can use a **wildcard A record** to cover all subdomains:

```
*.example.com.    A    203.0.113.10
```

> **Note:** DNS propagation can take up to 48 hours, but typically completes within minutes to a few hours. Verify propagation before deploying:

```bash
# Check if a subdomain resolves to your server
dig +short grafana.example.com
# Expected: 203.0.113.10

# Or use nslookup
nslookup grafana.example.com
```

---

## GitHub Account and Repository Access

The toolbox repository is deployed through Coolify's GitHub integration. You need:

1. **A GitHub account** with access to the repository containing this toolbox code.
2. **The repository pushed to GitHub** (public or private both work).

### Push the Repository to GitHub

If the repo is not yet on GitHub:

```bash
# Create a new repo on GitHub first, then:
cd /path/to/toolbox
git remote add origin git@github.com:<your-org>/toolbox.git
git push -u origin main
```

---

## Coolify GitHub App

Coolify uses a GitHub App to access your repositories. This must be set up once.

### Connect the GitHub App

1. Open Coolify UI at `https://coolify.example.com`.
2. Go to **Sources** in the left sidebar.
3. Click **+ Add** and select **GitHub App**.
4. Click **Register a GitHub App on github.com**.
5. Follow the GitHub OAuth flow:
   - Name the app (e.g., `coolify-toolbox`).
   - Select the organization or account that owns the toolbox repo.
   - Grant access to the specific repository (or all repositories).
6. After authorization, Coolify stores the app credentials automatically.

### Verify the Connection

```bash
# List available sources via Coolify API (after generating an API token)
curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/sources" | jq '.[].name'
```

Or in the Coolify UI: go to **Sources** and confirm the GitHub App shows a green "Connected" status.

---

## Firewall Configuration

Ensure the following ports are open on your server's firewall:

| Port  | Protocol | Purpose                                |
|-------|----------|----------------------------------------|
| 22    | TCP      | SSH access                             |
| 80    | TCP      | HTTP (Coolify redirects to HTTPS)      |
| 443   | TCP      | HTTPS (all public services via Coolify)|
| 8000  | TCP      | Coolify UI (can be closed after setup if proxied) |

All other service ports (5432, 6379, 9090, etc.) should **not** be exposed to the internet. They are only accessible within the Docker network.

```bash
# Example: UFW firewall setup
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw enable
sudo ufw status
```

---

## Checklist

Before proceeding to deployment, verify:

- [ ] Server meets minimum requirements (16 GB RAM, 4 cores, 100 GB SSD)
- [ ] Coolify is installed and accessible at `https://coolify.example.com`
- [ ] Docker and Docker Compose v2 are installed
- [ ] Domain DNS records point all subdomains to the server IP
- [ ] DNS propagation has completed (verify with `dig`)
- [ ] GitHub repository is created and code is pushed
- [ ] Coolify GitHub App is connected and has repository access
- [ ] Firewall allows ports 22, 80, 443 (and 8000 if needed)

Once all prerequisites are met, proceed to [02-coolify-setup.md](02-coolify-setup.md).
