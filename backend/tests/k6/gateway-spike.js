// =============================================================================
// K6 Spike Test: Sudden Traffic Surge
// =============================================================================
// Run: k6 run tests/k6/gateway-spike.js
// Purpose: Test system behavior under sudden traffic spikes

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { BASE_URL, API_KEY, scenarios, randomAppId, randomModel, randomMessage } from './config.js';

// Custom metrics
const recoveryTime = new Trend('recovery_time', true);
const requestsDuringSpike = new Counter('requests_during_spike');
const errorsDuringSpike = new Counter('errors_during_spike');

export const options = {
  scenarios: {
    spike: scenarios.spike,
  },
  thresholds: {
    // During spike, allow higher latency but track recovery
    'http_req_duration': ['p(95)<2000'], // 2s max during spike
    'http_req_failed': ['rate<0.10'],     // Allow 10% errors during spike
  },
};

export function setup() {
  const jar = http.cookieJar();

  const loginRes = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({
      email: 'admin@example.com',
      password: 'admin123456',
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  // Extract cookies from jar and return as header format
  const cookies = jar.cookiesForURL(BASE_URL);
  const cookieHeader = Object.entries(cookies)
    .map(([name, value]) => `${name}=${value}`)
    .join('; ');

  return { cookieHeader };
}

export default function (data) {
  const startTime = Date.now();

  // Simulate realistic TensorWall usage
  const res = http.post(
    `${BASE_URL}/v1/chat/completions`,
    JSON.stringify({
      model: randomModel(),
      messages: [{ role: 'user', content: randomMessage() }],
      max_tokens: 30,
      contract: {
        app_id: randomAppId(),
        feature: 'chat-support',
        action: 'generate',
        environment: 'development',
      },
    }),
    {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
      timeout: '60s', // Longer timeout during spike
    }
  );

  const duration = Date.now() - startTime;
  requestsDuringSpike.add(1);

  const success = check(res, {
    'request handled': (r) => r.status !== 0, // Connection not refused
    'valid response': (r) => [200, 429, 503].includes(r.status),
  });

  if (!success || res.status >= 500) {
    errorsDuringSpike.add(1);
  }

  // Track recovery - if response time goes back to normal after spike
  if (duration < 100) {
    recoveryTime.add(duration);
  }

  // Minimal sleep to maximize pressure
  sleep(0.1);
}

export function teardown(data) {
  console.log('\n=== Spike Test Complete ===');
  console.log('Analyze recovery_time metric to see how quickly system recovered');
}
