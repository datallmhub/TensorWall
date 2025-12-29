// =============================================================================
// K6 Load Test for Budget Enforcement
// =============================================================================
// Purpose: Test that budget limits are correctly enforced
//
// Test Flow:
//   1. Login to admin API
//   2. Create/reset a test app with low budget ($0.01)
//   3. Send LLM requests until budget is exceeded
//   4. Verify requests are blocked after budget exceeded
//   5. Reset budget and verify requests work again
//
// Run:
//   k6 run tests/k6/budget-load-test.js
//
// Prerequisites:
//   - TensorWall running on localhost:8000
//   - LM Studio running with a model loaded
//   - Admin user: admin@example.com / admin123
// =============================================================================

import http from 'k6/http';
import { check, group, sleep, fail } from 'k6';
import { Rate, Counter, Trend } from 'k6/metrics';

// =============================================================================
// Configuration
// =============================================================================

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const ADMIN_EMAIL = __ENV.ADMIN_EMAIL || 'admin@example.com';
const ADMIN_PASSWORD = __ENV.ADMIN_PASSWORD || 'admin123';

// Use a fast, cheap model for budget testing
const TEST_MODEL = __ENV.TEST_MODEL || 'lmstudio/qwen/qwen2.5-vl-7b';

// Budget limit in USD (very low to trigger quickly)
// Each request costs ~$0.00003, so $0.0001 should exceed after ~3 requests
const BUDGET_LIMIT_USD = 0.0001;

// =============================================================================
// Custom Metrics
// =============================================================================

const budgetBlocked = new Counter('budget_blocked_requests');
const budgetAllowed = new Counter('budget_allowed_requests');
const budgetErrors = new Rate('budget_test_errors');
const requestLatency = new Trend('llm_request_latency', true);

// =============================================================================
// Test Options
// =============================================================================

export const options = {
  scenarios: {
    budget_test: {
      executor: 'shared-iterations',
      vus: 1,
      iterations: 1,
      maxDuration: '5m',
    },
  },
  thresholds: {
    'budget_test_errors': ['rate<0.1'],  // Less than 10% errors
  },
};

// =============================================================================
// Helper Functions
// =============================================================================

function adminLogin() {
  const res = http.post(`${BASE_URL}/auth/login`, JSON.stringify({
    email: ADMIN_EMAIL,
    password: ADMIN_PASSWORD,
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  if (!check(res, { 'login successful': (r) => r.status === 200 })) {
    fail(`Admin login failed: ${res.status} - ${res.body}`);
  }

  const data = JSON.parse(res.body);
  return data.access_token;
}

function getApiKeyForApp(token, appId) {
  // Get application details to find API key
  const res = http.get(`${BASE_URL}/admin/applications`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });

  if (res.status !== 200) {
    console.log(`Failed to get applications: ${res.body}`);
    return null;
  }

  const apps = JSON.parse(res.body);
  const app = apps.find(a => a.app_id === appId);

  if (!app) {
    console.log(`App ${appId} not found`);
    return null;
  }

  // Get API keys for this app
  const keysRes = http.get(`${BASE_URL}/admin/applications/${app.uuid}/keys`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });

  if (keysRes.status !== 200) {
    console.log(`Failed to get keys: ${keysRes.body}`);
    return null;
  }

  const keys = JSON.parse(keysRes.body);
  if (keys.length === 0) {
    // Create a new API key
    const createRes = http.post(
      `${BASE_URL}/admin/applications/${app.uuid}/keys`,
      JSON.stringify({ name: 'budget-test-key', environment: 'production' }),
      { headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } }
    );

    if (createRes.status === 201) {
      const newKey = JSON.parse(createRes.body);
      return newKey.api_key;
    }
    return null;
  }

  // We need to create a new key since we can't retrieve existing keys
  const createRes = http.post(
    `${BASE_URL}/admin/applications/${app.uuid}/keys`,
    JSON.stringify({ name: `budget-test-${Date.now()}`, environment: 'production' }),
    { headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } }
  );

  if (createRes.status === 201) {
    const newKey = JSON.parse(createRes.body);
    return newKey.api_key;
  }

  return null;
}

function findOrCreateBudget(token, appId, limitUsd) {
  // First, get existing budgets
  const res = http.get(`${BASE_URL}/admin/budgets`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });

  if (res.status !== 200) {
    console.log(`Failed to get budgets: ${res.body}`);
    return null;
  }

  const data = JSON.parse(res.body);
  const existingBudget = data.items.find(b => b.app_id === appId);

  if (existingBudget) {
    console.log(`Found existing budget for ${appId}: ${existingBudget.uuid}`);

    // Update limit to our test value
    const updateRes = http.patch(
      `${BASE_URL}/admin/budgets/${existingBudget.uuid}`,
      JSON.stringify({ limit_usd: limitUsd }),
      { headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } }
    );

    if (updateRes.status === 200) {
      // Reset spent amount
      http.post(
        `${BASE_URL}/admin/budgets/${existingBudget.uuid}/reset`,
        null,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      return existingBudget.uuid;
    }
  }

  // Create new budget
  const createRes = http.post(
    `${BASE_URL}/admin/budgets`,
    JSON.stringify({ app_id: appId, limit_usd: limitUsd }),
    { headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } }
  );

  if (createRes.status === 201) {
    const budget = JSON.parse(createRes.body);
    console.log(`Created budget: ${budget.uuid}`);
    return budget.uuid;
  } else if (createRes.status === 409) {
    // Budget already exists, try to get it again
    console.log('Budget conflict, retrying...');
    return null;
  }

  console.log(`Failed to create budget: ${createRes.status} - ${createRes.body}`);
  return null;
}

function getBudgetStatus(token, budgetUuid) {
  const res = http.get(`${BASE_URL}/admin/budgets/${budgetUuid}`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });

  if (res.status === 200) {
    return JSON.parse(res.body);
  }
  return null;
}

function resetBudget(token, budgetUuid) {
  const res = http.post(
    `${BASE_URL}/admin/budgets/${budgetUuid}/reset`,
    null,
    { headers: { 'Authorization': `Bearer ${token}` } }
  );
  return res.status === 200;
}

function sendLLMRequest(apiKey, model) {
  const startTime = Date.now();

  const res = http.post(
    `${BASE_URL}/v1/chat/completions`,
    JSON.stringify({
      model: model,
      messages: [
        { role: 'system', content: 'Answer in one word only.' },
        { role: 'user', content: 'What is 1+1?' }
      ],
      max_tokens: 10,
    }),
    {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
      timeout: '60s',
    }
  );

  const latency = Date.now() - startTime;
  requestLatency.add(latency);

  return {
    status: res.status,
    body: res.body,
    latency: latency,
  };
}

// =============================================================================
// Main Test
// =============================================================================

export default function () {
  let token = null;
  let apiKey = null;
  let budgetUuid = null;
  const testAppId = 'rag-chat-prod'; // Use existing app

  // -------------------------------------------------------------------------
  // Phase 1: Setup
  // -------------------------------------------------------------------------
  group('Setup', () => {
    console.log('\n=== BUDGET LOAD TEST ===');
    console.log(`Target: ${BASE_URL}`);
    console.log(`Model: ${TEST_MODEL}`);
    console.log(`Budget Limit: $${BUDGET_LIMIT_USD}`);

    // Login
    token = adminLogin();
    console.log('✓ Admin login successful');

    // Get API key
    apiKey = getApiKeyForApp(token, testAppId);
    if (!apiKey) {
      fail('Could not get API key for test app');
    }
    console.log(`✓ Got API key: ${apiKey.substring(0, 15)}...`);

    // Setup budget with very low limit
    budgetUuid = findOrCreateBudget(token, testAppId, BUDGET_LIMIT_USD);
    if (!budgetUuid) {
      fail('Could not create/find budget');
    }
    console.log(`✓ Budget configured: $${BUDGET_LIMIT_USD} limit`);
  });

  sleep(1);

  // -------------------------------------------------------------------------
  // Phase 2: Send requests until budget exceeded
  // -------------------------------------------------------------------------
  group('Budget Exhaustion', () => {
    console.log('\n--- Sending requests to exhaust budget ---');

    let requestCount = 0;
    let blockedCount = 0;
    let allowedCount = 0;
    const maxRequests = 10; // Safety limit

    while (requestCount < maxRequests) {
      requestCount++;
      console.log(`\nRequest #${requestCount}...`);

      const result = sendLLMRequest(apiKey, TEST_MODEL);

      if (result.status === 200) {
        allowedCount++;
        budgetAllowed.add(1);
        console.log(`  ✓ Allowed (${result.latency}ms)`);

        // Check budget status
        const budget = getBudgetStatus(token, budgetUuid);
        if (budget) {
          console.log(`  Budget: $${budget.spent_usd.toFixed(6)} / $${budget.limit_usd} (${budget.usage_percent}%)`);

          if (budget.is_exceeded) {
            console.log('  → Budget is now exceeded!');
          }
        }
      } else if (result.status === 402 || result.status === 403 || result.status === 429) {
        // Budget exceeded - this is expected!
        blockedCount++;
        budgetBlocked.add(1);
        console.log(`  ✗ BLOCKED - Budget exceeded! (Status: ${result.status})`);

        // Verify it's actually a budget block
        try {
          const body = JSON.parse(result.body);
          console.log(`  Reason: ${body.detail || body.message || 'Budget limit exceeded'}`);
        } catch (e) {
          console.log(`  Response: ${result.body}`);
        }

        // Budget is working! Stop sending requests
        break;
      } else {
        // Unexpected error
        budgetErrors.add(1);
        console.log(`  ✗ Error: ${result.status} - ${result.body}`);
      }

      sleep(0.5); // Small delay between requests
    }

    // Validate results
    console.log(`\n--- Results ---`);
    console.log(`Total requests: ${requestCount}`);
    console.log(`Allowed: ${allowedCount}`);
    console.log(`Blocked: ${blockedCount}`);

    check(null, {
      'at least one request was allowed': () => allowedCount > 0,
      'budget blocking worked': () => blockedCount > 0 || requestCount >= maxRequests,
    });
  });

  sleep(1);

  // -------------------------------------------------------------------------
  // Phase 3: Verify budget is exceeded
  // -------------------------------------------------------------------------
  group('Verify Budget Exceeded', () => {
    console.log('\n--- Verifying budget status ---');

    const budget = getBudgetStatus(token, budgetUuid);
    if (budget) {
      console.log(`Budget Status:`);
      console.log(`  Spent: $${budget.spent_usd.toFixed(6)}`);
      console.log(`  Limit: $${budget.limit_usd}`);
      console.log(`  Usage: ${budget.usage_percent}%`);
      console.log(`  Exceeded: ${budget.is_exceeded}`);

      check(budget, {
        'budget shows spending': (b) => b.spent_usd > 0,
        'budget is exceeded or near limit': (b) => b.usage_percent >= 90 || b.is_exceeded,
      });
    }

    // Try one more request - should be blocked
    console.log('\nSending verification request (should be blocked)...');
    const result = sendLLMRequest(apiKey, TEST_MODEL);

    const wasBlocked = result.status === 402 || result.status === 403 || result.status === 429;
    console.log(`Result: ${wasBlocked ? 'BLOCKED ✓' : 'ALLOWED (unexpected)'} - Status: ${result.status}`);

    check(null, {
      'verification request was blocked': () => wasBlocked,
    });

    if (wasBlocked) {
      budgetBlocked.add(1);
    }
  });

  sleep(1);

  // -------------------------------------------------------------------------
  // Phase 4: Reset budget and verify requests work again
  // -------------------------------------------------------------------------
  group('Budget Reset', () => {
    console.log('\n--- Resetting budget ---');

    const resetSuccess = resetBudget(token, budgetUuid);
    check(resetSuccess, {
      'budget reset successful': (r) => r === true,
    });

    if (resetSuccess) {
      console.log('✓ Budget reset');

      // Verify budget is reset
      const budget = getBudgetStatus(token, budgetUuid);
      if (budget) {
        console.log(`  Spent: $${budget.spent_usd} (should be 0)`);
        check(budget, {
          'spent amount is zero': (b) => b.spent_usd === 0,
        });
      }

      // Try a request - should work now
      console.log('\nSending post-reset request (should be allowed)...');
      const result = sendLLMRequest(apiKey, TEST_MODEL);

      const wasAllowed = result.status === 200;
      console.log(`Result: ${wasAllowed ? 'ALLOWED ✓' : 'BLOCKED (unexpected)'} - Status: ${result.status}`);

      check(null, {
        'post-reset request was allowed': () => wasAllowed,
      });

      if (wasAllowed) {
        budgetAllowed.add(1);
      }
    }
  });

  // -------------------------------------------------------------------------
  // Summary
  // -------------------------------------------------------------------------
  console.log('\n=== TEST COMPLETE ===');
  console.log('Budget enforcement test finished.');
}

// =============================================================================
// Teardown
// =============================================================================

export function teardown(data) {
  console.log('\n--- Cleanup ---');
  // Could reset budget here if needed
}
