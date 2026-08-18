# Grafana Cloud — CMIS metrics

I3 wires Grafana to the existing M5 Prometheus text export. **The app does not need Grafana API keys.** Grafana Cloud pulls from the public `/metrics` URL.

## App endpoint

After deploy:

```
GET https://antern-deliverables.onrender.com/metrics
```

Returns Prometheus counters (`cmis_admissions_total`, `cmis_context_builds_total`, `cmis_context_abstentions_total`, …). No auth. Does not include memory content.

## Grafana Cloud setup (no keys in Render)

1. Open [Grafana Cloud](https://grafana.com/auth/sign-up/create-account) → your stack.
2. Add a **Prometheus** data source (Hosted Metrics is already in the stack), **or** create an HTTP scrape:
   - Connections → Add new connection → **HTTP Metrics** / **Prometheus** scrape target
   - URL: `https://antern-deliverables.onrender.com/metrics`
   - Scrape interval: `60s`
3. **Dashboards → New → Import** → paste `cmis-dashboard.json` from this folder.
4. Select the Prometheus data source you just configured.

## Optional: Grafana Cloud credentials (only if you later add remote write)

These are **Grafana-side**, not required for scrape:

| Field | Where |
|-------|--------|
| Stack URL | Grafana Cloud → stack details |
| Metrics username / instance ID | Grafana Cloud → Prometheus → Sending metrics |
| Cloud Access Policy token | Grafana Cloud → Access Policies |

Do **not** put those on the CMIS web service unless you add a remote-write sidecar later.

## PostHog (separate — does need Render env vars)

See the keys listed in `implementation/.env.example`. Grafana Cloud and PostHog are independent.

## Demo traffic (populate all panels)

Grafana stores **live scrapes**, not static JSON points. To fill every counter:

1. On Render, set `CMIS_RERANKER=off` and `CMIS_HYBRID_RETRIEVAL=0` (required for `/api/context` on free tier).
2. Run:

```powershell
cd Week-5/project/implementation
python scripts/seed_grafana_demo.py --delay-seconds 5
```

Traffic plan reference: `deploy/grafana/demo-traffic-plan.json` (~18 steps).

3. Re-import `cmis-dashboard.json` (version 2) or refresh the dashboard after 2–3 scrape intervals.
