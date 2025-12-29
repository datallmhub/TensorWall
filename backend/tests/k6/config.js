// =============================================================================
// K6 Load Test Configuration
// =============================================================================

export const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
export const API_KEY = __ENV.API_KEY || 'gw_load_test_abcdef123456';

// Test thresholds
export const thresholds = {
  // Gateway latency SLO: p95 < 50ms overhead
  'http_req_duration{type:gateway}': ['p(95)<50', 'p(99)<100'],

  // Auth endpoints
  'http_req_duration{type:auth}': ['p(95)<200', 'p(99)<500'],

  // Admin endpoints
  'http_req_duration{type:admin}': ['p(95)<500', 'p(99)<1000'],

  // LLM proxy (excluding LLM provider latency)
  'http_req_duration{type:llm_proxy}': ['p(95)<100', 'p(99)<200'],

  // Error rate < 1%
  'http_req_failed': ['rate<0.01'],

  // Health checks always fast
  'http_req_duration{type:health}': ['p(99)<50'],
};

// Scenarios
export const scenarios = {
  // Smoke test: minimal load to verify system works
  smoke: {
    executor: 'constant-vus',
    vus: 1,
    duration: '30s',
  },

  // Load test: normal expected load
  load: {
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '2m', target: 50 },   // Ramp up
      { duration: '5m', target: 50 },   // Steady state
      { duration: '2m', target: 0 },    // Ramp down
    ],
  },

  // Stress test: find breaking point
  stress: {
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '2m', target: 100 },
      { duration: '5m', target: 100 },
      { duration: '2m', target: 200 },
      { duration: '5m', target: 200 },
      { duration: '2m', target: 300 },
      { duration: '5m', target: 300 },
      { duration: '5m', target: 0 },
    ],
  },

  // Spike test: sudden traffic surge
  spike: {
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '10s', target: 10 },   // Normal
      { duration: '1m', target: 10 },
      { duration: '10s', target: 500 },  // Spike!
      { duration: '3m', target: 500 },
      { duration: '10s', target: 10 },   // Back to normal
      { duration: '1m', target: 10 },
      { duration: '10s', target: 0 },
    ],
  },

  // Soak test: extended duration for memory leaks
  soak: {
    executor: 'constant-vus',
    vus: 50,
    duration: '30m',
  },
};

// Test data generators
export function randomAppId() {
  // Only use apps that exist in the database
  return 'test-app';
}

export function randomModel() {
  // Use mock model for load testing (no real LLM calls)
  return 'mock-gpt';
}

export function randomMessage() {
  const messages = [
    'Hello, how are you?',
    'What is the capital of France?',
    'Explain quantum computing in simple terms.',
    'Write a haiku about programming.',
    'What is 2 + 2?',
  ];
  return messages[Math.floor(Math.random() * messages.length)];
}
