// =============================================================================
// K6 Smoke Test: Quick Validation
// =============================================================================
// Run: k6 run tests/k6/gateway-smoke.js
// Purpose: Quick sanity check that all endpoints work

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { BASE_URL, API_KEY, scenarios } from './config.js';

export const options = {
  scenarios: {
    smoke: scenarios.smoke,
  },
  thresholds: {
    'http_req_failed': ['rate<0.15'], // Allow up to 15% failures (429s are expected)
    'http_req_duration': ['p(95)<1000'],
  },
};

export function setup() {
  console.log(`\nSmoke test against: ${BASE_URL}\n`);

  // Create a cookie jar for this test
  const jar = http.cookieJar();

  const loginRes = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({
      email: 'admin@example.com',
      password: 'admin123456',
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  check(loginRes, {
    'login successful': (r) => r.status === 200,
  });

  if (loginRes.status !== 200) {
    console.error('Login failed:', loginRes.body);
    throw new Error('Cannot proceed without authentication');
  }

  // Extract cookies from response and return them as header format
  const cookies = jar.cookiesForURL(BASE_URL);
  const cookieHeader = Object.entries(cookies)
    .map(([name, value]) => `${name}=${value}`)
    .join('; ');

  return { cookieHeader };
}

export default function (data) {
  const authParams = {
    headers: {
      'Content-Type': 'application/json',
      'Cookie': data.cookieHeader,
    },
  };

  // ==========================================================================
  // 1. Health Endpoints
  // ==========================================================================
  group('1. Health Endpoints', () => {
    const checks = [
      { url: '/health', name: 'basic health' },
      { url: '/health/live', name: 'liveness' },
      { url: '/health/ready', name: 'readiness' },
    ];

    checks.forEach(({ url, name }) => {
      const res = http.get(`${BASE_URL}${url}`);
      check(res, {
        [`${name} returns 200`]: (r) => r.status === 200,
      });
    });
  });

  sleep(0.5);

  // ==========================================================================
  // 2. Authentication Endpoints
  // ==========================================================================
  group('2. Auth Endpoints', () => {
    // Get current user
    const meRes = http.get(`${BASE_URL}/auth/me`, authParams);
    check(meRes, {
      'get me returns 200': (r) => r.status === 200,
      'user has email': (r) => r.json('email') !== undefined,
      'user has role': (r) => r.json('role') !== undefined,
    });

    // Token refresh
    const refreshRes = http.post(`${BASE_URL}/auth/refresh`, null, authParams);
    check(refreshRes, {
      'refresh token works': (r) => r.status === 200,
    });
  });

  sleep(0.5);

  // ==========================================================================
  // 3. Admin API Endpoints
  // ==========================================================================
  group('3. Admin API', () => {
    // Applications
    const appsRes = http.get(`${BASE_URL}/admin/applications`, authParams);
    check(appsRes, {
      'get applications': (r) => r.status === 200,
      'applications is array': (r) => Array.isArray(r.json()),
    });

    // Policies
    const policiesRes = http.get(`${BASE_URL}/admin/policies`, authParams);
    check(policiesRes, {
      'get policies': (r) => r.status === 200,
    });

    // Budgets
    const budgetsRes = http.get(`${BASE_URL}/admin/budgets`, authParams);
    check(budgetsRes, {
      'get budgets': (r) => r.status === 200,
    });

    // Analytics overview
    const analyticsRes = http.get(`${BASE_URL}/admin/analytics/overview`, authParams);
    check(analyticsRes, {
      'get analytics overview': (r) => r.status === 200,
      'has total_requests': (r) => r.json('total_requests') !== undefined,
    });

    // Notifications
    const notifRes = http.get(`${BASE_URL}/admin/notifications?limit=5`, authParams);
    check(notifRes, {
      'get notifications': (r) => r.status === 200,
    });
  });

  sleep(0.5);

  // ==========================================================================
  // 4. LLM Gateway Endpoint
  // ==========================================================================
  group('4. LLM Gateway', () => {
    const chatRes = http.post(
      `${BASE_URL}/v1/chat/completions`,
      JSON.stringify({
        model: 'mock-gpt',
        messages: [{ role: 'user', content: 'Say "smoke test ok" in exactly 3 words.' }],
        max_tokens: 10,
        contract: {
          app_id: 'test-app',
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

    check(chatRes, {
      'chat completion works': (r) => r.status === 200 || r.status === 429,
      'has choices': (r) => r.status !== 200 || r.json('choices') !== undefined,
    });

    if (chatRes.status === 200) {
      console.log('LLM Response:', chatRes.json('choices')[0]?.message?.content);
    }
  });

  sleep(0.5);
}

export function teardown(data) {
  console.log('\n✅ Smoke test completed successfully!\n');
}
