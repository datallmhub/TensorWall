// =============================================================================
// K6 Load Test: TensorWall Core Endpoints
// =============================================================================
// Run: k6 run tests/k6/gateway-load.js
// With env: k6 run -e BASE_URL=https://api.example.com -e API_KEY=xxx tests/k6/gateway-load.js

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { BASE_URL, API_KEY, thresholds, scenarios, randomAppId, randomModel, randomMessage } from './config.js';

// Custom metrics
const gatewayLatency = new Trend('gateway_latency', true);
const policyCheckLatency = new Trend('policy_check_latency', true);
const errorRate = new Rate('error_rate');

// Test configuration
export const options = {
  scenarios: {
    // Default: load test
    default: scenarios.load,
  },
  thresholds: thresholds,
};

// Setup: authenticate and get tokens
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

  check(loginRes, {
    'login successful': (r) => r.status === 200,
  });

  // Extract cookies from jar and return as header format
  const cookies = jar.cookiesForURL(BASE_URL);
  const cookieHeader = Object.entries(cookies)
    .map(([name, value]) => `${name}=${value}`)
    .join('; ');

  return { cookieHeader };
}

export default function (data) {
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
    tags: { type: 'gateway' },
  };

  const authParams = {
    headers: {
      'Content-Type': 'application/json',
      'Cookie': data.cookieHeader,
    },
    tags: { type: 'admin' },
  };

  // ==========================================================================
  // Health Checks (high frequency)
  // ==========================================================================
  group('Health Checks', () => {
    const healthRes = http.get(`${BASE_URL}/health`, {
      tags: { type: 'health' },
    });

    check(healthRes, {
      'health check OK': (r) => r.status === 200,
      'health status healthy': (r) => r.json('status') === 'healthy',
    });

    const readyRes = http.get(`${BASE_URL}/health/ready`, {
      tags: { type: 'health' },
    });

    check(readyRes, {
      'ready check OK': (r) => r.status === 200,
    });
  });

  sleep(0.1);

  // ==========================================================================
  // LLM Chat Completions (core gateway function)
  // ==========================================================================
  group('LLM Chat Completions', () => {
    const startTime = Date.now();

    const chatRes = http.post(
      `${BASE_URL}/v1/chat/completions`,
      JSON.stringify({
        model: randomModel(),
        messages: [
          { role: 'user', content: randomMessage() },
        ],
        max_tokens: 50,
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
        tags: { type: 'llm_proxy' },
        timeout: '30s',
      }
    );

    const duration = Date.now() - startTime;
    gatewayLatency.add(duration);

    const success = check(chatRes, {
      'chat completion OK': (r) => r.status === 200 || r.status === 429,
      'has response': (r) => r.status !== 200 || r.json('choices') !== undefined,
    });

    if (!success) {
      errorRate.add(1);
      console.log(`Chat error: ${chatRes.status} - ${chatRes.body}`);
    } else {
      errorRate.add(0);
    }
  });

  sleep(0.5);

  // ==========================================================================
  // Admin API (dashboard operations)
  // ==========================================================================
  group('Admin Operations', () => {
    // Get applications
    const appsRes = http.get(`${BASE_URL}/admin/applications`, authParams);
    check(appsRes, {
      'get applications OK': (r) => r.status === 200,
    });

    // Get budgets
    const budgetsRes = http.get(`${BASE_URL}/admin/budgets`, authParams);
    check(budgetsRes, {
      'get budgets OK': (r) => r.status === 200,
    });

    // Get analytics overview
    const analyticsRes = http.get(`${BASE_URL}/admin/analytics/overview`, authParams);
    check(analyticsRes, {
      'get analytics OK': (r) => r.status === 200,
    });

    // Get notifications
    const notifRes = http.get(`${BASE_URL}/admin/notifications?limit=10`, authParams);
    check(notifRes, {
      'get notifications OK': (r) => r.status === 200,
    });
  });

  sleep(0.3);
}

// Teardown
export function teardown(data) {
  console.log('Load test completed');
}
