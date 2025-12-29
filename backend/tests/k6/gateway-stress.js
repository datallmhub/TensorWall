// =============================================================================
// K6 Stress Test: Find Breaking Point
// =============================================================================
// Run: k6 run tests/k6/gateway-stress.js
// Purpose: Find the maximum capacity before degradation

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { BASE_URL, API_KEY, thresholds, scenarios, randomAppId, randomModel, randomMessage } from './config.js';

// Custom metrics
const requestsBlocked = new Counter('requests_blocked');
const budgetExceeded = new Counter('budget_exceeded');
const policyDenied = new Counter('policy_denied');
const p95Latency = new Trend('p95_latency', true);

export const options = {
  scenarios: {
    stress: scenarios.stress,
  },
  thresholds: {
    'http_req_duration': ['p(95)<500', 'p(99)<1000'],
    'http_req_failed': ['rate<0.05'], // Allow 5% errors under stress
    'requests_blocked': ['count<100'],
  },
};

export function setup() {
  // Verify system is up
  const healthRes = http.get(`${BASE_URL}/health`);
  if (healthRes.status !== 200) {
    throw new Error('System not healthy, aborting stress test');
  }

  const jar = http.cookieJar();

  // Login
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
  // Mix of operations with realistic weights
  const rand = Math.random();

  if (rand < 0.6) {
    // 60% - LLM requests (main workload)
    testLLMRequest();
  } else if (rand < 0.85) {
    // 25% - Admin read operations
    testAdminRead(data);
  } else if (rand < 0.95) {
    // 10% - Health checks
    testHealthCheck();
  } else {
    // 5% - Admin write operations
    testAdminWrite(data);
  }

  sleep(Math.random() * 0.5); // Random sleep 0-500ms
}

function testLLMRequest() {
  const startTime = Date.now();

  const res = http.post(
    `${BASE_URL}/v1/chat/completions`,
    JSON.stringify({
      model: randomModel(),
      messages: [{ role: 'user', content: randomMessage() }],
      max_tokens: 20,
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
      timeout: '30s',
    }
  );

  const duration = Date.now() - startTime;
  p95Latency.add(duration);

  // Track different failure types
  if (res.status === 429) {
    requestsBlocked.add(1);
  } else if (res.status === 402) {
    budgetExceeded.add(1);
  } else if (res.status === 403) {
    policyDenied.add(1);
  }

  check(res, {
    'LLM request processed': (r) => [200, 429, 402, 403].includes(r.status),
  });
}

function testAdminRead(data) {
  const authParams = {
    headers: {
      'Content-Type': 'application/json',
      'Cookie': data.cookieHeader,
    },
  };

  const endpoints = [
    '/admin/applications',
    '/admin/budgets',
    '/admin/policies',
    '/admin/analytics/overview',
    '/admin/notifications?limit=5',
  ];

  const endpoint = endpoints[Math.floor(Math.random() * endpoints.length)];
  const res = http.get(`${BASE_URL}${endpoint}`, authParams);

  check(res, {
    'admin read OK': (r) => r.status === 200,
  });
}

function testAdminWrite(data) {
  const authParams = {
    headers: {
      'Content-Type': 'application/json',
      'Cookie': data.cookieHeader,
    },
  };

  // Mark notification as read (safe write operation)
  const notifRes = http.get(`${BASE_URL}/admin/notifications?limit=1`, authParams);
  if (notifRes.status === 200) {
    const notifications = notifRes.json();
    if (notifications && notifications.length > 0) {
      http.post(
        `${BASE_URL}/admin/notifications/${notifications[0].id}/read`,
        null,
        authParams
      );
    }
  }
}

function testHealthCheck() {
  const res = http.get(`${BASE_URL}/health/ready`);
  check(res, {
    'health check OK': (r) => r.status === 200,
  });
}

export function teardown(data) {
  console.log('\n=== Stress Test Summary ===');
  console.log('Check Grafana/metrics for detailed analysis');
}
