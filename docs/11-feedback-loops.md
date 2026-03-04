# 11 — Feedback-Loops

How to use customer feedback to automatically improve your software. This guide connects PostHog (analytics), Sentry (error tracking), Unleash (feature flags), and Grafana (dashboards) into a continuous feedback pipeline.

> **Prerequisites:** Your project must have PostHog, Sentry, and Unleash configured. See [10-project-workflow.md](10-project-workflow.md) for setup steps.

---

## 1. Feedback-Quellen

Every project collects feedback from six sources. Each source feeds into a different part of the improvement cycle.

### In-App Feedback (PostHog Surveys)

PostHog surveys let you ask users questions directly inside your app. Use them for NPS scores, feature satisfaction, and open-ended feedback.

```typescript
// Trigger a survey after a user completes onboarding
posthog.capture('onboarding_completed', {
  plan: 'pro',
  onboarding_duration_seconds: 180,
});
// PostHog survey is configured to show when 'onboarding_completed' fires
```

### Error Reports (Sentry)

Sentry automatically captures every unhandled exception, crash, and API error. Each error includes the stack trace, browser/device info, and the user's session context.

```typescript
// Add user context so Sentry can group errors by user
Sentry.setUser({ id: user.id, plan: user.plan });

// Add breadcrumbs for debugging context
Sentry.addBreadcrumb({
  category: 'ui.click',
  message: 'User clicked "Upgrade Plan"',
  level: 'info',
});
```

### Usage Analytics (PostHog)

PostHog captures how users actually behave: which pages they visit, where they drop off, what features they use, and how long they stay.

Key analytics features:
- **Funnels**: Where do users drop off in multi-step flows?
- **Retention**: Do users come back after their first visit?
- **Heatmaps**: Where do users click on each page?
- **Session recordings**: Watch real user sessions (consent required).

### Kundengespraeche

Customer calls and interviews are the richest feedback source. Record them (with consent), transcribe with Whisper, and extract structured insights.

See [13-voice-interface.md](13-voice-interface.md) for the transcription and analysis tool.

### Support-Tickets

Tickets from email, chat, or support forms. Link each ticket to a Sentry issue when the ticket is about a bug:

```markdown
## Support Ticket #1234
**User:** user@example.com
**Issue:** Cannot save payment method
**Sentry Link:** https://sentry.example.com/issues/5678/
**PostHog Session:** https://posthog.example.com/replay/abc123
```

### NPS Scores (PostHog Surveys)

Net Promoter Score surveys measure overall satisfaction. Set up a recurring NPS survey in PostHog:

```
How likely are you to recommend [product] to a friend?
[0] [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
```

PostHog automatically calculates your NPS score and segments responses into Promoters (9-10), Passives (7-8), and Detractors (0-6).

---

## 2. Automatische Feedback-Pipeline

All feedback sources flow into a single pipeline that drives decisions:

```
Customer Action
    │
    ├──→ PostHog Event ──→ Analytics Dashboard ──→ Insight ──→ Prioritize
    │         │
    │         ├──→ Funnel Drop-off Detected ──→ Session Recording ──→ UX Fix
    │         │
    │         └──→ Feature Flag Experiment ──→ A/B Test Result ──→ Ship or Revert
    │
    ├──→ Sentry Error ──→ Alert (Slack/Discord) ──→ Developer ──→ Fix Bug
    │         │
    │         └──→ Release Health Check ──→ Auto-revert (via feature flag)
    │
    ├──→ Survey Response ──→ PostHog Dashboard ──→ Trend Analysis
    │
    ├──→ Support Ticket ──→ Link to Sentry Issue ──→ Prioritize by User Count
    │
    └──→ Customer Call ──→ Whisper Transcription ──→ Tag Insights ──→ Backlog
```

**The key principle:** Every piece of feedback must be traceable to an action. No feedback disappears into a void.

---

## 3. PostHog fuer automatisiertes Feedback

### 3.1 Surveys einrichten (In-App-Feedback)

Create surveys in PostHog to collect feedback at the right moment:

```bash
# Create a survey via PostHog API
curl -s -X POST "https://posthog.example.com/api/projects/@current/surveys/" \
  -H "Authorization: Bearer $POSTHOG_PERSONAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Post-Checkout Satisfaction",
    "type": "popover",
    "questions": [
      {
        "type": "rating",
        "question": "How was your checkout experience?",
        "display": "emoji",
        "scale": 5
      },
      {
        "type": "open",
        "question": "What could we improve?"
      }
    ],
    "conditions": {
      "url": "*/checkout/success*"
    },
    "targeting_flag_filters": {
      "groups": [
        {
          "properties": [
            {"key": "completed_purchase", "value": true}
          ]
        }
      ]
    }
  }' | jq .
```

**Best practices:**
- Trigger surveys based on specific events, not randomly.
- Keep surveys short (1-2 questions maximum).
- Use rating questions for quantitative data, open questions for qualitative.
- Set a frequency cap so users are not asked too often (PostHog handles this).

### 3.2 Funnels einrichten (Wo Nutzer abspringen)

Define funnels for every critical user journey. Example for an e-commerce checkout:

```
Step 1: View Product      → event: 'product_viewed'
Step 2: Add to Cart       → event: 'product_added_to_cart'
Step 3: Start Checkout    → event: 'checkout_started'
Step 4: Enter Payment     → event: 'payment_entered'
Step 5: Complete Purchase  → event: 'purchase_completed'
```

Set up these events in your code:

```typescript
// Track funnel events with consistent properties
posthog.capture('product_viewed', {
  product_id: product.id,
  product_name: product.name,
  price: product.price,
  category: product.category,
});

posthog.capture('product_added_to_cart', {
  product_id: product.id,
  cart_value: cart.total,
});

posthog.capture('checkout_started', {
  cart_value: cart.total,
  item_count: cart.items.length,
});
```

In PostHog, create the funnel under **Insights** > **New Insight** > **Funnel**. Add each event as a step. PostHog will show the conversion rate between each step and highlight where users drop off.

### 3.3 Session Recordings (Was Nutzer wirklich tun)

Session recordings are the most powerful debugging tool for UX issues, but they require user consent under DSGVO.

**Enable only after consent:**

```typescript
function onConsentGranted() {
  posthog.set_config({
    persistence: 'localStorage+cookie',
    disable_session_recording: false,
  });
  posthog.opt_in_capturing();
  posthog.startSessionRecording();
}

function onConsentRevoked() {
  posthog.opt_out_capturing();
  posthog.set_config({
    disable_session_recording: true,
    persistence: 'memory',
  });
}
```

**Privacy safeguards:**
- PostHog automatically masks password fields.
- Add `ph-no-capture` class to sensitive elements to exclude them from recordings.
- Set a data retention policy in PostHog settings (e.g., 30 days).

```html
<!-- Exclude sensitive content from session recordings -->
<div class="ph-no-capture">
  <p>User's private medical information here</p>
</div>
```

### 3.4 Feature-Flag-Experimente (A/B-Tests)

Run A/B tests by combining Unleash feature flags with PostHog analytics:

```typescript
// 1. Check the feature flag
const variant = useFlag('new-pricing-page');

// 2. Track which variant the user sees
posthog.capture('pricing_page_viewed', {
  variant: variant ? 'new' : 'control',
});

// 3. Track the conversion event
posthog.capture('plan_selected', {
  variant: variant ? 'new' : 'control',
  plan: selectedPlan.name,
  price: selectedPlan.price,
});
```

In PostHog, create an **Experiment** insight that compares the conversion rate of `plan_selected` between users with `variant: 'new'` and `variant: 'control'`. PostHog calculates statistical significance automatically.

### 3.5 Kohortenanalyse (Welche Nutzergruppen Probleme haben)

Create cohorts in PostHog to segment users by behavior:

- **Power users**: completed > 10 actions in the last 7 days.
- **At-risk users**: active last month but not this month.
- **Error-prone users**: appeared in 3+ Sentry issues.
- **Free trial users**: signed up in the last 14 days, no purchase.

Use cohorts to filter dashboards, funnels, and session recordings. This reveals which user segments have the worst experience.

---

## 4. Sentry als Feedback-Quelle

Sentry is not just an error tracker. It is a direct feedback channel that tells you what is broken, for how many users, and since which release.

### 4.1 Error Trends: Welche Bugs betreffen die meisten Nutzer

In Sentry, go to **Issues** and sort by **Events** (descending). The top issues are the bugs affecting the most users.

Set up an alert for high-impact errors:

```bash
# Sentry alert rule: notify when an issue affects > 100 users in 1 hour
# Configure this in Sentry UI: Alerts > Create Alert Rule
# Conditions:
#   - EventFrequency > 100 in 1 hour
# Actions:
#   - Send Slack notification to #errors
#   - Assign to on-call developer
```

### 4.2 Release Health: Hat das letzte Deployment etwas kaputt gemacht?

Configure Sentry releases so you can track error rates per deployment:

```bash
# In your CI/CD pipeline, create a Sentry release
VERSION=$(git rev-parse --short HEAD)

sentry-cli releases new "$VERSION"
sentry-cli releases set-commits "$VERSION" --auto

# After deployment:
sentry-cli releases deploys "$VERSION" new -e production

# Upload source maps (for JS/TS projects):
sentry-cli releases files "$VERSION" upload-sourcemaps ./dist \
  --url-prefix '~/_next/static/'

sentry-cli releases finalize "$VERSION"
```

In the Sentry UI, the **Releases** page shows crash-free session rates per release. If the latest release drops below your threshold (e.g., 99.5%), investigate immediately.

### 4.3 User Impact: Wie viele Nutzer trifft jeder Fehler

Sentry tracks "users affected" for each issue. Use this to prioritize bug fixes:

| Priority | Criteria                               | Action                          |
|----------|---------------------------------------|---------------------------------|
| P0       | > 10% of users affected               | Drop everything, fix now        |
| P1       | 1-10% of users affected               | Fix this sprint                 |
| P2       | < 1% of users affected                | Add to backlog                  |
| P3       | Rare or cosmetic errors               | Fix when convenient             |

### 4.4 Auto-Assign: Fehler an zustaendige Entwickler routen

Configure Sentry code owners to automatically assign errors to the developer who owns the file:

Create a `CODEOWNERS` file in your repository:

```
# .github/CODEOWNERS
/src/auth/**       @alice
/src/payments/**   @bob
/src/ui/**         @carol
/api/**            @dave
```

In Sentry, enable **Code Owners** integration under **Settings** > **Integrations** > **GitHub**. Sentry will read the CODEOWNERS file and auto-assign issues to the responsible developer.

---

## 5. Feedback → Action Pipeline

This is the complete workflow from detecting a problem to shipping a fix.

### Schritt-fuer-Schritt

**Step 1: PostHog detects a drop-off in a funnel.**

You notice that the checkout funnel has a 40% drop-off between "Enter Payment" and "Complete Purchase". This was 15% last week.

**Step 2: Session recordings reveal the UX issue.**

Watch 5-10 session recordings of users who dropped off. You see that users on mobile are tapping the "Pay" button but nothing happens — there is a JavaScript error.

**Step 3: Cross-reference with Sentry.**

Search Sentry for errors on the checkout page in the last week. Find: `TypeError: Cannot read property 'stripe' of undefined` — 342 events, 289 users affected, started 3 days ago with release `v1.4.2`.

**Step 4: Create a GitHub issue with full context.**

```markdown
## Bug: Mobile checkout broken since v1.4.2

**Impact:** 289 users affected, checkout conversion dropped from 85% to 60%

**Evidence:**
- Sentry: https://sentry.example.com/issues/12345/
- PostHog funnel: https://posthog.example.com/insights/67890
- Session recordings: [link to filtered recordings]

**Root cause:** Stripe SDK not loading on mobile Safari due to CSP header change in v1.4.2.

**Fix:** Revert CSP change or add Stripe domain to CSP whitelist.
```

You can automate issue creation with a webhook (e.g., n8n or a simple script):

```bash
# Create GitHub issue from Sentry webhook via n8n or script
curl -s -X POST "https://api.github.com/repos/your-org/my-project/issues" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Bug: Mobile checkout broken since v1.4.2",
    "body": "**Sentry:** https://sentry.example.com/issues/12345/\n**Users affected:** 289\n**PostHog funnel:** checkout conversion dropped 25%",
    "labels": ["bug", "P0"]
  }'
```

**Step 5: Developer fixes behind a feature flag.**

```typescript
// Fix is gated behind a flag so it can be tested without affecting all users
const useNewStripeLoader = useFlag('fix-stripe-mobile-loading');

if (useNewStripeLoader) {
  // New approach: load Stripe SDK dynamically
  await loadStripe(process.env.NEXT_PUBLIC_STRIPE_KEY);
} else {
  // Old approach (broken on mobile)
  window.Stripe(process.env.NEXT_PUBLIC_STRIPE_KEY);
}
```

**Step 6: A/B test the fix.**

Enable the flag for 50% of users in production. In PostHog, compare the checkout funnel for users with and without the flag. The fix group should show higher conversion.

**Step 7: PostHog confirms improvement, enable for all.**

After 24 hours, PostHog shows:
- Flag ON: 84% checkout conversion (back to normal)
- Flag OFF: 60% checkout conversion (still broken)

Enable the flag for 100% of users.

**Step 8: Sentry confirms no new errors.**

Check Sentry: no new `TypeError` events related to Stripe since the flag was enabled. The fix is validated from both the user experience side (PostHog) and the technical side (Sentry).

**Step 9: Clean up.**

Remove the feature flag from code. Remove the old code path. Update the Sentry issue to resolved.

---

## 6. Kundengespraech-Analyse

Customer calls are qualitative feedback that complements the quantitative data from PostHog and Sentry.

### Workflow

```
1. Schedule customer call
    ↓
2. Record with consent (Zoom, Google Meet, or phone)
    ↓
3. Transcribe with Whisper (see docs/13-voice-interface.md)
    ↓
4. Extract structured insights
    ↓
5. Tag and categorize
    ↓
6. Feed into backlog as weighted input
```

### Automatische Kategorisierung

After transcription, automatically tag insights into categories:

| Tag              | Example Quote                                            |
|------------------|----------------------------------------------------------|
| `feature-request`| "It would be great if I could export data as CSV..."     |
| `bug-report`     | "Every time I click save, the page just goes blank..."   |
| `praise`         | "The new dashboard is exactly what I needed..."          |
| `confusion`      | "I don't understand what this button does..."            |
| `churn-risk`     | "We might switch to [competitor] because..."             |

### PostHog als Custom Events einspeisen

Feed structured call insights into PostHog so they appear alongside quantitative data:

```python
# After transcription and analysis, push insights to PostHog
import requests

def push_call_insight_to_posthog(insight: dict):
    """Send a customer call insight to PostHog as a custom event."""
    requests.post(
        "https://posthog.example.com/capture/",
        json={
            "api_key": POSTHOG_PROJECT_KEY,
            "event": "customer_call_insight",
            "distinct_id": insight["customer_id"],
            "properties": {
                "insight_type": insight["tag"],       # feature-request, bug, praise, etc.
                "summary": insight["summary"],
                "call_date": insight["date"],
                "sentiment": insight["sentiment"],     # positive, neutral, negative
                "product_area": insight["area"],       # onboarding, billing, dashboard, etc.
            },
        },
    )
```

Now in PostHog you can:
- Filter insights by type, sentiment, and product area.
- Correlate call feedback with usage data (do users who complained also have low retention?).
- Build a dashboard that combines quantitative metrics with qualitative themes.

---

## 7. Reporting

### 7.1 Woechentlicher automatischer Report

Set up a weekly report that combines data from all feedback sources. This can be a Grafana dashboard or an automated Slack message.

**Grafana Dashboard: "Weekly Feedback Summary"**

Create a dashboard in Grafana with these panels:

| Panel                        | Data Source    | Query / Description                                    |
|------------------------------|----------------|--------------------------------------------------------|
| Top 5 Sentry Errors          | Sentry API     | Issues sorted by event count this week                 |
| Checkout Funnel Conversion   | PostHog API    | Funnel completion rate trend (7 days)                  |
| NPS Score Trend              | PostHog API    | Weekly NPS from survey responses                       |
| Active Users (DAU/WAU)       | PostHog API    | Daily and weekly active user counts                    |
| Feature Flag Experiments     | Unleash API    | Active experiments and their current metrics           |
| Uptime Percentage            | Uptime Kuma    | Service availability this week                         |
| Customer Call Insights       | PostHog API    | Count of `customer_call_insight` events by tag         |

**Automated Slack Report (via script or n8n):**

```bash
#!/bin/bash
# weekly-report.sh - Run via cron every Monday at 9:00 AM
# Collects metrics from PostHog, Sentry, and Uptime Kuma, then posts to Slack.

WEEK=$(date -d 'last monday' +%Y-%m-%d)

# Get top Sentry errors
TOP_ERRORS=$(curl -s "https://sentry.example.com/api/0/projects/your-org/my-project/issues/?query=is:unresolved&sort=freq&limit=5" \
  -H "Authorization: Bearer $SENTRY_API_TOKEN" | \
  jq -r '.[] | "- \(.title) (\(.count) events, \(.userCount) users)"')

# Get PostHog key metric (example: weekly active users)
WAU=$(curl -s "https://posthog.example.com/api/projects/@current/insights/trend/" \
  -H "Authorization: Bearer $POSTHOG_PERSONAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"events": [{"id": "$pageview", "math": "weekly_active"}], "date_from": "-7d"}' | \
  jq -r '.result[0].aggregated_value')

# Post to Slack
curl -s -X POST "$SLACK_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "*Weekly Feedback Report ('$WEEK')*\n\n*Active Users:* '$WAU' WAU\n\n*Top Sentry Errors:*\n'"$TOP_ERRORS"'\n\n:grafana: <https://grafana.example.com/d/weekly-feedback|Full Dashboard>"
  }'
```

### 7.2 Monatliches Produkt-Review

Once a month, review all feedback data to decide what to build next:

**Agenda (60 minutes):**

1. **Quantitative Overview** (15 min)
   - PostHog: MAU trend, key funnel conversion rates, feature adoption percentages
   - Sentry: total error count trend, top 10 unresolved issues, crash-free rate
   - Uptime Kuma: monthly uptime percentage, incident count

2. **Qualitative Overview** (15 min)
   - Customer call themes: most requested features, most reported frustrations
   - NPS trend and detractor feedback
   - Support ticket themes

3. **Experiment Results** (15 min)
   - A/B test results from the month
   - Feature flags that were fully rolled out
   - Experiments that were reverted (and why)

4. **Prioritization for Next Month** (15 min)
   - Use the impact/effort matrix (see [10-project-workflow.md](10-project-workflow.md#43-priorisierung-impact-vs-effort))
   - Score each candidate based on: user impact (PostHog data), error impact (Sentry data), revenue impact, and effort estimate
   - Select items for the next sprint cycle

### 7.3 Grafana Dashboard fuer Feedback-Metriken

Create a dedicated Grafana dashboard that aggregates feedback metrics:

```json
{
  "dashboard": {
    "title": "Feedback Metrics",
    "panels": [
      {
        "title": "NPS Score (30-day rolling)",
        "type": "stat",
        "datasource": "PostHog"
      },
      {
        "title": "Error Rate by Release",
        "type": "timeseries",
        "datasource": "Sentry"
      },
      {
        "title": "Funnel Conversion Trend",
        "type": "timeseries",
        "datasource": "PostHog"
      },
      {
        "title": "Feature Requests by Area",
        "type": "piechart",
        "datasource": "PostHog"
      },
      {
        "title": "Service Uptime",
        "type": "gauge",
        "datasource": "Uptime Kuma"
      }
    ]
  }
}
```

Place the full dashboard JSON in `configs/grafana/provisioning/dashboards/json/feedback-metrics.json` and it will be auto-provisioned by Grafana.
