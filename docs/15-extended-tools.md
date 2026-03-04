# 15 — Erweiterte Tools: Vollstaendige Referenz

Dieses Dokument konsolidiert die vollstaendige Dokumentation aller erweiterten Tools der Toolbox. Jedes Tool wird mit Setup, Konfiguration, Praxis-Beispielen und Troubleshooting beschrieben.

## Inhaltsverzeichnis

- [1. Authentik — Single Sign-On (SSO)](#1-authentik--single-sign-on-sso)
- [2. Grafana Alloy — Log-Shipping](#2-grafana-alloy--log-shipping)
- [3. Restic — Automatisierte Backups](#3-restic--automatisierte-backups)
- [4. n8n — Workflow-Automation](#4-n8n--workflow-automation)
- [5. Trivy — Container-Security](#5-trivy--container-security)
- [6. OpenTelemetry — Vendor-neutrale Telemetrie](#6-opentelemetry--vendor-neutrale-telemetrie)
- [7. Plausible — Leichtgewichtige Analytics](#7-plausible--leichtgewichtige-analytics)

## Uebersicht: Alle erweiterten Tools

| Tool           | Kategorie          | Zweck                                                        | Prioritaet |
|----------------|--------------------|--------------------------------------------------------------|------------|
| Authentik      | Authentifizierung   | Zentrales SSO fuer alle Services (OIDC, SAML, LDAP)         | Hoch       |
| Grafana Alloy  | Observability       | Docker-Container-Logs an Loki senden                         | Hoch       |
| Restic         | Backup              | Automatisierte, verschluesselte Backups in MinIO (S3)        | Kritisch   |
| n8n            | Automation          | Workflow-Automation: Events verknuepfen, Reports, Alerts     | Mittel     |
| Trivy          | Security            | Container-Image-Scanning, IaC-Checks, Secret-Detection      | Hoch       |
| OpenTelemetry  | Observability       | Vendor-neutrale Traces, Metriken, Logs aus Anwendungen       | Mittel     |
| Plausible      | Analytics           | Cookie-freie Web-Analytics ohne Consent-Banner               | Niedrig    |


---

## 1. Authentik — Single Sign-On (SSO)


Dieses Dokument beschreibt die Einrichtung von Authentik als zentralen Identity Provider (IdP) fuer die gesamte Toolbox. Ziel ist ein einziger Login fuer alle Services: Grafana, Sentry, PostHog, Unleash, Infisical, MinIO und Uptime Kuma.

> **Voraussetzung:** Die Stacks `core-data` (PostgreSQL, Redis) und `networks` muessen bereits laufen. Siehe [04-deploy-stack.md](04-deploy-stack.md).

---

### 1. Was ist Authentik?

Authentik ist ein Open-Source Identity Provider, der als zentrale Authentifizierungs- und Autorisierungsschicht dient. Statt sich bei jedem Service einzeln anzumelden, loggen sich Benutzer einmal bei Authentik ein und erhalten automatisch Zugang zu allen angebundenen Anwendungen.

#### Unterstuetzte Protokolle

- **OpenID Connect (OIDC):** Modernes OAuth2-basiertes Protokoll. Bevorzugt fuer die meisten Services.
- **SAML 2.0:** Enterprise-Standard, benoetigt von einigen aelteren Anwendungen.
- **LDAP:** Authentik kann als LDAP-Server fungieren fuer Legacy-Anwendungen.
- **SCIM:** Automatische Benutzer-Provisionierung und -Deprovisionierung.
- **Proxy Authentication:** Forward-Auth fuer Services ohne native SSO-Unterstuetzung.

#### Warum SSO wichtig ist

Ohne SSO muss jeder Benutzer fuer jeden Service ein separates Konto mit separatem Passwort pflegen. Das fuehrt zu:

- Passwort-Wiederverwendung (Sicherheitsrisiko)
- Aufwendigem Onboarding/Offboarding (bei jedem Service einzeln)
- Fehlender zentraler MFA-Durchsetzung
- Keinem zentralen Audit-Log ueber Anmeldevorgaenge

Mit Authentik gibt es eine einzige Anlaufstelle fuer Benutzerverwaltung, Passwort-Policies und MFA.

#### Vergleich mit Keycloak

| Kriterium             | Authentik                       | Keycloak                        |
|-----------------------|---------------------------------|---------------------------------|
| UI                    | Modern, intuitiv                | Funktional, aber komplex        |
| Konfiguration         | Flows per Drag & Drop           | XML/JSON-basiert                |
| Ressourcenverbrauch   | ~300 MB RAM (Server + Worker)   | ~500-800 MB RAM                 |
| Proxy-Auth            | Eingebaut                       | Externer Adapter noetig         |
| Blueprints            | YAML-basierte Konfiguration     | Realm-Export (JSON)             |
| Sprache               | Python (Django)                 | Java (Quarkus)                  |
| DSGVO                 | Self-hosted, volle Kontrolle    | Self-hosted, volle Kontrolle    |

Authentik ist fuer diese Toolbox die bessere Wahl: leichtgewichtiger, einfacher zu konfigurieren, und die Proxy-Auth-Funktion loest das Problem von Services ohne native SSO-Unterstuetzung (z.B. Uptime Kuma).

#### DSGVO-Konformitaet

Authentik laeuft vollstaendig auf dem eigenen Server. Alle Authentifizierungsdaten (Benutzerkonten, Sessions, Tokens, Audit-Logs) bleiben in der eigenen PostgreSQL-Datenbank. Es werden keine Daten an Drittanbieter uebermittelt.

---

### 2. Architektur

#### Uebersicht

```
                           Internet
                              |
                    +---------v----------+
                    |      Coolify       |
                    |    (Traefik TLS)   |
                    +---------+----------+
                              |
            +-----------------+-----------------+
            |                                   |
    +-------v--------+                +---------v---------+
    |    Authentik    |                |   Alle Services   |
    |    Server       |                |                   |
    | auth.example.com|                | grafana.example.com
    +-------+--------+                | sentry.example.com
            |                         | posthog.example.com
    +-------v--------+                | unleash.example.com
    |    Authentik    |                | infisical.example.com
    |    Worker       |                | minio-console.example.com
    +-------+--------+                | status.example.com
            |                         +---------+---------+
    ========|=========================|=========|=========
            |   Docker Network "toolbox"        |
    ========|=========================|=========|=========
            |                         |
    +-------v--------+        +-------v--------+
    |   PostgreSQL   |        |     Redis      |
    |  (DB: authentik)|        |   (Sessions)   |
    +----------------+        +----------------+
```

#### Authentifizierungsfluss (OIDC)

```
Benutzer                  Grafana                Authentik
   |                         |                       |
   |-- Oeffne Grafana ------>|                       |
   |                         |-- 302 Redirect ------>|
   |                         |   /application/o/     |
   |                         |   authorize/          |
   |                         |                       |
   |<---- Login-Seite anzeigen ----------------------|
   |                         |                       |
   |-- Credentials eingeben ----------------------->|
   |                         |                       |
   |                         |<-- 302 Callback ------|
   |                         |   ?code=abc123        |
   |                         |                       |
   |                         |-- Token Exchange ---->|
   |                         |   (code -> token)     |
   |                         |                       |
   |                         |<-- Access Token ------|
   |                         |    + ID Token         |
   |                         |    + Userinfo         |
   |                         |                       |
   |<-- Eingeloggt ----------|                       |
```

#### Komponenten

- **Authentik Server:** Haupt-Webserver. Stellt die UI, die OIDC/SAML-Endpoints und die Admin-Oberflaeche bereit.
- **Authentik Worker:** Background-Worker fuer asynchrone Tasks (E-Mail-Versand, LDAP-Sync, Ereignisverarbeitung).
- **PostgreSQL:** Speichert alle Authentik-Daten (Benutzer, Gruppen, Anwendungen, Flows, Audit-Logs). Nutzt die gemeinsame PostgreSQL-Instanz der Toolbox mit einer separaten Datenbank `authentik`.
- **Redis:** Session-Cache und Task-Queue fuer den Worker. Nutzt die gemeinsame Redis-Instanz der Toolbox.

---

### 3. Stack Setup

#### PostgreSQL-Datenbank vorbereiten

Bevor Authentik gestartet wird, muss die Datenbank `authentik` in der gemeinsamen PostgreSQL-Instanz existieren. Fuege folgenden Eintrag zum Init-Script hinzu:

```sql
-- In stacks/core-data/init-scripts/postgres/01-create-databases.sql
-- (falls noch nicht vorhanden)
CREATE DATABASE authentik;
```

Falls PostgreSQL bereits laeuft und die Datenbank fehlt, erstelle sie manuell:

```bash
docker exec toolbox-postgres psql -U toolbox -c "CREATE DATABASE authentik;"
```

#### Docker Compose

Erstelle den Stack unter `stacks/auth/`:

```yaml
# stacks/auth/docker-compose.yml
# Authentik Identity Provider - SSO fuer alle Toolbox-Services

services:
  # -----------------------------------------------
  # Authentik Server
  # -----------------------------------------------
  authentik-server:
    image: ghcr.io/goauthentik/server:2024.6
    container_name: toolbox-authentik-server
    restart: unless-stopped
    command: server
    environment:
      # --- Datenbank ---
      AUTHENTIK_POSTGRESQL__HOST: postgres
      AUTHENTIK_POSTGRESQL__PORT: 5432
      AUTHENTIK_POSTGRESQL__NAME: authentik
      AUTHENTIK_POSTGRESQL__USER: ${POSTGRES_USER:-toolbox}
      AUTHENTIK_POSTGRESQL__PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
      # --- Redis ---
      AUTHENTIK_REDIS__HOST: redis
      AUTHENTIK_REDIS__PORT: 6379
      AUTHENTIK_REDIS__PASSWORD: ${REDIS_PASSWORD:?REDIS_PASSWORD is required}
      AUTHENTIK_REDIS__DB: 2
      # --- Authentik ---
      AUTHENTIK_SECRET_KEY: ${AUTHENTIK_SECRET_KEY:?AUTHENTIK_SECRET_KEY is required}
      AUTHENTIK_ERROR_REPORTING__ENABLED: "false"
      AUTHENTIK_DISABLE_UPDATE_CHECK: "true"
      AUTHENTIK_DISABLE_STARTUP_ANALYTICS: "true"
      # --- E-Mail (optional, fuer Passwort-Reset etc.) ---
      AUTHENTIK_EMAIL__HOST: ${AUTHENTIK_EMAIL_HOST:-}
      AUTHENTIK_EMAIL__PORT: ${AUTHENTIK_EMAIL_PORT:-587}
      AUTHENTIK_EMAIL__USERNAME: ${AUTHENTIK_EMAIL_USERNAME:-}
      AUTHENTIK_EMAIL__PASSWORD: ${AUTHENTIK_EMAIL_PASSWORD:-}
      AUTHENTIK_EMAIL__USE_TLS: ${AUTHENTIK_EMAIL_USE_TLS:-true}
      AUTHENTIK_EMAIL__FROM: ${AUTHENTIK_EMAIL_FROM:-authentik@example.com}
    volumes:
      - authentik_media:/media
      - authentik_templates:/templates
    networks:
      - toolbox
    healthcheck:
      test: ["CMD", "ak", "healthcheck"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

  # -----------------------------------------------
  # Authentik Worker
  # -----------------------------------------------
  authentik-worker:
    image: ghcr.io/goauthentik/server:2024.6
    container_name: toolbox-authentik-worker
    restart: unless-stopped
    command: worker
    environment:
      # Gleiche Umgebungsvariablen wie der Server
      AUTHENTIK_POSTGRESQL__HOST: postgres
      AUTHENTIK_POSTGRESQL__PORT: 5432
      AUTHENTIK_POSTGRESQL__NAME: authentik
      AUTHENTIK_POSTGRESQL__USER: ${POSTGRES_USER:-toolbox}
      AUTHENTIK_POSTGRESQL__PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
      AUTHENTIK_REDIS__HOST: redis
      AUTHENTIK_REDIS__PORT: 6379
      AUTHENTIK_REDIS__PASSWORD: ${REDIS_PASSWORD:?REDIS_PASSWORD is required}
      AUTHENTIK_REDIS__DB: 2
      AUTHENTIK_SECRET_KEY: ${AUTHENTIK_SECRET_KEY:?AUTHENTIK_SECRET_KEY is required}
      AUTHENTIK_ERROR_REPORTING__ENABLED: "false"
      AUTHENTIK_DISABLE_UPDATE_CHECK: "true"
      AUTHENTIK_DISABLE_STARTUP_ANALYTICS: "true"
      AUTHENTIK_EMAIL__HOST: ${AUTHENTIK_EMAIL_HOST:-}
      AUTHENTIK_EMAIL__PORT: ${AUTHENTIK_EMAIL_PORT:-587}
      AUTHENTIK_EMAIL__USERNAME: ${AUTHENTIK_EMAIL_USERNAME:-}
      AUTHENTIK_EMAIL__PASSWORD: ${AUTHENTIK_EMAIL_PASSWORD:-}
      AUTHENTIK_EMAIL__USE_TLS: ${AUTHENTIK_EMAIL_USE_TLS:-true}
      AUTHENTIK_EMAIL__FROM: ${AUTHENTIK_EMAIL_FROM:-authentik@example.com}
    volumes:
      - authentik_media:/media
      - authentik_templates:/templates
      - authentik_certs:/certs
    networks:
      - toolbox

volumes:
  authentik_media:
    name: toolbox_authentik_media
  authentik_templates:
    name: toolbox_authentik_templates
  authentik_certs:
    name: toolbox_authentik_certs

networks:
  toolbox:
    external: true
    name: toolbox
```

#### Umgebungsvariablen (.env.example)

```bash
# stacks/auth/.env.example
# Authentik Identity Provider

# --- Shared credentials (from core-data stack) ---
POSTGRES_USER=toolbox
POSTGRES_PASSWORD=CHANGE_ME_postgres_password
REDIS_PASSWORD=CHANGE_ME_redis_password

# --- Authentik-specific ---
# Geheimer Schluessel fuer Token-Signierung und Verschluesselung.
# Generieren mit: openssl rand -hex 32
AUTHENTIK_SECRET_KEY=CHANGE_ME_authentik_secret_key

# --- Authentik URL (oeffentliche URL, wie von Coolify geroutet) ---
AUTHENTIK_URL=https://auth.example.com

# --- E-Mail (optional, fuer Passwort-Reset und Einladungen) ---
# AUTHENTIK_EMAIL_HOST=smtp.example.com
# AUTHENTIK_EMAIL_PORT=587
# AUTHENTIK_EMAIL_USERNAME=authentik@example.com
# AUTHENTIK_EMAIL_PASSWORD=CHANGE_ME_email_password
# AUTHENTIK_EMAIL_USE_TLS=true
# AUTHENTIK_EMAIL_FROM=authentik@example.com
```

#### Secrets generieren

```bash
# Authentik Secret Key (64 Hex-Zeichen = 32 Bytes)
AUTHENTIK_SECRET_KEY=$(openssl rand -hex 32)
echo "AUTHENTIK_SECRET_KEY=$AUTHENTIK_SECRET_KEY"
```

> **Wichtig:** Den Secret Key sicher aufbewahren (Infisical, Passwort-Manager). Bei Verlust werden alle bestehenden Sessions und Tokens ungueltig.

---

### 4. Erstinstallation

#### 4.1 Deploy via Coolify

1. Erstelle in Coolify eine neue Docker-Compose-Ressource.
2. Zeige auf `stacks/auth/docker-compose.yml`.
3. Setze die Umgebungsvariablen aus der `.env.example`.
4. Weise die Domain `auth.example.com` dem Service `authentik-server` auf Port `9000` zu.
5. Deploye den Stack.

#### 4.2 Initialen Admin-Account erstellen

Authentik erstellt beim ersten Start automatisch einen Admin-Account mit dem Benutzernamen `akadmin`. Das initiale Passwort muss gesetzt werden:

```bash
# Setze das initiale Admin-Passwort
docker exec -it toolbox-authentik-server \
  ak create_admin_user \
  --username akadmin \
  --email admin@example.com \
  --password "DEIN_SICHERES_PASSWORT"
```

Alternativ kannst du das Passwort auch beim ersten Aufruf im Browser setzen:

1. Oeffne `https://auth.example.com/if/flow/initial-setup/`
2. Setze das Passwort fuer den `akadmin`-Account.

#### 4.3 Erster Login

1. Oeffne `https://auth.example.com`.
2. Melde dich an mit `akadmin` und dem gesetzten Passwort.
3. Du landest auf dem Authentik-Dashboard.

#### 4.4 Branding konfigurieren

1. Gehe zu **Admin-Bereich** (Zahnrad-Icon oben rechts) > **System** > **Tenants**.
2. Klicke auf den Standard-Tenant.
3. Aendere:
   - **Title:** Name deiner Organisation (z.B. "Toolbox SSO")
   - **Logo:** Lade dein Firmenlogo hoch (erscheint auf der Login-Seite)
   - **Favicon:** Lade ein Favicon hoch
   - **Default Flow:** Belasse auf dem Standard-Authentifizierungsflow

#### 4.5 Verifizierung

```bash
# Pruefe ob der Server laeuft
curl -s https://auth.example.com/-/health/live/
# Erwartet: HTTP 204

# Pruefe den Worker
docker logs toolbox-authentik-worker --tail 5
# Erwartet: "Worker connected" oder aehnlich
```

---

### 5. OIDC Provider einrichten

Fuer jeden Service, der an Authentik angebunden werden soll, muessen in Authentik zwei Objekte erstellt werden:

1. **Provider:** Definiert das Protokoll (OIDC/SAML) und die technischen Parameter (Redirect-URIs, Scopes).
2. **Application:** Benutzerseitige Darstellung. Verknuepft den Provider mit einer Zugriffsrichtlinie.

#### 5.1 Provider erstellen (OIDC)

1. Gehe zu **Admin-Bereich** > **Applications** > **Providers**.
2. Klicke **Create**.
3. Waehle **OAuth2/OpenID Provider**.
4. Konfiguriere:
   - **Name:** `grafana-provider` (oder der Name des Zielservices)
   - **Authorization Flow:** `default-provider-authorization-implicit-consent` (fuer interne Tools empfohlen, damit Benutzer nicht jedes Mal explizit zustimmen muessen)
   - **Client type:** `Confidential`
   - **Client ID:** wird automatisch generiert (kopieren!)
   - **Client Secret:** wird automatisch generiert (kopieren!)
   - **Redirect URIs:** Die Callback-URL des Zielservices (siehe pro Service unten)
   - **Signing Key:** Waehle den automatisch erstellten Self-Signed-Key
5. Unter **Advanced protocol settings:**
   - **Scopes:** `openid`, `profile`, `email`
   - **Subject mode:** `Based on the User's hashed ID`
   - **Token validity:** Access Token 5 Minuten, Refresh Token 30 Tage
6. Klicke **Finish**.

#### 5.2 Application erstellen

1. Gehe zu **Admin-Bereich** > **Applications** > **Applications**.
2. Klicke **Create**.
3. Konfiguriere:
   - **Name:** `Grafana` (oder der Name des Services)
   - **Slug:** `grafana` (wird Teil der OIDC-URLs)
   - **Provider:** Waehle den eben erstellten Provider
   - **Launch URL:** `https://grafana.example.com` (optional, fuer das Authentik-Portal)
   - **Icon:** Optional, ein Icon fuer das Authentik-Portal
4. Klicke **Create**.

#### 5.3 OIDC Endpoints

Nach dem Erstellen von Provider und Application stehen folgende Endpoints bereit:

| Endpoint          | URL                                                          |
|-------------------|--------------------------------------------------------------|
| Authorization     | `https://auth.example.com/application/o/authorize/`          |
| Token             | `https://auth.example.com/application/o/token/`              |
| Userinfo          | `https://auth.example.com/application/o/userinfo/`           |
| JWKS              | `https://auth.example.com/application/o/{slug}/jwks/`        |
| OpenID Config     | `https://auth.example.com/application/o/{slug}/.well-known/openid-configuration` |

Ersetze `{slug}` durch den Slug der jeweiligen Application (z.B. `grafana`).

---

### 6. Services anbinden

#### 6a. Grafana

Grafana hat native Unterstuetzung fuer Generic OAuth, was direkt mit Authentik funktioniert.

##### Authentik-Seite

1. Erstelle einen **OAuth2/OpenID Provider** mit:
   - **Name:** `grafana-provider`
   - **Redirect URI:** `https://grafana.example.com/login/generic_oauth`
   - **Scopes:** `openid profile email`
2. Erstelle eine **Application** mit:
   - **Name:** `Grafana`
   - **Slug:** `grafana`
   - **Provider:** `grafana-provider`
3. Notiere **Client ID** und **Client Secret**.

##### Grafana-Seite

Fuege folgende Umgebungsvariablen zur Grafana-Konfiguration im `stacks/observability/docker-compose.yml` hinzu:

```bash
# --- Authentik SSO ---
GF_AUTH_GENERIC_OAUTH_ENABLED=true
GF_AUTH_GENERIC_OAUTH_NAME=Authentik
GF_AUTH_GENERIC_OAUTH_CLIENT_ID=<Client ID aus Authentik>
GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET=<Client Secret aus Authentik>
GF_AUTH_GENERIC_OAUTH_AUTH_URL=https://auth.example.com/application/o/authorize/
GF_AUTH_GENERIC_OAUTH_TOKEN_URL=https://auth.example.com/application/o/token/
GF_AUTH_GENERIC_OAUTH_API_URL=https://auth.example.com/application/o/userinfo/
GF_AUTH_GENERIC_OAUTH_SCOPES=openid profile email
GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_PATH=contains(groups[*], 'grafana-admins') && 'Admin' || contains(groups[*], 'grafana-editors') && 'Editor' || 'Viewer'
GF_AUTH_GENERIC_OAUTH_ALLOW_ASSIGN_GRAFANA_ADMIN=true
GF_AUTH_GENERIC_OAUTH_AUTO_LOGIN=false
GF_AUTH_SIGNOUT_REDIRECT_URL=https://auth.example.com/application/o/grafana/end-session/
```

##### Rollen-Mapping

Authentik-Gruppen werden auf Grafana-Rollen gemappt:

| Authentik-Gruppe    | Grafana-Rolle | Beschreibung                               |
|---------------------|---------------|--------------------------------------------|
| `grafana-admins`    | Admin         | Vollzugriff (Datenquellen, Benutzer, etc.) |
| `grafana-editors`   | Editor        | Dashboards erstellen und bearbeiten        |
| (alle anderen)      | Viewer        | Nur Dashboards ansehen                     |

Erstelle diese Gruppen in Authentik unter **Directory** > **Groups** und weise Benutzer den jeweiligen Gruppen zu.

##### Testen

1. Starte Grafana neu: `docker restart toolbox-grafana`
2. Oeffne `https://grafana.example.com`.
3. Ein Button "Sign in with Authentik" sollte erscheinen.
4. Klicke darauf und melde dich mit deinem Authentik-Account an.
5. Du wirst zurueck zu Grafana geleitet und bist eingeloggt.

---

#### 6b. Sentry

Sentry unterstuetzt SAML und OIDC. OIDC ist einfacher einzurichten.

##### Authentik-Seite

1. Erstelle einen **OAuth2/OpenID Provider** mit:
   - **Name:** `sentry-provider`
   - **Redirect URI:** `https://sentry.example.com/auth/sso/`
   - **Scopes:** `openid profile email`
2. Erstelle eine **Application** mit:
   - **Name:** `Sentry`
   - **Slug:** `sentry`
   - **Provider:** `sentry-provider`
3. Notiere **Client ID** und **Client Secret**.

##### Sentry-Seite

Sentry benoetigt die SSO-Konfiguration ueber die Sentry-UI und Umgebungsvariablen:

```bash
# Umgebungsvariablen fuer stacks/error-tracking/docker-compose.yml
SENTRY_AUTH_PROVIDER=oidc
SENTRY_OIDC_CLIENT_ID=<Client ID aus Authentik>
SENTRY_OIDC_CLIENT_SECRET=<Client Secret aus Authentik>
SENTRY_OIDC_ISSUER=https://auth.example.com/application/o/sentry/
SENTRY_OIDC_SCOPE=openid profile email
```

Alternativ ueber die Sentry-Admin-UI:

1. Melde dich als Admin bei Sentry an.
2. Gehe zu **Settings** > **Auth** (Organisations-Ebene).
3. Klicke **Configure** bei OIDC/OAuth2.
4. Trage die Authentik-Endpoints ein:
   - **Client ID:** aus Authentik
   - **Client Secret:** aus Authentik
   - **Authorize URL:** `https://auth.example.com/application/o/authorize/`
   - **Token URL:** `https://auth.example.com/application/o/token/`
   - **Userinfo URL:** `https://auth.example.com/application/o/userinfo/`
5. Aktiviere **Allow new users to sign up via SSO**.

##### Testen

1. Starte Sentry neu falls Umgebungsvariablen geaendert wurden.
2. Oeffne `https://sentry.example.com`.
3. Klicke "Sign in with SSO".
4. Du wirst zu Authentik weitergeleitet, meldest dich an, und wirst zurueck zu Sentry geleitet.

---

#### 6c. PostHog

PostHog unterstuetzt SAML-basiertes SSO in der Self-Hosted-Version.

##### Authentik-Seite

1. Erstelle einen **SAML Provider** mit:
   - **Name:** `posthog-provider`
   - **ACS URL:** `https://posthog.example.com/complete/saml/`
   - **Issuer/Entity ID:** `https://auth.example.com`
   - **Service Provider Binding:** `Post`
   - **Signing Certificate:** Waehle den Self-Signed-Key
2. Erstelle eine **Application** mit:
   - **Name:** `PostHog`
   - **Slug:** `posthog`
   - **Provider:** `posthog-provider`

##### PostHog-Seite

1. Melde dich als Admin bei PostHog an.
2. Gehe zu **Organization Settings** > **Authentication Domains**.
3. Fuelle aus:
   - **Domain:** deine E-Mail-Domain (z.B. `example.com`)
   - **SAML Entity ID:** `https://auth.example.com`
   - **SAML ACS URL:** `https://posthog.example.com/complete/saml/`
   - **SAML SSO URL:** `https://auth.example.com/application/o/posthog/`
   - **SAML x509 Certificate:** Kopiere das Zertifikat aus Authentik (unter Provider > Signing Certificate > Download)
4. Aktiviere **Enforce SSO** um lokale Logins zu deaktivieren.
5. Aktiviere **Automatically provision users** um neue Benutzer automatisch anzulegen.

##### Testen

1. Oeffne `https://posthog.example.com` in einem Inkognito-Fenster.
2. Gib deine E-Mail-Adresse ein.
3. PostHog erkennt die Domain und leitet zu Authentik weiter.
4. Nach Anmeldung wirst du automatisch in PostHog eingeloggt.

---

#### 6d. Unleash

Unleash unterstuetzt OIDC nativ.

##### Authentik-Seite

1. Erstelle einen **OAuth2/OpenID Provider** mit:
   - **Name:** `unleash-provider`
   - **Redirect URI:** `https://unleash.example.com/auth/oidc/callback`
   - **Scopes:** `openid profile email`
2. Erstelle eine **Application** mit:
   - **Name:** `Unleash`
   - **Slug:** `unleash`
   - **Provider:** `unleash-provider`
3. Notiere **Client ID** und **Client Secret**.

##### Unleash-Seite

Fuege folgende Umgebungsvariablen zur Unleash-Konfiguration hinzu:

```bash
# Umgebungsvariablen fuer stacks/feature-flags/docker-compose.yml
AUTH_TYPE=open-id-connect
AUTH_OIDC_DISCOVER_URL=https://auth.example.com/application/o/unleash/.well-known/openid-configuration
AUTH_OIDC_CLIENT_ID=<Client ID aus Authentik>
AUTH_OIDC_CLIENT_SECRET=<Client Secret aus Authentik>
AUTH_OIDC_ENABLE_GROUPS_SYNCING=true
AUTH_OIDC_AUTO_CREATE=true
AUTH_OIDC_EMAIL_DOMAINS=example.com
```

##### Testen

1. Starte Unleash neu: `docker restart toolbox-unleash`
2. Oeffne `https://unleash.example.com`.
3. Ein "Sign in with OpenID Connect" Button erscheint.
4. Klicke darauf und melde dich bei Authentik an.

---

#### 6e. MinIO

MinIO unterstuetzt OIDC fuer die Console-Anmeldung.

##### Authentik-Seite

1. Erstelle einen **OAuth2/OpenID Provider** mit:
   - **Name:** `minio-provider`
   - **Redirect URI:** `https://minio-console.example.com/oauth_callback`
   - **Scopes:** `openid profile email minio-policy`
2. Erstelle eine **Application** mit:
   - **Name:** `MinIO`
   - **Slug:** `minio`
   - **Provider:** `minio-provider`
3. Erstelle einen **Scope Mapping** fuer MinIO-Policies:
   - Gehe zu **Customization** > **Property Mappings** > **Create** > **Scope Mapping**.
   - **Name:** `minio-policy`
   - **Scope name:** `minio-policy`
   - **Expression:**
     ```python
     return {
         "policy": "readwrite" if ak_is_group_member(request.user, name="minio-admins") else "readonly"
     }
     ```
4. Fuege den neuen Scope Mapping zum MinIO Provider hinzu (unter Provider > Edit > Scope Mapping).

##### MinIO-Seite

Fuege folgende Umgebungsvariablen zur MinIO-Konfiguration hinzu:

```bash
# Umgebungsvariablen fuer stacks/core-data/docker-compose.yml
MINIO_IDENTITY_OPENID_CONFIG_URL=https://auth.example.com/application/o/minio/.well-known/openid-configuration
MINIO_IDENTITY_OPENID_CLIENT_ID=<Client ID aus Authentik>
MINIO_IDENTITY_OPENID_CLIENT_SECRET=<Client Secret aus Authentik>
MINIO_IDENTITY_OPENID_CLAIM_NAME=policy
MINIO_IDENTITY_OPENID_SCOPES=openid,profile,email,minio-policy
MINIO_IDENTITY_OPENID_REDIRECT_URI=https://minio-console.example.com/oauth_callback
MINIO_IDENTITY_OPENID_DISPLAY_NAME=Authentik
```

##### MinIO Policy erstellen

MinIO muss eine Policy haben, die dem OIDC-Claim entspricht:

```bash
# Erstelle die readonly Policy
docker exec toolbox-minio mc admin policy create local readonly /dev/stdin <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::*"]
    }
  ]
}
EOF

# Erstelle die readwrite Policy (falls nicht vorhanden)
docker exec toolbox-minio mc admin policy create local readwrite /dev/stdin <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:*"],
      "Resource": ["arn:aws:s3:::*"]
    }
  ]
}
EOF
```

##### Testen

1. Starte MinIO neu: `docker restart toolbox-minio`
2. Oeffne `https://minio-console.example.com`.
3. Ein "Login with Authentik" Button erscheint neben dem normalen Login.
4. Klicke darauf und melde dich bei Authentik an.

---

#### 6f. Uptime Kuma

Uptime Kuma hat keine native OIDC/SAML-Unterstuetzung. Die Loesung ist Authentik's **Forward Auth Proxy**.

##### Funktionsweise

```
Benutzer --> Coolify (Traefik) --> Forward Auth Check --> Authentik
                                      |
                              Authentik sagt "OK"
                                      |
                              Traefik leitet weiter --> Uptime Kuma
```

Traefik prueft bei jedem Request an Uptime Kuma zunaechst bei Authentik, ob der Benutzer angemeldet ist. Nur authentifizierte Requests werden weitergeleitet.

##### Authentik-Seite

1. Erstelle einen **Proxy Provider** mit:
   - **Name:** `uptime-kuma-provider`
   - **Authorization Flow:** `default-provider-authorization-implicit-consent`
   - **Mode:** `Forward auth (single application)`
   - **External host:** `https://status.example.com`
2. Erstelle eine **Application** mit:
   - **Name:** `Uptime Kuma`
   - **Slug:** `uptime-kuma`
   - **Provider:** `uptime-kuma-provider`
3. Erstelle einen **Outpost** (falls noch keiner existiert):
   - Gehe zu **Applications** > **Outposts**.
   - Klicke **Create**.
   - **Name:** `toolbox-outpost`
   - **Type:** `Proxy`
   - **Integration:** Waehle die Docker-Integration (oder erstelle eine neue, die auf `unix:///var/run/docker.sock` zeigt)
   - **Applications:** Fuege `Uptime Kuma` hinzu.
   - Authentik startet automatisch einen Outpost-Container.

##### Traefik (Coolify) Konfiguration

Da Coolify Traefik verwendet, muessen Traefik-Labels zum Uptime-Kuma-Service hinzugefuegt werden:

```yaml
# In stacks/monitoring/docker-compose.yml - labels fuer uptime-kuma
services:
  uptime-kuma:
    # ... bestehende Konfiguration ...
    labels:
      # Forward Auth Middleware
      traefik.http.middlewares.authentik.forwardauth.address: "http://toolbox-authentik-server:9000/outpost.goauthentik.io/auth/traefik"
      traefik.http.middlewares.authentik.forwardauth.trustForwardHeader: "true"
      traefik.http.middlewares.authentik.forwardauth.authResponseHeaders: "X-authentik-username,X-authentik-groups,X-authentik-email,X-authentik-name,X-authentik-uid,X-authentik-jwt,X-authentik-meta-jwks,X-authentik-meta-outpost,X-authentik-meta-provider,X-authentik-meta-app,X-authentik-meta-version"
```

> **Hinweis:** Die exakte Traefik-Konfiguration haengt von der Coolify-Version ab. Moeglicherweise muessen die Labels in Coolify's UI unter "Advanced" > "Custom Labels" gesetzt werden.

##### Alternativer Ansatz: Authentik Embedded Outpost

Falls die Traefik-Labels nicht in Coolify konfigurierbar sind, kann die Authentik-interne Proxy-Funktion genutzt werden. Dies erfordert, dass Uptime Kuma nur ueber den Authentik-Proxy erreichbar ist, nicht direkt ueber Coolify.

##### Testen

1. Oeffne `https://status.example.com` im Inkognito-Modus.
2. Du wirst automatisch zur Authentik-Login-Seite weitergeleitet.
3. Nach Anmeldung wirst du zu Uptime Kuma weitergeleitet.

> **Wichtig:** Uptime Kumas eigenes Login-System bleibt aktiv. Der erste Login nach dem Forward-Auth erstellt keinen lokalen Uptime-Kuma-Account. Du musst weiterhin einen lokalen Admin-Account in Uptime Kuma fuer die initiale Konfiguration haben.

---

#### 6g. Infisical

Infisical unterstuetzt SAML-basiertes SSO.

##### Authentik-Seite

1. Erstelle einen **SAML Provider** mit:
   - **Name:** `infisical-provider`
   - **ACS URL:** `https://infisical.example.com/api/v1/sso/saml2/callback`
   - **Issuer/Entity ID:** `https://auth.example.com`
   - **Service Provider Binding:** `Post`
   - **Signing Certificate:** Waehle den Self-Signed-Key
   - **NameID Property Mapping:** `Email`
2. Erstelle eine **Application** mit:
   - **Name:** `Infisical`
   - **Slug:** `infisical`
   - **Provider:** `infisical-provider`

##### Infisical-Seite

1. Melde dich als Admin bei Infisical an.
2. Gehe zu **Organization Settings** > **Security** > **SAML SSO**.
3. Konfiguriere:
   - **Entrypoint (SSO URL):** `https://auth.example.com/application/saml/infisical/sso/binding/redirect/`
   - **Issuer:** `https://auth.example.com`
   - **Certificate:** Lade das Zertifikat aus Authentik herunter (Provider > Signing Certificate) und fuege es ein.
4. Klicke **Enable SAML SSO**.
5. Optional: Aktiviere **Enforce SAML SSO** um lokale Logins zu deaktivieren.

##### Testen

1. Oeffne `https://infisical.example.com` im Inkognito-Modus.
2. Klicke "Continue with SAML SSO".
3. Gib deine E-Mail-Adresse ein.
4. Du wirst zu Authentik weitergeleitet, meldest dich an, und wirst zurueck zu Infisical geleitet.

---

### 7. Benutzer- und Gruppenverwaltung

#### 7.1 Gruppen erstellen

Erstelle in Authentik unter **Directory** > **Groups** folgende Gruppen:

| Gruppenname         | Zweck                                        |
|---------------------|----------------------------------------------|
| `admins`            | Vollzugriff auf alle Services                |
| `developers`        | Zugriff auf Entwickler-Tools                 |
| `viewers`           | Nur-Lese-Zugriff                             |
| `grafana-admins`    | Grafana-Admin-Rolle                          |
| `grafana-editors`   | Grafana-Editor-Rolle                         |
| `minio-admins`      | MinIO readwrite-Policy                       |

#### 7.2 Gruppen den Applications zuweisen

Standardmaessig hat jeder Authentik-Benutzer Zugriff auf alle Applications. Um den Zugriff einzuschraenken:

1. Gehe zu **Admin-Bereich** > **Applications** > **Applications**.
2. Waehle eine Application (z.B. "Grafana").
3. Unter **Policy / Group / User Bindings** klicke **Bind existing policy/group/user**.
4. Waehle die Gruppe(n), die Zugriff haben sollen.
5. Setze den Haken bei **Negate result** NICHT.
6. Wiederhole fuer jede Application.

Beispiel-Zuordnung:

| Application   | Zugelassene Gruppen                       |
|---------------|-------------------------------------------|
| Grafana       | `admins`, `developers`, `viewers`         |
| Sentry        | `admins`, `developers`                    |
| PostHog       | `admins`, `developers`                    |
| Unleash       | `admins`, `developers`                    |
| MinIO         | `admins`                                  |
| Uptime Kuma   | `admins`, `developers`, `viewers`         |
| Infisical     | `admins`                                  |

#### 7.3 Benutzer einladen

1. Gehe zu **Directory** > **Users** > **Create**.
2. Fuege den Benutzer hinzu (Username, E-Mail, Name).
3. Weise ihn den entsprechenden Gruppen zu.
4. Erstelle einen **Recovery Link** (unter User > Recovery):
   - Der Link ermoeglicht dem Benutzer, sein Passwort zu setzen.
   - Sende den Link per E-Mail oder sicherem Kanal.

Alternativ per Invite-Flow:

1. Gehe zu **Directory** > **Invitations** > **Create**.
2. Setze einen Namen und optional eine Ablaufzeit.
3. Kopiere den generierten Einladungslink.
4. Sende den Link an den neuen Benutzer.
5. Der Benutzer registriert sich ueber den Link und wird automatisch den vordefinierten Gruppen zugewiesen.

#### 7.4 Offboarding

Wenn ein Teammitglied das Team verlaesst:

1. Gehe zu **Directory** > **Users**.
2. Waehle den Benutzer.
3. Klicke **Deactivate** (nicht loeschen, um Audit-Logs zu bewahren).
4. Der Benutzer kann sich sofort nirgendwo mehr anmelden.
5. Alle aktiven Sessions werden automatisch beendet.

---

### 8. Multi-Factor Authentication (MFA)

#### 8.1 TOTP einrichten (Authenticator App)

1. Gehe zu **Admin-Bereich** > **Flows and Stages** > **Stages**.
2. Suche den Stage `default-authentication-mfa-validation`.
3. Klicke darauf und pruefe, dass **TOTP Authenticators** aktiviert ist.

Benutzer koennen TOTP selbst einrichten:

1. Benutzer meldet sich an und oeffnet `https://auth.example.com/if/user/#/settings`.
2. Unter **MFA Devices** klickt er **Enroll** > **TOTP**.
3. Scannt den QR-Code mit einer Authenticator-App (Google Authenticator, Authy, etc.).
4. Bestaetigt mit einem Code.

#### 8.2 WebAuthn einrichten (Hardware-Keys)

WebAuthn erlaubt die Anmeldung mit Hardware-Sicherheitsschluesseln (YubiKey, etc.) oder biometrischen Methoden (Fingerabdruck, Face ID).

1. Pruefe, dass der Stage `default-authentication-mfa-validation` auch **WebAuthn Authenticators** aktiviert hat.
2. Benutzer gehen zu ihren Einstellungen und klicken **Enroll** > **WebAuthn**.
3. Der Browser fordert zur Registrierung des Sicherheitsschluessels auf.

#### 8.3 MFA erzwingen

Um MFA fuer alle Benutzer zu erzwingen:

1. Gehe zu **Admin-Bereich** > **Flows and Stages** > **Stages**.
2. Finde den Stage `default-authentication-mfa-validation`.
3. Unter **Stage Configuration:**
   - Setze **Not configured action** auf `Force user to configure an authenticator`.
4. Damit wird jeder Benutzer beim naechsten Login gezwungen, MFA einzurichten.

Um MFA nur fuer bestimmte Gruppen zu erzwingen:

1. Erstelle eine **Policy** unter **Flows and Stages** > **Policies** > **Create**.
2. Waehle **Expression Policy**.
3. **Name:** `require-mfa-for-admins`
4. **Expression:**
   ```python
   return ak_is_group_member(request.user, name="admins")
   ```
5. Binde diese Policy an den MFA-Stage im Authentifizierungsflow.

---

### 9. DSGVO-Aspekte

#### 9.1 Datenhoheit

Alle Authentifizierungsdaten verbleiben auf dem eigenen Server:

- Benutzerkonten (Name, E-Mail, Passwort-Hashes)
- Sessions und Tokens
- Gruppen und Berechtigungen
- Audit-Logs aller Anmelde- und Verwaltungsvorgaenge
- MFA-Registrierungen (TOTP-Seeds, WebAuthn-Credentials)

Kein Drittanbieter hat Zugriff auf diese Daten.

#### 9.2 Audit-Logs

Authentik protokolliert automatisch:

- Erfolgreiche und fehlgeschlagene Anmeldungen
- Aenderungen an Benutzern und Gruppen
- Aenderungen an Applications und Providers
- Token-Ausstellungen und -Widerrufe
- Administrative Aktionen

Einsehbar unter **Admin-Bereich** > **Events** > **Logs**.

Log-Retention konfigurieren:

1. Gehe zu **System** > **Settings**.
2. Setze **Event retention** (Standard: 365 Tage).

#### 9.3 Recht auf Loeschung (Art. 17 DSGVO)

Wenn ein Benutzer die Loeschung seiner Daten verlangt:

1. Gehe zu **Directory** > **Users**.
2. Waehle den Benutzer.
3. Klicke **Delete**.
4. Authentik loescht:
   - Das Benutzerkonto
   - Alle Sessions
   - Alle MFA-Registrierungen
   - Alle Token
5. Audit-Logs bleiben erhalten (berechtigtes Interesse: Sicherheit). Falls noetig, koennen auch diese geloescht werden:
   ```bash
   docker exec toolbox-authentik-server \
     ak shell -c "from authentik.events.models import Event; Event.objects.filter(user__username='benutzername').delete()"
   ```

#### 9.4 Session-Management

Benutzer koennen ihre aktiven Sessions selbst einsehen und beenden:

1. Oeffne `https://auth.example.com/if/user/#/settings`.
2. Unter **Sessions** werden alle aktiven Sessions angezeigt.
3. Einzelne Sessions koennen beendet werden.

Administratoren koennen Sessions aller Benutzer unter **Directory** > **Users** > **Sessions** verwalten.

---

### 10. Troubleshooting

#### Redirect Loops

**Symptom:** Browser zeigt "Zu viele Weiterleitungen" nach dem Login.

**Ursachen und Loesungen:**

1. **Falsche Redirect URI:** Pruefe, ob die Redirect URI im Authentik-Provider exakt mit der Callback-URL des Services uebereinstimmt. Beachte: trailing Slash, http vs. https.
2. **Cookie-Probleme:** Pruefe, ob die Domain des Services und die Domain von Authentik auf unterschiedlichen Domains liegen (Same-Site-Cookie-Probleme). Loesung: Stelle sicher, dass Authentik und die Services unter derselben Top-Level-Domain laufen (z.B. `auth.example.com` und `grafana.example.com`).
3. **Mixed Content:** Stelle sicher, dass alle URLs HTTPS verwenden. Kein Mischung von HTTP und HTTPS.

#### Zertifikatsfehler

**Symptom:** "Certificate verify failed" in den Service-Logs.

**Loesung:** Da alle Services im Docker-Netzwerk kommunizieren, verwenden Service-zu-Service-Aufrufe HTTP (nicht HTTPS). Stelle sicher, dass die Token-URL und Userinfo-URL in der Service-Konfiguration die oeffentliche HTTPS-URL verwenden und nicht die interne HTTP-URL, es sei denn, du hast die Zertifikate korrekt konfiguriert.

Fuer interne Kommunikation (innerhalb des Docker-Netzwerks):

```
# Token URL (intern, falls Zertifikatsprobleme):
http://toolbox-authentik-server:9000/application/o/token/

# Token URL (extern, empfohlen):
https://auth.example.com/application/o/token/
```

#### CORS-Fehler

**Symptom:** "Access to XMLHttpRequest has been blocked by CORS policy" im Browser.

**Loesung:** Pruefe die Redirect-URI-Konfiguration im Authentik-Provider. Die Origin der anfragenden Seite muss in der Redirect-URI erlaubt sein. Authentik setzt CORS-Header automatisch basierend auf den konfigurierten Redirect-URIs.

#### Token-Debugging

1. Gehe zu **Admin-Bereich** > **Applications** > **Provider** > (dein Provider).
2. Unter **Preview** kannst du ein Test-Token generieren und dessen Inhalt inspizieren.
3. Pruefe, ob die erwarteten Claims (email, groups, name) enthalten sind.

Alternativ per Kommandozeile:

```bash
# JWT debuggen (erfordert jq)
echo "DEIN_JWT_TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | jq .
```

#### Authentik-Logs pruefen

```bash
# Server-Logs
docker logs toolbox-authentik-server --tail 100

# Worker-Logs
docker logs toolbox-authentik-worker --tail 100

# Nur Fehler
docker logs toolbox-authentik-server 2>&1 | grep -i error

# In der Authentik-UI
# Admin-Bereich > System > Logs
```

#### Benutzer kann sich nicht anmelden

1. Pruefe, ob der Benutzer in Authentik aktiv ist (**Directory** > **Users** > Status).
2. Pruefe, ob der Benutzer der richtigen Gruppe zugewiesen ist.
3. Pruefe, ob die Application die richtige Gruppenbindung hat.
4. Pruefe die Audit-Logs unter **Events** > **Logs** fuer den betreffenden Benutzer.
5. Pruefe, ob der Benutzer MFA eingerichtet hat, falls MFA erzwungen wird.

#### Authentik-Container startet nicht

```bash
# Pruefe ob PostgreSQL erreichbar ist
docker exec toolbox-authentik-server \
  python -c "import psycopg2; psycopg2.connect(host='postgres', dbname='authentik', user='toolbox', password='...')"

# Pruefe ob Redis erreichbar ist
docker exec toolbox-authentik-server \
  python -c "import redis; r = redis.Redis(host='redis', port=6379, password='...', db=2); print(r.ping())"

# Pruefe die Datenbank-Migration
docker exec toolbox-authentik-server ak migrate --check
```

---

### Checkliste: Authentik vollstaendig eingerichtet

- [ ] Authentik Server und Worker laufen und sind healthy
- [ ] Admin-Account (`akadmin`) erstellt und Passwort geaendert
- [ ] Branding konfiguriert (Logo, Titel)
- [ ] Gruppen erstellt (`admins`, `developers`, `viewers`, service-spezifische Gruppen)
- [ ] Benutzer erstellt und Gruppen zugewiesen
- [ ] OIDC Provider + Application fuer Grafana erstellt und getestet
- [ ] OIDC Provider + Application fuer Sentry erstellt und getestet
- [ ] SAML Provider + Application fuer PostHog erstellt und getestet
- [ ] OIDC Provider + Application fuer Unleash erstellt und getestet
- [ ] OIDC Provider + Application fuer MinIO erstellt und getestet
- [ ] Proxy Provider + Application fuer Uptime Kuma erstellt und getestet
- [ ] SAML Provider + Application fuer Infisical erstellt und getestet
- [ ] MFA (TOTP und/oder WebAuthn) konfiguriert
- [ ] MFA-Enforcement-Policy aktiv (mindestens fuer Admins)
- [ ] Audit-Log-Retention konfiguriert
- [ ] Alle Secrets (Client IDs, Client Secrets) in Infisical gespeichert

---

## 2. Grafana Alloy — Log-Shipping


Dieses Dokument beschreibt die Einrichtung von Grafana Alloy als zentrale Telemetrie-Pipeline. Alloy sammelt Logs von allen Docker-Containern und schickt sie an Loki, sodass sie in Grafana durchsuchbar sind. Optional kann Alloy auch Metriken an Prometheus und Traces an Tempo weiterleiten.

> **Voraussetzung:** Der Observability-Stack (Loki, Prometheus, Tempo, Grafana) muss bereits laufen. Siehe [04-deploy-stack.md](04-deploy-stack.md).

---

### 1. Was ist Grafana Alloy?

Grafana Alloy ist ein OpenTelemetry-kompatibler Telemetrie-Collector von Grafana Labs. Es ist der offizielle Nachfolger von drei separaten Tools:

- **Promtail:** Log-Shipping an Loki (deprecated)
- **Grafana Agent:** Metrik-Sammlung (deprecated)
- **Grafana Agent Flow:** Flow-basierte Konfiguration (deprecated)

Alloy vereint alle drei Funktionen in einem einzigen Binary mit einer deklarativen Konfigurationssprache.

#### Was Alloy in der Toolbox tut

Ohne Alloy sind Container-Logs nur ueber `docker logs <container>` erreichbar. Das ist problematisch:

- Logs gehen verloren, wenn Container neu gestartet werden (je nach Log-Driver-Konfiguration).
- Keine zentrale Suche ueber alle Container hinweg.
- Keine Alerting-Moeglichkeit auf Log-Inhalte.
- Kein Korrelieren von Logs mit Metriken und Traces.

Mit Alloy werden alle Container-Logs automatisch an Loki geschickt. In Grafana koennen sie dann durchsucht, gefiltert und fuer Alerts verwendet werden.

#### Kernfunktionen

| Funktion               | Quelle                    | Ziel        | Protokoll         |
|-------------------------|---------------------------|-------------|--------------------|
| Docker-Container-Logs   | Docker Socket             | Loki        | Loki Push API      |
| System-Logs             | /var/log/*                | Loki        | Loki Push API      |
| Metriken                | Prometheus-Targets        | Prometheus  | Remote Write       |
| Traces                  | OpenTelemetry-SDKs        | Tempo       | OTLP gRPC/HTTP     |

---

### 2. Architektur

#### Datenfluss

```
+------------------+     +------------------+     +------------------+
| Docker Container |     | Docker Container |     | Docker Container |
| toolbox-postgres |     | toolbox-grafana  |     | toolbox-posthog  |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         | stdout/stderr          | stdout/stderr          | stdout/stderr
         |                        |                        |
+--------v------------------------v------------------------v---------+
|                        Docker Engine                                |
|                     /var/run/docker.sock                             |
+--------+-----------------------------------------------------------+
         |
         | Docker API (Log-Stream)
         |
+--------v-----------------------------------------------------------+
|                      Grafana Alloy                                  |
|  toolbox-alloy                                                      |
|                                                                     |
|  +-------------------+    +-------------------+    +--------------+ |
|  | discovery.docker  |--->| discovery.relabel |--->| loki.source  | |
|  | (Container finden)|    | (Labels setzen)   |    | .docker      | |
|  +-------------------+    +-------------------+    +------+-------+ |
|                                                           |         |
|                                                    +------v-------+ |
|                                                    | loki.write   | |
|                                                    | (an Loki     | |
|                                                    |  senden)     | |
|                                                    +--------------+ |
+---------------------------------------------------------------------+
         |
         | HTTP POST /loki/api/v1/push
         |
+--------v-----------------------------------------------------------+
|                         Loki                                        |
|  toolbox-loki:3100                                                  |
|  (Log-Aggregation und -Speicherung)                                 |
+--------+-----------------------------------------------------------+
         |
         | LogQL-Abfragen
         |
+--------v-----------------------------------------------------------+
|                        Grafana                                      |
|  toolbox-grafana:3000                                               |
|  (Dashboards, Explore, Alerting)                                    |
+---------------------------------------------------------------------+
```

#### Zusaetzliche Datenquellen (optional)

```
+------------------+                  +------------------+
| /var/log/syslog  |                  | App mit OTLP-SDK |
| /var/log/auth.log|                  | (Traces)         |
+--------+---------+                  +--------+---------+
         |                                     |
         | loki.source.file                    | otelcol.receiver.otlp
         |                                     |
+--------v-------------------------------------v---------+
|                      Grafana Alloy                      |
+--------+----------------------------+------------------+
         |                            |
    loki.write                   otelcol.exporter.otlp
         |                            |
+--------v--------+          +--------v--------+
|      Loki       |          |      Tempo      |
+-----------------+          +-----------------+
```

#### Integration in die Toolbox

Alloy laeuft als eigener Stack im Docker-Netzwerk `toolbox`. Er hat Zugriff auf den Docker Socket (read-only) um Container-Logs zu lesen und kommuniziert direkt mit Loki, Prometheus und Tempo ueber deren interne Hostnames.

---

### 3. Stack Setup

#### Docker Compose

```yaml
# stacks/log-shipping/docker-compose.yml
# Grafana Alloy - Telemetrie-Pipeline fuer die Toolbox

services:
  # -----------------------------------------------
  # Grafana Alloy
  # -----------------------------------------------
  alloy:
    image: grafana/alloy:v1.3.1
    container_name: toolbox-alloy
    restart: unless-stopped
    command:
      - run
      - --server.http.listen-addr=0.0.0.0:12345
      - --storage.path=/var/lib/alloy/data
      - /etc/alloy/config.alloy
    volumes:
      # Docker Socket fuer Container-Discovery und Log-Streaming
      - /var/run/docker.sock:/var/run/docker.sock:ro
      # System-Logs (optional)
      - /var/log:/var/log:ro
      # Alloy-Konfiguration
      - ./configs/config.alloy:/etc/alloy/config.alloy:ro
      # Persistenter Speicher fuer Positionen (welche Logs bereits gelesen wurden)
      - alloy_data:/var/lib/alloy/data
    networks:
      - toolbox
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:12345/-/healthy"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
    # Kein Port nach aussen exponieren - nur innerhalb des Docker-Netzwerks
    # Debug-UI erreichbar unter http://toolbox-alloy:12345 (intern)

volumes:
  alloy_data:
    name: toolbox_alloy_data

networks:
  toolbox:
    external: true
    name: toolbox
```

#### Umgebungsvariablen (.env.example)

Alloy benoetigt keine Umgebungsvariablen. Die gesamte Konfiguration liegt in `config.alloy`. Falls du spaeter Authentifizierung fuer Loki oder Prometheus verwenden moechtest, koennen Umgebungsvariablen in der Compose-Datei ergaenzt werden.

```bash
# stacks/log-shipping/.env.example
# Grafana Alloy - keine Umgebungsvariablen erforderlich
# Die Konfiguration erfolgt vollstaendig ueber configs/config.alloy
```

---

### 4. Alloy Konfiguration (config.alloy)

Die Konfiguration folgt der Alloy-eigenen deklarativen Sprache. Jeder Block definiert eine Komponente, die Daten empfaengt, verarbeitet oder weiterleitet.

Erstelle die Datei `stacks/log-shipping/configs/config.alloy`:

```alloy
// =============================================================================
// Grafana Alloy Konfiguration fuer die Toolbox
// =============================================================================
// Diese Konfiguration sammelt Logs von allen Docker-Containern im
// "toolbox" Netzwerk und schickt sie an Loki.
// =============================================================================

// -----------------------------------------------------------------------------
// 1. Docker Container Discovery
// -----------------------------------------------------------------------------
// Findet alle laufenden Docker-Container ueber den Docker Socket.
// Jeder Container wird als Target mit seinen Labels (Name, Image, etc.)
// registriert.

discovery.docker "containers" {
  host = "unix:///var/run/docker.sock"

  // Nur Container im "toolbox" Netzwerk einbeziehen.
  // Entferne diesen Filter, wenn auch Container ausserhalb des
  // Netzwerks geloggt werden sollen.
  filter {
    name   = "network"
    values = ["toolbox"]
  }

  // Aktualisierungsintervall: wie oft nach neuen/gestoppten Containern
  // gesucht wird.
  refresh_interval = "10s"
}

// -----------------------------------------------------------------------------
// 2. Label-Transformation (Relabeling)
// -----------------------------------------------------------------------------
// Extrahiert nuetzliche Labels aus den Docker-Metadaten und setzt sie
// als Loki-Labels. Labels bestimmen, wie Logs in Loki indiziert und
// abgefragt werden koennen.

discovery.relabel "containers" {
  targets = discovery.docker.containers.targets

  // Container-Name als Label "container" setzen.
  // Docker-Format: /container-name -> container-name (ohne fuehrenden Slash)
  rule {
    source_labels = ["__meta_docker_container_name"]
    regex         = "/(.*)"
    target_label  = "container"
  }

  // Docker Compose Service-Name als Label "service"
  rule {
    source_labels = ["__meta_docker_container_label_com_docker_compose_service"]
    target_label  = "service"
  }

  // Docker Compose Projekt-Name als Label "project"
  rule {
    source_labels = ["__meta_docker_container_label_com_docker_compose_project"]
    target_label  = "project"
  }

  // Container-Image als Label "image"
  rule {
    source_labels = ["__meta_docker_container_image"]
    target_label  = "image"
  }

  // Container-ID als Label (fuer Debugging)
  rule {
    source_labels = ["__meta_docker_container_id"]
    target_label  = "container_id"
  }

  // Statisches Label "job" setzen
  rule {
    target_label = "job"
    replacement  = "docker"
  }

  // Statisches Label "env" setzen
  rule {
    target_label = "env"
    replacement  = "production"
  }
}

// -----------------------------------------------------------------------------
// 3. Docker Log Collection
// -----------------------------------------------------------------------------
// Liest die Logs aller entdeckten Container ueber die Docker API.
// Verbindet sich ueber den Docker Socket und streamt stdout/stderr.

loki.source.docker "containers" {
  host    = "unix:///var/run/docker.sock"
  targets = discovery.relabel.containers.output

  // Leite alle Logs an die Verarbeitungspipeline weiter
  forward_to = [loki.process.pipeline.receiver]

  // Lese ab der aktuellen Position (nicht alle alten Logs beim Start)
  refresh_interval = "5s"
}

// -----------------------------------------------------------------------------
// 4. Log-Verarbeitungspipeline
// -----------------------------------------------------------------------------
// Verarbeitet Logs bevor sie an Loki geschickt werden:
// - JSON-Parsing (falls Log im JSON-Format)
// - Level-Extraktion
// - Timestamp-Korrektur
// - Filtern von unererwuenschten Logs

loki.process "pipeline" {
  forward_to = [loki.write.default.receiver]

  // --- JSON-Parsing ---
  // Viele Container loggen im JSON-Format. Versuche, JSON zu parsen
  // und extrahiere gaengige Felder.
  stage.json {
    expressions = {
      level   = "level",
      msg     = "msg",
      message = "message",
      ts      = "ts",
      time    = "time",
    }
  }

  // --- Level-Label setzen ---
  // Falls ein "level"-Feld im JSON gefunden wurde, setze es als Label.
  // Erlaubt spaeter Abfragen wie: {level="error"}
  stage.labels {
    values = {
      level = "",
    }
  }

  // --- Level normalisieren ---
  // Verschiedene Anwendungen verwenden verschiedene Level-Formate.
  // Normalisiere auf Kleinbuchstaben.
  stage.label_drop {
    values = ["filename", "container_id"]
  }

  // --- Unerwuenschte Logs filtern ---
  // Health-Check-Logs erzeugen viel Rauschen. Filtere sie heraus.
  stage.drop {
    source     = ""
    expression = ".*healthcheck.*"
    drop_counter_reason = "healthcheck"
  }

  stage.drop {
    source     = ""
    expression = ".*GET /health.*"
    drop_counter_reason = "health_endpoint"
  }

  stage.drop {
    source     = ""
    expression = ".*GET /-/healthy.*"
    drop_counter_reason = "healthy_endpoint"
  }

  stage.drop {
    source     = ""
    expression = ".*GET /-/ready.*"
    drop_counter_reason = "ready_endpoint"
  }

  stage.drop {
    source     = ""
    expression = ".*GET /ready.*"
    drop_counter_reason = "ready_endpoint_2"
  }
}

// -----------------------------------------------------------------------------
// 5. Loki Write Endpoint
// -----------------------------------------------------------------------------
// Sendet die verarbeiteten Logs an Loki.
// Verwendet den internen Docker-Hostname "loki" (aus dem toolbox-Netzwerk).

loki.write "default" {
  endpoint {
    url = "http://loki:3100/loki/api/v1/push"

    // Batching-Konfiguration
    // Alloy sammelt Logs und sendet sie in Batches fuer bessere Performance.
    batch_wait    = "1s"
    batch_size    = 1048576  // 1 MB

    // Retry bei Fehlern
    retry_on_http_429 = true
  }

  external_labels = {
    cluster = "toolbox",
    host    = "server-01",
  }
}
```

#### Erklaerung der einzelnen Bloecke

##### discovery.docker

Dieser Block verbindet sich mit dem Docker Socket und entdeckt alle laufenden Container. Er liefert Metadaten-Labels, die mit `__meta_docker_` beginnen:

- `__meta_docker_container_name`: Container-Name (z.B. `/toolbox-postgres`)
- `__meta_docker_container_image`: Image-Name (z.B. `postgres:16-alpine`)
- `__meta_docker_container_id`: Container-ID
- `__meta_docker_container_label_*`: Alle Container-Labels (inkl. Docker Compose Labels)

Der Filter `network = "toolbox"` stellt sicher, dass nur Container im Toolbox-Netzwerk erfasst werden.

##### discovery.relabel

Transformiert die Docker-Metadaten-Labels in benutzerfreundliche Loki-Labels. Ohne Relabeling wuerden die Logs nur mit den internen `__meta_docker_*`-Labels versehen, die in Loki nicht angezeigt werden.

**Wichtig:** Halte die Anzahl der Labels klein. Jede einzigartige Label-Kombination erzeugt einen neuen Log-Stream in Loki. Zu viele Labels fuehren zu hoher "Label Cardinality" und schlechter Loki-Performance.

Empfohlene Labels:

| Label      | Beispielwert          | Zweck                                    |
|------------|-----------------------|------------------------------------------|
| `container`| `toolbox-postgres`    | Identifiziert den Container              |
| `service`  | `postgres`            | Docker Compose Service-Name              |
| `project`  | `core-data`           | Docker Compose Projekt                   |
| `job`      | `docker`              | Trennung von Docker-Logs und System-Logs |
| `env`      | `production`          | Umgebung                                 |
| `level`    | `error`               | Log-Level (aus JSON extrahiert)          |

##### loki.source.docker

Liest die tatsaechlichen Log-Zeilen von den entdeckten Containern. Verbindet sich ueber die Docker API und streamt stdout/stderr in Echtzeit. Entspricht konzeptionell `docker logs -f` fuer alle Container gleichzeitig.

##### loki.process

Eine Pipeline von Verarbeitungsschritten:

1. **stage.json:** Versucht, jede Log-Zeile als JSON zu parsen und extrahiert Felder.
2. **stage.labels:** Setzt extrahierte Felder als Loki-Labels.
3. **stage.drop:** Verwirft unerwuenschte Log-Zeilen (Health-Checks, Readiness-Probes).

##### loki.write

Sendet die verarbeiteten Logs an Loki. Die URL `http://loki:3100` funktioniert, weil Alloy und Loki im selben Docker-Netzwerk (`toolbox`) laufen.

---

### 5. Erweiterte Konfiguration

#### 5.1 System-Logs sammeln

Um auch System-Logs (/var/log) an Loki zu senden, fuege folgenden Block zur `config.alloy` hinzu:

```alloy
// -----------------------------------------------------------------------------
// System-Log-Quellen
// -----------------------------------------------------------------------------

// Syslog
local.file_match "syslog" {
  path_targets = [
    {__path__ = "/var/log/syslog", job = "system", source = "syslog"},
  ]
}

loki.source.file "syslog" {
  targets    = local.file_match.syslog.targets
  forward_to = [loki.write.default.receiver]
}

// Auth-Log (SSH-Logins, sudo, etc.)
local.file_match "authlog" {
  path_targets = [
    {__path__ = "/var/log/auth.log", job = "system", source = "authlog"},
  ]
}

loki.source.file "authlog" {
  targets    = local.file_match.authlog.targets
  forward_to = [loki.write.default.receiver]
}
```

#### 5.2 Prometheus Metriken scrapen

Alloy kann Prometheus-Metriken direkt scrapen und per Remote Write an Prometheus senden. Das ist nuetzlich, wenn Prometheus selbst keine neuen Targets scrapen soll (z.B. Kurzlebige Container):

```alloy
// -----------------------------------------------------------------------------
// Prometheus Metrics Scraping (optional)
// -----------------------------------------------------------------------------

// Entdecke Container mit dem Label "prometheus.scrape=true"
discovery.docker "metrics" {
  host = "unix:///var/run/docker.sock"

  filter {
    name   = "label"
    values = ["prometheus.scrape=true"]
  }
}

discovery.relabel "metrics" {
  targets = discovery.docker.metrics.targets

  // Scrape-Port aus Container-Label lesen
  rule {
    source_labels = ["__meta_docker_container_label_prometheus_port"]
    target_label  = "__address__"
    regex         = "(.*)"
    replacement   = "${1}"
  }

  // Metriken-Pfad aus Container-Label lesen (Standard: /metrics)
  rule {
    source_labels = ["__meta_docker_container_label_prometheus_path"]
    target_label  = "__metrics_path__"
  }

  rule {
    source_labels = ["__meta_docker_container_name"]
    regex         = "/(.*)"
    target_label  = "container"
  }
}

prometheus.scrape "docker_containers" {
  targets    = discovery.relabel.metrics.output
  forward_to = [prometheus.remote_write.default.receiver]

  scrape_interval = "30s"
}

prometheus.remote_write "default" {
  endpoint {
    url = "http://prometheus:9090/api/v1/write"
  }
}
```

Um einen Container fuer Metriken-Scraping zu markieren, fuege Labels zum Docker-Container hinzu:

```yaml
# In einer docker-compose.yml
services:
  my-app:
    image: my-app:latest
    labels:
      prometheus.scrape: "true"
      prometheus.port: "my-app:8080"
      prometheus.path: "/metrics"
```

#### 5.3 OpenTelemetry Traces empfangen

Falls deine Anwendungen OpenTelemetry-SDKs verwenden, kann Alloy als OTLP-Empfaenger dienen und Traces an Tempo weiterleiten:

```alloy
// -----------------------------------------------------------------------------
// OpenTelemetry Trace Collection (optional)
// -----------------------------------------------------------------------------

// OTLP gRPC Empfaenger (Port 4317)
otelcol.receiver.otlp "default" {
  grpc {
    endpoint = "0.0.0.0:4317"
  }

  http {
    endpoint = "0.0.0.0:4318"
  }

  output {
    traces = [otelcol.exporter.otlp.tempo.input]
  }
}

// Weiterleitung an Tempo
otelcol.exporter.otlp "tempo" {
  client {
    endpoint = "tempo:4317"

    tls {
      insecure = true
    }
  }
}
```

Falls du OTLP verwendest, exponiere die Ports in der `docker-compose.yml`:

```yaml
services:
  alloy:
    # ... bestehende Konfiguration ...
    # Ports nur im Docker-Netzwerk, nicht nach aussen:
    # 4317 = OTLP gRPC, 4318 = OTLP HTTP
```

Da Alloy und die Anwendungen im selben Docker-Netzwerk laufen, sind die Ports automatisch erreichbar. Die Anwendung sendet Traces an `http://toolbox-alloy:4318` (HTTP) oder `toolbox-alloy:4317` (gRPC).

#### 5.4 Einzelne Container ausschliessen

Um bestimmte Container von der Log-Sammlung auszuschliessen, fuege eine Drop-Regel im Relabeling hinzu:

```alloy
// In discovery.relabel "containers" einfuegen:

  // Container mit dem Label "logging=disable" ignorieren
  rule {
    source_labels = ["__meta_docker_container_label_logging"]
    regex         = "disable"
    action        = "drop"
  }
```

In der `docker-compose.yml` des zu ignorierenden Services:

```yaml
services:
  noisy-service:
    image: noisy:latest
    labels:
      logging: "disable"
```

---

### 6. Grafana Dashboards fuer Logs

#### 6.1 Loki als Datenquelle in Grafana

Loki sollte bereits als Datenquelle in Grafana konfiguriert sein (durch die Provisioning-Dateien unter `stacks/observability/configs/grafana/provisioning/datasources/`). Falls nicht:

1. Oeffne Grafana > **Connections** > **Data Sources** > **Add data source**.
2. Waehle **Loki**.
3. **URL:** `http://loki:3100`
4. Klicke **Save & Test**.

#### 6.2 LogQL Query-Beispiele

LogQL ist die Abfragesprache von Loki. Im Folgenden praktische Beispiele fuer die Toolbox:

##### Alle Logs eines bestimmten Containers

```logql
{container="toolbox-postgres"}
```

##### Fehler-Logs aller Toolbox-Container

```logql
{container=~"toolbox-.*"} |= "ERROR"
```

##### Fehler-Logs mit Level-Label (aus JSON-Parsing)

```logql
{container=~"toolbox-.*", level="error"}
```

##### Logs eines bestimmten Docker-Compose-Projekts

```logql
{project="observability"}
```

##### Logs durchsuchen (case-insensitive)

```logql
{container="toolbox-sentry"} |~ "(?i)database connection"
```

##### Bestimmte Log-Zeilen ausschliessen

```logql
{container="toolbox-grafana"} != "live.pipeline" != "healthcheck"
```

##### JSON-Felder extrahieren und filtern

```logql
{container="toolbox-posthog"} | json | level="error" | line_format "{{.message}}"
```

##### Log-Rate pro Container (Logs pro Sekunde, letzte 5 Minuten)

```logql
rate({job="docker"}[5m])
```

Ergebnis: ein Zahlenwert pro Container, der die Log-Rate zeigt. Nützlich um "noisy" Container zu identifizieren.

##### Top 5 Container nach Log-Volumen

```logql
topk(5, sum by (container) (rate({job="docker"}[1h])))
```

##### Fehler-Rate ueber Zeit

```logql
sum(rate({job="docker"} |= "ERROR" [5m])) by (container)
```

##### Log-Kontext: Zeilen vor und nach einem Fehler

In Grafana Explore:
1. Finde die Fehler-Zeile mit `{container="toolbox-sentry"} |= "ERROR"`.
2. Klicke auf die Zeile.
3. Klicke "Show context" um die umgebenden Zeilen zu sehen.

#### 6.3 Empfohlene Dashboard-Panels

Erstelle ein Dashboard "Toolbox Logs" in Grafana mit folgenden Panels:

| Panel-Titel                    | Typ            | LogQL-Query                                                          |
|--------------------------------|----------------|----------------------------------------------------------------------|
| Log-Volume nach Container      | Bar Chart      | `sum by (container) (rate({job="docker"}[5m]))`                      |
| Error-Rate                     | Time Series    | `sum(rate({job="docker"} \|= "ERROR" [5m])) by (container)`         |
| Aktuelle Fehler (letzte 15min) | Logs Panel     | `{job="docker"} \|= "ERROR" `                                       |
| PostgreSQL Logs                | Logs Panel     | `{container="toolbox-postgres"}`                                     |
| Redis Logs                     | Logs Panel     | `{container="toolbox-redis"}`                                        |
| Container Log-Raten (Tabelle)  | Table          | `sum by (container) (count_over_time({job="docker"}[1h]))`           |

---

### 7. Alerting auf Logs

#### 7.1 Loki Alert Rules in Grafana

Grafana kann direkt auf Loki-Queries alerten. Das ist maechtiger als Alerting nur auf Metriken, weil bestimmte Log-Muster erkannt werden koennen.

##### Alert einrichten: Error-Rate Spike

1. Oeffne Grafana > **Alerting** > **Alert Rules** > **New Alert Rule**.
2. Konfiguriere:
   - **Name:** `High Error Rate in Docker Containers`
   - **Data source:** Loki
   - **Query:**
     ```logql
     sum(rate({job="docker"} |= "ERROR" [5m]))
     ```
   - **Condition:** `IS ABOVE 0.5` (mehr als 0.5 Fehler pro Sekunde)
   - **Evaluation interval:** 1m
   - **For:** 5m (Alert erst nach 5 Minuten anhaltendem Fehler)
3. Unter **Labels and annotations:**
   - **Summary:** `Hohe Fehlerrate in Docker-Containern`
   - **Description:** `Die Fehlerrate ueber alle Container liegt bei {{ $value }} Fehler/s.`
4. Unter **Notification:**
   - Waehle den Alertmanager als Contact Point.

##### Alert: OOM Killer erkannt

```logql
{job="system", source="syslog"} |= "Out of memory"
```

**Condition:** `count > 0` (jeder einzelne OOM-Eintrag loest einen Alert aus).

##### Alert: Disk-Space-Warnung

```logql
{job="system", source="syslog"} |= "No space left on device"
```

##### Alert: Fehlgeschlagene SSH-Logins

```logql
sum(rate({job="system", source="authlog"} |= "Failed password" [5m]))
```

**Condition:** `IS ABOVE 0.1` (mehr als 0.1 fehlgeschlagene Logins pro Sekunde = moeglicher Brute-Force-Angriff).

#### 7.2 Alert-Routing ueber Alertmanager

Alerts von Grafana/Loki werden an den Alertmanager weitergeleitet. Die Alertmanager-Konfiguration (unter `stacks/observability/configs/alertmanager/alertmanager.yml`) bestimmt, wohin die Alerts gesendet werden (Slack, E-Mail, etc.).

---

### 8. Performance und Ressourcen

#### 8.1 Ressourcenverbrauch von Alloy

| Ressource  | Typischer Verbrauch | Mit vielen Containern (30+) |
|------------|---------------------|-----------------------------|
| RAM        | 50-80 MB            | 100-200 MB                  |
| CPU        | <1% (idle)          | 2-5% (unter Last)           |
| Disk (I/O) | Minimal             | Abhaengig vom Log-Volumen   |

Alloy ist ressourcenschonend. Fuer die typische Toolbox mit 15-20 Containern liegt der Verbrauch bei unter 100 MB RAM.

#### 8.2 Log-Volumen schaetzen

Typische Log-Raten pro Container:

| Service                | Log-Rate (ca.)         | Tagesvolumen (ca.)    |
|------------------------|------------------------|-----------------------|
| PostgreSQL             | 10-50 Zeilen/min       | 50-200 MB/Tag         |
| Redis                  | 1-5 Zeilen/min         | 5-20 MB/Tag           |
| MinIO                  | 5-20 Zeilen/min        | 20-80 MB/Tag          |
| Grafana                | 5-15 Zeilen/min        | 20-60 MB/Tag          |
| Prometheus             | 2-10 Zeilen/min        | 10-40 MB/Tag          |
| Loki                   | 5-15 Zeilen/min        | 20-60 MB/Tag          |
| PostHog (mit Traffic)  | 50-200 Zeilen/min      | 200-800 MB/Tag        |
| Sentry (mit Traffic)   | 30-100 Zeilen/min      | 100-400 MB/Tag        |
| **Gesamt (geschaetzt)**| **100-500 Zeilen/min** | **500 MB - 2 GB/Tag** |

#### 8.3 Retention-Strategie

Loki ist auf 30 Tage Retention konfiguriert (in `stacks/observability/configs/loki/loki.yml`):

```yaml
# In loki.yml
limits_config:
  retention_period: 720h  # 30 Tage

compactor:
  retention_enabled: true
```

Bei einem geschaetzten Tagesvolumen von 1 GB ergibt das einen Speicherbedarf von ca. 10-15 GB fuer Loki (Kompression reduziert die Groesse um ca. 50-70%).

#### 8.4 Backpressure und Pufferung

Wenn Loki voruebergehend nicht erreichbar ist (Neustart, Ueberlastung), puffert Alloy die Logs im Arbeitsspeicher. Die Standard-Puffergroesse betraegt 100 MB. Falls der Puffer voll ist, werden die aeltesten Logs verworfen.

Um den Puffer anzupassen:

```alloy
loki.write "default" {
  endpoint {
    url = "http://loki:3100/loki/api/v1/push"
    batch_wait = "1s"
    batch_size = 1048576
  }

  // Maximale Queue-Groesse (Standard: 100 MB)
  queue_config {
    capacity = 200000000  // 200 MB
  }
}
```

---

### 9. Troubleshooting

#### Alloy schickt keine Logs an Loki

1. **Docker Socket Berechtigung pruefen:**
   ```bash
   docker exec toolbox-alloy ls -la /var/run/docker.sock
   # Erwartet: srw-rw---- 1 root docker ...
   ```
   Falls "Permission denied": Stelle sicher, dass der Alloy-Container Zugriff auf den Docker Socket hat (Volume-Mount `:ro`).

2. **Alloy-Logs pruefen:**
   ```bash
   docker logs toolbox-alloy --tail 50
   ```
   Suche nach Fehlermeldungen wie "connection refused" oder "permission denied".

3. **Loki erreichbar?:**
   ```bash
   docker exec toolbox-alloy wget -qO- http://loki:3100/ready
   # Erwartet: "ready"
   ```

4. **Container im richtigen Netzwerk?:**
   ```bash
   docker network inspect toolbox --format '{{range .Containers}}{{.Name}} {{end}}'
   ```
   Pruefe, ob sowohl `toolbox-alloy` als auch `toolbox-loki` im Netzwerk sind.

#### Loki lehnt Logs ab

1. **Rate Limits:**
   Loki hat Standard-Rate-Limits. Pruefe die Loki-Logs:
   ```bash
   docker logs toolbox-loki 2>&1 | grep "rate limit"
   ```
   Falls Rate-Limits greifen, erhoehe sie in `loki.yml`:
   ```yaml
   limits_config:
     ingestion_rate_mb: 10
     ingestion_burst_size_mb: 20
   ```

2. **Label Cardinality:**
   ```bash
   docker logs toolbox-loki 2>&1 | grep "max streams"
   ```
   Falls zu viele Streams: Reduziere die Anzahl der Labels in der Alloy-Konfiguration. Verwende keine hochkardinalitaeten Labels wie `container_id` oder `request_id`.

3. **Loki Speicher voll:**
   ```bash
   docker exec toolbox-loki df -h /loki
   ```

#### Debug-Endpoint von Alloy

Alloy stellt eine Debug-UI unter Port 12345 bereit. Innerhalb des Docker-Netzwerks:

```bash
# Von einem anderen Container im Netzwerk:
curl http://toolbox-alloy:12345/

# Oder per SSH auf den Server und dann:
docker exec toolbox-alloy wget -qO- http://localhost:12345/
```

Verfuegbare Endpoints:

| Endpoint                         | Beschreibung                                |
|----------------------------------|---------------------------------------------|
| `http://alloy:12345/`            | Web-UI mit Komponentengraph                 |
| `http://alloy:12345/-/healthy`   | Health Check                                |
| `http://alloy:12345/-/ready`     | Readiness Check                             |
| `http://alloy:12345/metrics`     | Alloy-eigene Prometheus-Metriken            |

#### Konfiguration validieren

Bevor du eine neue Konfiguration deployest, validiere sie:

```bash
# Auf dem Server
docker run --rm \
  -v /pfad/zu/config.alloy:/etc/alloy/config.alloy:ro \
  grafana/alloy:v1.3.1 \
  fmt --check /etc/alloy/config.alloy
```

#### Logs in Grafana nicht sichtbar

1. Pruefe, ob die Loki-Datenquelle in Grafana korrekt konfiguriert ist (**Connections** > **Data Sources** > **Loki** > **Test**).
2. Pruefe den Zeitbereich in Grafana (oben rechts). Logs der letzten 15 Minuten auswaehlen.
3. Starte mit einer einfachen Query: `{job="docker"}` um ueberhaupt Logs zu sehen.
4. Falls keine Logs: Pruefe ob Alloy laeuft und Logs an Loki sendet (siehe oben).

---

### Checkliste: Alloy vollstaendig eingerichtet

- [ ] `stacks/log-shipping/docker-compose.yml` erstellt
- [ ] `stacks/log-shipping/configs/config.alloy` erstellt
- [ ] Stack via Coolify deployed
- [ ] Alloy-Container laeuft und ist healthy
- [ ] Docker-Logs erscheinen in Grafana > Explore > Loki
- [ ] Health-Check-Logs werden herausgefiltert (kein Rauschen)
- [ ] Labels sind korrekt: `container`, `service`, `project`, `job`
- [ ] Log-Dashboard in Grafana erstellt
- [ ] Mindestens ein Alert auf Error-Rate konfiguriert
- [ ] Loki-Retention auf 30 Tage gesetzt und verifiziert

---

## 3. Restic — Automatisierte Backups


Dieses Dokument beschreibt die Einrichtung eines automatisierten Backup-Systems mit Restic und MinIO. Alle Docker-Volumes, PostgreSQL-Datenbanken und Redis-Daten werden regelmaessig gesichert, verschluesselt und dedupliziert in MinIO (S3) abgelegt.

> **Voraussetzung:** Der `core-data`-Stack (PostgreSQL, Redis, MinIO) muss bereits laufen. Siehe [04-deploy-stack.md](04-deploy-stack.md).

---

### 1. Was ist Restic?

Restic ist ein schnelles, sicheres Backup-Programm mit folgenden Eigenschaften:

- **Verschluesselung:** Alle Backups werden mit AES-256 verschluesselt, bevor sie das System verlassen. Selbst wenn jemand Zugriff auf den MinIO-Bucket erhaelt, kann er die Daten nicht lesen.
- **Deduplizierung:** Restic teilt Dateien in Bloecke (Chunks) und speichert jeden Block nur einmal. Wenn sich nur 1% einer Datenbank-Datei aendert, wird nur dieser 1% gesichert.
- **Inkrementelle Backups:** Nach dem initialen Full-Backup werden nur geaenderte Bloecke uebertragen. Ein taegliches Backup dauert typischerweise Sekunden bis wenige Minuten.
- **S3-Backend:** Restic kann direkt in S3-kompatiblen Speicher schreiben. MinIO stellt diesen bereit.
- **Snapshot-basiert:** Jedes Backup ist ein Snapshot. Man kann zu jedem beliebigen Zeitpunkt zurueckkehren.

#### Warum Backups fuer Docker-Volumes wichtig sind

Docker-Volumes speichern alle persistenten Daten der Toolbox:

- PostgreSQL: Alle Datenbanken (Grafana, Sentry, PostHog, Unleash, Infisical, Authentik)
- Redis: Cache-Daten, Sessions, Task-Queues
- MinIO: Alle hochgeladenen Dateien und Objekte
- Grafana: Dashboards, Alerting-Konfiguration
- Loki: Log-Daten (30 Tage)
- Prometheus: Metrik-Daten (30 Tage)

Ein Verlust dieser Volumes (Festplatten-Ausfall, versehentliches Loeschen, Ransomware) bedeutet den Verlust aller Daten. Regelmaessige Backups sind nicht optional.

---

### 2. Architektur

#### Backup-Datenfluss

```
+---------------------------------------------------------------------+
|                        Docker Host                                   |
|                                                                      |
|  +----------------+  +----------------+  +----------------+          |
|  | toolbox-       |  | toolbox-       |  | toolbox-       |          |
|  | postgres       |  | redis          |  | grafana        |  ...     |
|  |                |  |                |  |                |          |
|  +-------+--------+  +-------+--------+  +-------+--------+         |
|          |                    |                    |                  |
|   +------v------+     +------v------+     +------v------+           |
|   | postgres_   |     | redis_     |     | grafana_   |            |
|   | data        |     | data       |     | data       |            |
|   | (Volume)    |     | (Volume)   |     | (Volume)   |            |
|   +------+------+     +------+------+     +------+------+           |
|          |                    |                    |                  |
|  ========|====================|====================|=============    |
|          |         /var/lib/docker/volumes          |                 |
|  ========|====================|====================|=============    |
|          |                    |                    |                  |
|  +-------v--------------------v--------------------v-----------+     |
|  |                  toolbox-backup                              |    |
|  |                                                              |    |
|  |  1. pg_dump (PostgreSQL)                                     |    |
|  |  2. redis-cli BGSAVE (Redis)                                 |    |
|  |  3. restic backup (alle Volumes)                             |    |
|  |                                                              |    |
|  +-------+------------------------------------------------------+    |
|          |                                                           |
|          | S3 API (HTTP)                                             |
|          |                                                           |
|  +-------v---------+                                                 |
|  |    MinIO         |                                                |
|  |  Bucket: backups |                                                |
|  |  (verschluesselt |                                                |
|  |   + dedupliziert)|                                                |
|  +------------------+                                                |
+---------------------------------------------------------------------+
```

#### Volume-Inventar

Folgende Volumes muessen regelmaessig gesichert werden:

| Volume                        | Stack            | Daten                              | Prioritaet |
|-------------------------------|------------------|------------------------------------|------------|
| `toolbox_postgres_data`       | core-data        | Alle Datenbanken                   | Kritisch   |
| `toolbox_redis_data`          | core-data        | Cache, Sessions, Queues            | Hoch       |
| `toolbox_minio_data`          | core-data        | Alle Objekte/Dateien               | Kritisch   |
| `toolbox_grafana_data`        | observability    | Dashboards, Plugins                | Mittel     |
| `toolbox_prometheus_data`     | observability    | Metrik-Zeitreihen (30d)            | Niedrig    |
| `toolbox_loki_data`           | observability    | Log-Daten (30d)                    | Niedrig    |
| `toolbox_tempo_data`          | observability    | Trace-Daten                        | Niedrig    |
| `toolbox_alertmanager_data`   | observability    | Silence-Konfiguration              | Niedrig    |
| `toolbox_authentik_media`     | auth             | Authentik-Medien (Logos etc.)      | Mittel     |
| `toolbox_authentik_templates` | auth             | Custom Templates                   | Mittel     |
| `toolbox_authentik_certs`     | auth             | Zertifikate                        | Hoch       |
| `toolbox_alloy_data`          | log-shipping     | Log-Positionen                     | Niedrig    |

**Prioritaeten:**
- **Kritisch:** Datenverlust ist nicht akzeptabel. Taeglich sichern.
- **Hoch:** Wichtige Daten, deren Verlust erheblichen Aufwand verursacht.
- **Mittel:** Daten, die mit Aufwand rekonstruiert werden koennen.
- **Niedrig:** Daten, die sich automatisch neu aufbauen (Metriken, Logs, Traces werden von den Quellen neu generiert).

---

### 3. Stack Setup

#### Docker Compose

```yaml
# stacks/backups/docker-compose.yml
# Restic Backup-Service fuer die gesamte Toolbox

services:
  # -----------------------------------------------
  # Backup Runner
  # -----------------------------------------------
  backup:
    image: restic/restic:0.17.3
    container_name: toolbox-backup
    restart: unless-stopped
    entrypoint: /bin/sh
    command:
      - -c
      - |
        echo "Backup-Container gestartet. Warte auf Cron-Jobs..."
        # Crontab installieren
        echo "0 2 * * * /scripts/backup.sh >> /var/log/backup.log 2>&1" > /etc/crontabs/root
        echo "0 3 * * 0 /scripts/verify.sh >> /var/log/backup.log 2>&1" >> /etc/crontabs/root
        echo "0 4 1 * * /scripts/cleanup.sh >> /var/log/backup.log 2>&1" >> /etc/crontabs/root
        crond -f -l 2
    environment:
      # --- Restic Repository (MinIO S3) ---
      RESTIC_REPOSITORY: s3:http://minio:9000/backups
      RESTIC_PASSWORD: ${BACKUP_ENCRYPTION_KEY:?BACKUP_ENCRYPTION_KEY is required}
      AWS_ACCESS_KEY_ID: ${BACKUP_MINIO_ACCESS_KEY:?BACKUP_MINIO_ACCESS_KEY is required}
      AWS_SECRET_ACCESS_KEY: ${BACKUP_MINIO_SECRET_KEY:?BACKUP_MINIO_SECRET_KEY is required}
      # --- PostgreSQL ---
      PGHOST: postgres
      PGPORT: "5432"
      PGUSER: ${POSTGRES_USER:-toolbox}
      PGPASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
      # --- Redis ---
      REDIS_PASSWORD: ${REDIS_PASSWORD:?REDIS_PASSWORD is required}
      # --- Uptime Kuma Push Monitor (optional) ---
      UPTIME_KUMA_PUSH_URL: ${UPTIME_KUMA_PUSH_URL:-}
      # --- Alertmanager (optional) ---
      ALERTMANAGER_URL: ${ALERTMANAGER_URL:-http://alertmanager:9093}
    volumes:
      # Alle Docker-Volumes (read-only)
      - /var/lib/docker/volumes:/source:ro
      # Temporaeres Verzeichnis fuer Dumps
      - backup_tmp:/tmp/backup
      # Backup-Skripte
      - ./scripts:/scripts:ro
      # Log-Datei
      - backup_logs:/var/log
    networks:
      - toolbox

volumes:
  backup_tmp:
    name: toolbox_backup_tmp
  backup_logs:
    name: toolbox_backup_logs

networks:
  toolbox:
    external: true
    name: toolbox
```

#### Umgebungsvariablen (.env.example)

```bash
# stacks/backups/.env.example
# Restic Backup-Service

# --- Restic Verschluesselung ---
# Passwort fuer die Verschluesselung aller Backups.
# KRITISCH: Ohne dieses Passwort koennen Backups nicht wiederhergestellt werden!
# Generieren mit: openssl rand -hex 32
# Offline sichern (Passwort-Manager, Tresor, Ausdruck).
BACKUP_ENCRYPTION_KEY=CHANGE_ME_backup_encryption_key

# --- MinIO Zugangsdaten fuer Backups ---
# Separater MinIO-Benutzer nur fuer Backups (eingeschraenkte Rechte).
# Siehe Abschnitt "MinIO Bucket einrichten".
BACKUP_MINIO_ACCESS_KEY=CHANGE_ME_backup_access_key
BACKUP_MINIO_SECRET_KEY=CHANGE_ME_backup_secret_key

# --- Shared credentials (from core-data stack) ---
POSTGRES_USER=toolbox
POSTGRES_PASSWORD=CHANGE_ME_postgres_password
REDIS_PASSWORD=CHANGE_ME_redis_password

# --- Monitoring (optional) ---
# Uptime Kuma Push Monitor URL fuer Backup-Status-Meldungen.
# Erstelle einen Push-Monitor in Uptime Kuma und trage die URL hier ein.
# UPTIME_KUMA_PUSH_URL=https://status.example.com/api/push/XXXXXXXXXX?status=up&msg=OK

# --- Alertmanager (optional, Standard: http://alertmanager:9093) ---
# ALERTMANAGER_URL=http://alertmanager:9093
```

#### Secrets generieren

```bash
# Backup-Verschluesselungsschluessel
BACKUP_ENCRYPTION_KEY=$(openssl rand -hex 32)
echo "BACKUP_ENCRYPTION_KEY=$BACKUP_ENCRYPTION_KEY"

# MinIO-Zugangsdaten fuer Backups (werden in Schritt 4 erstellt)
BACKUP_MINIO_ACCESS_KEY=$(openssl rand -hex 16)
BACKUP_MINIO_SECRET_KEY=$(openssl rand -hex 32)
echo "BACKUP_MINIO_ACCESS_KEY=$BACKUP_MINIO_ACCESS_KEY"
echo "BACKUP_MINIO_SECRET_KEY=$BACKUP_MINIO_SECRET_KEY"
```

> **KRITISCH:** Den `BACKUP_ENCRYPTION_KEY` SOFORT offline sichern. Speichere ihn in Infisical UND an einem zweiten, unabhaengigen Ort (Passwort-Manager, gedruckt im Tresor). Ohne diesen Schluessel sind alle Backups wertlos.

---

### 4. MinIO Bucket einrichten

#### 4.1 Bucket erstellen

Verbinde dich mit MinIO ueber den `mc` CLI-Client:

```bash
# mc konfigurieren (einmalig)
docker exec toolbox-minio mc alias set local http://localhost:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}

# Backup-Bucket erstellen
docker exec toolbox-minio mc mb local/backups

# Bucket-Verschluesselung aktivieren (Server-Side Encryption)
docker exec toolbox-minio mc encrypt set sse-s3 local/backups
```

#### 4.2 IAM-Benutzer mit eingeschraenkten Rechten

Erstelle einen separaten MinIO-Benutzer, der nur auf den Backup-Bucket zugreifen kann:

```bash
# Benutzer erstellen
docker exec toolbox-minio mc admin user add local ${BACKUP_MINIO_ACCESS_KEY} ${BACKUP_MINIO_SECRET_KEY}

# Policy erstellen (nur Backup-Bucket)
docker exec toolbox-minio mc admin policy create local backup-policy /dev/stdin <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:ListMultipartUploadParts",
        "s3:AbortMultipartUpload"
      ],
      "Resource": [
        "arn:aws:s3:::backups",
        "arn:aws:s3:::backups/*"
      ]
    }
  ]
}
EOF

# Policy dem Benutzer zuweisen
docker exec toolbox-minio mc admin policy attach local backup-policy --user ${BACKUP_MINIO_ACCESS_KEY}
```

#### 4.3 Lifecycle Policy (alte Backups loeschen)

MinIO kann Objekte automatisch nach einer bestimmten Zeit loeschen. Das dient als zusaetzliche Sicherheit, falls Restic's eigene Retention-Bereinigung nicht greift:

```bash
# Lifecycle-Regel: Objekte nach 120 Tagen loeschen
docker exec toolbox-minio mc ilm rule add local/backups \
  --expiry-days 120 \
  --prefix "" \
  --tags "type=backup"
```

> **Hinweis:** Restic verwaltet seine eigene Retention (siehe Abschnitt 6). Die MinIO-Lifecycle-Policy ist ein zusaetzliches Sicherheitsnetz, das verwaiste Objekte nach 120 Tagen entfernt.

#### 4.4 Restic Repository initialisieren

Bevor das erste Backup erstellt werden kann, muss das Restic-Repository im MinIO-Bucket initialisiert werden:

```bash
# Vom Backup-Container aus
docker exec toolbox-backup restic init

# Oder direkt
docker exec -e RESTIC_REPOSITORY=s3:http://minio:9000/backups \
  -e RESTIC_PASSWORD="${BACKUP_ENCRYPTION_KEY}" \
  -e AWS_ACCESS_KEY_ID="${BACKUP_MINIO_ACCESS_KEY}" \
  -e AWS_SECRET_ACCESS_KEY="${BACKUP_MINIO_SECRET_KEY}" \
  toolbox-backup restic init
```

Erwartet: `created restic repository ... at s3:http://minio:9000/backups`

Falls das Repository bereits existiert, erscheint eine Fehlermeldung. Das ist in Ordnung.

---

### 5. Backup-Skripte

Erstelle die folgenden Skripte unter `stacks/backups/scripts/`.

#### 5a. PostgreSQL Backup (pg_dump)

```bash
#!/bin/sh
# stacks/backups/scripts/backup-postgres.sh
# Erstellt individuelle Dumps aller PostgreSQL-Datenbanken.

set -eu

DUMP_DIR="/tmp/backup/postgres"
mkdir -p "${DUMP_DIR}"

echo "[$(date -Iseconds)] PostgreSQL-Backup gestartet"

# Liste aller Datenbanken (ausser System-DBs)
DATABASES=$(PGPASSWORD="${PGPASSWORD}" psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -t -A -c \
  "SELECT datname FROM pg_database WHERE datistemplate = false AND datname NOT IN ('postgres', 'template0', 'template1');")

if [ -z "${DATABASES}" ]; then
  echo "[$(date -Iseconds)] WARNUNG: Keine Datenbanken gefunden!"
  exit 1
fi

FAILED=0

for DB in ${DATABASES}; do
  echo "[$(date -Iseconds)] Dumpe Datenbank: ${DB}"
  DUMP_FILE="${DUMP_DIR}/${DB}.sql.gz"

  if PGPASSWORD="${PGPASSWORD}" pg_dump \
    -h "${PGHOST}" \
    -p "${PGPORT}" \
    -U "${PGUSER}" \
    -d "${DB}" \
    --format=custom \
    --compress=6 \
    --no-owner \
    --no-privileges \
    -f "${DUMP_DIR}/${DB}.dump" 2>&1; then

    SIZE=$(du -sh "${DUMP_DIR}/${DB}.dump" | cut -f1)
    echo "[$(date -Iseconds)] OK: ${DB} (${SIZE})"
  else
    echo "[$(date -Iseconds)] FEHLER: Dump von ${DB} fehlgeschlagen!"
    FAILED=$((FAILED + 1))
  fi
done

echo "[$(date -Iseconds)] PostgreSQL-Backup abgeschlossen. ${FAILED} Fehler."

if [ "${FAILED}" -gt 0 ]; then
  exit 1
fi
```

#### 5b. Redis Backup (BGSAVE + RDB)

```bash
#!/bin/sh
# stacks/backups/scripts/backup-redis.sh
# Erstellt ein Redis-Backup ueber BGSAVE.

set -eu

DUMP_DIR="/tmp/backup/redis"
mkdir -p "${DUMP_DIR}"

echo "[$(date -Iseconds)] Redis-Backup gestartet"

# BGSAVE ausloesen
redis-cli -h redis -p 6379 -a "${REDIS_PASSWORD}" --no-auth-warning BGSAVE

# Warte bis BGSAVE abgeschlossen ist (max. 60 Sekunden)
WAITED=0
while [ "${WAITED}" -lt 60 ]; do
  SAVE_IN_PROGRESS=$(redis-cli -h redis -p 6379 -a "${REDIS_PASSWORD}" --no-auth-warning \
    LASTSAVE 2>/dev/null)

  BG_STATUS=$(redis-cli -h redis -p 6379 -a "${REDIS_PASSWORD}" --no-auth-warning \
    INFO persistence 2>/dev/null | grep rdb_bgsave_in_progress | tr -d '\r' | cut -d: -f2)

  if [ "${BG_STATUS}" = "0" ]; then
    echo "[$(date -Iseconds)] BGSAVE abgeschlossen"
    break
  fi

  echo "[$(date -Iseconds)] Warte auf BGSAVE... (${WAITED}s)"
  sleep 2
  WAITED=$((WAITED + 2))
done

if [ "${WAITED}" -ge 60 ]; then
  echo "[$(date -Iseconds)] WARNUNG: BGSAVE Timeout nach 60 Sekunden"
fi

# dump.rdb liegt im Redis-Volume unter /data
# Da wir /var/lib/docker/volumes als /source gemountet haben,
# liegt die Datei unter /source/toolbox_redis_data/_data/dump.rdb
REDIS_DUMP="/source/toolbox_redis_data/_data/dump.rdb"

if [ -f "${REDIS_DUMP}" ]; then
  cp "${REDIS_DUMP}" "${DUMP_DIR}/dump.rdb"
  SIZE=$(du -sh "${DUMP_DIR}/dump.rdb" | cut -f1)
  echo "[$(date -Iseconds)] Redis-Backup OK (${SIZE})"
else
  echo "[$(date -Iseconds)] WARNUNG: dump.rdb nicht gefunden unter ${REDIS_DUMP}"
  echo "[$(date -Iseconds)] Redis-Backup wird uebersprungen."
fi
```

#### 5c. Volume Backup (Restic)

```bash
#!/bin/sh
# stacks/backups/scripts/backup-volumes.sh
# Sichert alle Docker-Volumes mit Restic.

set -eu

echo "[$(date -Iseconds)] Volume-Backup gestartet"

# Alle Volumes sichern (liegen unter /source/)
# Exclude-Patterns: temporaere Dateien, Caches, Lock-Dateien
restic backup /source/ \
  --tag volumes \
  --tag "date:$(date +%Y-%m-%d)" \
  --exclude "/source/toolbox_backup_tmp/" \
  --exclude "/source/toolbox_backup_logs/" \
  --exclude "*.tmp" \
  --exclude "*.swp" \
  --exclude "*.lock" \
  --exclude "lost+found" \
  --exclude ".cache" \
  --verbose

echo "[$(date -Iseconds)] Volume-Backup abgeschlossen"
```

#### 5d. PostgreSQL-Dump Backup (Restic)

```bash
#!/bin/sh
# stacks/backups/scripts/backup-dumps.sh
# Sichert die PostgreSQL- und Redis-Dumps mit Restic.

set -eu

echo "[$(date -Iseconds)] Dump-Backup gestartet"

restic backup /tmp/backup/ \
  --tag dumps \
  --tag postgres \
  --tag redis \
  --tag "date:$(date +%Y-%m-%d)" \
  --verbose

echo "[$(date -Iseconds)] Dump-Backup abgeschlossen"

# Temporaere Dumps aufraeumen
echo "[$(date -Iseconds)] Raeume temporaere Dumps auf..."
rm -rf /tmp/backup/postgres/*
rm -rf /tmp/backup/redis/*
echo "[$(date -Iseconds)] Aufraeumen abgeschlossen"
```

#### 5e. Haupt-Backup-Skript (backup.sh)

```bash
#!/bin/sh
# stacks/backups/scripts/backup.sh
# Haupt-Backup-Skript. Wird taeglich per Cron ausgefuehrt.
# Fuehrt alle Einzelskripte aus und meldet den Status.

set -eu

TIMESTAMP=$(date -Iseconds)
echo "============================================================"
echo "[${TIMESTAMP}] BACKUP GESTARTET"
echo "============================================================"

STATUS="ok"
ERROR_MSG=""

# --- Schritt 1: PostgreSQL-Dump ---
echo ""
echo "--- Schritt 1/4: PostgreSQL-Dump ---"
if /scripts/backup-postgres.sh; then
  echo "[$(date -Iseconds)] PostgreSQL-Dump: OK"
else
  STATUS="fail"
  ERROR_MSG="${ERROR_MSG}PostgreSQL-Dump fehlgeschlagen. "
  echo "[$(date -Iseconds)] PostgreSQL-Dump: FEHLGESCHLAGEN"
fi

# --- Schritt 2: Redis-Dump ---
echo ""
echo "--- Schritt 2/4: Redis-Dump ---"
if /scripts/backup-redis.sh; then
  echo "[$(date -Iseconds)] Redis-Dump: OK"
else
  STATUS="fail"
  ERROR_MSG="${ERROR_MSG}Redis-Dump fehlgeschlagen. "
  echo "[$(date -Iseconds)] Redis-Dump: FEHLGESCHLAGEN"
fi

# --- Schritt 3: Restic Backup der Dumps ---
echo ""
echo "--- Schritt 3/4: Restic Backup (Dumps) ---"
if /scripts/backup-dumps.sh; then
  echo "[$(date -Iseconds)] Restic Dump-Backup: OK"
else
  STATUS="fail"
  ERROR_MSG="${ERROR_MSG}Restic Dump-Backup fehlgeschlagen. "
  echo "[$(date -Iseconds)] Restic Dump-Backup: FEHLGESCHLAGEN"
fi

# --- Schritt 4: Restic Backup der Volumes ---
echo ""
echo "--- Schritt 4/4: Restic Backup (Volumes) ---"
if /scripts/backup-volumes.sh; then
  echo "[$(date -Iseconds)] Restic Volume-Backup: OK"
else
  STATUS="fail"
  ERROR_MSG="${ERROR_MSG}Restic Volume-Backup fehlgeschlagen. "
  echo "[$(date -Iseconds)] Restic Volume-Backup: FEHLGESCHLAGEN"
fi

# --- Status-Meldung ---
echo ""
echo "============================================================"
SNAPSHOTS=$(restic snapshots --latest 1 --compact 2>/dev/null | tail -1 || echo "unbekannt")
echo "[$(date -Iseconds)] Letzter Snapshot: ${SNAPSHOTS}"

if [ "${STATUS}" = "ok" ]; then
  echo "[$(date -Iseconds)] BACKUP ERFOLGREICH ABGESCHLOSSEN"

  # Uptime Kuma Push Monitor benachrichtigen (falls konfiguriert)
  if [ -n "${UPTIME_KUMA_PUSH_URL:-}" ]; then
    wget -qO- "${UPTIME_KUMA_PUSH_URL}&status=up&msg=Backup+erfolgreich" 2>/dev/null || true
  fi
else
  echo "[$(date -Iseconds)] BACKUP MIT FEHLERN ABGESCHLOSSEN: ${ERROR_MSG}"

  # Uptime Kuma Push Monitor benachrichtigen (Fehler)
  if [ -n "${UPTIME_KUMA_PUSH_URL:-}" ]; then
    wget -qO- "${UPTIME_KUMA_PUSH_URL}&status=down&msg=Backup+fehlgeschlagen" 2>/dev/null || true
  fi

  # Alert an Alertmanager senden
  if [ -n "${ALERTMANAGER_URL:-}" ]; then
    wget -qO- --post-data='[{
      "labels": {
        "alertname": "BackupFailed",
        "severity": "critical",
        "job": "backup"
      },
      "annotations": {
        "summary": "Toolbox-Backup fehlgeschlagen",
        "description": "'"${ERROR_MSG}"'"
      }
    }]' \
    --header="Content-Type: application/json" \
    "${ALERTMANAGER_URL}/api/v2/alerts" 2>/dev/null || true
  fi

  exit 1
fi
```

#### 5f. Verifikations-Skript (verify.sh)

```bash
#!/bin/sh
# stacks/backups/scripts/verify.sh
# Prueft die Integritaet aller Backups.
# Wird woechentlich per Cron ausgefuehrt (Sonntag, 03:00 Uhr).

set -eu

echo "============================================================"
echo "[$(date -Iseconds)] BACKUP-VERIFIZIERUNG GESTARTET"
echo "============================================================"

# Restic check prueft:
# - Alle Datenbloecke im Repository auf Konsistenz
# - Alle Snapshot-Referenzen auf Gueltigkeit
# - Pack-Dateien auf Korruption
echo "[$(date -Iseconds)] Starte restic check..."

if restic check --verbose 2>&1; then
  echo "[$(date -Iseconds)] Verifizierung: OK - Alle Backups integer"

  if [ -n "${UPTIME_KUMA_PUSH_URL:-}" ]; then
    wget -qO- "${UPTIME_KUMA_PUSH_URL}&status=up&msg=Backup+Verifizierung+OK" 2>/dev/null || true
  fi
else
  echo "[$(date -Iseconds)] FEHLER: Backup-Verifizierung fehlgeschlagen!"

  if [ -n "${ALERTMANAGER_URL:-}" ]; then
    wget -qO- --post-data='[{
      "labels": {
        "alertname": "BackupVerificationFailed",
        "severity": "critical",
        "job": "backup"
      },
      "annotations": {
        "summary": "Backup-Verifizierung fehlgeschlagen",
        "description": "restic check hat Fehler im Backup-Repository gefunden."
      }
    }]' \
    --header="Content-Type: application/json" \
    "${ALERTMANAGER_URL}/api/v2/alerts" 2>/dev/null || true
  fi

  exit 1
fi

# Statistiken ausgeben
echo ""
echo "[$(date -Iseconds)] Repository-Statistiken:"
restic stats 2>/dev/null || true

echo ""
echo "[$(date -Iseconds)] Letzte 5 Snapshots:"
restic snapshots --last 5 --compact 2>/dev/null || true

echo ""
echo "============================================================"
echo "[$(date -Iseconds)] VERIFIZIERUNG ABGESCHLOSSEN"
echo "============================================================"
```

#### 5g. Cleanup-Skript (cleanup.sh)

```bash
#!/bin/sh
# stacks/backups/scripts/cleanup.sh
# Entfernt alte Backups nach der Retention-Policy.
# Wird monatlich per Cron ausgefuehrt (1. des Monats, 04:00 Uhr).

set -eu

echo "============================================================"
echo "[$(date -Iseconds)] BACKUP-BEREINIGUNG GESTARTET"
echo "============================================================"

# Retention-Policy:
# - Behalte die letzten 7 taeglichen Backups
# - Behalte die letzten 4 woechentlichen Backups
# - Behalte die letzten 6 monatlichen Backups
# - Behalte die letzten 2 jaehrlichen Backups

echo "[$(date -Iseconds)] Wende Retention-Policy an..."
echo "  Taeglich: 7"
echo "  Woechentlich: 4"
echo "  Monatlich: 6"
echo "  Jaehrlich: 2"

restic forget \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 6 \
  --keep-yearly 2 \
  --prune \
  --verbose 2>&1

echo ""
echo "[$(date -Iseconds)] Repository-Groesse nach Bereinigung:"
restic stats 2>/dev/null || true

echo ""
echo "============================================================"
echo "[$(date -Iseconds)] BEREINIGUNG ABGESCHLOSSEN"
echo "============================================================"
```

#### Skripte ausfuehrbar machen

```bash
chmod +x stacks/backups/scripts/*.sh
```

---

### 6. Zeitplanung (Cron)

Die Cron-Jobs werden automatisch im Backup-Container installiert (siehe `docker-compose.yml`, Abschnitt `command`).

#### Zeitplan

| Job           | Zeitplan                | Cron-Ausdruck       | Beschreibung                          |
|---------------|-------------------------|----------------------|---------------------------------------|
| Backup        | Taeglich, 02:00 Uhr    | `0 2 * * *`         | Vollstaendiges Backup aller Daten     |
| Verifizierung | Sonntags, 03:00 Uhr    | `0 3 * * 0`         | Integritaetspruefung des Repositorys  |
| Bereinigung   | 1. des Monats, 04:00   | `0 4 1 * *`         | Alte Snapshots nach Retention loeschen|

#### Manuelles Backup ausloesen

```bash
# Sofort ein Backup starten (ohne auf Cron zu warten)
docker exec toolbox-backup /scripts/backup.sh

# Nur PostgreSQL dumpen
docker exec toolbox-backup /scripts/backup-postgres.sh

# Nur Verifizierung
docker exec toolbox-backup /scripts/verify.sh

# Nur Bereinigung
docker exec toolbox-backup /scripts/cleanup.sh
```

#### Alternative: Ofelia (Docker-nativer Cron)

Statt `crond` im Container kann auch Ofelia verwendet werden, ein Docker-nativer Cron-Scheduler, der Jobs in anderen Containern ausfuehrt:

```yaml
# Alternative: Ofelia als separater Service
services:
  ofelia:
    image: mcuadros/ofelia:latest
    container_name: toolbox-ofelia
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    labels:
      ofelia.enabled: "true"

  backup:
    image: restic/restic:0.17.3
    container_name: toolbox-backup
    # ... (wie oben, aber ohne crond-Command)
    command: ["sleep", "infinity"]
    labels:
      ofelia.enabled: "true"
      ofelia.job-exec.backup.schedule: "0 2 * * *"
      ofelia.job-exec.backup.command: "/scripts/backup.sh"
      ofelia.job-exec.verify.schedule: "0 3 * * 0"
      ofelia.job-exec.verify.command: "/scripts/verify.sh"
      ofelia.job-exec.cleanup.schedule: "0 4 1 * *"
      ofelia.job-exec.cleanup.command: "/scripts/cleanup.sh"
```

---

### 7. Restore-Prozedur

#### 7.1 Verfuegbare Snapshots auflisten

```bash
# Alle Snapshots anzeigen
docker exec toolbox-backup restic snapshots

# Snapshots mit bestimmtem Tag
docker exec toolbox-backup restic snapshots --tag dumps
docker exec toolbox-backup restic snapshots --tag volumes

# Snapshots eines bestimmten Datums
docker exec toolbox-backup restic snapshots --tag "date:2024-06-15"

# Detaillierte Snapshot-Infos
docker exec toolbox-backup restic snapshots --json | jq '.[0]'
```

#### 7.2 Inhalte eines Snapshots durchsuchen

```bash
# Dateien in einem Snapshot auflisten
docker exec toolbox-backup restic ls latest

# Dateien in einem bestimmten Snapshot auflisten
docker exec toolbox-backup restic ls abc12345

# Nach einer bestimmten Datei suchen
docker exec toolbox-backup restic ls latest | grep "grafana"
```

#### 7.3 PostgreSQL wiederherstellen

```bash
# 1. Letzten Dump-Snapshot wiederherstellen
docker exec toolbox-backup restic restore latest \
  --tag dumps \
  --target /tmp/restore \
  --include "/tmp/backup/postgres/"

# 2. Verfuegbare Dumps auflisten
docker exec toolbox-backup ls -la /tmp/restore/tmp/backup/postgres/

# 3. Einzelne Datenbank wiederherstellen
# ACHTUNG: Dies ueberschreibt die aktuelle Datenbank!
docker exec toolbox-backup pg_restore \
  -h postgres \
  -p 5432 \
  -U "${PGUSER}" \
  -d grafana \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  /tmp/restore/tmp/backup/postgres/grafana.dump

# 4. Fuer jede weitere Datenbank wiederholen:
# docker exec toolbox-backup pg_restore ... -d sentry ... /tmp/restore/.../sentry.dump
# docker exec toolbox-backup pg_restore ... -d posthog ... /tmp/restore/.../posthog.dump
# docker exec toolbox-backup pg_restore ... -d unleash ... /tmp/restore/.../unleash.dump
# docker exec toolbox-backup pg_restore ... -d infisical ... /tmp/restore/.../infisical.dump
# docker exec toolbox-backup pg_restore ... -d authentik ... /tmp/restore/.../authentik.dump

# 5. Temporaere Dateien aufraeumen
docker exec toolbox-backup rm -rf /tmp/restore
```

#### 7.4 Redis wiederherstellen

```bash
# 1. Redis-Dump wiederherstellen
docker exec toolbox-backup restic restore latest \
  --tag dumps \
  --target /tmp/restore \
  --include "/tmp/backup/redis/"

# 2. Redis stoppen
docker stop toolbox-redis

# 3. dump.rdb ersetzen
# HINWEIS: Der Pfad haengt von der Docker-Installation ab
cp /tmp/restore/tmp/backup/redis/dump.rdb /var/lib/docker/volumes/toolbox_redis_data/_data/dump.rdb

# 4. Redis starten
docker start toolbox-redis

# 5. Verifizieren
docker exec toolbox-redis redis-cli -a "${REDIS_PASSWORD}" DBSIZE
```

#### 7.5 Einzelnes Volume wiederherstellen

```bash
# Beispiel: Grafana-Volume wiederherstellen

# 1. Service stoppen
docker stop toolbox-grafana

# 2. Volume-Inhalt wiederherstellen
docker exec toolbox-backup restic restore latest \
  --tag volumes \
  --target /tmp/restore \
  --include "/source/toolbox_grafana_data/"

# 3. Alten Volume-Inhalt ersetzen
# ACHTUNG: Dies ueberschreibt den aktuellen Inhalt!
rm -rf /var/lib/docker/volumes/toolbox_grafana_data/_data/*
cp -a /tmp/restore/source/toolbox_grafana_data/_data/* \
  /var/lib/docker/volumes/toolbox_grafana_data/_data/

# 4. Service starten
docker start toolbox-grafana

# 5. Verifizieren
curl -s https://grafana.example.com/api/health
```

#### 7.6 Point-in-Time Restore

Um einen bestimmten Zeitpunkt wiederherzustellen:

```bash
# Alle Snapshots mit Zeitstempel anzeigen
docker exec toolbox-backup restic snapshots

# Snapshot-ID des gewuenschten Zeitpunkts identifizieren
# Beispiel: abc12345

# Spezifischen Snapshot wiederherstellen
docker exec toolbox-backup restic restore abc12345 \
  --target /tmp/restore

# Dann wie oben die gewuenschten Daten kopieren
```

---

### 8. Ueberwachung

#### 8.1 Uptime Kuma Push Monitor

Erstelle in Uptime Kuma einen Push-Monitor fuer den Backup-Status:

1. Oeffne `https://status.example.com`.
2. Klicke **Add New Monitor**.
3. Waehle Typ: **Push**.
4. Konfiguriere:
   - **Friendly Name:** `Toolbox Backup`
   - **Push Interval:** `86400` (24 Stunden -- wenn kein Push innerhalb von 24h kommt, wird Alert ausgeloest)
   - **Heartbeat Retry:** `3`
5. Kopiere die Push-URL.
6. Trage die URL als `UPTIME_KUMA_PUSH_URL` in die `.env`-Datei des Backup-Stacks ein.

#### 8.2 Alertmanager

Das Backup-Skript sendet bei Fehlern automatisch einen Alert an den Alertmanager. Der Alertmanager leitet diesen an die konfigurierten Empfaenger weiter (Slack, E-Mail, etc.).

Stelle sicher, dass in der Alertmanager-Konfiguration (`stacks/observability/configs/alertmanager/alertmanager.yml`) ein passendes Routing fuer das Label `job: backup` existiert:

```yaml
# In alertmanager.yml
route:
  group_by: ['alertname']
  receiver: 'default'
  routes:
    - match:
        job: backup
      receiver: 'backup-alerts'
      group_wait: 0s
      repeat_interval: 1h

receivers:
  - name: 'backup-alerts'
    # Konfiguriere deinen bevorzugten Kanal:
    # slack_configs, email_configs, webhook_configs, etc.
```

#### 8.3 Grafana Dashboard fuer Backups

Erstelle ein einfaches Dashboard, das den Backup-Status visualisiert. Da der Backup-Container Logs schreibt, koennen diese ueber Loki abgefragt werden (wenn Alloy konfiguriert ist):

| Panel-Titel           | Typ         | LogQL-Query                                                     |
|------------------------|-------------|-----------------------------------------------------------------|
| Letztes Backup-Ergebnis| Stat        | `{container="toolbox-backup"} \|= "BACKUP ERFOLGREICH"`        |
| Backup-Fehler         | Logs        | `{container="toolbox-backup"} \|= "FEHLGESCHLAGEN"`            |
| Backup-Dauer          | Logs        | `{container="toolbox-backup"} \|= "BACKUP GESTARTET" or "ABGESCHLOSSEN"` |

#### 8.4 Restic Repository-Statistiken

```bash
# Repository-Groesse und Snapshot-Anzahl
docker exec toolbox-backup restic stats

# Detaillierte Statistiken
docker exec toolbox-backup restic stats --mode raw-data
```

---

### 9. Verschluesselung und Sicherheit

#### 9.1 Restic Verschluesselung

Restic verschluesselt alle Daten, bevor sie an MinIO gesendet werden:

- **Algorithmus:** AES-256-CTR fuer Daten, Poly1305-AES fuer Authentifizierung
- **Schluesselableitung:** scrypt (password-based key derivation)
- **Was verschluesselt wird:** Alle Dateninhalte, Dateinamen und Metadaten
- **Was NICHT verschluesselt wird:** Blob-Groessen und der Repo-Konfigurationsblock

Der Verschluesselungsschluessel wird aus dem `RESTIC_PASSWORD` (= `BACKUP_ENCRYPTION_KEY`) abgeleitet.

#### 9.2 Schluessel-Management

| Schluessel               | Speicherort                     | Wer braucht ihn?        |
|--------------------------|----------------------------------|--------------------------|
| `BACKUP_ENCRYPTION_KEY`  | Infisical + Offline-Kopie       | Backup-Container, Restore|
| `BACKUP_MINIO_ACCESS_KEY`| Infisical                       | Backup-Container         |
| `BACKUP_MINIO_SECRET_KEY`| Infisical                       | Backup-Container         |

#### 9.3 Backup des Backup-Passworts

Der `BACKUP_ENCRYPTION_KEY` ist der kritischste Schluessel im gesamten System. Ohne ihn koennen Backups nicht wiederhergestellt werden.

Speichere ihn an mindestens drei unabhaengigen Orten:

1. **Infisical** (im Toolbox-Projekt, Ordner `/backups`)
2. **Passwort-Manager** (1Password, Bitwarden, KeePass, etc.)
3. **Offline** (Ausdruck in einem verschlossenen Umschlag im Tresor oder Safe)

> **Tipp:** Speichere den Schluessel NICHT nur in Infisical. Wenn der Server komplett ausfaellt und du die Backups brauchst, brauchst du den Schluessel bevor Infisical wiederhergestellt ist.

#### 9.4 MinIO Server-Side Encryption

MinIO verschluesselt zusaetzlich alle Objekte im Backup-Bucket mit Server-Side Encryption (SSE-S3). Das bedeutet: die Daten sind doppelt verschluesselt:

1. Restic verschluesselt auf Client-Seite (AES-256)
2. MinIO verschluesselt auf Server-Seite (AES-256)

---

### 10. Disaster Recovery Playbook

Dieses Playbook beschreibt die vollstaendige Wiederherstellung der Toolbox nach einem Totalausfall des Servers.

#### Voraussetzungen fuer Recovery

Du brauchst:

- Zugang zu einem neuen Server (oder den reparierten alten Server)
- Den `BACKUP_ENCRYPTION_KEY`
- Die MinIO-Zugangsdaten (`BACKUP_MINIO_ACCESS_KEY`, `BACKUP_MINIO_SECRET_KEY`)
- Zugang zu den MinIO-Daten (entweder MinIO noch intakt, oder ein Off-Site-Backup der MinIO-Daten)

#### Schritt 1: Neuen Server vorbereiten

```bash
# Betriebssystem installieren (Ubuntu 22.04+ empfohlen)
# Docker installieren
curl -fsSL https://get.docker.com | sh

# Docker-Netzwerk erstellen
docker network create toolbox
```

#### Schritt 2: Coolify installieren

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

Folge dem Coolify-Setup-Wizard. Siehe [02-coolify-setup.md](02-coolify-setup.md).

#### Schritt 3: MinIO deployen

Deploye den `core-data`-Stack, aber zunaechst nur MinIO. Die PostgreSQL- und Redis-Daten werden spaeter aus dem Backup wiederhergestellt.

```bash
# Minimal: Nur MinIO starten
# (Verwende die gleichen MINIO_ROOT_USER / MINIO_ROOT_PASSWORD wie zuvor)
docker run -d \
  --name toolbox-minio \
  --network toolbox \
  -e MINIO_ROOT_USER=<dein_minio_user> \
  -e MINIO_ROOT_PASSWORD=<dein_minio_passwort> \
  -v toolbox_minio_data:/data \
  minio/minio:latest \
  server /data --console-address ":9001"
```

Falls die MinIO-Daten verloren sind (Backup-Repository liegt AUF MinIO!), brauchst du ein Off-Site-Backup oder musst die MinIO-Daten von einem anderen Backup-Medium wiederherstellen.

> **Wichtig:** Wenn MinIO die einzige Kopie der Backups ist UND MinIO verloren ist, kannst du nicht wiederherstellen. Daher ist ein Off-Site-Backup (externes S3, NAS, etc.) dringend empfohlen fuer Produktionsumgebungen. Siehe unten "Off-Site-Backup".

#### Schritt 4: Restic Repository verbinden

```bash
# Temporaeren Backup-Container starten
docker run -it --rm \
  --network toolbox \
  -e RESTIC_REPOSITORY=s3:http://minio:9000/backups \
  -e RESTIC_PASSWORD=<dein_backup_encryption_key> \
  -e AWS_ACCESS_KEY_ID=<dein_backup_access_key> \
  -e AWS_SECRET_ACCESS_KEY=<dein_backup_secret_key> \
  -v /var/lib/docker/volumes:/restore \
  restic/restic:0.17.3 \
  snapshots

# Letzten Snapshot identifizieren
# Ausgabe zeigt Snapshot-IDs, Zeitstempel und Tags
```

#### Schritt 5: Alle Volumes wiederherstellen

```bash
# Vollstaendigen Volume-Snapshot wiederherstellen
docker run -it --rm \
  --network toolbox \
  -e RESTIC_REPOSITORY=s3:http://minio:9000/backups \
  -e RESTIC_PASSWORD=<dein_backup_encryption_key> \
  -e AWS_ACCESS_KEY_ID=<dein_backup_access_key> \
  -e AWS_SECRET_ACCESS_KEY=<dein_backup_secret_key> \
  -v /var/lib/docker/volumes:/restore \
  restic/restic:0.17.3 \
  restore latest --tag volumes --target /restore/
```

Die Volumes liegen nun unter `/var/lib/docker/volumes/restore/source/toolbox_*/`. Kopiere sie an die richtigen Stellen:

```bash
# Fuer jedes Volume
for vol in postgres_data redis_data grafana_data prometheus_data loki_data \
  tempo_data alertmanager_data authentik_media authentik_templates authentik_certs; do

  SOURCE="/var/lib/docker/volumes/restore/source/toolbox_${vol}/_data"
  TARGET="/var/lib/docker/volumes/toolbox_${vol}/_data"

  if [ -d "${SOURCE}" ]; then
    # Volume erstellen (falls es noch nicht existiert)
    docker volume create "toolbox_${vol}" 2>/dev/null || true
    # Daten kopieren
    mkdir -p "${TARGET}"
    cp -a "${SOURCE}/." "${TARGET}/"
    echo "Wiederhergestellt: toolbox_${vol}"
  fi
done

# Aufraeumen
rm -rf /var/lib/docker/volumes/restore
```

#### Schritt 6: PostgreSQL aus Dump wiederherstellen

```bash
# PostgreSQL-Dumps wiederherstellen
docker run -it --rm \
  --network toolbox \
  -e RESTIC_REPOSITORY=s3:http://minio:9000/backups \
  -e RESTIC_PASSWORD=<dein_backup_encryption_key> \
  -e AWS_ACCESS_KEY_ID=<dein_backup_access_key> \
  -e AWS_SECRET_ACCESS_KEY=<dein_backup_secret_key> \
  -v /tmp/restore:/tmp/restore \
  restic/restic:0.17.3 \
  restore latest --tag dumps --target /tmp/restore

# PostgreSQL starten (mit wiederhergestelltem Volume)
# Dann fuer jede Datenbank den Dump importieren:
for DB in grafana sentry posthog unleash infisical authentik; do
  docker exec toolbox-postgres pg_restore \
    -U toolbox \
    -d ${DB} \
    --clean --if-exists --no-owner --no-privileges \
    /tmp/restore/tmp/backup/postgres/${DB}.dump \
    2>/dev/null || echo "Hinweis: ${DB} uebersprungen (kein Dump vorhanden oder Fehler)"
done
```

#### Schritt 7: Alle Stacks deployen

Deploye alle Stacks in der Reihenfolge aus [04-deploy-stack.md](04-deploy-stack.md):

1. Core Data (PostgreSQL, Redis, MinIO)
2. Secrets (Infisical)
3. Auth (Authentik)
4. Observability
5. Analytics (PostHog)
6. Error Tracking (Sentry)
7. Feature Flags (Unleash)
8. Monitoring (Uptime Kuma)
9. Search & AI (Meilisearch, Qdrant)
10. Log Shipping (Alloy)
11. Backups (diesen Stack)

#### Schritt 8: Verifizierung

Pruefe jeden Service:

```bash
# PostgreSQL
docker exec toolbox-postgres pg_isready -U toolbox

# Redis
docker exec toolbox-redis redis-cli -a ${REDIS_PASSWORD} DBSIZE

# Grafana
curl -s https://grafana.example.com/api/health

# Sentry
curl -s https://sentry.example.com/_health/

# PostHog
curl -s https://posthog.example.com/_health

# Unleash
curl -s https://unleash.example.com/health

# Infisical
curl -s https://infisical.example.com/api/status

# Uptime Kuma
curl -s https://status.example.com

# MinIO
curl -s http://minio:9000/minio/health/live
```

#### Off-Site-Backup (dringend empfohlen)

Da MinIO sowohl die Produktionsdaten ALS AUCH die Backups speichert, besteht ein Single-Point-of-Failure. Fuer Produktionsumgebungen empfehlen wir ein zusaetzliches Off-Site-Backup:

```bash
# Option 1: Restic mit zweitem Repository (externer S3-Provider)
restic -r s3:https://s3.provider.com/toolbox-backup copy --from-repo s3:http://minio:9000/backups

# Option 2: MinIO Bucket Replication zu einem anderen MinIO-Server
docker exec toolbox-minio mc replicate add local/backups \
  --remote-bucket "https://ACCESS_KEY:SECRET_KEY@remote-minio.example.com/backups"

# Option 3: rclone Sync zu einem externen Speicher
rclone sync minio:backups remote:toolbox-backups --transfers 4
```

---

### 11. Troubleshooting

#### Backup zu langsam

1. **Netzwerk pruefen:** MinIO und der Backup-Container kommunizieren ueber das Docker-Netzwerk. Pruefe die Netzwerkperformance:
   ```bash
   docker exec toolbox-backup wget -O /dev/null http://minio:9000/minio/health/live
   ```

2. **Grosse PostgreSQL-Datenbanken:** Fuer sehr grosse Datenbanken (>10 GB) kann `pg_dump` lange dauern. Erwaege Parallel-Dump:
   ```bash
   pg_dump -h postgres -U toolbox -d posthog --format=directory --jobs=4 -f /tmp/backup/postgres/posthog_dir/
   ```

3. **MinIO-Performance:** Pruefe die Disk-I/O des MinIO-Volumes:
   ```bash
   docker exec toolbox-minio mc admin speedtest local
   ```

#### Restic Lock (stale lock)

Wenn ein Backup-Prozess unerwartet abbricht, bleibt moeglicherweise ein Lock bestehen:

```bash
# Lock anzeigen
docker exec toolbox-backup restic list locks

# Stale Lock entfernen (NUR wenn kein Backup laeuft!)
docker exec toolbox-backup restic unlock

# Lock entfernen und Repository reparieren
docker exec toolbox-backup restic unlock --remove-all
```

> **Wichtig:** Verwende `restic unlock` nur, wenn du SICHER bist, dass kein anderer Backup-Prozess laeuft. Gleichzeitige Schreiboperationen koennen das Repository beschaedigen.

#### MinIO Bucket voll

```bash
# Bucket-Groesse pruefen
docker exec toolbox-minio mc du local/backups

# Disk-Space pruefen
docker exec toolbox-minio df -h /data

# Alte Snapshots manuell entfernen
docker exec toolbox-backup restic forget --keep-last 5 --prune

# Lifecycle-Policy pruefen
docker exec toolbox-minio mc ilm rule list local/backups
```

#### Restore schlaegt fehl

1. **Snapshot-Integritaet pruefen:**
   ```bash
   docker exec toolbox-backup restic check --read-data
   ```
   Dieser Befehl liest ALLE Daten aus dem Repository und prueft sie. Kann bei grossen Repositories Stunden dauern.

2. **Einzelne Datei aus Snapshot extrahieren:**
   ```bash
   docker exec toolbox-backup restic dump latest /source/toolbox_postgres_data/_data/PG_VERSION > /tmp/test
   ```

3. **Anderes Snapshot versuchen:**
   ```bash
   # Alle Snapshots auflisten
   docker exec toolbox-backup restic snapshots

   # Einen aelteren Snapshot verwenden
   docker exec toolbox-backup restic restore <snapshot-id> --target /tmp/restore
   ```

#### Backup-Container startet nicht

```bash
# Logs pruefen
docker logs toolbox-backup --tail 50

# Haeufige Ursachen:
# 1. Restic Repository nicht initialisiert -> restic init ausfuehren
# 2. MinIO nicht erreichbar -> Docker-Netzwerk pruefen
# 3. Falsche Zugangsdaten -> .env-Datei pruefen

# Repository-Verbindung testen
docker exec toolbox-backup restic snapshots
```

#### Fehlermeldung "repository contains pack files with invalid data"

```bash
# Repository reparieren
docker exec toolbox-backup restic repair packs

# Danach Verifizierung
docker exec toolbox-backup restic check
```

#### Fehlermeldung "Fatal: unable to create lock"

```bash
# Pruefe ob bereits ein Prozess laeuft
docker exec toolbox-backup ps aux | grep restic

# Falls nicht, Lock entfernen
docker exec toolbox-backup restic unlock
```

---

### Checkliste: Backups vollstaendig eingerichtet

- [ ] MinIO Backup-Bucket erstellt und Verschluesselung aktiviert
- [ ] MinIO IAM-Benutzer mit eingeschraenkten Rechten erstellt
- [ ] `BACKUP_ENCRYPTION_KEY` generiert und an 3 Orten gesichert
- [ ] Restic Repository initialisiert (`restic init`)
- [ ] `stacks/backups/docker-compose.yml` erstellt
- [ ] Alle Backup-Skripte unter `stacks/backups/scripts/` erstellt und ausfuehrbar
- [ ] Backup-Container laeuft
- [ ] Manuelles Backup erfolgreich durchgefuehrt (`/scripts/backup.sh`)
- [ ] Cron-Jobs aktiv (taeglich, woechentlich, monatlich)
- [ ] Test-Restore durchgefuehrt (mindestens eine Datenbank)
- [ ] Uptime Kuma Push Monitor eingerichtet
- [ ] Alertmanager Routing fuer Backup-Alerts konfiguriert
- [ ] Disaster Recovery Playbook mit dem Team geteilt
- [ ] Off-Site-Backup eingerichtet (fuer Produktionsumgebungen)

---

## 4. n8n — Workflow-Automation


Dieses Dokument beschreibt die Einrichtung von n8n als zentrale Workflow-Automation-Plattform fuer die Toolbox. n8n verbindet alle Services miteinander und automatisiert wiederkehrende Aufgaben: Sentry-Fehler werden zu Slack-Nachrichten und GitHub-Issues, Uptime-Kuma-Alerts loesen Incident-Response aus, und taegliche Reports fassen PostHog-Metriken zusammen.

> **Voraussetzung:** Der `core-data`-Stack (PostgreSQL, Redis) muss bereits laufen. Siehe [04-deploy-stack.md](04-deploy-stack.md).

---

### 1. Was ist n8n?

n8n ist eine Open-Source Workflow-Automation-Plattform. Sie ist die selbstgehostete Alternative zu Zapier, Make (Integromat) und Microsoft Power Automate. Workflows werden visuell im Browser erstellt: Nodes (Bausteine) werden per Drag & Drop verbunden, jeder Node fuehrt eine Aktion aus oder reagiert auf ein Event.

#### Kernfunktionen

- **400+ Integrationen:** Slack, GitHub, PostgreSQL, HTTP Request, E-Mail, Webhook, Cron, und viele mehr.
- **Visueller Editor:** Workflows werden per Drag & Drop im Browser erstellt. Kein Code noetig, aber moeglich (JavaScript/Python in Function-Nodes).
- **Webhook-Trigger:** n8n kann HTTP-Webhooks empfangen und darauf reagieren. Perfekt fuer Sentry, PostHog, Uptime Kuma und GitHub.
- **Cron-Trigger:** Zeitgesteuerte Workflows (taeglich, stuendlich, minuetlich).
- **Error Handling:** Fehlerhafte Workflow-Ausfuehrungen werden protokolliert und koennen automatisch wiederholt werden.
- **Credentials Store:** API-Keys und Tokens werden verschluesselt in n8n gespeichert.

#### Warum n8n in der Toolbox?

Ohne Automation sind die Toolbox-Services isolierte Inseln. Wenn ein Sentry-Fehler auftritt, muss jemand manuell Sentry pruefen, dann manuell ein GitHub-Issue erstellen, dann manuell das Team benachrichtigen. Mit n8n passiert das automatisch in Sekunden.

Typische Use Cases:

| Trigger                          | Aktion                                              |
|----------------------------------|------------------------------------------------------|
| Sentry: Neuer Fehler             | Slack-Nachricht + GitHub-Issue                       |
| PostHog: User Signup-Event       | Slack-Benachrichtigung                               |
| Uptime Kuma: Service down        | Slack-Alert + GitHub-Incident-Issue                  |
| Cron: Taeglich 9:00 Uhr         | PostHog + Sentry Zusammenfassung nach Slack          |
| Unleash: Feature Flag aktiviert  | Slack-Post + PostHog-Annotation                      |
| Backup-Skript: Fertig            | Slack-Bericht (Erfolg/Fehler)                        |

#### DSGVO-Konformitaet

n8n laeuft vollstaendig auf dem eigenen Server. Alle Workflow-Daten, Credentials und Ausfuehrungshistorien bleiben in der eigenen PostgreSQL-Datenbank. Es werden keine Daten an Drittanbieter uebermittelt (ausser wenn ein Workflow explizit externe APIs aufruft, z.B. Slack).

---

### 2. Architektur

#### Datenfluss

```
+------------------+    +------------------+    +------------------+
|     Sentry       |    |     PostHog      |    |   Uptime Kuma    |
|  (Error Events)  |    |  (User Events)   |    | (Status Alerts)  |
+--------+---------+    +--------+---------+    +--------+---------+
         |                       |                       |
         | Webhook               | Webhook               | Webhook
         |                       |                       |
+--------v-----------------------v-----------------------v---------+
|                                                                   |
|                            n8n                                    |
|                   toolbox-n8n:5678                                 |
|                                                                   |
|   +-------------------+  +-------------------+  +--------------+  |
|   | Webhook Trigger   |  | Cron Trigger      |  | Manual       |  |
|   | (empfaengt Events)|  | (zeitgesteuert)   |  | Trigger      |  |
|   +--------+----------+  +--------+----------+  +------+-------+  |
|            |                      |                     |          |
|   +--------v----------+  +-------v-----------+  +------v-------+  |
|   | Filter / Transform|  | API Abfragen      |  | Function     |  |
|   | (If, Set, Switch) |  | (HTTP Request)    |  | (JavaScript) |  |
|   +--------+----------+  +-------+-----------+  +------+-------+  |
|            |                      |                     |          |
|   +--------v----------------------v---------------------v-------+  |
|   |                    Aktionen                                 |  |
|   |  Slack Message | GitHub Issue | Email | PostHog Annotation  |  |
|   +---------------------------------------------------------+   |  |
+---+-------------------------------------------------------------+--+
    |                           |
    | PostgreSQL (Workflow-     | Redis (Queue fuer
    |  Daten, Credentials,     |  Worker-Modus)
    |  Ausfuehrungshistorie)   |
    |                           |
+---v---------------------------v---+
|         Core Data Stack           |
|  toolbox-postgres / toolbox-redis |
+-----------------------------------+
```

#### Ressourcen

n8n nutzt die gemeinsame Infrastruktur der Toolbox:

- **PostgreSQL:** Speichert Workflows, Credentials (AES-256-verschluesselt), Ausfuehrungshistorie, Benutzerkonten. Eigene Datenbank `n8n`.
- **Redis:** Task-Queue fuer den Worker-Modus (parallele Ausfuehrung). Nutzt eine separate Redis-DB (DB 3), um nicht mit anderen Services zu kollidieren.

#### Integration in die Toolbox

n8n laeuft als eigener Stack im Docker-Netzwerk `toolbox`. Es kann alle anderen Services ueber deren interne Hostnames erreichen (z.B. `http://posthog:8000` fuer PostHog-API-Aufrufe innerhalb des Netzwerks).

---

### 3. Stack Setup

#### PostgreSQL-Datenbank vorbereiten

Bevor n8n gestartet wird, muss die Datenbank `n8n` in der gemeinsamen PostgreSQL-Instanz existieren. Fuege folgenden Eintrag zum Init-Script hinzu:

```sql
-- In stacks/core-data/init-scripts/postgres/01-create-databases.sql
-- (falls noch nicht vorhanden)
CREATE DATABASE n8n;
```

Falls PostgreSQL bereits laeuft und die Datenbank fehlt, erstelle sie manuell:

```bash
docker exec toolbox-postgres psql -U toolbox -c "CREATE DATABASE n8n;"
docker exec toolbox-postgres psql -U toolbox -c "GRANT ALL PRIVILEGES ON DATABASE n8n TO toolbox;"
```

#### Docker Compose

```yaml
# stacks/automation/docker-compose.yml
# n8n Workflow Automation - verbindet alle Toolbox-Services

services:
  # -----------------------------------------------
  # n8n - Workflow Automation Engine
  # -----------------------------------------------
  n8n:
    image: n8nio/n8n:latest
    container_name: toolbox-n8n
    restart: unless-stopped
    environment:
      # --- Datenbank (gemeinsame PostgreSQL-Instanz) ---
      DB_TYPE: postgresdb
      DB_POSTGRESDB_HOST: postgres
      DB_POSTGRESDB_PORT: 5432
      DB_POSTGRESDB_DATABASE: n8n
      DB_POSTGRESDB_USER: ${POSTGRES_USER:-toolbox}
      DB_POSTGRESDB_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
      # --- Redis Queue (fuer parallele Ausfuehrung) ---
      QUEUE_BULL_REDIS_HOST: redis
      QUEUE_BULL_REDIS_PORT: 6379
      QUEUE_BULL_REDIS_PASSWORD: ${REDIS_PASSWORD:?REDIS_PASSWORD is required}
      QUEUE_BULL_REDIS_DB: 3
      # --- n8n Konfiguration ---
      N8N_HOST: ${N8N_HOST:-n8n.example.com}
      N8N_PORT: 5678
      N8N_PROTOCOL: https
      WEBHOOK_URL: https://${N8N_HOST:-n8n.example.com}/
      # --- Verschluesselung ---
      # Schluessel fuer die AES-256-Verschluesselung aller Credentials.
      # Bei Verlust koennen gespeicherte Credentials nicht mehr entschluesselt werden!
      N8N_ENCRYPTION_KEY: ${N8N_ENCRYPTION_KEY:?N8N_ENCRYPTION_KEY is required}
      # --- Benutzerverwaltung ---
      N8N_USER_MANAGEMENT_DISABLED: "false"
      # --- Ausfuehrungshistorie ---
      EXECUTIONS_DATA_PRUNE: "true"
      EXECUTIONS_DATA_MAX_AGE: 168
      EXECUTIONS_DATA_PRUNE_MAX_COUNT: 50000
      # --- Timezone ---
      GENERIC_TIMEZONE: Europe/Berlin
      TZ: Europe/Berlin
      # --- Telemetrie deaktivieren ---
      N8N_DIAGNOSTICS_ENABLED: "false"
      N8N_VERSION_NOTIFICATIONS_ENABLED: "false"
    volumes:
      - n8n_data:/home/node/.n8n
    networks:
      - toolbox
    healthcheck:
      test: ["CMD-SHELL", "wget --spider -q http://localhost:5678/healthz || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    # Port 5678 wird nicht nach aussen exponiert.
    # Coolify routet den Traffic ueber die zugewiesene Domain.

volumes:
  n8n_data:
    name: toolbox_n8n_data

networks:
  toolbox:
    external: true
    name: toolbox
```

#### Umgebungsvariablen (.env.example)

```bash
# stacks/automation/.env.example
# n8n Workflow Automation

# --- Shared credentials (from core-data stack) ---
POSTGRES_USER=toolbox
POSTGRES_PASSWORD=CHANGE_ME_postgres_password
REDIS_PASSWORD=CHANGE_ME_redis_password

# --- n8n-specific ---
# Oeffentliche Domain (wird von Coolify geroutet)
N8N_HOST=n8n.example.com

# Verschluesselungsschluessel fuer Credentials (AES-256).
# Generieren mit: openssl rand -hex 32
# WICHTIG: Diesen Schluessel sicher aufbewahren! Bei Verlust koennen
# alle gespeicherten Credentials (API-Keys, Tokens) nicht mehr
# entschluesselt werden.
N8N_ENCRYPTION_KEY=CHANGE_ME_n8n_encryption_key
```

#### Secrets generieren

```bash
# n8n Encryption Key (64 Hex-Zeichen = 32 Bytes)
N8N_ENCRYPTION_KEY=$(openssl rand -hex 32)
echo "N8N_ENCRYPTION_KEY=$N8N_ENCRYPTION_KEY"
```

> **Wichtig:** Den Encryption Key in Infisical oder einem Passwort-Manager sichern. Ohne diesen Schluessel koennen gespeicherte Credentials nicht wiederhergestellt werden.

---

### 4. Erstinstallation

#### 4.1 Datenbank anlegen

```bash
# Pruefe ob PostgreSQL laeuft
docker exec toolbox-postgres pg_isready -U toolbox
# Erwartet: /var/run/postgresql:5432 - accepting connections

# Erstelle die n8n-Datenbank
docker exec toolbox-postgres psql -U toolbox -c "CREATE DATABASE n8n;"
docker exec toolbox-postgres psql -U toolbox -c "GRANT ALL PRIVILEGES ON DATABASE n8n TO toolbox;"
```

#### 4.2 Deploy via Coolify

1. Erstelle in Coolify eine neue Docker-Compose-Ressource.
2. Zeige auf `stacks/automation/docker-compose.yml`.
3. Setze die Umgebungsvariablen aus der `.env.example`.
4. Weise die Domain `n8n.example.com` dem Service `n8n` auf Port `5678` zu.
5. Deploye den Stack.

#### 4.3 Admin-Account erstellen

Beim ersten Aufruf von `https://n8n.example.com` wird der Setup-Wizard angezeigt:

1. Oeffne `https://n8n.example.com`.
2. Erstelle einen Owner-Account (E-Mail, Passwort, Name).
3. Du landest auf dem n8n-Dashboard.

#### 4.4 Webhook-URL verifizieren

Die Webhook-URL ist entscheidend fuer alle Webhook-Trigger. Pruefe sie:

1. Oeffne n8n > **Settings** > **General**.
2. Pruefe, dass die **Webhook URL** auf `https://n8n.example.com/` gesetzt ist.
3. Erstelle einen Test-Workflow mit einem Webhook-Node und pruefe, ob die angezeigte URL korrekt ist.

#### 4.5 Verifizierung

```bash
# Pruefe ob n8n laeuft
docker logs toolbox-n8n --tail 10
# Erwartet: "n8n ready on 0.0.0.0, port 5678"

# Health Check
curl -s https://n8n.example.com/healthz
# Erwartet: {"status":"ok"}
```

---

### 5. Praxis-Workflows

#### 5a. Sentry Error -> Slack Notification + GitHub Issue

Dieser Workflow wird bei jedem neuen Sentry-Fehler ausgeloest: Er filtert nach Severity, sendet eine Slack-Nachricht und erstellt ein GitHub-Issue.

##### Workflow-Aufbau (Nodes)

```
[Webhook Trigger] --> [If: Severity >= ERROR] --> [Slack: Send Message]
                                               --> [GitHub: Create Issue]
```

##### Schritt 1: Webhook Trigger erstellen

1. Erstelle einen neuen Workflow in n8n.
2. Fuege einen **Webhook**-Node hinzu:
   - **HTTP Method:** POST
   - **Path:** `sentry-error`
   - **Authentication:** Header Auth
   - **Header Name:** `X-Sentry-Hook-Signature`
3. Aktiviere den Workflow. Notiere die Webhook-URL: `https://n8n.example.com/webhook/sentry-error`

##### Schritt 2: Sentry Webhook einrichten

1. Oeffne Sentry > **Settings** > **Integrations** > **Internal Integrations**.
2. Klicke **Create New Integration**.
3. Konfiguriere:
   - **Name:** `n8n Automation`
   - **Webhook URL:** `https://n8n.example.com/webhook/sentry-error`
   - **Permissions:** Issue & Event: Read
   - **Webhooks:** Aktiviere `issue` (Alert-Webhooks)
4. Speichere und notiere das **Client Secret** (fuer die Signatur-Verifizierung).
5. Unter **Alerts** > **Alert Rules** erstelle eine Regel:
   - **When:** A new issue is created
   - **Then:** Send a notification via [n8n Automation]

##### Schritt 3: Severity filtern (If-Node)

Fuege einen **If**-Node hinzu:

- **Condition:** `{{ $json.data.issue.level }}` ist gleich `error` ODER `fatal`
- Damit werden `info`- und `warning`-Level-Eintraege ignoriert.

##### Schritt 4: Slack-Nachricht senden

Fuege einen **Slack**-Node hinzu:

- **Resource:** Message
- **Operation:** Send
- **Channel:** `#engineering-alerts`
- **Message:**
  ```
  :rotating_light: *Sentry Error*
  *{{ $json.data.issue.title }}*
  Project: {{ $json.data.issue.project.name }}
  Level: {{ $json.data.issue.level }}
  Times seen: {{ $json.data.issue.count }}
  Link: {{ $json.data.issue.permalink }}
  ```

##### Schritt 5: GitHub Issue erstellen

Fuege einen **GitHub**-Node hinzu:

- **Resource:** Issue
- **Operation:** Create
- **Owner:** dein-github-username
- **Repository:** dein-repo
- **Title:** `[Sentry] {{ $json.data.issue.title }}`
- **Body:**
  ```
  ## Sentry Error Report

  **Error:** {{ $json.data.issue.title }}
  **Project:** {{ $json.data.issue.project.name }}
  **Level:** {{ $json.data.issue.level }}
  **First seen:** {{ $json.data.issue.firstSeen }}
  **Times seen:** {{ $json.data.issue.count }}

  [View in Sentry]({{ $json.data.issue.permalink }})

  ---
  *Automatically created by n8n workflow*
  ```
- **Labels:** `bug`, `sentry`

##### Vollstaendiger Workflow JSON-Export

```json
{
  "name": "Sentry Error → Slack + GitHub",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "sentry-error",
        "options": {}
      },
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [240, 300],
      "name": "Sentry Webhook"
    },
    {
      "parameters": {
        "conditions": {
          "options": {
            "caseSensitive": false
          },
          "combinator": "or",
          "conditions": [
            {
              "leftValue": "={{ $json.data.issue.level }}",
              "rightValue": "error",
              "operator": { "type": "string", "operation": "equals" }
            },
            {
              "leftValue": "={{ $json.data.issue.level }}",
              "rightValue": "fatal",
              "operator": { "type": "string", "operation": "equals" }
            }
          ]
        }
      },
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [460, 300],
      "name": "Severity Filter"
    },
    {
      "parameters": {
        "channel": "#engineering-alerts",
        "text": ":rotating_light: *Sentry Error*\n*{{ $json.data.issue.title }}*\nProject: {{ $json.data.issue.project.name }}\nLevel: {{ $json.data.issue.level }}\nTimes seen: {{ $json.data.issue.count }}\nLink: {{ $json.data.issue.permalink }}"
      },
      "type": "n8n-nodes-base.slack",
      "typeVersion": 2,
      "position": [700, 200],
      "name": "Slack Alert"
    },
    {
      "parameters": {
        "owner": "your-org",
        "repository": "your-repo",
        "title": "=[Sentry] {{ $json.data.issue.title }}",
        "body": "=## Sentry Error Report\n\n**Error:** {{ $json.data.issue.title }}\n**Project:** {{ $json.data.issue.project.name }}\n**Level:** {{ $json.data.issue.level }}\n**First seen:** {{ $json.data.issue.firstSeen }}\n**Times seen:** {{ $json.data.issue.count }}\n\n[View in Sentry]({{ $json.data.issue.permalink }})\n\n---\n*Automatically created by n8n*",
        "labels": ["bug", "sentry"]
      },
      "type": "n8n-nodes-base.github",
      "typeVersion": 1,
      "position": [700, 400],
      "name": "Create GitHub Issue"
    }
  ],
  "connections": {
    "Sentry Webhook": { "main": [[{ "node": "Severity Filter", "type": "main", "index": 0 }]] },
    "Severity Filter": {
      "main": [
        [{ "node": "Slack Alert", "type": "main", "index": 0 }, { "node": "Create GitHub Issue", "type": "main", "index": 0 }],
        []
      ]
    }
  }
}
```

---

#### 5b. PostHog Event -> Custom Action

Dieser Workflow reagiert auf spezifische PostHog-Events, z.B. wenn ein neuer Benutzer sich registriert.

##### PostHog Webhook konfigurieren

1. Oeffne PostHog > **Data Management** > **Actions**.
2. Erstelle eine neue Action:
   - **Name:** `User Signed Up`
   - **Match:** Custom event `user_signed_up`
3. Gehe zu PostHog > **Settings** > **Project** > **Webhooks**.
4. Fuege einen Webhook hinzu:
   - **URL:** `https://n8n.example.com/webhook/posthog-signup`
   - **Events:** Waehle die Action `User Signed Up`

##### n8n Workflow

```
[Webhook: posthog-signup] --> [Set: Extract User Data] --> [Slack: Welcome Message]
```

1. **Webhook-Node:** Path `posthog-signup`, Method POST.
2. **Set-Node:** Extrahiere die relevanten Felder:
   - `userName`: `{{ $json.data.person.properties.name }}`
   - `userEmail`: `{{ $json.data.person.properties.email }}`
   - `signupDate`: `{{ $json.data.timestamp }}`
3. **Slack-Node:**
   - Channel: `#new-signups`
   - Message:
     ```
     :wave: *Neuer User*
     Name: {{ $json.userName }}
     E-Mail: {{ $json.userEmail }}
     Zeitpunkt: {{ $json.signupDate }}
     ```

---

#### 5c. Uptime Kuma Alert -> Incident Response

Wenn ein Service ausfaellt, wird automatisch ein Incident-Prozess gestartet.

##### Uptime Kuma Notification Provider einrichten

1. Oeffne Uptime Kuma > **Settings** > **Notifications**.
2. Klicke **Setup Notification**.
3. Waehle **Webhook**:
   - **URL:** `https://n8n.example.com/webhook/uptime-alert`
   - **Request Method:** POST
   - **Content Type:** application/json
4. Teste die Notification.

##### n8n Workflow

```
[Webhook: uptime-alert] --> [If: Status=down] --> [Slack: Alert #ops-critical]
                                                --> [GitHub: Create Incident Issue]
                         --> [If: Status=up]   --> [Slack: Resolution #ops]
                                                --> [GitHub: Close Issue + Comment]
```

**Webhook Payload von Uptime Kuma:**

```json
{
  "heartbeat": {
    "status": 0,
    "msg": "Connection refused",
    "time": "2025-01-15 10:30:00",
    "duration": 120
  },
  "monitor": {
    "name": "PostHog",
    "url": "https://posthog.example.com"
  }
}
```

**If-Node Bedingung (Service down):**

- `{{ $json.heartbeat.status }}` ist gleich `0`

**Slack Alert (Down):**

```
:red_circle: *SERVICE DOWN*
Service: {{ $json.monitor.name }}
URL: {{ $json.monitor.url }}
Fehler: {{ $json.heartbeat.msg }}
Zeitpunkt: {{ $json.heartbeat.time }}
```

**Slack Alert (Recovery):**

```
:large_green_circle: *SERVICE RECOVERED*
Service: {{ $json.monitor.name }}
URL: {{ $json.monitor.url }}
Downtime: {{ $json.heartbeat.duration }}s
Zeitpunkt: {{ $json.heartbeat.time }}
```

**GitHub Issue (Incident):**

- **Title:** `Incident: {{ $json.monitor.name }} down`
- **Labels:** `incident`, `ops`
- **Body:** Service-Details und Fehlermeldung

---

#### 5d. Taeglicher Analytics Report

Jeden Morgen um 9:00 Uhr wird eine Zusammenfassung aus PostHog und Sentry nach Slack geschickt.

##### n8n Workflow

```
[Cron: 9:00 daily] --> [HTTP: PostHog API] --> [HTTP: Sentry API] --> [Function: Format] --> [Slack: #daily-report]
```

**Cron-Node:**

- **Mode:** Every Day
- **Hour:** 9
- **Minute:** 0

**PostHog API Abfrage (HTTP Request Node):**

- **Method:** POST
- **URL:** `http://posthog:8000/api/projects/1/insights/trend/`
- **Authentication:** Header Auth (`Authorization: Bearer YOUR_POSTHOG_API_KEY`)
- **Body (JSON):**
  ```json
  {
    "events": [{"id": "$pageview", "math": "total"}],
    "date_from": "-1d",
    "date_to": "now"
  }
  ```

**Sentry API Abfrage (HTTP Request Node):**

- **Method:** GET
- **URL:** `http://sentry:9000/api/0/projects/sentry/your-project/issues/?query=is:unresolved&statsPeriod=24h`
- **Authentication:** Header Auth (`Authorization: Bearer YOUR_SENTRY_API_TOKEN`)

**Function-Node (JavaScript):**

```javascript
const posthogData = $input.first().json;
const sentryData = $input.last().json;

const pageViews = posthogData.result?.[0]?.aggregated_value || 'N/A';
const openIssues = Array.isArray(sentryData) ? sentryData.length : 0;
const criticalIssues = Array.isArray(sentryData)
  ? sentryData.filter(i => i.level === 'fatal' || i.level === 'error').length
  : 0;

const today = new Date().toLocaleDateString('de-DE', {
  weekday: 'long',
  year: 'numeric',
  month: 'long',
  day: 'numeric'
});

return [{
  json: {
    message: `:newspaper: *Daily Report - ${today}*\n\n` +
      `*Analytics (PostHog):*\n` +
      `- Page Views (gestern): ${pageViews}\n\n` +
      `*Error Tracking (Sentry):*\n` +
      `- Neue ungeloeste Issues: ${openIssues}\n` +
      `- Davon Error/Fatal: ${criticalIssues}\n\n` +
      `_Report generiert von n8n_`
  }
}];
```

**Slack-Node:**

- Channel: `#daily-report`
- Message: `{{ $json.message }}`

---

#### 5e. Feature Flag Rollout Automation

Wenn ein Feature Flag in Unleash fuer Production aktiviert wird, startet ein automatisierter Ueberwachungsprozess.

##### Unleash Webhook einrichten

1. Oeffne Unleash > **Configure** > **Addons**.
2. Klicke **New Addon** > **Webhook**.
3. Konfiguriere:
   - **URL:** `https://n8n.example.com/webhook/unleash-flag`
   - **Events:** `feature-environment-enabled`, `feature-environment-disabled`
4. Speichere den Addon.

##### n8n Workflow

```
[Webhook: unleash-flag] --> [If: Environment=production]
    --> [Slack: #releases]
    --> [HTTP: PostHog Annotation]
    --> [Wait: 1 hour]
    --> [HTTP: Sentry Error Count]
    --> [If: Error Rate > Threshold]
        --> TRUE:  [HTTP: Unleash Disable Flag] --> [Slack: Flag Disabled Alert]
        --> FALSE: [Slack: Rollout Successful]
```

**Slack-Nachricht bei Aktivierung:**

```
:rocket: *Feature Flag Activated*
Flag: {{ $json.data.featureName }}
Environment: {{ $json.data.environment }}
Activated by: {{ $json.createdBy }}
```

**PostHog Annotation erstellen (HTTP Request):**

- **Method:** POST
- **URL:** `http://posthog:8000/api/projects/1/annotations/`
- **Body:**
  ```json
  {
    "content": "Feature Flag enabled: {{ $json.data.featureName }}",
    "date_marker": "{{ $now.toISO() }}",
    "scope": "project"
  }
  ```

**Sentry Error Count pruefen (nach 1 Stunde Wait-Node):**

- **Method:** GET
- **URL:** `http://sentry:9000/api/0/projects/sentry/your-project/stats/?stat=received&resolution=1h&since={{ $now.minus(1, 'hour').toUnixInteger() }}`

**Auto-Disable bei Fehler-Spike (HTTP Request):**

- **Method:** POST
- **URL:** `http://unleash:4242/api/admin/projects/default/features/{{ $json.data.featureName }}/environments/production/off`
- **Header:** `Authorization: *:*.YOUR_UNLEASH_API_TOKEN`

---

#### 5f. Backup Status Notification

Das Backup-Skript (siehe [17-restic-backups.md](17-restic-backups.md)) kann nach Abschluss einen Webhook an n8n senden.

##### Webhook Aufruf im Backup-Skript

Fuege am Ende des Backup-Skripts hinzu:

```bash
# Bei Erfolg
curl -s -X POST https://n8n.example.com/webhook/backup-status \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"success\",
    \"type\": \"$BACKUP_TYPE\",
    \"duration_seconds\": $DURATION,
    \"size_bytes\": $BACKUP_SIZE,
    \"snapshots_total\": $SNAPSHOT_COUNT,
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
  }"

# Bei Fehler
curl -s -X POST https://n8n.example.com/webhook/backup-status \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"failure\",
    \"type\": \"$BACKUP_TYPE\",
    \"error\": \"$ERROR_MESSAGE\",
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
  }"
```

##### n8n Workflow

```
[Webhook: backup-status] --> [If: status=success]
    --> TRUE:  [Slack: #ops "Backup erfolgreich"]
    --> FALSE: [Slack: #ops-critical "Backup fehlgeschlagen!"]
```

**Slack bei Erfolg:**

```
:white_check_mark: *Backup Successful*
Type: {{ $json.type }}
Duration: {{ Math.round($json.duration_seconds / 60) }} min
Size: {{ Math.round($json.size_bytes / 1024 / 1024) }} MB
Snapshots total: {{ $json.snapshots_total }}
```

**Slack bei Fehler:**

```
:x: *BACKUP FAILED*
Type: {{ $json.type }}
Error: {{ $json.error }}
Timestamp: {{ $json.timestamp }}
@channel Please investigate immediately!
```

---

### 6. Webhook-Konfiguration

#### 6.1 n8n Webhook-URLs

Alle Webhook-Trigger in n8n erzeugen zwei URLs:

| URL-Typ     | Format                                                 | Zweck                |
|-------------|--------------------------------------------------------|----------------------|
| Production  | `https://n8n.example.com/webhook/<path>`               | Fuer aktive Workflows|
| Test        | `https://n8n.example.com/webhook-test/<path>`          | Fuer Debugging       |

**Wichtig:** Die Production-URL funktioniert nur, wenn der Workflow **aktiv** ist (gruener Toggle oben rechts). Die Test-URL funktioniert nur waehrend des manuellen Testens im Editor.

#### 6.2 Webhook Security

##### Header Authentication

Fuege jedem Webhook-Node eine Authentifizierung hinzu:

1. Im Webhook-Node: **Authentication** > **Header Auth**.
2. Setze einen Header-Namen (z.B. `X-Webhook-Secret`) und einen geheimen Wert.
3. Konfiguriere die sendende Anwendung, diesen Header mitzuschicken.

##### IP-Einschraenkung (optional)

Da alle Services im Docker-Netzwerk `toolbox` laufen, kommen interne Webhooks von Docker-internen IPs. Fuer externe Webhooks (z.B. GitHub) koennen IP-Ranges auf Reverse-Proxy-Ebene (Coolify/Traefik) eingeschraenkt werden.

#### 6.3 Sentry Webhook Einrichtung

1. Sentry > **Settings** > **Integrations** > **Internal Integrations** > Create.
2. Setze die Webhook-URL auf `https://n8n.example.com/webhook/sentry-error`.
3. Waehle die Events: `issue` (fuer neue und zugewiesene Issues).
4. Notiere das **Client Secret** fuer die Signatur-Verifizierung.

#### 6.4 PostHog Webhook Einrichtung

1. PostHog > **Settings** > **Project Settings** > **Webhook Integration**.
2. Setze die URL auf `https://n8n.example.com/webhook/posthog-event`.
3. Alternativ: Nutze PostHog **Actions** mit Webhook-Destination fuer spezifische Events.

#### 6.5 Uptime Kuma Notification Provider

1. Uptime Kuma > **Settings** > **Notifications** > **Setup Notification**.
2. Typ: **Webhook**.
3. URL: `https://n8n.example.com/webhook/uptime-alert`.
4. Content Type: `application/json`.
5. Weise die Notification den gewuenschten Monitoren zu.

---

### 7. Credentials Management

#### 7.1 Credentials in n8n speichern

n8n verschluesselt alle Credentials mit AES-256 unter Verwendung des `N8N_ENCRYPTION_KEY`. Credentials werden in der PostgreSQL-Datenbank gespeichert.

Erstelle folgende Credentials in n8n unter **Settings** > **Credentials**:

| Credential-Typ        | Name                  | Benoetigte Werte                          |
|------------------------|-----------------------|-------------------------------------------|
| Slack API              | `Slack Toolbox`       | Bot Token (OAuth Token)                   |
| GitHub API             | `GitHub Toolbox`      | Personal Access Token (Scopes: repo)      |
| Header Auth            | `Sentry API Token`    | Authorization: Bearer TOKEN               |
| Header Auth            | `PostHog API Key`     | Authorization: Bearer TOKEN               |
| Header Auth            | `Unleash API Token`   | Authorization: *:*.TOKEN                  |

#### 7.2 API-Tokens generieren

**Sentry API Token:**

1. Sentry > **Settings** > **Account** > **API** > **Auth Tokens**.
2. Erstelle einen Token mit Scopes: `project:read`, `event:read`, `issue:read`.

**PostHog API Key:**

1. PostHog > **Settings** > **Project** > **Personal API Keys**.
2. Erstelle einen Key mit Scopes: `query:read`, `annotation:write`.

**GitHub Personal Access Token:**

1. GitHub > **Settings** > **Developer Settings** > **Personal Access Tokens** > **Fine-grained tokens**.
2. Erstelle einen Token mit Scopes: `Issues: Read and Write` fuer die relevanten Repositories.

**Slack Bot Token:**

1. Erstelle eine Slack App unter https://api.slack.com/apps.
2. Fuege OAuth Scopes hinzu: `chat:write`, `chat:write.public`.
3. Installiere die App in deinem Workspace.
4. Kopiere den Bot User OAuth Token (`xoxb-...`).

**Unleash API Token:**

1. Unleash > **Configure** > **API Access**.
2. Erstelle einen Admin API Token.

#### 7.3 Integration mit Infisical (optional)

Anstatt Credentials direkt in n8n zu speichern, koennen sensible Werte in Infisical verwaltet und ueber Umgebungsvariablen in n8n injiziert werden. n8n kann Umgebungsvariablen in Workflows ueber `$env.VARIABLE_NAME` referenzieren.

Fuege die Variable `N8N_CUSTOM_EXTENSIONS` nicht hinzu - stattdessen nutze HTTP Request Nodes mit Headern, die auf `$env`-Variablen verweisen:

```yaml
# In docker-compose.yml zusaetzliche Umgebungsvariablen:
environment:
  SENTRY_API_TOKEN: ${SENTRY_API_TOKEN}
  POSTHOG_API_KEY: ${POSTHOG_API_KEY}
  SLACK_BOT_TOKEN: ${SLACK_BOT_TOKEN}
```

In n8n-Workflows dann: `{{ $env.SENTRY_API_TOKEN }}`

---

### 8. Monitoring und Troubleshooting

#### 8.1 Ausfuehrungshistorie

n8n speichert alle Workflow-Ausfuehrungen mit Status, Dauer und Ein-/Ausgabedaten:

1. Oeffne n8n > **Executions** (linke Seitenleiste).
2. Filtere nach:
   - **Status:** `Success`, `Error`, `Waiting`
   - **Workflow:** Bestimmter Workflow
   - **Zeitraum:** Letzte 24 Stunden, 7 Tage, etc.
3. Klicke auf eine Ausfuehrung um den Datenfluss durch jeden Node zu sehen.

#### 8.2 Fehlgeschlagene Workflows

Konfiguriere Fehler-Notifications direkt in n8n:

1. Oeffne n8n > **Settings** > **Workflow Settings** (pro Workflow).
2. Unter **Error Workflow:** Waehle einen dedizierten Error-Handler-Workflow.
3. Der Error-Handler empfaengt den Fehlernamen, die Fehlermeldung und den betroffenen Workflow.

**Error-Handler Workflow:**

```
[Error Trigger] --> [Slack: Send Error to #n8n-errors]
```

Slack-Nachricht:

```
:warning: *n8n Workflow Error*
Workflow: {{ $json.workflow.name }}
Error: {{ $json.execution.error.message }}
Node: {{ $json.execution.lastNodeExecuted }}
Execution ID: {{ $json.execution.id }}
Link: https://n8n.example.com/workflow/{{ $json.workflow.id }}/executions/{{ $json.execution.id }}
```

#### 8.3 Performance

| Einstellung                    | Empfehlung           | Beschreibung                                  |
|--------------------------------|----------------------|-----------------------------------------------|
| `EXECUTIONS_DATA_PRUNE`       | `true`               | Alte Ausfuehrungen automatisch loeschen       |
| `EXECUTIONS_DATA_MAX_AGE`     | `168` (7 Tage)       | Ausfuehrungen aelter als 7 Tage loeschen     |
| `EXECUTIONS_DATA_PRUNE_MAX_COUNT` | `50000`          | Maximal 50.000 Ausfuehrungen behalten        |

Typischer Ressourcenverbrauch:

| Ressource | Idle             | Unter Last (10+ gleichzeitige Workflows) |
|-----------|------------------|------------------------------------------|
| RAM       | 150-250 MB       | 300-500 MB                               |
| CPU       | <1%              | 5-15%                                    |
| Disk      | Abhaengig von Ausfuehrungshistorie | Abhaengig von Ausfuehrungshistorie |

#### 8.4 Haeufige Probleme

##### Webhook antwortet mit 404

- **Ursache:** Workflow ist nicht aktiv.
- **Loesung:** Oeffne den Workflow und aktiviere ihn (gruener Toggle oben rechts).
- **Hinweis:** Beim Testen im Editor wird die Test-URL (`/webhook-test/`) verwendet, nicht die Production-URL.

##### Webhook-Timeout

- **Ursache:** Der Workflow braucht laenger als die Standard-Timeout-Zeit.
- **Loesung:** Fuege einen **Respond to Webhook**-Node am Anfang des Workflows hinzu. Dieser antwortet sofort dem Aufrufer (HTTP 200) und der Rest des Workflows laeuft asynchron weiter.

##### Credentials-Fehler nach Migration

- **Ursache:** `N8N_ENCRYPTION_KEY` hat sich geaendert oder wurde nicht migriert.
- **Loesung:** Der Encryption Key muss identisch sein mit dem Schluessel, der beim Erstellen der Credentials verwendet wurde. Stelle den alten Key wieder her oder erstelle alle Credentials neu.

##### n8n startet nicht - Datenbankfehler

```bash
# Pruefe ob die Datenbank existiert
docker exec toolbox-postgres psql -U toolbox -l | grep n8n
# Erwartet: n8n | toolbox | ...

# Pruefe die Verbindung
docker exec toolbox-n8n wget -qO- http://postgres:5432 2>&1 || echo "Connection check"

# Pruefe die Logs
docker logs toolbox-n8n --tail 50 2>&1 | grep -i error
```

##### Redis-Verbindungsfehler

```bash
# Pruefe ob Redis erreichbar ist
docker exec toolbox-n8n wget -qO- http://redis:6379 2>&1 || echo "Redis check"

# Pruefe ob die Redis-DB 3 nutzbar ist
docker exec toolbox-redis redis-cli -a YOUR_REDIS_PASSWORD -n 3 PING
# Erwartet: PONG
```

---

### 9. Backup der n8n-Workflows

#### 9.1 Workflows exportieren

n8n bietet einen CLI-Befehl zum Exportieren aller Workflows:

```bash
# Alle Workflows als JSON exportieren
docker exec toolbox-n8n n8n export:workflow --all --output=/home/node/.n8n/backups/workflows.json

# Alle Credentials exportieren (verschluesselt)
docker exec toolbox-n8n n8n export:credentials --all --output=/home/node/.n8n/backups/credentials.json
```

#### 9.2 Workflows importieren

```bash
# Workflows importieren
docker exec toolbox-n8n n8n import:workflow --input=/home/node/.n8n/backups/workflows.json

# Credentials importieren
docker exec toolbox-n8n n8n import:credentials --input=/home/node/.n8n/backups/credentials.json
```

#### 9.3 Automatisches Backup

Da n8n alle Daten in PostgreSQL speichert, werden die Workflows automatisch durch das Restic-Backup der PostgreSQL-Datenbank gesichert (siehe [17-restic-backups.md](17-restic-backups.md)). Ein separates Backup ist nicht zwingend noetig, kann aber als zusaetzliche Sicherung dienen.

---

### Checkliste: n8n vollstaendig eingerichtet

- [ ] PostgreSQL-Datenbank `n8n` erstellt
- [ ] `stacks/automation/docker-compose.yml` erstellt
- [ ] `.env` mit Encryption Key und Shared Credentials konfiguriert
- [ ] Encryption Key sicher in Infisical / Passwort-Manager gespeichert
- [ ] Stack via Coolify deployed
- [ ] n8n-Container laeuft und ist healthy
- [ ] Admin-Account erstellt
- [ ] Webhook-URL korrekt konfiguriert (`https://n8n.example.com/`)
- [ ] Credentials erstellt: Slack, GitHub, Sentry, PostHog, Unleash
- [ ] Workflow: Sentry Error -> Slack + GitHub Issue (aktiv)
- [ ] Workflow: Uptime Kuma Alert -> Incident Response (aktiv)
- [ ] Workflow: Taeglicher Report -> Slack (aktiv)
- [ ] Error-Handler-Workflow konfiguriert
- [ ] Ausfuehrungshistorie-Pruning aktiviert
- [ ] Sentry Webhook-Integration eingerichtet
- [ ] PostHog Webhook-Integration eingerichtet
- [ ] Uptime Kuma Notification Provider eingerichtet
- [ ] Unleash Webhook-Addon eingerichtet
- [ ] Backup-Skript Webhook-Aufruf integriert

---

## 5. Trivy — Container-Security


Dieses Dokument beschreibt die Einrichtung von Trivy als Schwachstellen-Scanner fuer die gesamte Toolbox. Trivy scannt alle Docker-Images auf bekannte Sicherheitsluecken (CVEs), prueft Docker-Compose-Dateien auf Fehlkonfigurationen und findet versehentlich committete Secrets im Code.

> **Voraussetzung:** Der `core-data`-Stack und die zu scannenden Stacks muessen bereits laufen. Siehe [04-deploy-stack.md](04-deploy-stack.md).

---

### 1. Was ist Trivy?

Trivy ist ein Open-Source Vulnerability- und Misconfiguration-Scanner von Aqua Security. Es ist das am weitesten verbreitete Open-Source-Tool fuer Container-Security und wird von der CNCF (Cloud Native Computing Foundation) als Sandbox-Projekt gefuehrt.

#### Was Trivy findet

| Scan-Typ           | Was wird gescannt?                              | Was wird gefunden?                                     |
|---------------------|--------------------------------------------------|--------------------------------------------------------|
| Container Images   | OS-Pakete, Sprachbibliotheken in Docker-Images  | CVEs (bekannte Schwachstellen)                         |
| Filesystem         | Lokale Dateien und Verzeichnisse                | CVEs in Abhaengigkeiten, Secrets, Lizenzen            |
| Git Repository     | Versionierter Code                               | CVEs, Secrets in der History                           |
| IaC (Infra as Code)| Docker-Compose, Dockerfile, Terraform, K8s      | Fehlkonfigurationen (z.B. Root-Container, kein Healthcheck) |
| Secret Scanning    | Quellcode, Konfigurationsdateien                | API-Keys, Passwoerter, Tokens im Klartext             |

#### Warum Container-Scanning wichtig ist

Jedes Docker-Image basiert auf einem Base-Image (z.B. `alpine:3.20`, `debian:bookworm`) und enthaelt Hunderte von OS-Paketen und Bibliotheken. Jedes einzelne Paket kann bekannte Schwachstellen haben. Ein Image, das heute sicher ist, kann morgen eine kritische CVE haben, weil eine neue Schwachstelle entdeckt wurde.

Beispiel: `postgres:16-alpine` enthaelt Alpine Linux, OpenSSL, zlib, libxml2 und dutzende weitere Pakete. Wenn in OpenSSL eine neue CVE veroeffentlicht wird, ist das PostgreSQL-Image betroffen, obwohl PostgreSQL selbst keine Schwachstelle hat.

#### Trivy Vulnerability Database

Trivy nutzt eine eigene Datenbank, die aus mehreren Quellen gespeist wird:

- **NVD (National Vulnerability Database):** US-Regierungsdatenbank fuer CVEs
- **Alpine SecDB:** Alpine Linux Security-Advisories
- **Debian Security Tracker:** Debian-spezifische Advisories
- **Red Hat CVE Database:** RHEL/CentOS-Advisories
- **GitHub Advisory Database:** Advisories fuer Open-Source-Pakete
- **Go Vulnerability Database, npm Audit, etc.**

Die Datenbank wird bei jedem Scan automatisch aktualisiert (oder aus einem Cache geladen).

---

### 2. Architektur

#### Scanning-Pipeline

```
+------------------+     +------------------+     +------------------+
| Docker Images    |     | Compose-Dateien  |     | Quellcode        |
| (alle laufenden  |     | (stacks/*)       |     | (boilerplates/,  |
|  Container)      |     |                  |     |  Dockerfiles)    |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         | trivy image            | trivy config           | trivy fs --scanners secret
         |                        |                        |
+--------v------------------------v------------------------v---------+
|                                                                     |
|                        Trivy Scanner                                |
|                   toolbox-trivy (Container)                          |
|                                                                     |
|   +-------------------+  +-------------------+  +--------------+    |
|   | Vulnerability DB  |  | Misconfiguration  |  | Secret       |    |
|   | (CVE-Datenbank,   |  | Checks            |  | Patterns     |    |
|   |  auto-updated)    |  | (Best Practices)  |  | (Regex-based)|    |
|   +-------------------+  +-------------------+  +--------------+    |
|                                                                     |
+--------+----------------------------+------------------+------------+
         |                            |                  |
         v                            v                  v
   +-----+------+           +--------+-------+    +-----+------+
   | JSON Report|           | HTML Report    |    | SARIF      |
   | (maschinen-|           | (menschenles-  |    | (GitHub    |
   |  lesbar)   |           |  bar)          |    |  Security) |
   +-----+------+           +--------+-------+    +-----+------+
         |                            |                  |
         v                            v                  v
   +-----+------+           +--------+-------+    +-----+------+
   | n8n Webhook|           | /reports/      |    | GitHub     |
   | (Alert)    |           | (Archiv)       |    | Security   |
   +------------+           +----------------+    | Tab        |
                                                  +------------+
```

#### Integration in die Toolbox

Trivy laeuft als Container im Docker-Netzwerk `toolbox`. Es hat Lesezugriff auf den Docker Socket (`/var/run/docker.sock:ro`) um die Images aller laufenden Container zu scannen. Reports werden in einem Volume gespeichert und koennen ueber n8n-Webhooks als Alerts an Slack geschickt werden.

---

### 3. Installation

#### Option A: Trivy als Docker Container (empfohlen)

Fuer regelmaessiges Scanning wird Trivy als Container im Toolbox-Stack betrieben:

```yaml
# stacks/security/docker-compose.yml
# Trivy Container Security Scanner

services:
  # -----------------------------------------------
  # Trivy - Vulnerability Scanner
  # -----------------------------------------------
  trivy:
    image: aquasec/trivy:latest
    container_name: toolbox-trivy
    restart: "no"
    volumes:
      # Docker Socket fuer Image-Scanning (read-only)
      - /var/run/docker.sock:/var/run/docker.sock:ro
      # Trivy-Cache (Vulnerability-DB, damit nicht bei jedem Scan neu heruntergeladen)
      - trivy_cache:/root/.cache/trivy
      # Scan-Skripte
      - ./scripts:/scripts:ro
      # Reports-Ausgabe
      - ./reports:/reports
      # Zugriff auf Toolbox-Stacks fuer IaC-Scanning
      - ../../stacks:/toolbox-stacks:ro
    networks:
      - toolbox
    entrypoint: ["sleep", "infinity"]
    # Der Container laeuft dauerhaft und wird per `docker exec` angesteuert.
    # Alternativ: entrypoint auf das Scan-Skript setzen und per Cron neustarten.

volumes:
  trivy_cache:
    name: toolbox_trivy_cache

networks:
  toolbox:
    external: true
    name: toolbox
```

#### Option B: Trivy-Binary direkt auf dem Server

```bash
# Installation auf Ubuntu/Debian
sudo apt-get install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor | sudo tee /usr/share/keyrings/trivy.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy

# Verify
trivy --version
```

#### Vulnerability-DB vorab laden

Beim ersten Scan laedt Trivy die Vulnerability-Datenbank herunter (~50 MB). Das kann einige Minuten dauern. Um den ersten Scan zu beschleunigen:

```bash
# Datenbank vorab herunterladen
docker exec toolbox-trivy trivy image --download-db-only

# Pruefe die DB-Version
docker exec toolbox-trivy trivy --version
```

---

### 4. Alle Toolbox-Images scannen

#### Vollstaendige Image-Liste

Die Toolbox besteht aus den folgenden Docker-Images. Jedes muss regelmaessig gescannt werden:

```bash
# === Core Data ===
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL postgres:16-alpine
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL redis:7-alpine
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL minio/minio:latest

# === Observability ===
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL prom/prometheus:v2.53.0
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL grafana/grafana-oss:11.1.0
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL grafana/loki:3.1.0
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL grafana/tempo:2.5.0
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL prom/alertmanager:v0.27.0

# === Analytics ===
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL posthog/posthog:latest
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL clickhouse/clickhouse-server:24.3-alpine
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL bitnami/kafka:3.7

# === Error Tracking ===
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL getsentry/sentry:latest

# === Feature Flags ===
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL unleashorg/unleash-server:latest

# === Monitoring ===
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL louislam/uptime-kuma:1

# === Search & AI ===
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL getmeili/meilisearch:v1.9
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL qdrant/qdrant:v1.10.1

# === Secrets ===
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL infisical/infisical:latest
```

#### Output-Formate

Trivy unterstuetzt verschiedene Ausgabeformate:

```bash
# Tabellenformat (Standard, menschenlesbar)
docker exec toolbox-trivy trivy image postgres:16-alpine

# JSON (maschinenlesbar, fuer Weiterverarbeitung)
docker exec toolbox-trivy trivy image --format json --output /reports/postgres.json postgres:16-alpine

# HTML Report (lesbar im Browser)
docker exec toolbox-trivy trivy image --format template --template "@contrib/html.tpl" --output /reports/postgres.html postgres:16-alpine

# SARIF (fuer GitHub Security Tab)
docker exec toolbox-trivy trivy image --format sarif --output /reports/postgres.sarif postgres:16-alpine

# Nur Zusammenfassung (Anzahl CVEs pro Severity)
docker exec toolbox-trivy trivy image --severity CRITICAL,HIGH,MEDIUM,LOW postgres:16-alpine 2>&1 | tail -5
```

#### Severity-Filter

```bash
# Nur CRITICAL und HIGH (empfohlen fuer Alerts)
docker exec toolbox-trivy trivy image --severity HIGH,CRITICAL postgres:16-alpine

# Alle Schwachstellen (inkl. MEDIUM, LOW, UNKNOWN)
docker exec toolbox-trivy trivy image postgres:16-alpine

# Nur fixbare Schwachstellen (ignoriert CVEs ohne verfuegbaren Patch)
docker exec toolbox-trivy trivy image --ignore-unfixed postgres:16-alpine
```

---

### 5. Scan-Skript (scan-all.sh)

Das folgende Skript scannt alle laufenden Container-Images, generiert Reports und sendet eine Zusammenfassung.

```bash
#!/bin/bash
# stacks/security/scripts/scan-all.sh
# Scannt alle laufenden Docker-Container-Images und generiert Reports.
#
# Verwendung:
#   docker exec toolbox-trivy /scripts/scan-all.sh
#   Oder als Cron-Job: 0 3 * * * docker exec toolbox-trivy /scripts/scan-all.sh

set -euo pipefail

# === Konfiguration ===
REPORT_DIR="/reports/$(date +%Y-%m-%d)"
SUMMARY_FILE="${REPORT_DIR}/summary.txt"
N8N_WEBHOOK_URL="${N8N_WEBHOOK_URL:-https://n8n.example.com/webhook/trivy-scan}"
SEVERITY_FILTER="CRITICAL,HIGH"
EXIT_CODE=0

# === Verzeichnis erstellen ===
mkdir -p "${REPORT_DIR}"

echo "========================================="
echo "Trivy Security Scan - $(date +%Y-%m-%d\ %H:%M:%S)"
echo "========================================="
echo ""

# === Datenbank aktualisieren ===
echo "[*] Aktualisiere Vulnerability-Datenbank..."
trivy image --download-db-only 2>/dev/null
echo "[+] Datenbank aktualisiert."
echo ""

# === Zaehler initialisieren ===
TOTAL_CRITICAL=0
TOTAL_HIGH=0
TOTAL_MEDIUM=0
TOTAL_LOW=0
TOTAL_IMAGES=0
FAILED_IMAGES=""
CRITICAL_IMAGES=""

# === Alle laufenden Container-Images ermitteln ===
# Nutzt den Docker Socket um die Images aller Container mit "toolbox-" Prefix zu finden
IMAGES=$(docker ps --format '{{.Image}}' --filter "name=toolbox-" | sort -u)

echo "[*] Gefundene Images: $(echo "${IMAGES}" | wc -l)"
echo ""

# === Jedes Image scannen ===
for IMAGE in ${IMAGES}; do
    TOTAL_IMAGES=$((TOTAL_IMAGES + 1))
    # Sicherer Dateiname (Slashes und Doppelpunkte ersetzen)
    SAFE_NAME=$(echo "${IMAGE}" | tr '/:' '__')

    echo "--- Scanne: ${IMAGE} ---"

    # JSON-Report erstellen
    if trivy image \
        --format json \
        --output "${REPORT_DIR}/${SAFE_NAME}.json" \
        --severity "${SEVERITY_FILTER}" \
        --ignore-unfixed \
        "${IMAGE}" 2>/dev/null; then

        # HTML-Report erstellen
        trivy image \
            --format template \
            --template "@contrib/html.tpl" \
            --output "${REPORT_DIR}/${SAFE_NAME}.html" \
            --severity "${SEVERITY_FILTER}" \
            --ignore-unfixed \
            "${IMAGE}" 2>/dev/null || true

        # CVE-Zaehler aus JSON extrahieren
        if [ -f "${REPORT_DIR}/${SAFE_NAME}.json" ]; then
            CRITICAL=$(cat "${REPORT_DIR}/${SAFE_NAME}.json" | \
                python3 -c "
import json, sys
data = json.load(sys.stdin)
count = 0
for result in data.get('Results', []):
    for vuln in result.get('Vulnerabilities', []):
        if vuln.get('Severity') == 'CRITICAL':
            count += 1
print(count)
" 2>/dev/null || echo "0")

            HIGH=$(cat "${REPORT_DIR}/${SAFE_NAME}.json" | \
                python3 -c "
import json, sys
data = json.load(sys.stdin)
count = 0
for result in data.get('Results', []):
    for vuln in result.get('Vulnerabilities', []):
        if vuln.get('Severity') == 'HIGH':
            count += 1
print(count)
" 2>/dev/null || echo "0")

            TOTAL_CRITICAL=$((TOTAL_CRITICAL + CRITICAL))
            TOTAL_HIGH=$((TOTAL_HIGH + HIGH))

            if [ "${CRITICAL}" -gt 0 ]; then
                CRITICAL_IMAGES="${CRITICAL_IMAGES}${IMAGE} (${CRITICAL} CRITICAL)\n"
                EXIT_CODE=1
            fi

            echo "    CRITICAL: ${CRITICAL}, HIGH: ${HIGH}"
        fi
    else
        FAILED_IMAGES="${FAILED_IMAGES}${IMAGE}\n"
        echo "    [!] Scan fehlgeschlagen"
    fi

    echo ""
done

# === Zusammenfassung erstellen ===
cat > "${SUMMARY_FILE}" <<EOF
Trivy Security Scan Summary
Date: $(date +%Y-%m-%d\ %H:%M:%S)
Images scanned: ${TOTAL_IMAGES}

CVE Summary (fixable only):
  CRITICAL: ${TOTAL_CRITICAL}
  HIGH:     ${TOTAL_HIGH}

$(if [ -n "${CRITICAL_IMAGES}" ]; then
    echo "Images with CRITICAL vulnerabilities:"
    echo -e "${CRITICAL_IMAGES}"
fi)

$(if [ -n "${FAILED_IMAGES}" ]; then
    echo "Failed scans:"
    echo -e "${FAILED_IMAGES}"
fi)

Reports: ${REPORT_DIR}/
EOF

echo "========================================="
echo "ZUSAMMENFASSUNG"
echo "========================================="
cat "${SUMMARY_FILE}"

# === n8n Webhook benachrichtigen ===
if command -v curl &> /dev/null; then
    STATUS="success"
    if [ ${EXIT_CODE} -ne 0 ]; then
        STATUS="critical_found"
    fi

    curl -s -X POST "${N8N_WEBHOOK_URL}" \
        -H "Content-Type: application/json" \
        -d "{
            \"status\": \"${STATUS}\",
            \"total_images\": ${TOTAL_IMAGES},
            \"total_critical\": ${TOTAL_CRITICAL},
            \"total_high\": ${TOTAL_HIGH},
            \"critical_images\": \"$(echo -e "${CRITICAL_IMAGES}" | tr '\n' '|')\",
            \"report_dir\": \"${REPORT_DIR}\",
            \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
        }" 2>/dev/null || echo "[!] Webhook-Benachrichtigung fehlgeschlagen"
fi

echo ""
echo "Reports gespeichert unter: ${REPORT_DIR}/"
exit ${EXIT_CODE}
```

Skript ausfuehrbar machen:

```bash
chmod +x stacks/security/scripts/scan-all.sh
```

Manuell ausfuehren:

```bash
docker exec toolbox-trivy /scripts/scan-all.sh
```

---

### 6. Schwachstellen verstehen

#### CVE-Severity-Level

Trivy nutzt CVSS (Common Vulnerability Scoring System) Scores um Schwachstellen in Severity-Level einzuteilen:

| Severity  | CVSS Score | Bedeutung                                                   | Handlungsbedarf         |
|-----------|------------|--------------------------------------------------------------|--------------------------|
| CRITICAL  | 9.0 - 10.0 | Angreifer kann das System vollstaendig uebernehmen. Remote exploitbar ohne Authentifizierung. | Sofort updaten. Exploitpfad pruefen. |
| HIGH      | 7.0 - 8.9  | Schwerwiegende Auswirkungen moeglich. Erfordert teilweise Vorbedingungen. | Innerhalb von 1 Woche updaten. |
| MEDIUM    | 4.0 - 6.9  | Eingeschraenkte Auswirkung oder erfordert spezifische Bedingungen. | Im naechsten Maintenance-Fenster updaten. |
| LOW       | 0.1 - 3.9  | Minimale Auswirkung. Schwer auszunutzen.                     | Tracken, bei naechster Gelegenheit updaten. |

#### Fixed vs. Unfixed Vulnerabilities

- **Fixed:** Ein Patch ist im Upstream verfuegbar. Das Image muss auf eine neuere Version aktualisiert werden.
- **Unfixed:** Kein Patch verfuegbar. Die Schwachstelle existiert, kann aber noch nicht behoben werden. In diesem Fall: Risiko bewerten und ggf. Workarounds implementieren.

```bash
# Nur fixbare Schwachstellen anzeigen (empfohlen fuer den Tagesalltag)
docker exec toolbox-trivy trivy image --ignore-unfixed postgres:16-alpine

# Alle Schwachstellen anzeigen (fuer vollstaendiges Audit)
docker exec toolbox-trivy trivy image postgres:16-alpine
```

#### Was tun bei einer CRITICAL CVE?

1. **Pruefen, ob der Exploitpfad relevant ist.** Nicht jede CRITICAL CVE ist in jeder Umgebung ausnutzbar. Eine OpenSSL-Luecke in einem Image, das OpenSSL nicht direkt nutzt, hat ein geringeres Risiko.
2. **Image aktualisieren.** In der `docker-compose.yml` das Image-Tag auf die neueste Version setzen und neu deployen.
3. **Falls kein Fix verfuegbar:** Pruefen, ob ein neueres Base-Image (z.B. von `alpine:3.19` auf `alpine:3.20`) die CVE behebt.
4. **Ggf. in `.trivyignore` aufnehmen** (mit Kommentar und Datum), wenn die CVE akzeptiert wird.

#### Beispiel-Output lesen

```
postgres:16-alpine (alpine 3.20.3)

Total: 3 (HIGH: 2, CRITICAL: 1)

+-------------------+------------------+----------+-------------------+-------------------+
|      LIBRARY      | VULNERABILITY ID | SEVERITY | INSTALLED VERSION |  FIXED VERSION    |
+-------------------+------------------+----------+-------------------+-------------------+
| libssl3           | CVE-2024-XXXXX   | CRITICAL | 3.3.1-r0          | 3.3.1-r1          |
| libcrypto3        | CVE-2024-YYYYY   | HIGH     | 3.3.1-r0          | 3.3.1-r1          |
| busybox           | CVE-2024-ZZZZZ   | HIGH     | 1.36.1-r28        | 1.36.1-r29        |
+-------------------+------------------+----------+-------------------+-------------------+
```

In diesem Beispiel:

- `libssl3` hat eine CRITICAL CVE. Update von `3.3.1-r0` auf `3.3.1-r1` behebt sie.
- Da es ein Alpine-Paket ist, wird ein Update des Base-Images (`postgres:16-alpine` auf die neueste Version pullen) den Fix enthalten.

---

### 7. CI/CD Integration

#### GitHub Actions Workflow

Erstelle eine GitHub Actions Workflow-Datei, die bei jedem Push Docker-Images und Code scannt:

```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    # Woechentlich Montag 6:00 UTC
    - cron: '0 6 * * 1'

permissions:
  security-events: write
  contents: read

jobs:
  trivy-image-scan:
    name: Scan Docker Images
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        image:
          - postgres:16-alpine
          - redis:7-alpine
          - minio/minio:latest
          - grafana/grafana-oss:11.1.0
          - prom/prometheus:v2.53.0
          - grafana/loki:3.1.0
          - grafana/tempo:2.5.0
          - prom/alertmanager:v0.27.0
          - posthog/posthog:latest
          - getsentry/sentry:latest
          - unleashorg/unleash-server:latest
          - louislam/uptime-kuma:1
          - getmeili/meilisearch:v1.9
          - qdrant/qdrant:v1.10.1
          - infisical/infisical:latest
    steps:
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ matrix.image }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          ignore-unfixed: true

      - name: Upload Trivy scan results to GitHub Security tab
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

  trivy-config-scan:
    name: Scan IaC Configuration
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Trivy config scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'config'
          scan-ref: 'stacks/'
          format: 'sarif'
          output: 'trivy-config.sarif'
          severity: 'CRITICAL,HIGH,MEDIUM'

      - name: Upload config scan results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-config.sarif'

  trivy-secret-scan:
    name: Scan for Secrets
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Trivy secret scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          scanners: 'secret'
          format: 'table'
          severity: 'CRITICAL,HIGH,MEDIUM'

  deployment-gate:
    name: Deployment Gate
    runs-on: ubuntu-latest
    needs: [trivy-image-scan, trivy-config-scan, trivy-secret-scan]
    steps:
      - name: Check scan results
        run: |
          echo "All security scans passed. Deployment is allowed."
```

#### Pre-Deployment Check

Bevor ein neues Image ueber Coolify deployed wird, kann es vorab gescannt werden:

```bash
# Image pullen und scannen, bevor es deployed wird
docker pull posthog/posthog:latest
docker exec toolbox-trivy trivy image --severity CRITICAL --exit-code 1 posthog/posthog:latest

# Exit-Code 0 = keine CRITICAL CVEs, Deployment erlaubt
# Exit-Code 1 = CRITICAL CVEs gefunden, Deployment blockieren
```

---

### 8. Zeitgesteuertes Scanning

#### Cron-Jobs einrichten

Erstelle einen Cron-Job auf dem Server fuer regelmaessige Scans:

```bash
# Crontab editieren
crontab -e

# Taeglich um 3:00 Uhr alle Images scannen
0 3 * * * docker exec toolbox-trivy /scripts/scan-all.sh >> /var/log/trivy-scan.log 2>&1

# Woechentlich Sonntag 2:00 Uhr: Vollstaendiger Scan (alle Severities, inkl. unfixed)
0 2 * * 0 docker exec toolbox-trivy /scripts/scan-full.sh >> /var/log/trivy-full-scan.log 2>&1

# Monatlich am 1. um 4:00 Uhr: IaC-Scan der Docker-Compose-Dateien
0 4 1 * * docker exec toolbox-trivy trivy config /toolbox-stacks/ --format json --output /reports/iac-$(date +\%Y-\%m).json >> /var/log/trivy-iac-scan.log 2>&1
```

#### Woechentliches Full-Scan-Skript

```bash
#!/bin/bash
# stacks/security/scripts/scan-full.sh
# Vollstaendiger Scan aller Images inklusive aller Severity-Level und unfixed CVEs.

set -euo pipefail

REPORT_DIR="/reports/full-$(date +%Y-%m-%d)"
mkdir -p "${REPORT_DIR}"

echo "Vollstaendiger Security Scan - $(date)"

IMAGES=$(docker ps --format '{{.Image}}' --filter "name=toolbox-" | sort -u)

for IMAGE in ${IMAGES}; do
    SAFE_NAME=$(echo "${IMAGE}" | tr '/:' '__')
    echo "Scanne: ${IMAGE} (alle Severities, inkl. unfixed)..."

    trivy image \
        --format json \
        --output "${REPORT_DIR}/${SAFE_NAME}.json" \
        "${IMAGE}" 2>/dev/null || echo "Scan fehlgeschlagen: ${IMAGE}"
done

echo "Reports: ${REPORT_DIR}/"
echo "Fertig: $(date)"
```

#### Alertmanager-Integration bei Scan-Fehlern

Falls der Cron-Job fehlschlaegt, kann Alertmanager benachrichtigt werden. Fuege eine Prometheus Alert Rule hinzu:

```yaml
# In stacks/observability/configs/prometheus/alerts.yml
groups:
  - name: security
    rules:
      - alert: TrivyScanFailed
        expr: time() - node_textfile_mtime_seconds{file="trivy_last_scan.prom"} > 90000
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Trivy Security Scan nicht ausgefuehrt"
          description: "Der letzte Trivy-Scan ist aelter als 25 Stunden. Pruefen, ob der Cron-Job laeuft."
```

Dafuer muss das Scan-Skript eine Textfile-Metrik schreiben:

```bash
# Am Ende von scan-all.sh hinzufuegen:
echo "trivy_last_scan_timestamp $(date +%s)" > /var/lib/node_exporter/trivy_last_scan.prom
echo "trivy_critical_count ${TOTAL_CRITICAL}" >> /var/lib/node_exporter/trivy_last_scan.prom
echo "trivy_high_count ${TOTAL_HIGH}" >> /var/lib/node_exporter/trivy_last_scan.prom
```

---

### 9. IaC Scanning (Infrastructure as Code)

#### Docker-Compose-Dateien scannen

Trivy prueft Docker-Compose-Dateien auf Security Best Practices:

```bash
# Alle Stacks scannen
docker exec toolbox-trivy trivy config /toolbox-stacks/

# Einzelnen Stack scannen
docker exec toolbox-trivy trivy config /toolbox-stacks/core-data/

# Mit spezifischem Severity-Filter
docker exec toolbox-trivy trivy config --severity HIGH,CRITICAL /toolbox-stacks/
```

#### Typische Findings

| Finding                              | Severity | Bedeutung                                                | Empfehlung                       |
|--------------------------------------|----------|----------------------------------------------------------|----------------------------------|
| Container running as root            | HIGH     | Container laeuft als Root-User, erhoehtes Risiko bei Container-Breakout | `user: "1000:1000"` setzen       |
| No healthcheck defined               | MEDIUM   | Keine automatische Fehlererkennung                       | `healthcheck` hinzufuegen        |
| No resource limits set               | MEDIUM   | Container kann unbegrenzt RAM/CPU verbrauchen            | `deploy.resources.limits` setzen |
| Privileged container                 | CRITICAL | Container hat vollen Host-Zugriff                        | `privileged: false` oder entfernen |
| Docker socket mounted writable       | HIGH     | Container kann Docker-API manipulieren                   | `:ro` (read-only) verwenden      |
| No network policy                    | LOW      | Kein Netzwerk-Isolation zwischen Containern              | In Single-Server-Setup akzeptabel|
| Sensitive environment variable       | MEDIUM   | Passwoerter direkt in Compose-Datei statt als Secret    | `${VAR}` mit .env verwenden      |

#### Dockerfiles scannen

Falls eigene Dockerfiles vorhanden sind (z.B. in `boilerplates/`):

```bash
# Einzelnes Dockerfile scannen
docker exec toolbox-trivy trivy config /toolbox-stacks/../boilerplates/nextjs/Dockerfile

# Alle Dockerfiles im Repository scannen
docker exec toolbox-trivy trivy config --file-patterns "dockerfile:Dockerfile*" /toolbox-stacks/../
```

Typische Dockerfile-Findings:

| Finding                            | Severity | Empfehlung                                        |
|------------------------------------|----------|---------------------------------------------------|
| Running as root (no USER)          | HIGH     | `USER node` oder `USER appuser` hinzufuegen       |
| Using `latest` tag                 | MEDIUM   | Spezifisches Tag verwenden (z.B. `node:20-alpine`)|
| ADD instead of COPY                | LOW      | `COPY` bevorzugen (kein Auto-Entpacken, klarer)   |
| No HEALTHCHECK instruction         | MEDIUM   | `HEALTHCHECK CMD ...` hinzufuegen                 |

---

### 10. Secret Scanning

#### Quellcode scannen

Trivy findet versehentlich committete Secrets wie API-Keys, Passwoerter und Tokens:

```bash
# Aktuelles Verzeichnis scannen
docker exec toolbox-trivy trivy fs --scanners secret /toolbox-stacks/

# Gesamtes Repository scannen (falls eingebunden)
docker exec toolbox-trivy trivy fs --scanners secret /path/to/repo/

# Bestimmte Dateitypen ausschliessen
docker exec toolbox-trivy trivy fs --scanners secret --skip-files "*.md,*.txt" /toolbox-stacks/
```

#### Was Trivy als Secret erkennt

| Secret-Typ                  | Beispiel-Pattern                      |
|-----------------------------|---------------------------------------|
| AWS Access Key              | `AKIA[0-9A-Z]{16}`                   |
| GitHub Token                | `ghp_[a-zA-Z0-9]{36}`               |
| Slack Webhook URL           | `https://hooks.slack.com/services/...`|
| Generic API Key             | `api[_-]?key[=:]\s*["']?[a-zA-Z0-9]` |
| Private Key                 | `-----BEGIN RSA PRIVATE KEY-----`    |
| PostgreSQL Connection String| `postgres://user:pass@host/db`       |
| JWT Token                   | `eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*` |

#### Pre-Commit Hook

Verhindere, dass Secrets ueberhaupt ins Repository gelangen:

```bash
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/aquasecurity/trivy
    rev: v0.55.0
    hooks:
      - id: trivy-secret
        name: Trivy Secret Scanner
        entry: trivy fs --scanners secret --exit-code 1
        language: system
        pass_filenames: false
```

Alternativ als einfacher Git-Hook:

```bash
#!/bin/bash
# .git/hooks/pre-commit
# Scannt staged Files auf Secrets

echo "Running Trivy Secret Scan..."
trivy fs --scanners secret --exit-code 1 --severity HIGH,CRITICAL .
if [ $? -ne 0 ]; then
    echo ""
    echo "COMMIT BLOCKED: Secrets gefunden!"
    echo "Entferne die Secrets und versuche es erneut."
    exit 1
fi
```

---

### 11. Reports und Dashboards

#### 11.1 HTML Report generieren

```bash
# Einzelnes Image
docker exec toolbox-trivy trivy image \
    --format template \
    --template "@contrib/html.tpl" \
    --output /reports/grafana-$(date +%Y%m%d).html \
    grafana/grafana-oss:11.1.0

# Alle Images (im scan-all.sh Skript enthalten)
```

Die HTML-Reports koennen ueber einen einfachen HTTP-Server zugaenglich gemacht werden oder als Attachment per E-Mail versendet werden.

#### 11.2 JSON-Daten in Grafana visualisieren

Wenn das Scan-Skript Prometheus-Metriken schreibt (siehe Abschnitt 8), koennen diese in Grafana als Dashboard dargestellt werden:

**Empfohlene Dashboard-Panels:**

| Panel                         | Typ         | Metrik / Query                            |
|-------------------------------|-------------|-------------------------------------------|
| CRITICAL CVEs Total           | Stat        | `trivy_critical_count`                    |
| HIGH CVEs Total               | Stat        | `trivy_high_count`                        |
| Letzter Scan-Zeitpunkt        | Stat        | `trivy_last_scan_timestamp`               |
| CVE-Trend ueber Zeit          | Time Series | `trivy_critical_count` ueber 30 Tage     |
| Images mit CRITICAL           | Table       | Aus JSON-Reports parsen                   |

#### 11.3 SARIF fuer GitHub Security Tab

SARIF (Static Analysis Results Interchange Format) ist der Standard fuer Security-Findings in GitHub:

```bash
# SARIF-Report generieren
docker exec toolbox-trivy trivy image \
    --format sarif \
    --output /reports/postgres.sarif \
    postgres:16-alpine
```

In der GitHub Actions Pipeline (siehe Abschnitt 7) werden SARIF-Reports automatisch hochgeladen und erscheinen unter **Security** > **Code scanning alerts** im GitHub-Repository.

#### 11.4 Report-Retention

Reports sammeln sich ueber die Zeit an. Erstelle ein Cleanup-Skript:

```bash
#!/bin/bash
# stacks/security/scripts/cleanup-reports.sh
# Loescht Reports aelter als 90 Tage

REPORT_BASE="/reports"
RETENTION_DAYS=90

echo "Loesche Reports aelter als ${RETENTION_DAYS} Tage..."
find "${REPORT_BASE}" -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} + 2>/dev/null || true
echo "Cleanup abgeschlossen."
```

Cron-Job:

```bash
# Monatlich am 15. um 5:00 Uhr alte Reports loeschen
0 5 15 * * docker exec toolbox-trivy /scripts/cleanup-reports.sh
```

---

### 12. .trivyignore: False Positives behandeln

#### Datei erstellen

Wenn Trivy Schwachstellen meldet, die akzeptiert werden (z.B. weil der Exploitpfad nicht relevant ist), koennen sie in einer `.trivyignore`-Datei ausgenommen werden:

```bash
# stacks/security/.trivyignore
# Format: CVE-ID  # Begruendung (Wer, Wann, Warum)

# OpenSSL: Nur relevant fuer DTLS, wird in der Toolbox nicht verwendet
# Akzeptiert von: nikla, 2025-01-15
CVE-2024-12345

# busybox: Nur relevant bei direktem Shell-Zugriff, Container sind nicht oeffentlich erreichbar
# Akzeptiert von: nikla, 2025-01-15
CVE-2024-67890
```

#### .trivyignore verwenden

```bash
# Scan mit .trivyignore
docker exec toolbox-trivy trivy image \
    --ignorefile /scripts/.trivyignore \
    postgres:16-alpine
```

#### Best Practices fuer .trivyignore

- **Immer eine Begruendung hinzufuegen** (wer hat es akzeptiert, wann, warum).
- **Regelmaessig reviewen** (mindestens monatlich), ob die Begruendung noch gilt.
- **Versionieren:** Die `.trivyignore`-Datei gehoert ins Git-Repository.
- **Minimieren:** Nur CVEs aufnehmen, bei denen der Exploitpfad nachweislich nicht relevant ist.

---

### 13. Troubleshooting

#### Langsame Scans

**Ursache:** Trivy laedt bei jedem Scan die Vulnerability-DB herunter.

**Loesung:** Cache-Volume verwenden (bereits in der Compose-Datei konfiguriert):

```bash
# Cache pruefen
docker exec toolbox-trivy ls -la /root/.cache/trivy/

# Cache-Groesse
docker exec toolbox-trivy du -sh /root/.cache/trivy/
# Typisch: 200-500 MB

# Manuell aktualisieren (ohne Scan)
docker exec toolbox-trivy trivy image --download-db-only
```

Falls der Cache-Download fehlschlaegt:

```bash
# Cache loeschen und neu herunterladen
docker exec toolbox-trivy rm -rf /root/.cache/trivy/db
docker exec toolbox-trivy trivy image --download-db-only
```

#### DB-Download schlaegt fehl (Netzwerk)

**Symptom:** `FATAL failed to download vulnerability DB`

**Ursachen:**

1. **Kein Internetzugang:** Der Trivy-Container muss das Internet erreichen koennen.
2. **DNS-Problem:** Docker-DNS kann Domains nicht aufloesen.
3. **Rate Limiting:** GitHub (ghcr.io) hat Rate Limits fuer anonyme Downloads.

**Loesungen:**

```bash
# DNS pruefen
docker exec toolbox-trivy nslookup ghcr.io

# Manueller Download mit Proxy
docker exec toolbox-trivy trivy image --download-db-only --db-repository ghcr.io/aquasecurity/trivy-db

# Offline-Modus: DB manuell herunterladen und einbinden
# (auf einem System mit Internetzugang)
trivy image --download-db-only --cache-dir ./trivy-cache
# Dann den Cache als Volume einbinden
```

#### False Positives

**Symptom:** Trivy meldet eine CVE, die nachweislich nicht relevant ist.

**Loesung:**

1. Pruefe den CVE-Eintrag auf https://nvd.nist.gov/ und verstehe den Exploitpfad.
2. Falls nicht relevant: In `.trivyignore` aufnehmen (mit Begruendung).
3. Falls unklar: Als akzeptiertes Risiko dokumentieren und beim naechsten Review pruefen.

```bash
# Details zu einer spezifischen CVE anzeigen
docker exec toolbox-trivy trivy image --vuln-type os postgres:16-alpine 2>&1 | grep -A 5 "CVE-2024-XXXXX"
```

#### Image nicht scanbar

**Symptom:** `unable to initialize a scanner: unable to detect OS`

**Ursache:** Das Image nutzt ein nicht unterstuetztes OS oder ist ein Scratch-Image.

**Loesung:**

```bash
# Image-OS pruefen
docker exec toolbox-trivy trivy image --list-all-pkgs postgres:16-alpine 2>&1 | head -5

# Fuer Scratch/Distroless-Images: Nur Sprachbibliotheken scannen
docker exec toolbox-trivy trivy image --vuln-type library your-scratch-image:latest
```

#### Scanner und Docker Socket

**Symptom:** `Cannot connect to the Docker daemon`

**Loesung:** Pruefe, ob der Docker Socket korrekt eingebunden ist:

```bash
# Socket-Zugriff pruefen
docker exec toolbox-trivy ls -la /var/run/docker.sock
# Erwartet: srw-rw---- 1 root docker ...

# Docker API erreichbar?
docker exec toolbox-trivy curl -s --unix-socket /var/run/docker.sock http://localhost/version | head -1
```

---

### Checkliste: Trivy vollstaendig eingerichtet

- [ ] `stacks/security/docker-compose.yml` erstellt
- [ ] Trivy-Container laeuft (`docker ps | grep toolbox-trivy`)
- [ ] Vulnerability-DB erfolgreich heruntergeladen
- [ ] `scripts/scan-all.sh` erstellt und ausfuehrbar
- [ ] Manueller Test-Scan eines Images erfolgreich
- [ ] Alle Toolbox-Images einmal gescannt (Baseline)
- [ ] CRITICAL-CVEs dokumentiert und behoben oder in `.trivyignore` aufgenommen
- [ ] Cron-Job fuer taeglichen Scan eingerichtet
- [ ] Cron-Job fuer woechentlichen Full-Scan eingerichtet
- [ ] n8n-Workflow fuer Scan-Benachrichtigungen erstellt (siehe [18-n8n-automation.md](18-n8n-automation.md))
- [ ] `.trivyignore` mit Begruendungen erstellt
- [ ] GitHub Actions Workflow fuer CI/CD-Integration eingerichtet
- [ ] IaC-Scan der Docker-Compose-Dateien durchgefuehrt
- [ ] Secret-Scan des Repositories durchgefuehrt
- [ ] Report-Verzeichnis und Cleanup-Cron eingerichtet

---

## 6. OpenTelemetry — Vendor-neutrale Telemetrie


Dieses Dokument beschreibt die Einrichtung des OpenTelemetry Collectors als zentrale Telemetrie-Pipeline fuer die Toolbox. Der Collector empfaengt Traces, Metriken und Logs von allen Anwendungen ueber das standardisierte OTLP-Protokoll und leitet sie an die bestehenden Backends (Tempo, Prometheus, Loki) weiter. Zusaetzlich wird die Instrumentierung aller Boilerplates (Next.js, FastAPI, Astro, Flutter, Swift) vollstaendig beschrieben.

> **Voraussetzung:** Der Observability-Stack (Prometheus, Loki, Tempo, Grafana) muss bereits laufen. Siehe [04-deploy-stack.md](04-deploy-stack.md). Grundlagen zu Grafana Alloy finden sich in [16-grafana-alloy.md](16-grafana-alloy.md).

---

### 1. Was ist OpenTelemetry?

OpenTelemetry (OTel) ist ein CNCF-Projekt (Cloud Native Computing Foundation) und der vendor-neutrale Standard fuer Telemetriedaten: **Traces**, **Metriken** und **Logs**. Es definiert APIs, SDKs und ein Datenformat (OTLP -- OpenTelemetry Protocol), das von allen grossen Observability-Plattformen unterstuetzt wird.

#### Das Problem ohne OpenTelemetry

Ohne OTel ist jede Anwendung direkt an die Backends gekoppelt:

```
Anwendung A  ---> Sentry SDK          ---> Sentry
Anwendung A  ---> prometheus_client    ---> Prometheus
Anwendung A  ---> custom logger        ---> Loki (via Alloy)
Anwendung B  ---> Sentry SDK          ---> Sentry
Anwendung B  ---> prometheus_client    ---> Prometheus
```

Probleme:
- **Vendor Lock-in:** Wenn du von Sentry zu Tempo wechselst, musst du alle Anwendungen aendern.
- **Mehrere SDKs:** Jede Anwendung braucht separate SDKs fuer Traces, Metriken, Logs.
- **Keine zentrale Kontrolle:** Sampling, Filtering und Enrichment muessen in jeder Anwendung einzeln konfiguriert werden.
- **Keine Korrelation:** Traces, Metriken und Logs haben keine gemeinsame Identitaet.

#### Die Loesung mit OpenTelemetry

```
Anwendung A  ---> OTel SDK  ---> OTLP ---> OTel Collector ---> Tempo (Traces)
                                                           ---> Prometheus (Metriken)
                                                           ---> Loki (Logs)
                                                           ---> Sentry (Errors)

Anwendung B  ---> OTel SDK  ---> OTLP ---> OTel Collector ---> (gleiche Backends)
```

Vorteile:
- **Ein SDK** pro Sprache fuer Traces, Metriken und Logs.
- **Vendor-neutral:** Backends koennen ohne Code-Aenderung in den Anwendungen gewechselt werden.
- **Zentrale Pipeline:** Sampling, Filtering, Enrichment und Routing im Collector.
- **Automatische Korrelation:** Trace-IDs werden automatisch in Logs und Metriken injiziert.

#### OTLP-Protokoll

OTLP (OpenTelemetry Protocol) ist das Transportprotokoll:

| Variante    | Port  | Verwendung                             |
|-------------|-------|----------------------------------------|
| OTLP/gRPC   | 4317  | Hoch-performant, fuer Backends         |
| OTLP/HTTP   | 4318  | Einfacher zu debuggen, fuer Browser    |

Der bestehende Tempo-Service akzeptiert bereits OTLP auf beiden Ports. Der OTel Collector wird als zusaetzliche Schicht davor geschaltet, um Routing, Sampling und Enrichment zu uebernehmen.

---

### 2. Architektur

#### Datenfluss mit OTel Collector

```
+------------------+   +------------------+   +------------------+   +-----------------+
|  Next.js App     |   |  FastAPI App     |   |  Astro (Browser) |   | Flutter / Swift |
|  OTel SDK (Node) |   |  OTel SDK (Py)   |   |  OTel SDK (Web)  |   | OTel SDK (Dart/ |
|                  |   |                  |   |                  |   |  Swift)         |
+--------+---------+   +--------+---------+   +--------+---------+   +--------+--------+
         |                      |                      |                      |
         | OTLP/gRPC            | OTLP/gRPC            | OTLP/HTTP            | OTLP/HTTP
         | :4317                | :4317                | :4318                | :4318
         |                      |                      |                      |
+--------v----------------------v----------------------v----------------------v--------+
|                                                                                       |
|                          OpenTelemetry Collector                                      |
|                       toolbox-otel-collector:4317/4318                                |
|                                                                                       |
|  +----------------+   +-------------------+   +------------------+   +--------------+ |
|  | Receivers      |   | Processors        |   | Exporters        |   | Extensions   | |
|  |                |   |                   |   |                  |   |              | |
|  | - otlp (gRPC)  |   | - memory_limiter  |   | - otlp/tempo     |   | - health     | |
|  | - otlp (HTTP)  |   | - batch           |   | - prometheusrw   |   | - zpages     | |
|  | - prometheus   |   | - attributes      |   | - loki           |   |              | |
|  |   (scraper)    |   | - resource        |   | - otlp/sentry    |   |              | |
|  |                |   | - filter          |   | - debug          |   |              | |
|  |                |   | - tail_sampling   |   |                  |   |              | |
|  +----------------+   +-------------------+   +------------------+   +--------------+ |
|                                                                                       |
+-----------+------------------------+------------------------+------------------------+
            |                        |                        |
            | OTLP/gRPC             | Remote Write            | Loki Push API
            | :4317                 | :9090                   | :3100
            |                        |                        |
   +--------v--------+     +--------v--------+     +--------v--------+
   |     Tempo       |     |   Prometheus    |     |      Loki       |
   | toolbox-tempo   |     | toolbox-prom    |     |  toolbox-loki   |
   | (Traces)        |     | (Metriken)      |     |  (Logs)         |
   +-----------------+     +-----------------+     +-----------------+
            |                        |                        |
            +------------------------+------------------------+
                                     |
                              +------v------+
                              |   Grafana   |
                              | Dashboards, |
                              | Explore,    |
                              | Alerting    |
                              +-------------+
```

#### Collector-Komponenten

| Komponente  | Aufgabe                                                              |
|-------------|----------------------------------------------------------------------|
| Receivers   | Empfangen Telemetriedaten (OTLP, Prometheus Scraping)                |
| Processors  | Verarbeiten, filtern, anreichern, samplen                            |
| Exporters   | Senden Daten an Backends (Tempo, Prometheus, Loki, Sentry)           |
| Extensions  | Health Checks, Debug-Seiten, Authentifizierung                       |
| Pipelines   | Verknuepfen Receivers -> Processors -> Exporters fuer jeden Typ      |

#### OTel Collector vs. Grafana Alloy

Beide koennen als Telemetrie-Pipeline dienen. In der Toolbox ergaenzen sie sich:

| Aspekt                      | OTel Collector                     | Grafana Alloy                    |
|-----------------------------|------------------------------------|----------------------------------|
| Primaerer Zweck             | App-Telemetrie empfangen und routen | Docker-Logs sammeln              |
| Datenquellen                | OTLP von Anwendungen               | Docker Socket, Dateisystem       |
| Traces                      | Ja (Kernfunktion)                  | Ja (Weiterleitung)               |
| Metriken                    | Ja (OTLP + Scraping)              | Ja (Scraping + Remote Write)     |
| Logs von Anwendungen        | Ja (ueber OTLP)                   | Nein (nur Docker stdout/stderr)  |
| Docker-Container-Discovery  | Nein                               | Ja (Kernfunktion)                |
| Tail Sampling               | Ja (fortgeschritten)              | Nein                             |

**Empfehlung:** Alloy fuer Docker-Logs (laeuft bereits). OTel Collector fuer App-Telemetrie (Traces, Metriken, strukturierte Logs aus den SDKs). Beide laufen parallel im `toolbox`-Netzwerk.

---

### 3. Stack Setup

#### Docker Compose

```yaml
# stacks/telemetry/docker-compose.yml
# OpenTelemetry Collector - Zentrale Telemetrie-Pipeline

services:
  # -----------------------------------------------
  # OpenTelemetry Collector (Contrib-Distribution)
  # -----------------------------------------------
  # Die "contrib"-Distribution enthaelt alle Community-Exporters,
  # z.B. Loki-Exporter, Sentry-Exporter, Tail Sampling Processor.
  # Die Standard-Distribution ("otel/opentelemetry-collector") hat
  # nur die Kern-Komponenten.
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.114.0
    container_name: toolbox-otel-collector
    restart: unless-stopped
    command: ["--config=/etc/otel/config.yaml"]
    volumes:
      - ./configs/otel-config.yaml:/etc/otel/config.yaml:ro
    networks:
      - toolbox
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:13133/"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
    # Ports nur im Docker-Netzwerk erreichbar (kein "ports:" nach aussen).
    # Anwendungen im toolbox-Netzwerk erreichen den Collector ueber:
    #   - toolbox-otel-collector:4317 (OTLP gRPC)
    #   - toolbox-otel-collector:4318 (OTLP HTTP)
    #   - toolbox-otel-collector:8889 (Prometheus Metriken des Collectors selbst)
    deploy:
      resources:
        limits:
          memory: 1024M
        reservations:
          memory: 256M

networks:
  toolbox:
    external: true
    name: toolbox
```

#### Umgebungsvariablen (.env.example)

```bash
# stacks/telemetry/.env.example
# Der OTel Collector benoetigt keine Umgebungsvariablen.
# Die gesamte Konfiguration liegt in configs/otel-config.yaml.
#
# Falls du spaeter Authentifizierung oder Sentry-Export hinzufuegst:
# SENTRY_DSN=https://examplePublicKey@sentry.example.com/1
```

#### Verzeichnisstruktur

```
stacks/telemetry/
  docker-compose.yml
  .env.example
  configs/
    otel-config.yaml
```

---

### 4. Collector-Konfiguration (otel-config.yaml)

Diese Konfiguration ist das Herztueck des Collectors. Sie definiert, was empfangen, wie verarbeitet und wohin exportiert wird.

```yaml
# stacks/telemetry/configs/otel-config.yaml
# ===========================================================================
# OpenTelemetry Collector Konfiguration fuer die Toolbox
# ===========================================================================
#
# Datenfluss:
#   Apps -> [Receivers] -> [Processors] -> [Exporters] -> Backends
#
# Backends:
#   - Traces  -> Tempo    (toolbox-tempo:4317)
#   - Metrics -> Prometheus (toolbox-prometheus:9090)
#   - Logs    -> Loki     (toolbox-loki:3100)
# ===========================================================================

# ---------------------------------------------------------------------------
# RECEIVERS
# ---------------------------------------------------------------------------
# Empfangen Telemetriedaten von Anwendungen.
receivers:
  # OTLP-Empfaenger: Das Hauptprotokoll fuer alle Telemetriedaten.
  # Anwendungen senden ueber gRPC (Port 4317) oder HTTP (Port 4318).
  otlp:
    protocols:
      grpc:
        endpoint: "0.0.0.0:4317"
        # Max. Nachrichtengroesse: 16 MB (Standard: 4 MB).
        # Groessere Batches erhoehen den Durchsatz.
        max_recv_msg_size_mib: 16
      http:
        endpoint: "0.0.0.0:4318"
        # CORS fuer Browser-SDKs (Astro, Next.js Client-Side).
        # Erlaube Anfragen von allen Toolbox-Domains.
        cors:
          allowed_origins:
            - "https://*.example.com"
            - "http://localhost:*"
          allowed_headers:
            - "Content-Type"
            - "X-Requested-With"
          max_age: 7200

  # Prometheus-Scraping: Der Collector kann selbst Metriken scrapen.
  # Optional -- kann den standalone Prometheus-Scraper ergaenzen oder ersetzen.
  prometheus:
    config:
      scrape_configs:
        # Collector-eigene Metriken
        - job_name: "otel-collector"
          scrape_interval: 30s
          static_configs:
            - targets: ["localhost:8888"]

# ---------------------------------------------------------------------------
# PROCESSORS
# ---------------------------------------------------------------------------
# Verarbeiten Daten zwischen Empfang und Export.
processors:
  # --- Memory Limiter ---
  # Schuetzt den Collector vor Out-of-Memory. MUSS der erste Processor
  # in jeder Pipeline sein.
  #
  # Funktionsweise:
  #   - Prueft alle check_interval ob das Limit erreicht ist.
  #   - Bei limit_mib: Lehnt neue Daten ab (Backpressure).
  #   - Bei spike_limit_mib: Zusaetzlicher Puffer fuer Spitzen.
  memory_limiter:
    check_interval: 1s
    limit_mib: 512
    spike_limit_mib: 128

  # --- Batch Processor ---
  # Sammelt Daten und sendet sie in Batches an die Exporters.
  # Reduziert die Anzahl der HTTP-Requests an die Backends massiv.
  #
  # - timeout: Max. Wartezeit bevor ein Batch gesendet wird.
  # - send_batch_size: Max. Anzahl Spans/Datenpunkte pro Batch.
  # - send_batch_max_size: Absolutes Maximum (verhindert zu grosse Requests).
  batch:
    timeout: 5s
    send_batch_size: 1024
    send_batch_max_size: 2048

  # --- Attributes Processor ---
  # Fuegt allen Telemetriedaten zusaetzliche Attribute hinzu.
  # Nuetzlich fuer Environment-Kennzeichnung und Namespace.
  attributes:
    actions:
      # Umgebung kennzeichnen (production, staging, development)
      - key: deployment.environment
        value: production
        action: upsert
      # Toolbox als Namespace
      - key: service.namespace
        value: toolbox
        action: upsert

  # --- Resource Processor ---
  # Setzt Resource-Attribute (beschreiben die Quelle, nicht den einzelnen Span).
  # Resource-Attribute gelten fuer die gesamte Telemetrie eines Service.
  resource:
    attributes:
      - key: host.name
        value: "toolbox-server"
        action: upsert
      - key: deployment.environment
        value: production
        action: upsert

  # --- Resource Detection Processor ---
  # Erkennt automatisch Informationen ueber die Host-Umgebung.
  resourcedetection:
    detectors: [env, system, docker]
    system:
      hostname_sources: ["os"]
    timeout: 5s

  # --- Filter Processor ---
  # Filtert unerwuenschte Telemetriedaten heraus.
  # Health-Check-Spans erzeugen enormes Rauschen und haben keinen
  # diagnostischen Wert.
  filter/traces:
    error_mode: ignore
    traces:
      span:
        # Health-Check-Endpunkte herausfiltern
        - 'attributes["http.target"] == "/health"'
        - 'attributes["http.target"] == "/healthz"'
        - 'attributes["http.target"] == "/ready"'
        - 'attributes["http.target"] == "/readyz"'
        - 'attributes["http.target"] == "/-/healthy"'
        - 'attributes["http.target"] == "/-/ready"'
        - 'attributes["http.route"] == "/health"'
        - 'attributes["url.path"] == "/health"'
        - 'attributes["url.path"] == "/healthz"'
        # Kubernetes Probes
        - 'attributes["http.user_agent"] == "kube-probe/1.28"'

  filter/metrics:
    error_mode: ignore
    metrics:
      metric:
        # Interne Go-Runtime-Metriken herausfiltern (zu detailliert)
        - 'name == "runtime.uptime"'

  # --- Tail Sampling Processor ---
  # Entscheidet NACH Empfang aller Spans einer Trace, ob die Trace
  # behalten oder verworfen wird. Im Gegensatz zu Head Sampling
  # (Entscheidung am Anfang) kann Tail Sampling Fehler und langsame
  # Requests immer behalten.
  #
  # WICHTIG: Tail Sampling funktioniert nur, wenn alle Spans einer
  # Trace zum selben Collector kommen. Bei mehreren Collector-Instanzen
  # muss ein Load Balancer mit trace-id-basiertem Routing verwendet werden.
  tail_sampling:
    # Wartezeit fuer verspaetete Spans (Cross-Service-Traces brauchen
    # Zeit bis alle Spans eingetroffen sind).
    decision_wait: 10s
    # Maximale Anzahl gleichzeitig gehaltener Traces.
    num_traces: 50000
    # Erwartete Anzahl neuer Traces pro Sekunde (fuer Speicher-Reservierung).
    expected_new_traces_per_sec: 100
    policies:
      # Policy 1: Alle Fehler behalten (100%)
      - name: errors-policy
        type: status_code
        status_code:
          status_codes: [ERROR]
      # Policy 2: Alle langsamen Requests behalten (>1 Sekunde)
      - name: latency-policy
        type: latency
        latency:
          threshold_ms: 1000
      # Policy 3: Normale Requests nur zu 10% behalten
      - name: probabilistic-policy
        type: probabilistic
        probabilistic:
          sampling_percentage: 10

# ---------------------------------------------------------------------------
# EXPORTERS
# ---------------------------------------------------------------------------
# Senden verarbeitete Daten an die Backends.
exporters:
  # --- Tempo (Traces) ---
  # Sendet Traces ueber OTLP/gRPC an Tempo.
  # Tempo laeuft bereits im toolbox-Netzwerk und akzeptiert OTLP auf :4317.
  otlp/tempo:
    endpoint: "tempo:4317"
    tls:
      insecure: true
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s
    sending_queue:
      enabled: true
      num_consumers: 4
      queue_size: 1000

  # --- Prometheus (Metriken) ---
  # Sendet Metriken ueber Remote Write an Prometheus.
  # Prometheus muss Remote Write aktiviert haben (--web.enable-remote-write-receiver).
  prometheusremotewrite:
    endpoint: "http://prometheus:9090/api/v1/write"
    tls:
      insecure: true
    resource_to_telemetry_conversion:
      enabled: true
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s

  # --- Loki (Logs) ---
  # Sendet strukturierte Logs an Loki.
  # Verwendet den Loki-Exporter aus der Contrib-Distribution.
  loki:
    endpoint: "http://loki:3100/loki/api/v1/push"
    default_labels_enabled:
      exporter: true
      job: true
      instance: true
      level: true

  # --- Debug Exporter ---
  # Gibt Telemetriedaten in die Collector-Logs aus.
  # NUR fuer Debugging verwenden, niemals in Produktion aktiviert lassen!
  # Aktiviere ihn temporaer, indem du ihn zu einer Pipeline hinzufuegst.
  debug:
    verbosity: detailed
    sampling_initial: 5
    sampling_thereafter: 200

# ---------------------------------------------------------------------------
# EXTENSIONS
# ---------------------------------------------------------------------------
# Zusaetzliche Funktionen des Collectors.
extensions:
  # Health Check Endpoint: GET http://localhost:13133/
  # Wird vom Docker Healthcheck verwendet.
  health_check:
    endpoint: "0.0.0.0:13133"

  # zPages: Debug-UI unter http://localhost:55679/debug/tracez
  # Zeigt aktive Traces, Sampling-Entscheidungen und Pipeline-Status.
  zpages:
    endpoint: "0.0.0.0:55679"

# ---------------------------------------------------------------------------
# SERVICE
# ---------------------------------------------------------------------------
# Verknuepft alle Komponenten zu Pipelines.
service:
  extensions: [health_check, zpages]

  # Eigene Telemetrie des Collectors (fuer Monitoring des Collectors selbst)
  telemetry:
    logs:
      level: info
    metrics:
      address: "0.0.0.0:8888"

  pipelines:
    # --- Traces Pipeline ---
    traces:
      receivers: [otlp]
      processors:
        - memory_limiter       # Immer zuerst: OOM-Schutz
        - filter/traces        # Health-Checks rausfiltern
        - resource             # Resource-Attribute setzen
        - resourcedetection    # Host-Info erkennen
        - attributes           # Umgebung und Namespace setzen
        - tail_sampling        # Sampling (Fehler behalten, Rest 10%)
        - batch                # Batching (immer zuletzt vor Export)
      exporters: [otlp/tempo]

    # --- Metriken Pipeline ---
    metrics:
      receivers: [otlp, prometheus]
      processors:
        - memory_limiter
        - filter/metrics
        - resource
        - attributes
        - batch
      exporters: [prometheusremotewrite]

    # --- Logs Pipeline ---
    logs:
      receivers: [otlp]
      processors:
        - memory_limiter
        - resource
        - attributes
        - batch
      exporters: [loki]
```

#### Erklaerung der Konfigurationssektionen

##### Receivers

Receivers oeffnen Ports und warten auf eingehende Daten. Der `otlp`-Receiver ist der Haupteinstiegspunkt. Er akzeptiert alle drei Signaltypen (Traces, Metriken, Logs) ueber ein Protokoll. Die CORS-Konfiguration ist notwendig, damit Browser-basierte Anwendungen (Astro, Next.js Client-Side) Telemetriedaten senden koennen.

Der `prometheus`-Receiver ist optional und kann Prometheus-Metriken scrapen. Er funktioniert identisch zu einer `scrape_configs`-Sektion in `prometheus.yml`.

##### Processors

Die Reihenfolge der Processors in einer Pipeline ist entscheidend:

1. **memory_limiter:** Immer zuerst. Schuetzt vor OOM.
2. **filter:** Frueh filtern spart Ressourcen in nachfolgenden Processors.
3. **resource / resourcedetection:** Resource-Attribute setzen.
4. **attributes:** Span/Metrik-Attribute setzen.
5. **tail_sampling:** Sampling-Entscheidung (nur fuer Traces).
6. **batch:** Immer zuletzt. Sammelt und sendet in Batches.

##### Exporters

Jeder Exporter sendet Daten an genau ein Backend. Die `retry_on_failure`- und `sending_queue`-Konfiguration stellt sicher, dass keine Daten verloren gehen, wenn ein Backend temporaer nicht erreichbar ist.

##### Pipelines

Pipelines verbinden Receivers mit Processors und Exporters. Jeder Signaltyp (traces, metrics, logs) hat eine eigene Pipeline. Ein Receiver kann in mehreren Pipelines verwendet werden, ebenso wie Processors und Exporters.

---

### 5. App-Integration

#### 5a. Next.js (TypeScript)

##### Installation

```bash
npm install \
  @opentelemetry/api \
  @opentelemetry/sdk-node \
  @opentelemetry/auto-instrumentations-node \
  @opentelemetry/exporter-trace-otlp-grpc \
  @opentelemetry/exporter-metrics-otlp-grpc \
  @opentelemetry/exporter-logs-otlp-grpc \
  @opentelemetry/resources \
  @opentelemetry/semantic-conventions
```

##### Instrumentierung (instrumentation.ts)

Erstelle die Datei `src/instrumentation.ts` (Next.js laedt diese automatisch):

```typescript
// src/instrumentation.ts
// Next.js laedt diese Datei automatisch beim Start (ab Next.js 13.4+).
// Siehe: https://nextjs.org/docs/app/building-your-application/optimizing/instrumentation

export async function register() {
  // Nur server-seitig instrumentieren (nicht im Browser)
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    const { NodeSDK } = await import('@opentelemetry/sdk-node');
    const { getNodeAutoInstrumentations } = await import(
      '@opentelemetry/auto-instrumentations-node'
    );
    const { OTLPTraceExporter } = await import(
      '@opentelemetry/exporter-trace-otlp-grpc'
    );
    const { OTLPMetricExporter } = await import(
      '@opentelemetry/exporter-metrics-otlp-grpc'
    );
    const { Resource } = await import('@opentelemetry/resources');
    const {
      ATTR_SERVICE_NAME,
      ATTR_SERVICE_VERSION,
    } = await import('@opentelemetry/semantic-conventions');
    const { PeriodicExportingMetricReader } = await import(
      '@opentelemetry/sdk-metrics'
    );

    const sdk = new NodeSDK({
      // Resource beschreibt den Service
      resource: new Resource({
        [ATTR_SERVICE_NAME]: 'nextjs-app',
        [ATTR_SERVICE_VERSION]: process.env.npm_package_version || '0.0.0',
        'deployment.environment': process.env.NODE_ENV || 'development',
      }),

      // Traces an den OTel Collector senden
      traceExporter: new OTLPTraceExporter({
        url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT
          || 'http://toolbox-otel-collector:4317',
      }),

      // Metriken an den OTel Collector senden
      metricReader: new PeriodicExportingMetricReader({
        exporter: new OTLPMetricExporter({
          url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT
            || 'http://toolbox-otel-collector:4317',
        }),
        exportIntervalMillis: 30000, // Alle 30 Sekunden
      }),

      // Automatische Instrumentierung fuer:
      // - HTTP (incoming + outgoing requests)
      // - Express/Next.js routing
      // - pg (PostgreSQL queries)
      // - ioredis (Redis commands)
      // - dns, net, fs (System-Aufrufe)
      instrumentations: [
        getNodeAutoInstrumentations({
          // HTTP-Instrumentierung: Health-Checks ignorieren
          '@opentelemetry/instrumentation-http': {
            ignoreIncomingRequestHook: (req) => {
              const url = req.url || '';
              return url === '/health' || url === '/api/health';
            },
          },
          // fs-Instrumentierung deaktivieren (zu viel Rauschen)
          '@opentelemetry/instrumentation-fs': { enabled: false },
          // DNS-Instrumentierung deaktivieren
          '@opentelemetry/instrumentation-dns': { enabled: false },
        }),
      ],
    });

    sdk.start();

    // Graceful Shutdown: Offene Spans und Metriken flushen
    process.on('SIGTERM', () => {
      sdk.shutdown().then(
        () => console.log('OTel SDK shut down successfully'),
        (err) => console.error('Error shutting down OTel SDK', err)
      );
    });
  }
}
```

##### Custom Spans fuer Business-Logik

```typescript
// src/lib/tracing.ts
import { trace, SpanStatusCode } from '@opentelemetry/api';

// Tracer fuer die Anwendung erstellen
const tracer = trace.getTracer('nextjs-app', '1.0.0');

// Beispiel: Bestellvorgang tracen
export async function processOrder(orderId: string, items: string[]) {
  return tracer.startActiveSpan('process-order', async (span) => {
    try {
      // Attribute setzen (durchsuchbar in Tempo)
      span.setAttribute('order.id', orderId);
      span.setAttribute('order.item_count', items.length);

      // Verschachtelte Spans fuer Teilschritte
      await tracer.startActiveSpan('validate-payment', async (paymentSpan) => {
        // ... Payment-Validierung ...
        paymentSpan.setAttribute('payment.method', 'credit_card');
        paymentSpan.end();
      });

      await tracer.startActiveSpan('update-inventory', async (inventorySpan) => {
        // ... Inventar aktualisieren ...
        inventorySpan.setAttribute('inventory.items_updated', items.length);
        inventorySpan.end();
      });

      span.setStatus({ code: SpanStatusCode.OK });
    } catch (error) {
      // Fehler im Span aufzeichnen
      span.setStatus({
        code: SpanStatusCode.ERROR,
        message: error instanceof Error ? error.message : 'Unknown error',
      });
      span.recordException(error as Error);
      throw error;
    } finally {
      span.end();
    }
  });
}
```

##### Umgebungsvariablen fuer Next.js

```bash
# .env.local oder via Infisical
OTEL_EXPORTER_OTLP_ENDPOINT=http://toolbox-otel-collector:4317
OTEL_SERVICE_NAME=nextjs-app
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production,service.namespace=toolbox
```

##### next.config.js Anpassung

```javascript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Aktiviere die Instrumentierung
  experimental: {
    instrumentationHook: true,
  },
};

module.exports = nextConfig;
```

---

#### 5b. FastAPI (Python)

##### Installation

```bash
pip install \
  opentelemetry-api \
  opentelemetry-sdk \
  opentelemetry-instrumentation-fastapi \
  opentelemetry-instrumentation-httpx \
  opentelemetry-instrumentation-psycopg2 \
  opentelemetry-instrumentation-redis \
  opentelemetry-instrumentation-sqlalchemy \
  opentelemetry-exporter-otlp-proto-grpc \
  opentelemetry-propagator-b3
```

Oder ueber `requirements.txt`:

```
opentelemetry-api>=1.27.0
opentelemetry-sdk>=1.27.0
opentelemetry-instrumentation-fastapi>=0.48b0
opentelemetry-instrumentation-httpx>=0.48b0
opentelemetry-instrumentation-psycopg2>=0.48b0
opentelemetry-instrumentation-redis>=0.48b0
opentelemetry-instrumentation-sqlalchemy>=0.48b0
opentelemetry-exporter-otlp-proto-grpc>=1.27.0
```

##### Instrumentierung (telemetry.py)

```python
# app/telemetry.py
"""
OpenTelemetry Setup fuer FastAPI.
Importiere setup_telemetry() in main.py und rufe es vor app-Start auf.
"""

import logging
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

logger = logging.getLogger(__name__)


def setup_telemetry(
    service_name: str = "fastapi-app",
    service_version: str = "0.1.0",
    otlp_endpoint: str = "http://toolbox-otel-collector:4317",
    environment: str = "production",
) -> None:
    """
    Initialisiert OpenTelemetry mit automatischer Instrumentierung.

    Args:
        service_name: Name des Service (erscheint in Tempo/Grafana).
        service_version: Version des Service.
        otlp_endpoint: OTLP gRPC Endpoint des OTel Collectors.
        environment: Deployment-Umgebung (production, staging, development).
    """
    # Resource beschreibt den Service
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": environment,
            "service.namespace": "toolbox",
        }
    )

    # --- Traces ---
    trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(trace_provider)

    # --- Metriken ---
    metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
    metric_reader = PeriodicExportingMetricReader(
        metric_exporter,
        export_interval_millis=30000,  # Alle 30 Sekunden
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # --- Auto-Instrumentierung ---
    # Diese Instrumentierungen patchen die Libraries automatisch.
    # Jeder HTTP-Request, jede DB-Query, jeder Redis-Call wird als Span erfasst.
    HTTPXClientInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    RedisInstrumentor().instrument()
    # SQLAlchemy (falls verwendet)
    # SQLAlchemyInstrumentor().instrument()

    logger.info(
        "OpenTelemetry initialized: service=%s, endpoint=%s",
        service_name,
        otlp_endpoint,
    )


def instrument_fastapi(app) -> None:
    """
    Instrumentiert eine FastAPI-App.
    Muss nach app = FastAPI() aufgerufen werden.
    """
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="health,healthz,ready,readyz,docs,openapi.json",
    )
```

##### Integration in main.py

```python
# app/main.py
import os
from fastapi import FastAPI
from app.telemetry import setup_telemetry, instrument_fastapi

# OTel initialisieren BEVOR die App erstellt wird
setup_telemetry(
    service_name=os.getenv("OTEL_SERVICE_NAME", "fastapi-app"),
    service_version=os.getenv("APP_VERSION", "0.1.0"),
    otlp_endpoint=os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://toolbox-otel-collector:4317"
    ),
    environment=os.getenv("DEPLOYMENT_ENV", "production"),
)

app = FastAPI(title="My API")

# FastAPI instrumentieren (nach App-Erstellung)
instrument_fastapi(app)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

##### Custom Spans und Metriken in FastAPI

```python
# app/services/order_service.py
from opentelemetry import trace, metrics

# Tracer und Meter fuer die Anwendung
tracer = trace.get_tracer("fastapi-app.order_service")
meter = metrics.get_meter("fastapi-app.order_service")

# Custom Metriken
order_counter = meter.create_counter(
    name="orders.created",
    description="Anzahl erstellter Bestellungen",
    unit="1",
)
order_duration = meter.create_histogram(
    name="orders.processing_duration",
    description="Verarbeitungsdauer einer Bestellung",
    unit="ms",
)


async def create_order(user_id: str, items: list[dict]) -> dict:
    """Erstellt eine Bestellung mit Custom Tracing."""
    with tracer.start_as_current_span("create_order") as span:
        # Attribute setzen (durchsuchbar in Tempo)
        span.set_attribute("user.id", user_id)
        span.set_attribute("order.item_count", len(items))

        # Verschachtelter Span: Inventar pruefen
        with tracer.start_as_current_span("check_inventory") as inv_span:
            # ... Inventar pruefen ...
            inv_span.set_attribute("inventory.all_available", True)

        # Verschachtelter Span: Zahlung verarbeiten
        with tracer.start_as_current_span("process_payment") as pay_span:
            # ... Zahlung verarbeiten ...
            pay_span.set_attribute("payment.method", "stripe")
            pay_span.set_attribute("payment.amount_cents", 4999)

        # Metriken aufzeichnen
        order_counter.add(1, {"payment.method": "stripe"})
        order_duration.record(250, {"order.size": "medium"})

        return {"order_id": "ord_123", "status": "created"}
```

##### Context Propagation (Request-Kontext weitergeben)

```python
# app/services/external_api.py
"""
Context Propagation: Wenn dein FastAPI-Service einen anderen Service aufruft,
wird der Trace-Kontext automatisch im HTTP-Header mitgesendet.
httpx ist bereits instrumentiert -- du musst nichts tun.
"""
import httpx
from opentelemetry import trace

tracer = trace.get_tracer("fastapi-app.external_api")


async def call_payment_service(order_id: str) -> dict:
    """
    Ruft den Payment-Service auf.
    Der Trace-Kontext wird automatisch als W3C Trace Context Header mitgesendet:
      traceparent: 00-<trace-id>-<span-id>-01
    """
    with tracer.start_as_current_span("call_payment_service") as span:
        span.set_attribute("order.id", order_id)

        async with httpx.AsyncClient() as client:
            # httpx-Instrumentierung fuegt traceparent-Header automatisch hinzu
            response = await client.post(
                "http://payment-service:8000/api/payments",
                json={"order_id": order_id},
            )
            span.set_attribute("http.status_code", response.status_code)
            return response.json()
```

---

#### 5c. Astro (Client-Side / Browser)

Browser-Telemetrie erfordert den Web-SDK und sendet ueber OTLP/HTTP (nicht gRPC, da Browser kein gRPC unterstuetzen).

##### Installation

```bash
npm install \
  @opentelemetry/api \
  @opentelemetry/sdk-trace-web \
  @opentelemetry/instrumentation-document-load \
  @opentelemetry/instrumentation-fetch \
  @opentelemetry/instrumentation-xml-http-request \
  @opentelemetry/exporter-trace-otlp-http \
  @opentelemetry/context-zone \
  @opentelemetry/resources
```

##### Instrumentierung (telemetry.ts)

```typescript
// src/lib/telemetry.ts
import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { Resource } from '@opentelemetry/resources';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { DocumentLoadInstrumentation } from '@opentelemetry/instrumentation-document-load';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { XMLHttpRequestInstrumentation } from '@opentelemetry/instrumentation-xml-http-request';

export function initTelemetry() {
  const resource = new Resource({
    'service.name': 'astro-website',
    'service.version': '1.0.0',
    'deployment.environment': import.meta.env.MODE,
  });

  const exporter = new OTLPTraceExporter({
    // OTLP/HTTP Endpoint (CORS muss im Collector konfiguriert sein)
    url: 'https://otel-collector.example.com/v1/traces',
  });

  const provider = new WebTracerProvider({
    resource,
    spanProcessors: [new BatchSpanProcessor(exporter)],
  });

  provider.register({
    contextManager: new ZoneContextManager(),
  });

  // Automatische Instrumentierung
  registerInstrumentations({
    instrumentations: [
      // Seitenlade-Performance (Navigation Timing API)
      new DocumentLoadInstrumentation(),
      // fetch() Aufrufe
      new FetchInstrumentation({
        // Nur eigene API-Aufrufe tracen, nicht externe
        ignoreUrls: [/google/, /analytics/, /sentry/],
        // Trace-Kontext an eigene APIs propagieren
        propagateTraceHeaderCorsUrls: [/api\.example\.com/],
      }),
      // XMLHttpRequest (Legacy)
      new XMLHttpRequestInstrumentation({
        ignoreUrls: [/google/, /analytics/],
      }),
    ],
  });
}
```

##### Einbindung in Astro

```astro
---
// src/layouts/BaseLayout.astro
---
<html>
  <head>
    <meta charset="utf-8" />
    <title>My Site</title>
  </head>
  <body>
    <slot />
    <script>
      import { initTelemetry } from '../lib/telemetry';
      // Nur in Produktion initialisieren
      if (import.meta.env.PROD) {
        initTelemetry();
      }
    </script>
  </body>
</html>
```

##### Custom Spans fuer User-Interaktionen

```typescript
// src/lib/tracking.ts
import { trace } from '@opentelemetry/api';

const tracer = trace.getTracer('astro-website');

// Beispiel: Button-Klick tracen
export function trackSignup(plan: string) {
  const span = tracer.startSpan('user-signup');
  span.setAttribute('signup.plan', plan);
  span.setAttribute('signup.source', window.location.pathname);
  span.end();
}

// Beispiel: Suche tracen
export function trackSearch(query: string, resultCount: number) {
  const span = tracer.startSpan('site-search');
  span.setAttribute('search.query', query);
  span.setAttribute('search.result_count', resultCount);
  span.end();
}
```

**Hinweis:** Fuer Browser-Telemetrie muss der OTel Collector ueber eine oeffentliche URL erreichbar sein (z.B. `https://otel-collector.example.com`), da der Browser direkt an den Collector sendet. Konfiguriere einen Reverse Proxy ueber Coolify, der nur den OTLP-HTTP-Port (4318) exponiert. CORS muss im Collector konfiguriert sein (siehe Abschnitt 4).

---

#### 5d. Flutter (Dart)

##### Installation

```yaml
# pubspec.yaml
dependencies:
  opentelemetry_api: ^0.18.0
  opentelemetry_sdk: ^0.18.0
  opentelemetry_exporter_otlp_http: ^0.18.0
```

##### Instrumentierung

```dart
// lib/telemetry.dart
import 'package:opentelemetry_api/opentelemetry_api.dart';
import 'package:opentelemetry_sdk/opentelemetry_sdk.dart';
import 'package:opentelemetry_exporter_otlp_http/opentelemetry_exporter_otlp_http.dart';

class TelemetryService {
  static late Tracer _tracer;

  static Future<void> initialize() async {
    final exporter = OtlpHttpTraceExporter(
      endpoint: 'https://otel-collector.example.com/v1/traces',
    );

    final provider = TracerProviderBuilder()
        .addSpanProcessor(BatchSpanProcessor(exporter))
        .setResource(Resource([
          Attribute.fromString('service.name', 'flutter-app'),
          Attribute.fromString('service.version', '1.0.0'),
          Attribute.fromString('deployment.environment', 'production'),
        ]))
        .build();

    registerGlobalTracerProvider(provider);
    _tracer = provider.getTracer('flutter-app');
  }

  /// HTTP-Anfrage mit Tracing
  static Future<T> traceHttpRequest<T>(
    String name,
    Future<T> Function() request, {
    Map<String, String>? attributes,
  }) async {
    final span = _tracer.startSpan(name);
    try {
      attributes?.forEach((key, value) {
        span.setAttribute(Attribute.fromString(key, value));
      });
      final result = await request();
      span.setStatus(StatusCode.ok);
      return result;
    } catch (e) {
      span.setStatus(StatusCode.error, description: e.toString());
      span.recordException(e);
      rethrow;
    } finally {
      span.end();
    }
  }

  /// Custom Event tracen
  static void trackEvent(String name, Map<String, String> attributes) {
    final span = _tracer.startSpan(name);
    attributes.forEach((key, value) {
      span.setAttribute(Attribute.fromString(key, value));
    });
    span.end();
  }
}
```

##### Verwendung in Flutter

```dart
// lib/main.dart
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await TelemetryService.initialize();
  runApp(const MyApp());
}

// In einem Service:
final data = await TelemetryService.traceHttpRequest(
  'fetch-products',
  () => apiClient.get('/api/products'),
  attributes: {'category': 'electronics'},
);
```

---

#### 5e. Swift (iOS / macOS)

##### Installation

```swift
// Package.swift (oder ueber Xcode SPM)
dependencies: [
    .package(
        url: "https://github.com/open-telemetry/opentelemetry-swift",
        from: "1.10.0"
    ),
],
targets: [
    .target(
        name: "MyApp",
        dependencies: [
            .product(name: "OpenTelemetryApi", package: "opentelemetry-swift"),
            .product(name: "OpenTelemetrySdk", package: "opentelemetry-swift"),
            .product(name: "OtlpGRPCSpanExporting", package: "opentelemetry-swift"),
            .product(name: "URLSessionInstrumentation", package: "opentelemetry-swift"),
        ]
    ),
]
```

##### Instrumentierung

```swift
// TelemetrySetup.swift
import OpenTelemetryApi
import OpenTelemetrySdk
import OtlpGRPCSpanExporting
import URLSessionInstrumentation
import Foundation

enum TelemetrySetup {
    static func initialize() {
        // OTLP Exporter konfigurieren
        let otlpExporter = OtlpGRPCSpanExporter(
            channel: /* gRPC Channel zu otel-collector.example.com:4317 */
        )

        // TracerProvider erstellen
        let tracerProvider = TracerProviderBuilder()
            .add(spanProcessor: BatchSpanProcessor(spanExporter: otlpExporter))
            .with(resource: Resource(attributes: [
                ResourceAttributes.serviceName.rawValue:
                    AttributeValue.string("swift-app"),
                ResourceAttributes.serviceVersion.rawValue:
                    AttributeValue.string("1.0.0"),
                "deployment.environment":
                    AttributeValue.string("production"),
            ]))
            .build()

        OpenTelemetry.registerTracerProvider(tracerProvider: tracerProvider)

        // URLSession automatisch instrumentieren
        URLSessionInstrumentation(
            configuration: URLSessionInstrumentationConfiguration(
                shouldInstrument: { request in
                    // Nur eigene API-Aufrufe instrumentieren
                    return request.url?.host?.contains("api.example.com") ?? false
                }
            )
        )
    }
}
```

##### Verwendung in Swift

```swift
// OrderService.swift
import OpenTelemetryApi

class OrderService {
    private let tracer = OpenTelemetry.instance.tracerProvider
        .get(instrumentationName: "swift-app", instrumentationVersion: "1.0.0")

    func createOrder(userId: String, items: [OrderItem]) async throws -> Order {
        let span = tracer.spanBuilder(spanName: "create-order").startSpan()
        defer { span.end() }

        span.setAttribute(key: "user.id", value: userId)
        span.setAttribute(key: "order.item_count", value: items.count)

        do {
            let order = try await apiClient.post("/orders", body: items)
            span.setStatus(.ok)
            return order
        } catch {
            span.setStatus(.error(description: error.localizedDescription))
            span.addEvent(name: "exception", attributes: [
                "exception.message": AttributeValue.string(error.localizedDescription),
            ])
            throw error
        }
    }
}
```

---

### 6. Distributed Tracing in der Praxis

#### End-to-End Trace: Browser -> Next.js -> FastAPI -> PostgreSQL

Ein typischer Trace durch die gesamte Toolbox sieht so aus:

```
Browser (Astro/Next.js Client)
  |
  | fetch("https://app.example.com/api/orders")
  | Header: traceparent: 00-<trace-id>-<span-id-1>-01
  |
  v
Next.js Server (Node.js)
  |
  | Span: "GET /api/orders" (auto-instrumentiert)
  |   Attribute: http.method=GET, http.route=/api/orders
  |
  | httpx.post("http://fastapi-app:8000/api/orders/process")
  | Header: traceparent: 00-<trace-id>-<span-id-2>-01
  |
  v
FastAPI (Python)
  |
  | Span: "POST /api/orders/process" (auto-instrumentiert)
  |   Attribute: http.method=POST, http.route=/api/orders/process
  |
  | db.execute("SELECT * FROM orders WHERE ...")
  |
  | Span: "SELECT orders" (auto-instrumentiert via psycopg2)
  |   Attribute: db.system=postgresql, db.statement="SELECT * FROM ..."
  |
  v
PostgreSQL
```

Alle Spans teilen dieselbe `trace-id`. In Grafana/Tempo kannst du die gesamte Kette als Wasserfall-Diagramm sehen.

#### Context Propagation (W3C Trace Context)

Context Propagation ist der Mechanismus, der Traces ueber Service-Grenzen hinweg verbindet. Er basiert auf dem W3C Trace Context Standard und funktioniert ueber HTTP-Header:

```
traceparent: 00-<trace-id>-<parent-span-id>-<trace-flags>
             |   |          |               |
             |   |          |               +-- 01 = sampled
             |   |          +-- ID des aktuellen Spans
             |   +-- Eindeutige Trace-ID (32 hex chars)
             +-- Version (immer 00)
```

Beispiel:
```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

Die OTel SDKs setzen diesen Header automatisch bei ausgehenden HTTP-Requests und lesen ihn bei eingehenden Requests.

#### Traces in Grafana/Tempo anzeigen

1. Oeffne Grafana > **Explore**.
2. Waehle **Tempo** als Datenquelle.
3. Suche nach Traces:
   - Nach Service: `{resource.service.name="fastapi-app"}`
   - Nach Dauer: `{duration > 1s}`
   - Nach Status: `{status = error}`
   - Nach Attribut: `{span.http.route="/api/orders"}`
4. Klicke auf eine Trace-ID fuer das Wasserfall-Diagramm.

#### Trace-zu-Log-Korrelation

Um Logs mit Traces zu verknuepfen, muss die `trace_id` in den Log-Zeilen erscheinen.

**Python (FastAPI) -- Logging mit Trace-ID:**

```python
# app/logging_config.py
import logging
from opentelemetry import trace


class TraceIdFilter(logging.Filter):
    """Fuegt trace_id und span_id zu jedem Log-Eintrag hinzu."""

    def filter(self, record):
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx.is_valid:
            record.trace_id = format(ctx.trace_id, '032x')
            record.span_id = format(ctx.span_id, '016x')
        else:
            record.trace_id = "0" * 32
            record.span_id = "0" * 16
        return True


# Logging-Format mit trace_id
LOGGING_CONFIG = {
    "version": 1,
    "filters": {
        "trace_id": {"()": TraceIdFilter},
    },
    "formatters": {
        "json": {
            "format": '{"time":"%(asctime)s","level":"%(levelname)s",'
                      '"logger":"%(name)s","trace_id":"%(trace_id)s",'
                      '"span_id":"%(span_id)s","message":"%(message)s"}',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["trace_id"],
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}
```

In Grafana kannst du dann von einem Log-Eintrag direkt zum zugehoerigen Trace springen:
1. Finde den Log-Eintrag in Loki.
2. Klicke auf die `trace_id` im Log.
3. Grafana oeffnet den Trace in Tempo.

#### Service Map in Grafana

Tempo generiert automatisch eine Service Map aus den Traces. Diese zeigt alle Services und ihre Abhaengigkeiten:

1. Oeffne Grafana > **Explore** > **Tempo**.
2. Klicke auf **Service Graph** (Tab oben).
3. Die Karte zeigt: `Browser -> Next.js -> FastAPI -> PostgreSQL`.
4. Kanten zeigen: Request-Rate, Fehlerrate, Latenz.

---

### 7. Custom Metrics

Der OTel Collector leitet App-Metriken an Prometheus weiter. Drei Metriktypen stehen zur Verfuegung:

#### Counter (zaehlt Ereignisse)

```python
# Python
from opentelemetry import metrics

meter = metrics.get_meter("my-app")
request_counter = meter.create_counter(
    name="http.requests.total",
    description="Gesamtzahl der HTTP-Requests",
    unit="1",
)

# Verwenden
request_counter.add(1, {"http.method": "GET", "http.route": "/api/users"})
```

```typescript
// TypeScript
import { metrics } from '@opentelemetry/api';

const meter = metrics.getMeter('my-app');
const errorCounter = meter.createCounter('errors.total', {
  description: 'Gesamtzahl der Fehler',
  unit: '1',
});

// Verwenden
errorCounter.add(1, { 'error.type': 'validation', 'error.code': '422' });
```

#### Histogram (misst Verteilungen)

```python
# Python
duration_histogram = meter.create_histogram(
    name="http.request.duration",
    description="Dauer der HTTP-Requests",
    unit="ms",
)

# Verwenden
import time
start = time.time()
# ... Request verarbeiten ...
duration_ms = (time.time() - start) * 1000
duration_histogram.record(duration_ms, {"http.route": "/api/orders"})
```

#### Gauge (aktueller Wert)

```python
# Python
# UpDownCounter als Gauge-Alternative
active_users = meter.create_up_down_counter(
    name="users.active",
    description="Aktuell aktive Benutzer",
    unit="1",
)

# Verwenden
active_users.add(1)   # Benutzer kommt
active_users.add(-1)  # Benutzer geht
```

#### In Prometheus abfragen

Die Metriken erscheinen in Prometheus unter dem Praefixnamen. In Grafana:

```promql
# Request-Rate pro Route (letzte 5 Minuten)
rate(http_requests_total[5m])

# 95. Perzentil der Request-Dauer
histogram_quantile(0.95, rate(http_request_duration_bucket[5m]))

# Aktive Benutzer
users_active
```

---

### 8. Tail Sampling

#### Warum Tail Sampling?

100% aller Traces zu speichern ist teuer:
- **Speicher:** Jeder Trace besteht aus mehreren Spans. 1000 Requests/Sekunde mit 5 Spans/Request = 5000 Spans/Sekunde.
- **Netzwerk:** OTLP-Daten muessen an den Collector und von dort an Tempo gesendet werden.
- **Tempo-Speicher:** Tempo muss alle Traces indizieren und speichern.

#### Head Sampling vs. Tail Sampling

| Aspekt              | Head Sampling                    | Tail Sampling                    |
|---------------------|----------------------------------|----------------------------------|
| Entscheidungspunkt  | Am Anfang der Trace              | Nach allen Spans empfangen       |
| Fehler behalten     | Nein (Entscheidung vor Fehler)   | Ja (Fehler-Status bekannt)       |
| Langsame Requests   | Nein (Dauer unbekannt)           | Ja (Dauer bekannt)               |
| Speicherverbrauch   | Niedrig                          | Hoeher (Traces im Puffer)        |
| Konfigurationsort   | Im SDK                           | Im Collector                     |

Tail Sampling ist immer vorzuziehen, weil es garantiert, dass alle Fehler und langsamen Requests behalten werden.

#### Sampling-Strategie fuer die Toolbox

Die Collector-Konfiguration (Abschnitt 4) implementiert folgende Strategie:

| Policy                  | Bedingung                      | Sampling-Rate |
|-------------------------|--------------------------------|---------------|
| `errors-policy`         | Span-Status = ERROR            | 100%          |
| `latency-policy`        | Trace-Dauer > 1000ms           | 100%          |
| `probabilistic-policy`  | Alle anderen Traces            | 10%           |

Das bedeutet:
- **Jeder Fehler** wird gespeichert (fuer Debugging).
- **Jeder langsame Request** wird gespeichert (fuer Performance-Analyse).
- **Normale Requests** werden zu 10% gespeichert (fuer Baseline-Metriken).

#### Sampling-Rate anpassen

Fuer hoch-frequentierte Services kann die Rate weiter reduziert werden:

```yaml
# In otel-config.yaml unter tail_sampling.policies:
- name: high-volume-service
  type: and
  and:
    and_sub_policy:
      - name: service-filter
        type: string_attribute
        string_attribute:
          key: service.name
          values: ["high-volume-api"]
      - name: probabilistic
        type: probabilistic
        probabilistic:
          sampling_percentage: 1  # Nur 1% der normalen Traces
```

---

### 9. Sentry + OpenTelemetry

#### Option A: Sentry SDK exportiert OTLP (empfohlen)

Ab Sentry SDK v8+ kann das Sentry SDK Traces im OTLP-Format exportieren. So fliessen Traces sowohl zu Sentry (Errors + Performance) als auch zu Tempo (Distributed Tracing).

```typescript
// Next.js: sentry.client.config.ts
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: 'https://examplePublicKey@sentry.example.com/1',
  tracesSampleRate: 1.0,

  // OTLP-Export aktivieren (ab Sentry SDK v8+)
  enableTracing: true,

  // Sentry sendet Traces an den OTel Collector
  // Der Collector leitet sie an Tempo UND Sentry weiter
});
```

#### Option B: Collector exportiert zu Sentry

Der OTel Collector kann Traces direkt an Sentry exportieren. Fuege den Sentry-Exporter zur Collector-Konfiguration hinzu:

```yaml
# In otel-config.yaml
exporters:
  # ... bestehende Exporters ...
  sentry:
    dsn: "https://examplePublicKey@sentry.example.com/1"

service:
  pipelines:
    traces:
      # ... bestehende Receivers und Processors ...
      exporters: [otlp/tempo, sentry]  # Dual-Export
```

#### Entscheidungsmatrix

| Szenario                             | Empfehlung                                |
|--------------------------------------|-------------------------------------------|
| Nur Traces (kein Sentry)             | OTel SDK -> Collector -> Tempo            |
| Sentry + Tempo                       | Option A (Sentry SDK + OTLP)              |
| Bestehende Sentry-Integration        | Option A (SDK-Upgrade auf v8+)            |
| Kein Sentry SDK moeglich             | Option B (Collector exportiert zu Sentry) |

---

### 10. Troubleshooting

#### Keine Traces in Tempo/Grafana

1. **Collector laeuft?**
   ```bash
   docker ps | grep otel-collector
   docker logs toolbox-otel-collector --tail 50
   ```

2. **Collector Health Check:**
   ```bash
   docker exec toolbox-otel-collector wget -qO- http://localhost:13133/
   # Erwartet: {"status":"Server available","..."}
   ```

3. **Tempo erreichbar vom Collector?**
   ```bash
   docker exec toolbox-otel-collector wget -qO- http://tempo:3200/ready
   # Erwartet: "ready"
   ```

4. **OTLP-Endpoint in der App korrekt?**
   ```bash
   # Aus einem App-Container testen:
   docker exec <app-container> wget -qO- http://toolbox-otel-collector:4318/v1/traces
   # Erwartet: HTTP 405 (Method Not Allowed) -- der Endpoint existiert, akzeptiert aber nur POST
   ```

5. **Debug-Exporter aktivieren:**
   ```yaml
   # Temporaer in otel-config.yaml:
   service:
     pipelines:
       traces:
         exporters: [otlp/tempo, debug]
   ```
   Dann in den Collector-Logs nach Spans suchen:
   ```bash
   docker logs toolbox-otel-collector 2>&1 | grep "Span #"
   ```

#### Hoher Speicherverbrauch des Collectors

1. **Memory Limiter pruefen:**
   ```bash
   docker stats toolbox-otel-collector
   ```
   Falls der Collector nahe am Limit ist, erhoehe `limit_mib` in der Konfiguration oder reduziere das Tail-Sampling-Fenster (`decision_wait`).

2. **Tail Sampling reduzieren:**
   ```yaml
   tail_sampling:
     decision_wait: 5s         # Von 10s auf 5s reduzieren
     num_traces: 25000         # Von 50000 auf 25000 reduzieren
   ```

3. **Batch-Groesse anpassen:**
   ```yaml
   batch:
     timeout: 2s               # Schneller senden
     send_batch_size: 512      # Kleinere Batches
   ```

#### Fehlende Spans in Traces

1. **Instrumentierung aktiv?**
   - Pruefe, ob das OTel SDK in der Anwendung korrekt initialisiert ist.
   - Pruefe die Anwendungs-Logs nach OTel-bezogenen Fehlern.

2. **Context Propagation funktioniert?**
   - Pruefe, ob der `traceparent`-Header in ausgehenden HTTP-Requests gesetzt wird:
     ```bash
     # In der FastAPI-Anwendung:
     curl -v http://fastapi-app:8000/api/orders 2>&1 | grep traceparent
     ```

3. **Health-Check-Filter zu aggressiv?**
   - Falls Spans fehlen, die keine Health-Checks sind, pruefe die Filter-Regeln im Collector.

#### CORS-Fehler bei Browser-Telemetrie

Wenn der Browser Telemetriedaten an den Collector sendet und CORS-Fehler auftreten:

1. **CORS-Konfiguration pruefen:**
   ```yaml
   # In otel-config.yaml unter receivers.otlp.protocols.http:
   cors:
     allowed_origins:
       - "https://example.com"
       - "https://*.example.com"
       - "http://localhost:*"    # Fuer lokale Entwicklung
     allowed_headers:
       - "*"
   ```

2. **Collector oeffentlich erreichbar?**
   Der Collector muss ueber eine Coolify-Domain erreichbar sein, z.B. `otel-collector.example.com`, die auf Port 4318 des Containers zeigt.

#### Prometheus Remote Write Fehler

Falls Metriken nicht in Prometheus ankommen:

1. **Remote Write aktiviert?**
   Prometheus muss mit dem Flag `--web.enable-remote-write-receiver` gestartet sein:
   ```yaml
   # In der Prometheus docker-compose.yml:
   command:
     - '--config.file=/etc/prometheus/prometheus.yml'
     - '--web.enable-remote-write-receiver'
   ```

2. **Endpoint korrekt?**
   ```bash
   docker exec toolbox-otel-collector wget -qO- http://prometheus:9090/api/v1/status/config
   ```

#### zPages Debug-UI

Der Collector bietet eine Debug-UI unter Port 55679 (intern):

```bash
# Pipeline-Ueberblick
docker exec toolbox-otel-collector wget -qO- http://localhost:55679/debug/tracez

# Aktive Spans
docker exec toolbox-otel-collector wget -qO- http://localhost:55679/debug/tracez?type=0
```

---

### Checkliste: OpenTelemetry vollstaendig eingerichtet

- [ ] `stacks/telemetry/docker-compose.yml` erstellt
- [ ] `stacks/telemetry/configs/otel-config.yaml` erstellt und getestet
- [ ] Stack via Coolify deployed
- [ ] Collector-Container laeuft und ist healthy (`/health` Endpoint)
- [ ] Tempo empfaengt Traces vom Collector (Grafana > Explore > Tempo)
- [ ] Prometheus empfaengt Metriken (Remote Write aktiviert)
- [ ] Loki empfaengt Logs vom Collector
- [ ] Mindestens eine Anwendung instrumentiert (Next.js oder FastAPI)
- [ ] Custom Spans erscheinen in Tempo
- [ ] Trace-zu-Log-Korrelation funktioniert (trace_id in Logs)
- [ ] Health-Check-Spans werden herausgefiltert
- [ ] Tail Sampling konfiguriert (Fehler 100%, normal 10%)
- [ ] Service Map in Grafana sichtbar
- [ ] Collector-eigene Metriken in Prometheus (`otel_collector_*`)

---

## 7. Plausible — Leichtgewichtige Analytics


Dieses Dokument beschreibt die Einrichtung von Plausible Analytics als leichtgewichtige, datenschutzfreundliche Web-Analytics-Loesung. Plausible ist cookie-frei, benoetigt keinen Consent-Banner und ergaenzt PostHog fuer einfache Websites und Marketing-Seiten. Es wird als self-hosted Community Edition im Toolbox-Stack betrieben.

> **Voraussetzung:** Der `core-data`-Stack (PostgreSQL) muss bereits laufen. Siehe [04-deploy-stack.md](04-deploy-stack.md). Fuer die DSGVO-Grundlagen siehe [08-cookie-consent.md](08-cookie-consent.md).

---

### 1. Was ist Plausible?

Plausible Analytics ist ein Open-Source Web-Analytics-Tool, das als datenschutzfreundliche Alternative zu Google Analytics entwickelt wurde. Es ist das einzige weit verbreitete Analytics-Tool, das **standardmaessig keine Cookies setzt** und damit ohne Consent-Banner betrieben werden kann.

#### Kernmerkmale

| Merkmal                       | Detail                                                       |
|-------------------------------|--------------------------------------------------------------|
| Cookie-frei                   | Setzt keine Cookies, kein localStorage, kein sessionStorage  |
| Consent-Banner                | Nicht erforderlich (DSGVO-konform ohne Konfiguration)        |
| Script-Groesse                | ~1.6 KB (gzip), vollstaendig unter 5 KB                     |
| Open Source                   | AGPL-v3 Lizenz, self-hosted Community Edition                |
| Datenhoheit                   | Alle Daten auf dem eigenen Server                             |
| IP-Adressen                   | Werden fuer Geolocation genutzt, aber nie gespeichert         |
| Besucheridentifikation        | Taeglicher Hash aus IP + User-Agent (ohne Speicherung)       |
| Retention                     | Unbegrenzt (aggregierte Daten, keine Einzelprofile)           |
| Ressourcenverbrauch           | ~256 MB RAM, minimale CPU                                    |
| Abhaengigkeiten               | PostgreSQL + ClickHouse                                      |

#### Wann Plausible verwenden

| Szenario                                            | Empfehlung  |
|-----------------------------------------------------|-------------|
| Marketing-Website, Landingpage, Blog                | Plausible   |
| Statische Website (Astro)                           | Plausible   |
| Portfolio, Dokumentation                            | Plausible   |
| Web-App mit Funnels, Session Recording              | PostHog     |
| A/B-Tests, Experimente                              | PostHog     |
| Mobile App Analytics                                | PostHog     |
| SaaS-Dashboard mit User-Identifikation              | PostHog     |
| Einfache Pageview-Analytics + komplexe App-Analytics | Beides      |

**Faustregel:** Plausible fuer alles, wo du nur wissen willst "wie viele Besucher, woher, welche Seiten". PostHog fuer alles, wo du wissen willst "was tun die Besucher, warum brechen sie ab, welche Version konvertiert besser".

---

### 2. Plausible vs PostHog -- Detaillierter Vergleich

#### Feature-Vergleich

| Feature                         | Plausible                      | PostHog                              |
|---------------------------------|--------------------------------|--------------------------------------|
| **Datenschutz**                 |                                |                                      |
| Cookie-frei (Standard)         | Ja                             | Ja (memory-Modus, braucht Config)    |
| Consent-Banner noetig          | Nein                           | Ja (fuer vollen Funktionsumfang)     |
| IP-Speicherung                 | Nie                            | Konfigurierbar                       |
| DSGVO ohne Config              | Ja                             | Nein (Konfiguration noetig)          |
| **Tracking**                    |                                |                                      |
| Pageviews                      | Ja                             | Ja                                   |
| Custom Events                  | Ja (einfach, key-value)        | Ja (komplex, verschachtelt)          |
| User-Identifikation            | Nein                           | Ja                                   |
| Session Recording              | Nein                           | Ja                                   |
| Heatmaps                       | Nein                           | Ja                                   |
| Autocapture                    | Nein                           | Ja                                   |
| **Analyse**                     |                                |                                      |
| Funnels                        | Basis (Custom Event Funnels)   | Fortgeschritten (multi-step)         |
| Retention                      | Nein                           | Ja                                   |
| Cohorten                       | Nein                           | Ja                                   |
| Dashboards                     | 1 pro Website                  | Unbegrenzt, anpassbar                |
| **Experimente**                 |                                |                                      |
| A/B Testing                    | Nein                           | Ja (oder via Unleash)                |
| Feature Flags                  | Nein                           | Ja (oder via Unleash)                |
| Surveys                        | Nein                           | Ja                                   |
| **Technisch**                   |                                |                                      |
| Script-Groesse (gzip)          | ~1.6 KB                       | ~45 KB                               |
| RAM-Verbrauch                  | ~256 MB                        | ~4 GB+                               |
| CPU-Verbrauch                  | Minimal                        | Moderat bis hoch                     |
| Abhaengigkeiten                | PostgreSQL, ClickHouse         | PostgreSQL, ClickHouse, Redis, Kafka |
| Setup-Komplexitaet             | Niedrig (2 Container)          | Hoch (8+ Container)                  |
| API                            | Stats API, Sites API           | Umfangreiche REST + Query API        |

#### Ressourcenvergleich

| Ressource               | Plausible                   | PostHog                          |
|--------------------------|-----------------------------|----------------------------------|
| Docker Container         | 2 (Plausible + ClickHouse)  | 8+ (App, Worker, ClickHouse,     |
|                          |                             | Kafka, Redis, Plugin Server...)  |
| RAM (Minimum)            | 512 MB                      | 4 GB                             |
| RAM (Empfohlen)          | 1 GB                        | 8 GB                             |
| Disk (pro 1M Events)     | ~50 MB (ClickHouse)         | ~200 MB (ClickHouse + Kafka)     |
| CPU                      | 0.5 Cores                   | 2+ Cores                         |

#### Empfehlung fuer die Toolbox

Verwende **beide** Tools parallel:

- **Plausible** fuer alle oeffentlichen Websites (Marketing, Blog, Docs, Landingpages). Vorteile: kein Consent-Banner, minimaler Overhead, sofort einsatzbereit.
- **PostHog** fuer Web-Apps und SaaS-Produkte. Vorteile: Session Recording, Funnels, A/B-Tests, User-Identifikation.

Beide koennen auf derselben Seite laufen, ohne sich zu beeinflussen. Es gibt keine Daten-Duplizierung, da sie unterschiedliche Datenmodelle verwenden.

---

### 3. Architektur

#### Datenfluss

```
+------------------+   +------------------+   +------------------+
|  Website A       |   |  Website B       |   |  Website C       |
|  (Astro Blog)    |   |  (Next.js Landing|   |  (Docs)          |
|                  |   |   Page)          |   |                  |
+--------+---------+   +--------+---------+   +--------+---------+
         |                      |                      |
         | <script data-domain="a.example.com"         |
         |   src="https://plausible.example.com/       |
         |   js/script.js">                            |
         |                      |                      |
+--------v----------------------v----------------------v---------+
|                                                                 |
|                    Plausible Analytics                          |
|               toolbox-plausible:8000                            |
|                                                                 |
|  +------------------+          +------------------+             |
|  | Phoenix App      |          | Event Processing |             |
|  | (Elixir/Erlang)  |          | (ClickHouse      |             |
|  |                  |          |  Ingestion)      |             |
|  +--------+---------+          +--------+---------+             |
|           |                             |                       |
+-----------+-----------------------------+-----------------------+
            |                             |
   +--------v--------+          +--------v------------------+
   |   PostgreSQL     |          |   ClickHouse              |
   | toolbox-postgres |          | toolbox-plausible-        |
   | (shared)         |          | clickhouse                |
   |                  |          | (Event-Speicher)          |
   | DB: plausible    |          |                           |
   | - Sites          |          | - Pageviews               |
   | - Users          |          | - Events                  |
   | - Goals          |          | - Sessions (aggregiert)   |
   | - Settings       |          |                           |
   +-----------------+          +---------------------------+
```

#### Datenspeicherung

| Daten                  | Speicherort              | Zweck                              |
|------------------------|--------------------------|------------------------------------|
| Sites, Users, Goals    | PostgreSQL (shared)      | Konfiguration und Verwaltung       |
| Pageviews, Events      | ClickHouse (dediziert)   | Analytische Abfragen (schnell)     |
| Sessions (aggregiert)  | ClickHouse (dediziert)   | Besucherzaehlung ohne Cookies      |

#### ClickHouse: Shared oder Dediziert?

PostHog verwendet ebenfalls ClickHouse. Es gibt zwei Optionen:

**Option A: Dedizierter ClickHouse (empfohlen)**
- Eigene ClickHouse-Instanz nur fuer Plausible.
- Vorteil: Keine Interferenz mit PostHog. Einfacher zu debuggen.
- Nachteil: Zusaetzlicher RAM-Verbrauch (~256 MB).

**Option B: Shared ClickHouse**
- Plausible nutzt die PostHog-ClickHouse-Instanz.
- Vorteil: Weniger Container, weniger RAM gesamt.
- Nachteil: PostHog und Plausible koennen sich gegenseitig beeinflussen. Nicht empfohlen fuer Produktion.

Diese Dokumentation verwendet **Option A** (dedizierter ClickHouse).

---

### 4. Stack Setup

#### Docker Compose

```yaml
# stacks/plausible/docker-compose.yml
# Plausible Analytics - Leichtgewichtige, Cookie-freie Web-Analytics

services:
  # -----------------------------------------------
  # Plausible Analytics (Community Edition)
  # -----------------------------------------------
  plausible:
    image: ghcr.io/plausible/community-edition:v2.1.4
    container_name: toolbox-plausible
    restart: unless-stopped
    command: sh -c "sleep 10 && /entrypoint.sh db createdb && /entrypoint.sh db migrate && /entrypoint.sh run"
    depends_on:
      plausible-events-db:
        condition: service_healthy
    environment:
      # --- Datenbanken ---
      # PostgreSQL (shared mit der Toolbox)
      DATABASE_URL: "postgres://${PLAUSIBLE_DB_USER:-plausible}:${PLAUSIBLE_DB_PASSWORD}@postgres:5432/${PLAUSIBLE_DB_NAME:-plausible}"
      # ClickHouse (dediziert fuer Plausible)
      CLICKHOUSE_DATABASE_URL: "http://plausible-events-db:8123/plausible_events"

      # --- Basis-Konfiguration ---
      # Oeffentliche URL (fuer Links in E-Mails, OAuth Callbacks, etc.)
      BASE_URL: "${PLAUSIBLE_BASE_URL:-https://plausible.example.com}"
      # Geheimer Schluessel (mind. 64 Zeichen, generieren mit: openssl rand -base64 48)
      SECRET_KEY_BASE: "${PLAUSIBLE_SECRET_KEY_BASE}"
      # TOTP-Verschluesselungsschluessel fuer 2FA (generieren mit: openssl rand -base64 32)
      TOTP_VAULT_KEY: "${PLAUSIBLE_TOTP_VAULT_KEY}"

      # --- Registrierung ---
      # "invite_only": Nur der Admin kann neue Benutzer einladen.
      # "true": Oeffentliche Registrierung erlaubt.
      # "false": Registrierung komplett deaktiviert (nach initialem Setup).
      DISABLE_REGISTRATION: "${PLAUSIBLE_DISABLE_REGISTRATION:-invite_only}"

      # --- E-Mail (fuer Einladungen, Passwort-Reset, Weekly Reports) ---
      MAILER_EMAIL: "${PLAUSIBLE_MAILER_EMAIL:-plausible@example.com}"
      SMTP_HOST_ADDR: "${PLAUSIBLE_SMTP_HOST:-mail.example.com}"
      SMTP_HOST_PORT: "${PLAUSIBLE_SMTP_PORT:-587}"
      SMTP_USER_NAME: "${PLAUSIBLE_SMTP_USER:-}"
      SMTP_USER_PWD: "${PLAUSIBLE_SMTP_PASSWORD:-}"
      SMTP_HOST_SSL_ENABLED: "${PLAUSIBLE_SMTP_SSL:-true}"

      # --- Geolocation (MaxMind GeoIP2, optional) ---
      # Registriere dich kostenlos bei maxmind.com fuer einen License Key.
      # Ohne Geolocation funktioniert Plausible, zeigt aber keine Laender-Daten.
      MAXMIND_LICENSE_KEY: "${PLAUSIBLE_MAXMIND_LICENSE_KEY:-}"
      MAXMIND_EDITION: "GeoLite2-City"

      # --- Google Search Console (optional) ---
      GOOGLE_CLIENT_ID: "${PLAUSIBLE_GOOGLE_CLIENT_ID:-}"
      GOOGLE_CLIENT_SECRET: "${PLAUSIBLE_GOOGLE_CLIENT_SECRET:-}"

      # --- Sonstige ---
      # Log-Level: debug, info, warn, error
      LOG_LEVEL: "info"
    networks:
      - toolbox
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 60s
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  # -----------------------------------------------
  # ClickHouse (dediziert fuer Plausible Events)
  # -----------------------------------------------
  # Separater ClickHouse, um PostHog nicht zu beeinflussen.
  # Plausible-Events sind klein und ClickHouse braucht wenig RAM.
  plausible-events-db:
    image: clickhouse/clickhouse-server:24.3-alpine
    container_name: toolbox-plausible-clickhouse
    restart: unless-stopped
    volumes:
      - plausible_clickhouse_data:/var/lib/clickhouse
      - plausible_clickhouse_logs:/var/log/clickhouse-server
      # ClickHouse-Konfiguration fuer minimalen RAM-Verbrauch
      - ./configs/clickhouse-config.xml:/etc/clickhouse-server/config.d/logging.xml:ro
      - ./configs/clickhouse-user-config.xml:/etc/clickhouse-server/users.d/logging.xml:ro
    networks:
      - toolbox
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8123/ping"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
    ulimits:
      nofile:
        soft: 262144
        hard: 262144
    deploy:
      resources:
        limits:
          memory: 1024M
        reservations:
          memory: 256M

volumes:
  plausible_clickhouse_data:
    name: toolbox_plausible_clickhouse_data
  plausible_clickhouse_logs:
    name: toolbox_plausible_clickhouse_logs

networks:
  toolbox:
    external: true
    name: toolbox
```

#### ClickHouse-Konfiguration (minimaler RAM-Verbrauch)

```xml
<!-- stacks/plausible/configs/clickhouse-config.xml -->
<!-- Reduziert ClickHouse-Logging fuer minimalen Ressourcenverbrauch -->
<clickhouse>
    <logger>
        <level>warning</level>
        <console>true</console>
    </logger>
    <!-- Maximale Speichernutzung begrenzen -->
    <max_server_memory_usage_to_ram_ratio>0.5</max_server_memory_usage_to_ram_ratio>
</clickhouse>
```

```xml
<!-- stacks/plausible/configs/clickhouse-user-config.xml -->
<clickhouse>
    <profiles>
        <default>
            <log_queries>0</log_queries>
            <log_query_threads>0</log_query_threads>
            <max_memory_usage>500000000</max_memory_usage>
        </default>
    </profiles>
</clickhouse>
```

#### Umgebungsvariablen (.env.example)

```bash
# stacks/plausible/.env.example
# Plausible Analytics - Umgebungsvariablen
#
# Generiere Secrets mit:
#   openssl rand -base64 48   (fuer SECRET_KEY_BASE)
#   openssl rand -base64 32   (fuer TOTP_VAULT_KEY)

# --- Datenbank ---
PLAUSIBLE_DB_USER=plausible
PLAUSIBLE_DB_PASSWORD=CHANGE_ME_PLAUSIBLE_DB_PASSWORD
PLAUSIBLE_DB_NAME=plausible

# --- Basis ---
PLAUSIBLE_BASE_URL=https://plausible.example.com
PLAUSIBLE_SECRET_KEY_BASE=CHANGE_ME_GENERATE_WITH_OPENSSL_RAND_BASE64_48
PLAUSIBLE_TOTP_VAULT_KEY=CHANGE_ME_GENERATE_WITH_OPENSSL_RAND_BASE64_32

# --- Registrierung ---
# invite_only | true | false
PLAUSIBLE_DISABLE_REGISTRATION=invite_only

# --- E-Mail ---
PLAUSIBLE_MAILER_EMAIL=plausible@example.com
PLAUSIBLE_SMTP_HOST=mail.example.com
PLAUSIBLE_SMTP_PORT=587
PLAUSIBLE_SMTP_USER=plausible@example.com
PLAUSIBLE_SMTP_PASSWORD=CHANGE_ME_SMTP_PASSWORD
PLAUSIBLE_SMTP_SSL=true

# --- Geolocation (optional, aber empfohlen) ---
# Registriere dich kostenlos: https://www.maxmind.com/en/geolite2/signup
PLAUSIBLE_MAXMIND_LICENSE_KEY=

# --- Google Search Console (optional) ---
# Erstelle OAuth Credentials: https://console.cloud.google.com/apis/credentials
PLAUSIBLE_GOOGLE_CLIENT_ID=
PLAUSIBLE_GOOGLE_CLIENT_SECRET=
```

#### PostgreSQL-Datenbank anlegen

Die Plausible-Datenbank muss in der shared PostgreSQL-Instanz angelegt werden. Fuege folgenden Eintrag zur Init-Script-Datei hinzu:

```sql
-- In compose/init-scripts/postgres/01-create-databases.sql einfuegen:
CREATE DATABASE plausible;
CREATE USER plausible WITH ENCRYPTED PASSWORD 'CHANGE_ME_PLAUSIBLE_DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE plausible TO plausible;
ALTER DATABASE plausible OWNER TO plausible;
```

Falls die Datenbank bereits existiert (PostgreSQL laeuft schon):

```bash
docker exec -it toolbox-postgres psql -U postgres -c "
  CREATE DATABASE plausible;
  CREATE USER plausible WITH ENCRYPTED PASSWORD 'CHANGE_ME_PLAUSIBLE_DB_PASSWORD';
  GRANT ALL PRIVILEGES ON DATABASE plausible TO plausible;
  ALTER DATABASE plausible OWNER TO plausible;
"
```

#### Verzeichnisstruktur

```
stacks/plausible/
  docker-compose.yml
  .env.example
  configs/
    clickhouse-config.xml
    clickhouse-user-config.xml
```

---

### 5. Erstinstallation

#### Schritt 1: Secrets generieren

```bash
# SECRET_KEY_BASE generieren (mind. 64 Zeichen)
openssl rand -base64 48
# Beispiel-Output: kR3x7Q8z...lM2nP5v= (64 Zeichen)

# TOTP_VAULT_KEY generieren (fuer 2FA-Verschluesselung)
openssl rand -base64 32
# Beispiel-Output: aB3cD4eF...gH5iJ6k=
```

#### Schritt 2: .env erstellen

```bash
cp stacks/plausible/.env.example stacks/plausible/.env
# Secrets eintragen (oder ueber Infisical verwalten)
```

#### Schritt 3: Deploy via Coolify

1. Oeffne Coolify > **Projects** > **New Resource** > **Docker Compose**.
2. Lade `stacks/plausible/docker-compose.yml` hoch.
3. Setze die Domain auf `plausible.example.com`.
4. Aktiviere HTTPS (Let's Encrypt).
5. Klicke **Deploy**.

#### Schritt 4: Admin-Account erstellen

Nach dem ersten Start erstellt Plausible automatisch keinen Admin-Account. Oeffne `https://plausible.example.com` und erstelle den ersten Account ueber das Web-Interface. Dieser Account wird automatisch zum Admin.

**Wichtig:** Setze `DISABLE_REGISTRATION=invite_only` oder `DISABLE_REGISTRATION=false` fuer den ersten Start. Nach der Erstellung des Admin-Accounts kann die Registrierung eingeschraenkt werden.

#### Schritt 5: Erste Website hinzufuegen

1. Nach dem Login klicke auf **Add a website**.
2. Gib die Domain ein: `example.com` (ohne `https://`).
3. Waehle die Zeitzone.
4. Klicke **Add snippet** fuer das Tracking-Script.

---

### 6. Tracking-Script einbinden

Das Plausible-Script ist extrem leichtgewichtig (~1.6 KB gzip) und blockiert weder das Rendering noch die Interaktivitaet. Es wird mit `defer` geladen und fuehrt sich nach dem DOM-Laden aus.

#### 6a. Astro

```astro
---
// src/layouts/BaseLayout.astro
// Plausible braucht KEINEN Consent-Banner!
// Einfach das Script einbinden und fertig.

interface Props {
  title: string;
}

const { title } = Astro.props;
---

<html lang="de">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>

    <!-- Plausible Analytics (cookie-frei, kein Consent noetig) -->
    <script
      defer
      data-domain="example.com"
      src="https://plausible.example.com/js/script.js"
    ></script>
  </head>
  <body>
    <slot />
  </body>
</html>
```

Fuer erweiterte Features (Outbound Links, File Downloads, Custom Events):

```astro
<!-- Erweitertes Script mit zusaetzlichen Modulen -->
<script
  defer
  data-domain="example.com"
  src="https://plausible.example.com/js/script.file-downloads.outbound-links.tagged-events.js"
></script>
```

Verfuegbare Script-Erweiterungen (kombinierbar im Dateinamen):

| Erweiterung          | Dateiname-Suffix          | Funktion                              |
|----------------------|---------------------------|---------------------------------------|
| Outbound Links       | `.outbound-links`         | Klicks auf externe Links tracken      |
| File Downloads       | `.file-downloads`         | Downloads von Dateien tracken         |
| Tagged Events        | `.tagged-events`          | Custom Events via CSS-Klassen         |
| Revenue Tracking     | `.revenue`                | Umsatz-Tracking bei Custom Events     |
| Hash-basiertes Routing | `.hash`                 | SPA-Routing mit Hash-URLs             |
| Page exclusions      | `data-exclude` Attribut   | Bestimmte Seiten ignorieren           |

#### 6b. Next.js

```tsx
// src/app/layout.tsx
import Script from 'next/script';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="de">
      <body>
        {children}

        {/* Plausible Analytics (cookie-frei, kein Consent noetig) */}
        <Script
          defer
          data-domain="app.example.com"
          src="https://plausible.example.com/js/script.js"
          strategy="afterInteractive"
        />
      </body>
    </html>
  );
}
```

##### Plausible als React-Hook (optional)

```typescript
// src/hooks/usePlausible.ts
/**
 * React-Hook fuer Plausible Custom Events.
 * Usage: const plausible = usePlausible();
 *        plausible('Signup', { props: { plan: 'premium' } });
 */
export function usePlausible() {
  return function plausible(
    eventName: string,
    options?: { props?: Record<string, string | number | boolean> }
  ) {
    if (typeof window !== 'undefined' && (window as any).plausible) {
      (window as any).plausible(eventName, options);
    }
  };
}
```

#### 6c. Statisches HTML

```html
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <title>My Page</title>
  <!-- Plausible Analytics -->
  <script defer data-domain="example.com"
    src="https://plausible.example.com/js/script.js"></script>
</head>
<body>
  <h1>Hello World</h1>
</body>
</html>
```

#### 6d. Mehrere Domains auf einer Seite

Falls eine Seite unter mehreren Domains erreichbar ist:

```html
<script defer
  data-domain="example.com,staging.example.com"
  src="https://plausible.example.com/js/script.js"></script>
```

#### 6e. Bestimmte Seiten ausschliessen

```html
<script defer
  data-domain="example.com"
  data-exclude="/admin/*, /internal/*"
  src="https://plausible.example.com/js/script.js"></script>
```

---

### 7. Custom Events

#### Goals definieren

Custom Events muessen zuerst als "Goals" in Plausible registriert werden:

1. Oeffne Plausible > **Settings** > **Goals**.
2. Klicke **Add Goal**.
3. Waehle **Custom Event**.
4. Gib den Event-Namen ein (z.B. `Signup`).
5. Optional: Definiere Custom Properties (z.B. `plan`, `source`).

#### Events senden (JavaScript)

```javascript
// Einfacher Event (ohne Properties)
plausible('Signup');

// Event mit Properties
plausible('Signup', {
  props: {
    plan: 'premium',
    source: 'hero-cta',
  },
});

// Event mit Revenue-Tracking
// (Script-Erweiterung .revenue erforderlich)
plausible('Purchase', {
  revenue: {
    currency: 'EUR',
    amount: 49.99,
  },
  props: {
    product: 'Annual Plan',
  },
});

// 404-Seiten tracken
// Fuege dieses Script auf deiner 404-Seite hinzu:
plausible('404', {
  props: {
    path: document.location.pathname,
  },
});
```

#### Tagged Events (ueber CSS-Klassen)

Mit der `.tagged-events` Script-Erweiterung koennen Events direkt in HTML definiert werden, ohne JavaScript zu schreiben:

```html
<!-- Button-Klick als Event tracken -->
<button class="plausible-event-name=Signup plausible-event-plan=premium">
  Jetzt registrieren
</button>

<!-- Link-Klick als Event tracken -->
<a
  href="/download/whitepaper.pdf"
  class="plausible-event-name=Download plausible-event-document=whitepaper"
>
  Whitepaper herunterladen
</a>

<!-- Formular-Submit als Event tracken -->
<form class="plausible-event-name=ContactForm">
  <input type="email" name="email" />
  <button type="submit">Absenden</button>
</form>
```

#### Outbound Link Tracking

Mit der `.outbound-links` Script-Erweiterung werden Klicks auf externe Links automatisch getrackt. Es muss kein Goal definiert werden. Der Event heisst `Outbound Link: Click` und die Property `url` enthaelt die Ziel-URL.

#### File Download Tracking

Mit der `.file-downloads` Script-Erweiterung werden Downloads automatisch getrackt. Unterstuetzte Dateitypen: `.pdf`, `.xlsx`, `.docx`, `.txt`, `.rtf`, `.csv`, `.exe`, `.key`, `.pptx`, `.7z`, `.pkg`, `.rar`, `.gz`, `.zip`, `.avi`, `.mov`, `.mp4`, `.mpeg`, `.wmv`, `.midi`, `.mp3`, `.wav`, `.wma`.

#### Typische Custom Events fuer eine Website

| Event-Name            | Properties                      | Wann tracken                       |
|-----------------------|---------------------------------|------------------------------------|
| `Signup`              | `plan`, `source`                | Benutzer erstellt Account          |
| `Download`            | `document`, `format`            | Datei-Download                     |
| `Purchase`            | `product`, `plan` + Revenue     | Kauf abgeschlossen                 |
| `Newsletter`          | `source`                        | Newsletter-Anmeldung               |
| `ContactForm`         | `subject`                       | Kontaktformular abgesendet         |
| `CTA_Click`           | `button`, `page`                | Call-to-Action geklickt            |
| `Search`              | `query`                         | Suche ausgefuehrt                  |
| `VideoPlay`           | `title`, `duration`             | Video abgespielt                   |
| `404`                 | `path`                          | Nicht-gefundene Seite besucht      |

---

### 8. API

Plausible bietet zwei APIs: die **Stats API** (Daten abfragen) und die **Sites API** (Sites verwalten).

#### API-Key erstellen

1. Oeffne Plausible > **Settings** > **API Keys**.
2. Klicke **Create API Key**.
3. Kopiere den Key (wird nur einmal angezeigt).

#### Stats API: Daten abfragen

```bash
# Basis-URL fuer alle API-Aufrufe
PLAUSIBLE_URL="https://plausible.example.com"
API_KEY="plausible-api-key-here"

# --- Aktuelle Besucher (Realtime) ---
curl -s "${PLAUSIBLE_URL}/api/v1/stats/realtime/visitors?site_id=example.com" \
  -H "Authorization: Bearer ${API_KEY}"
# Antwort: 42

# --- Aggregierte Statistiken (heute) ---
curl -s "${PLAUSIBLE_URL}/api/v1/stats/aggregate?site_id=example.com&period=day&metrics=visitors,pageviews,bounce_rate,visit_duration" \
  -H "Authorization: Bearer ${API_KEY}"
# Antwort:
# {
#   "results": {
#     "visitors": {"value": 1523},
#     "pageviews": {"value": 4210},
#     "bounce_rate": {"value": 42},
#     "visit_duration": {"value": 185}
#   }
# }

# --- Top-Seiten (letzte 30 Tage) ---
curl -s "${PLAUSIBLE_URL}/api/v1/stats/breakdown?site_id=example.com&period=30d&property=event:page&limit=10&metrics=visitors,pageviews" \
  -H "Authorization: Bearer ${API_KEY}"

# --- Besucher nach Land ---
curl -s "${PLAUSIBLE_URL}/api/v1/stats/breakdown?site_id=example.com&period=month&property=visit:country&limit=10" \
  -H "Authorization: Bearer ${API_KEY}"

# --- Traffic-Quellen ---
curl -s "${PLAUSIBLE_URL}/api/v1/stats/breakdown?site_id=example.com&period=month&property=visit:source&limit=10" \
  -H "Authorization: Bearer ${API_KEY}"

# --- Conversion-Rate fuer ein Goal ---
curl -s "${PLAUSIBLE_URL}/api/v1/stats/aggregate?site_id=example.com&period=month&metrics=visitors,events&filters=event:goal==Signup" \
  -H "Authorization: Bearer ${API_KEY}"

# --- Timeseries (Besucher pro Tag, letzte 30 Tage) ---
curl -s "${PLAUSIBLE_URL}/api/v1/stats/timeseries?site_id=example.com&period=30d&metrics=visitors,pageviews" \
  -H "Authorization: Bearer ${API_KEY}"
```

#### Sites API: Websites verwalten

```bash
# --- Alle Sites auflisten ---
curl -s "${PLAUSIBLE_URL}/api/v1/sites" \
  -H "Authorization: Bearer ${API_KEY}"

# --- Neue Site anlegen ---
curl -s "${PLAUSIBLE_URL}/api/v1/sites" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"domain": "new-site.example.com", "timezone": "Europe/Berlin"}'

# --- Site loeschen ---
curl -s -X DELETE "${PLAUSIBLE_URL}/api/v1/sites/old-site.example.com" \
  -H "Authorization: Bearer ${API_KEY}"

# --- Shared Link erstellen (fuer oeffentliche Dashboards) ---
curl -s "${PLAUSIBLE_URL}/api/v1/sites/shared-links" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"site_id": "example.com", "name": "Public Dashboard"}'
```

#### API in n8n Workflows

Plausible-API-Daten koennen in n8n fuer automatisierte Reports verwendet werden:

```
n8n Workflow: "Weekly Analytics Report"

1. [Cron Trigger] -- Montag 09:00 Uhr
2. [HTTP Request] -- GET ${PLAUSIBLE_URL}/api/v1/stats/aggregate
                     ?site_id=example.com
                     &period=7d
                     &metrics=visitors,pageviews,bounce_rate
3. [HTTP Request] -- GET ${PLAUSIBLE_URL}/api/v1/stats/breakdown
                     ?site_id=example.com
                     &period=7d
                     &property=event:page
                     &limit=5
4. [Set Node] -- Format the data as readable text
5. [Slack / Email] -- Send weekly report

Ergebnis: Jeden Montag automatisch ein Bericht mit
  - Besucher letzte Woche
  - Top 5 Seiten
  - Bounce Rate
  - Vergleich zur Vorwoche
```

---

### 9. Plausible + PostHog Together

#### Architektur: Paralleler Betrieb

```
+------------------+                  +------------------+
| Marketing-Site   |                  | Web-App          |
| (Astro)          |                  | (Next.js)        |
+--------+---------+                  +--------+---------+
         |                                     |
         | Plausible Script (1.6 KB)           | Plausible Script (1.6 KB)
         | (kein Consent noetig)               | + PostHog SDK (45 KB)
         |                                     | (mit Consent-Banner)
         |                                     |
+--------v---------+               +----------v---------+
|   Plausible      |               |   Plausible        |
| (Pageviews,      |               | (Pageviews)        |
|  Referrers,      |               |                    |
|  Countries)      |               |   PostHog          |
+------------------+               | (Funnels, Sessions,|
                                   |  Heatmaps, A/B)    |
                                   +--------------------+
```

#### Entscheidungsmatrix: Wann welches Dashboard oeffnen?

| Frage                                           | Tool      |
|-------------------------------------------------|-----------|
| Wie viele Besucher hatten wir gestern?          | Plausible |
| Woher kommen unsere Besucher?                   | Plausible |
| Welche Seiten sind am beliebtesten?             | Plausible |
| Wie hoch ist die Bounce Rate?                   | Plausible |
| Welche Suchbegriffe bringen Traffic?            | Plausible |
| Wo brechen Benutzer im Signup-Flow ab?          | PostHog   |
| Welche Version des CTAs konvertiert besser?     | PostHog   |
| Was hat der Benutzer vor dem Fehler getan?      | PostHog   |
| Welches Feature wird am meisten genutzt?        | PostHog   |
| Wie verhaelt sich Kohorte A vs Kohorte B?       | PostHog   |

#### Integration in Code

```astro
---
// Layout fuer Marketing-Site: nur Plausible
---
<html>
  <head>
    <!-- Plausible: cookie-frei, kein Consent -->
    <script defer data-domain="example.com"
      src="https://plausible.example.com/js/script.js"></script>
  </head>
  <body><slot /></body>
</html>
```

```tsx
// Layout fuer Web-App: Plausible + PostHog
// Plausible braucht keinen Consent, PostHog schon

import Script from 'next/script';
import { ConsentBanner } from '@/components/ConsentBanner';

export default function AppLayout({ children }) {
  return (
    <html lang="de">
      <body>
        {children}

        {/* Plausible: immer aktiv (cookie-frei) */}
        <Script
          defer
          data-domain="app.example.com"
          src="https://plausible.example.com/js/script.js"
        />

        {/* PostHog: nur nach Consent */}
        <ConsentBanner />
      </body>
    </html>
  );
}
```

#### Kein Daten-Duplizierungsproblem

Plausible und PostHog verwenden unterschiedliche Datenmodelle und zaehlen Besucher unterschiedlich:

| Aspekt                   | Plausible                          | PostHog                          |
|--------------------------|------------------------------------|----------------------------------|
| Besucher-ID              | Taeglicher Hash (IP + UA)          | Persistent (Cookie/localStorage) |
| Neuer Besucher           | Jeden Tag neu                      | Bis Cookie geloescht wird        |
| Pageview-Zaehlung        | Identisch                          | Identisch                        |
| Session-Definition       | 30 Min. Inaktivitaet               | Konfigurierbar                   |
| Unique Visitors (Monat)  | Geschaetzt (taegliche Hashes)      | Exakt (persistente ID)           |

Die Zahlen werden **leicht** unterschiedlich sein. Das ist normal und erwartbar. Plausible-Zahlen sind typischerweise etwas hoeher, da jeder Tag als neuer Besucher zaehlt.

---

### 10. Google Search Console Integration

Plausible kann Suchbegriffe aus der Google Search Console importieren und direkt im Dashboard anzeigen. Das ist ein grosser Vorteil gegenueber reinem Pageview-Tracking, da du siehst, mit welchen Suchbegriffen Besucher deine Seite finden.

#### Voraussetzungen

1. Google Search Console Account mit verifizierter Site.
2. Google Cloud Console Projekt mit OAuth 2.0 Credentials.
3. Search Console API aktiviert.

#### Schritt 1: Google Cloud Projekt konfigurieren

1. Oeffne [Google Cloud Console](https://console.cloud.google.com).
2. Erstelle ein neues Projekt oder waehle ein bestehendes.
3. Aktiviere die **Google Search Console API**:
   - APIs & Services > Library > "Search Console API" suchen > Enable.
4. Erstelle OAuth 2.0 Credentials:
   - APIs & Services > Credentials > Create Credentials > OAuth Client ID.
   - Application type: **Web application**.
   - Authorized redirect URIs: `https://plausible.example.com/auth/google/callback`.
5. Kopiere **Client ID** und **Client Secret**.

#### Schritt 2: Credentials in Plausible konfigurieren

Setze die Umgebungsvariablen (`.env` oder Infisical):

```bash
PLAUSIBLE_GOOGLE_CLIENT_ID=123456789-abcdef.apps.googleusercontent.com
PLAUSIBLE_GOOGLE_CLIENT_SECRET=GOCSPX-abcdefghijk
```

#### Schritt 3: In Plausible verknuepfen

1. Oeffne Plausible > **Settings** > **Search Console**.
2. Klicke **Connect Google Account**.
3. Melde dich mit deinem Google-Account an und erlaube den Zugriff.
4. Waehle die korrekte Search Console Property aus.
5. Suchbegriffe erscheinen ab sofort im Dashboard unter "Search Terms".

---

### 11. DSGVO Deep Dive

#### Warum Plausible keinen Consent-Banner braucht

Plausible ist so konzipiert, dass es unter die Ausnahme fuer "technisch notwendige" bzw. "analytisch berechtigte" Verarbeitung faellt (Art. 6(1)(f) DSGVO -- berechtigtes Interesse). Hier ist die detaillierte Analyse:

#### Keine Cookies

Plausible setzt keine Cookies. Ueberhaupt keine. Weder First-Party noch Third-Party. Das Script schreibt weder in `document.cookie`, noch in `localStorage`, noch in `sessionStorage`, noch in `IndexedDB`.

#### Keine persistenten Identifikatoren

Plausible identifiziert Besucher ueber einen taeglichen Hash:

```
hash = SHA-256(
  website_domain +
  IP_address +
  User_Agent +
  daily_salt            // Aendert sich jeden Tag
)
```

Dieser Hash wird:
- **Nie gespeichert.** Er wird nur zum Zeitpunkt des Requests berechnet.
- **Nie an den Browser zurueckgesendet.**
- **Taeglich ungueltig.** Der Salt rotiert um Mitternacht.
- **Nicht umkehrbar.** Aus dem Hash kann die IP-Adresse nicht rekonstruiert werden.

#### IP-Adressen werden nicht gespeichert

IP-Adressen werden fuer die Geolocation verwendet (Land, Region, Stadt), aber **nie in der Datenbank gespeichert**. Der Ablauf:

```
1. Request kommt rein mit IP 203.0.113.42
2. IP -> GeoIP-Lookup -> "Germany, Berlin"
3. "Germany, Berlin" wird gespeichert
4. IP wird VERWORFEN (nicht in DB, nicht in Logs)
```

#### Keine Profilbildung

Plausible speichert keine individuellen Besucherprofile. Alle Daten sind aggregiert:

| Was Plausible speichert           | Was Plausible NICHT speichert  |
|-----------------------------------|-------------------------------|
| "Seite X hatte 150 Besucher"     | "Besucher A war auf Seite X"  |
| "42% der Besucher aus DE"        | "IP 203.x war aus DE"        |
| "Bounce Rate: 38%"               | "Besucher B hat 1 Seite besucht" |
| "Firefox: 23% der Besucher"      | "User-Agent von Besucher C"  |

#### Rechtsgrundlage: Berechtigtes Interesse (Art. 6(1)(f))

Die ePrivacy-Richtlinie (Art. 5(3)) und die DSGVO erlauben die Verarbeitung ohne Einwilligung, wenn:

1. **Keine Cookies gesetzt werden** -- erfuellt.
2. **Keine persistenten Identifikatoren verwendet werden** -- erfuellt (taeglicher Hash).
3. **Die Verarbeitung fuer den berechtigten Betrieb notwendig ist** -- Web-Analytics ist ein anerkanntes berechtigtes Interesse.
4. **Die Rechte der Betroffenen nicht ueberwiegen** -- da keine personenbezogenen Daten gespeichert werden, ist der Eingriff minimal.

#### Vergleich mit Google Analytics

| Aspekt                       | Plausible              | Google Analytics 4       |
|------------------------------|------------------------|--------------------------|
| Cookies                      | Keine                  | Ja (_ga, _gid, etc.)     |
| Consent-Banner               | Nicht noetig           | Immer noetig             |
| IP-Speicherung               | Nie                    | Ja (anonymisiert)        |
| Daten an Dritte              | Nie (self-hosted)      | Ja (Google-Server, USA)  |
| User-Tracking (Cross-Session)| Nein                   | Ja                       |
| DSGVO-konform ohne Config    | Ja                     | Nein                     |
| Datentransfer in Drittlaender| Nein                   | Ja (USA, Schrems II)     |

#### Datenschutzerklaerung: Textbaustein fuer Plausible

Fuege folgenden Abschnitt zu deiner Datenschutzerklaerung hinzu:

```
Webanalyse mit Plausible Analytics

Wir verwenden Plausible Analytics, eine datenschutzfreundliche
Web-Analyse-Software. Plausible setzt keine Cookies und speichert
keine personenbezogenen Daten. Es werden keine IP-Adressen
gespeichert und kein Cross-Site- oder Cross-Device-Tracking
durchgefuehrt.

Die erhobenen Daten (Seitenaufrufe, Verweisquellen, verwendete
Browser und Betriebssysteme, Laender) werden ausschliesslich in
aggregierter Form verarbeitet. Ein Rueckschluss auf einzelne
Personen ist nicht moeglich.

Die Verarbeitung erfolgt auf Grundlage unseres berechtigten
Interesses an der statistischen Auswertung des Nutzerverhaltens
zu Optimierungszwecken gemaess Art. 6 Abs. 1 lit. f DSGVO.

Plausible Analytics wird auf unseren eigenen Servern betrieben.
Es findet keine Datenuebermittlung an Dritte oder in
Drittlaender statt.

Weitere Informationen: https://plausible.io/data-policy
```

---

### 12. Monitoring & Backup

#### Uptime Kuma Monitor

Richte einen Monitor in Uptime Kuma ein, um die Verfuegbarkeit von Plausible zu ueberwachen:

```
Monitor-Typ: HTTP(s)
URL: https://plausible.example.com/api/health
Methode: GET
Erwarteter Status: 200
Intervall: 60 Sekunden
Retry: 3
Benachrichtigung: Slack / E-Mail
```

#### ClickHouse-Monitor

```
Monitor-Typ: HTTP(s)
URL: http://toolbox-plausible-clickhouse:8123/ping
Methode: GET
Erwarteter Status: 200 (Antwort: "Ok.\n")
Intervall: 60 Sekunden
Hinweis: Nur intern erreichbar (kein oeffentlicher Endpoint)
```

#### Backup-Strategie

Plausible-Daten muessen an zwei Stellen gesichert werden:

##### PostgreSQL (Konfigurationsdaten)

PostgreSQL wird bereits ueber das Toolbox-Backup gesichert (siehe [17-restic-backups.md](17-restic-backups.md)). Falls ein separates Backup noetig ist:

```bash
# PostgreSQL-Dump fuer Plausible
docker exec toolbox-postgres pg_dump -U plausible -d plausible \
  | gzip > plausible_postgres_$(date +%Y%m%d).sql.gz
```

##### ClickHouse (Event-Daten)

```bash
# ClickHouse-Backup (nur Plausible-Daten)
docker exec toolbox-plausible-clickhouse clickhouse-client \
  --query "SELECT * FROM plausible_events.events FORMAT Native" \
  > plausible_events_$(date +%Y%m%d).native

# Oder als komprimiertes Backup des gesamten Datenverzeichnisses:
docker stop toolbox-plausible-clickhouse
tar -czf plausible_clickhouse_data_$(date +%Y%m%d).tar.gz \
  /var/lib/docker/volumes/toolbox_plausible_clickhouse_data/_data/
docker start toolbox-plausible-clickhouse
```

##### Automatisiertes Backup mit Restic

Fuege die Plausible-Volumes zum bestehenden Restic-Backup hinzu:

```bash
# In der Restic-Backup-Konfiguration (z.B. restic-backup.sh):
# PostgreSQL wird bereits gesichert.
# ClickHouse-Daten-Volume hinzufuegen:
restic backup \
  /var/lib/docker/volumes/toolbox_plausible_clickhouse_data/
```

#### Grafana Dashboard fuer Plausible

Der Plausible-Container exportiert keine Prometheus-Metriken nativ. Aber du kannst die Plausible Stats API in Grafana verwenden:

1. Installiere das **JSON API** Datasource Plugin in Grafana.
2. Konfiguriere eine neue Datenquelle:
   - Typ: **JSON API**
   - URL: `http://toolbox-plausible:8000/api/v1/stats`
   - Custom Headers: `Authorization: Bearer <API_KEY>`
3. Erstelle Dashboard-Panels:

| Panel                            | API-Abfrage                                                   |
|----------------------------------|---------------------------------------------------------------|
| Aktuelle Besucher (Realtime)     | `/realtime/visitors?site_id=example.com`                      |
| Besucher heute                   | `/aggregate?site_id=example.com&period=day&metrics=visitors`  |
| Pageviews heute                  | `/aggregate?site_id=example.com&period=day&metrics=pageviews` |
| Bounce Rate (7 Tage)             | `/aggregate?site_id=example.com&period=7d&metrics=bounce_rate`|
| Besucher-Trend (30 Tage)        | `/timeseries?site_id=example.com&period=30d&metrics=visitors` |

---

### 13. Troubleshooting

#### Script wird von Ad-Blockern geblockt

Ad-Blocker (uBlock Origin, AdGuard, etc.) blockieren haeufig Plausible-Scripts, weil sie auf bekannten Analytics-Blocklisten stehen. Loesung: **Proxy das Script ueber deine eigene Domain.**

##### Option A: Proxy ueber Next.js (rewrites)

```javascript
// next.config.js
module.exports = {
  async rewrites() {
    return [
      {
        source: '/js/analytics.js',
        destination: 'https://plausible.example.com/js/script.js',
      },
      {
        source: '/api/event',
        destination: 'https://plausible.example.com/api/event',
      },
    ];
  },
};
```

Dann im HTML:

```html
<script defer data-domain="example.com"
  data-api="/api/event"
  src="/js/analytics.js"></script>
```

##### Option B: Proxy ueber Nginx (falls Coolify Nginx verwendet)

```nginx
location = /js/analytics.js {
    proxy_pass https://plausible.example.com/js/script.js;
    proxy_set_header Host plausible.example.com;
    proxy_ssl_server_name on;
}

location = /api/event {
    proxy_pass https://plausible.example.com/api/event;
    proxy_set_header Host plausible.example.com;
    proxy_ssl_server_name on;
    proxy_buffering off;
}
```

##### Option C: Selbst-gehostetes Script

Da Plausible self-hosted ist, kannst du das Script auch direkt von deiner Domain ausliefern. Kopiere die Script-Datei und passe die API-URL an:

```bash
# Script herunterladen
curl -o public/js/data.js https://plausible.example.com/js/script.js

# Im Script die API-URL aendern (fuer self-hosted ist das bereits korrekt)
```

#### Keine Daten im Dashboard

1. **Script geladen?**
   Oeffne die Browser-Developer-Tools (F12) > Network. Suche nach `script.js`. Status muss 200 sein.

2. **Domain korrekt?**
   Das `data-domain` Attribut muss exakt mit der in Plausible registrierten Domain uebereinstimmen. Keine Protokolle (`https://`), keine Pfade (`/blog`).

   ```html
   <!-- RICHTIG -->
   <script data-domain="example.com" ...></script>

   <!-- FALSCH -->
   <script data-domain="https://example.com" ...></script>
   <script data-domain="www.example.com" ...></script>  <!-- wenn ohne www registriert -->
   ```

3. **CSP-Header blockieren?**
   Falls deine Seite Content Security Policy Header setzt, muss die Plausible-Domain erlaubt sein:

   ```
   Content-Security-Policy:
     script-src 'self' https://plausible.example.com;
     connect-src 'self' https://plausible.example.com;
   ```

4. **Plausible-Container laeuft?**
   ```bash
   docker ps | grep plausible
   docker logs toolbox-plausible --tail 50
   ```

5. **Plausible Health Check:**
   ```bash
   curl -s https://plausible.example.com/api/health
   # Erwartet: "ok"
   ```

#### ClickHouse-Fehler

1. **ClickHouse laeuft?**
   ```bash
   docker ps | grep plausible-clickhouse
   docker logs toolbox-plausible-clickhouse --tail 50
   ```

2. **ClickHouse Speicherplatz:**
   ```bash
   docker exec toolbox-plausible-clickhouse du -sh /var/lib/clickhouse/
   ```

3. **ClickHouse Memory:**
   ```bash
   docker stats toolbox-plausible-clickhouse --no-stream
   ```

4. **ClickHouse Connectivity:**
   ```bash
   docker exec toolbox-plausible wget -qO- http://plausible-events-db:8123/ping
   # Erwartet: "Ok.\n"
   ```

#### Plausible kann PostgreSQL nicht erreichen

```bash
# Pruefe ob PostgreSQL im toolbox-Netzwerk ist:
docker exec toolbox-plausible wget -qO- "http://postgres:5432" 2>&1 || echo "Port erreichbar"

# Pruefe die Datenbank:
docker exec toolbox-postgres psql -U plausible -d plausible -c "SELECT 1"
```

#### Migration von Google Analytics

Plausible unterstuetzt den Import von Google Analytics (UA und GA4) Daten:

1. Oeffne Plausible > **Settings** > **Imports & Exports**.
2. Klicke **Import from Google Analytics**.
3. Melde dich mit deinem Google-Account an.
4. Waehle die Google Analytics Property.
5. Waehle den Zeitraum fuer den Import.
6. Starte den Import (kann je nach Datenmenge Stunden dauern).

Importierte Daten:
- Pageviews und Besucher (historisch)
- Traffic-Quellen (Referrer)
- Laender und Geraete
- Seiten

**Nicht** importiert:
- Individuelle Benutzerprofile (Plausible speichert keine)
- E-Commerce-Daten
- Custom Dimensions

#### Plausible-Container startet nicht

Haeufigste Ursache: Die Datenbanken sind noch nicht bereit. Der Container wartet 10 Sekunden (siehe `command` in docker-compose), aber ClickHouse kann laenger brauchen.

```bash
# Logs pruefen:
docker logs toolbox-plausible 2>&1 | head -30

# Haeufige Fehler:
# "connection refused" -> ClickHouse oder PostgreSQL noch nicht bereit
# "database does not exist" -> PostgreSQL-Datenbank noch nicht angelegt
# "SECRET_KEY_BASE missing" -> Umgebungsvariable fehlt
```

Loesung: Container neu starten, nachdem ClickHouse und PostgreSQL healthy sind:

```bash
docker restart toolbox-plausible
```

---

### Checkliste: Plausible vollstaendig eingerichtet

- [ ] PostgreSQL-Datenbank `plausible` angelegt
- [ ] `stacks/plausible/docker-compose.yml` erstellt
- [ ] `stacks/plausible/configs/clickhouse-config.xml` erstellt
- [ ] `stacks/plausible/configs/clickhouse-user-config.xml` erstellt
- [ ] `.env` mit Secrets befuellt (`SECRET_KEY_BASE`, `TOTP_VAULT_KEY`)
- [ ] Stack via Coolify deployed
- [ ] Plausible-Container laeuft und ist healthy
- [ ] ClickHouse-Container laeuft und ist healthy
- [ ] Admin-Account erstellt und eingeloggt
- [ ] Erste Website hinzugefuegt
- [ ] Tracking-Script in mindestens einer Website eingebunden
- [ ] Pageviews erscheinen im Plausible-Dashboard
- [ ] MaxMind GeoIP konfiguriert (Laender-Daten sichtbar)
- [ ] Custom Events definiert und getestet (mindestens ein Goal)
- [ ] Uptime Kuma Monitor eingerichtet
- [ ] Backup fuer PostgreSQL und ClickHouse verifiziert
- [ ] Datenschutzerklaerung aktualisiert
- [ ] (Optional) Google Search Console verknuepft
- [ ] (Optional) Script-Proxy gegen Ad-Blocker eingerichtet
