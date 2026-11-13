# Load testing

`load.js` is a [k6](https://k6.io) script that mimics real traffic: 50% anonymous visitors browsing properties and
hotels, 30% tenants opening their dashboard and invoices, 20% landlords checking their portfolio.

## Run it (against a staging server, never production)
1. On staging, raise the rate limits in `.env`, then `docker compose restart backend`:
   `THROTTLE_ANON=100000/hour  THROTTLE_USER=100000/hour  THROTTLE_LOGIN=1000/min`
2. Create one tenant and one landlord test account (the demo seed command is fine on staging).
3. Run:
   ```bash
   docker run --rm -i -e BASE_URL=https://staging-api.example.com -e PROFILE=load \
     -e LANDLORD_EMAIL=l@test.ke -e LANDLORD_PASSWORD=... -e TENANT_EMAIL=t@test.ke -e TENANT_PASSWORD=... \
     grafana/k6 run - < loadtest/load.js
   ```
   Profiles: `smoke` (check the script works) → `load` (ramp to 100 users) → `stress` (to 400) → `soak` (30 min steady).
4. Watch the server while it runs: `docker stats`, `docker compose logs -f backend`, and Postgres connections.

Pass marks (set in the script): under 1% failed requests, 95% of requests under 800 ms, dashboards under 1.2 s.
Note the test generates traffic from one machine: use a separate small server so your own laptop or the app server isn't the bottleneck.
