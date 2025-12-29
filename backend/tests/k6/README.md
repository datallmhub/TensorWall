# K6 Load Tests for LLM Gateway

Performance and load testing suite using [k6](https://k6.io/).

## Installation

```bash
# macOS
brew install k6

# Linux
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# Docker
docker run --rm -i grafana/k6 run - <script.js
```

## Test Scripts

| Script | Purpose | Duration | VUs |
|--------|---------|----------|-----|
| `gateway-smoke.js` | Quick sanity check | 30s | 1 |
| `gateway-load.js` | Normal load testing | 9min | 50 |
| `gateway-stress.js` | Find breaking point | 26min | 100-300 |
| `gateway-spike.js` | Sudden traffic surge | 6min | 10→500→10 |

## Quick Start

```bash
# 1. Start the gateway locally
docker-compose up -d

# 2. Run smoke test (quick validation)
k6 run tests/k6/gateway-smoke.js

# 3. Run load test
k6 run tests/k6/gateway-load.js
```

## Environment Variables

```bash
# Target URL (default: http://localhost:8000)
k6 run -e BASE_URL=https://api.example.com tests/k6/gateway-smoke.js

# API Key for LLM requests
k6 run -e API_KEY=your-api-key tests/k6/gateway-load.js

# Full example
k6 run \
  -e BASE_URL=https://api.staging.example.com \
  -e API_KEY=test-key-123 \
  tests/k6/gateway-load.js
```

## Test Scenarios

### Smoke Test
Quick validation that all endpoints work.
```bash
k6 run tests/k6/gateway-smoke.js
```
- 1 virtual user
- 30 seconds
- Zero errors expected

### Load Test
Normal expected traffic pattern.
```bash
k6 run tests/k6/gateway-load.js
```
- Ramp up to 50 VUs over 2 minutes
- Steady state for 5 minutes
- Ramp down over 2 minutes

### Stress Test
Find the breaking point.
```bash
k6 run tests/k6/gateway-stress.js
```
- Progressive increase: 100 → 200 → 300 VUs
- Identifies capacity limits
- Monitors error rates

### Spike Test
Sudden traffic surge.
```bash
k6 run tests/k6/gateway-spike.js
```
- Normal: 10 VUs
- Spike: 500 VUs (10 seconds ramp)
- Measures recovery time

## Thresholds (SLOs)

| Metric | Target | Description |
|--------|--------|-------------|
| Gateway latency (p95) | < 50ms | Core proxy overhead |
| Gateway latency (p99) | < 100ms | Worst case overhead |
| Auth endpoints (p95) | < 200ms | Login, refresh |
| Admin endpoints (p95) | < 500ms | Dashboard API |
| Error rate | < 1% | Overall failures |
| Health check (p99) | < 50ms | Always fast |

## Output & Analysis

### Console Summary
```bash
k6 run tests/k6/gateway-load.js
```

### JSON Output
```bash
k6 run --out json=results.json tests/k6/gateway-load.js
```

### InfluxDB + Grafana
```bash
k6 run --out influxdb=http://localhost:8086/k6 tests/k6/gateway-load.js
```

### Cloud (k6 Cloud)
```bash
k6 cloud tests/k6/gateway-load.js
```

## CI/CD Integration

### GitHub Actions
```yaml
- name: Run k6 load test
  uses: grafana/k6-action@v0.3.1
  with:
    filename: tests/k6/gateway-smoke.js
  env:
    BASE_URL: ${{ secrets.STAGING_API_URL }}
    API_KEY: ${{ secrets.TEST_API_KEY }}
```

## Interpreting Results

### Good Results
```
✓ http_req_duration..............: avg=45ms   p(95)=48ms  p(99)=52ms
✓ http_req_failed................: 0.00%
✓ gateway_latency................: avg=12ms   p(95)=18ms
```

### Warning Signs
- `http_req_duration` p95 > 100ms → Gateway overhead too high
- `http_req_failed` > 1% → Stability issues
- `requests_blocked` increasing → Rate limiting kicking in
- Memory/CPU trending up → Potential leak

## Custom Metrics

| Metric | Description |
|--------|-------------|
| `gateway_latency` | Time spent in gateway (excluding LLM) |
| `policy_check_latency` | Policy evaluation time |
| `requests_blocked` | Rate-limited requests |
| `budget_exceeded` | Budget limit hits |
| `recovery_time` | Time to return to normal after spike |
