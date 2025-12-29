import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

// Test configuration
export const options = {
  stages: [
    { duration: '30s', target: 10 },  // Ramp up to 10 users
    { duration: '1m', target: 20 },   // Stay at 20 users
    { duration: '30s', target: 0 },   // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests should be below 2s
    errors: ['rate<0.1'],              // Error rate should be less than 10%
  },
};

const BASE_URL = 'http://localhost:8000';
const API_KEY = 'gw_load_test_abcdef123456';

// Test data
const apps = ['test-app', 'mobile-app', 'web-app'];
const features = ['chat-support', 'code-generation', 'summarization', 'translation'];
const models = ['mock-gpt', 'gpt-4o-mini', 'gpt-4o', 'claude-3-5-sonnet'];
const users = ['alice@example.com', 'bob@example.com', 'charlie@example.com', 'anonymous'];
const environments = ['development', 'staging', 'production'];

// Prompt variations
const prompts = [
  'Hello, how are you?',
  'Write a Python function to calculate fibonacci numbers',
  'Summarize the following text: Lorem ipsum dolor sit amet...',
  'Translate to French: The weather is nice today',
  'Explain quantum computing in simple terms',
  'What is the capital of France?',
  'Help me debug this code: def foo(): pass',
  'Generate a creative story about a robot',
];

// Risky prompts (for blocked requests testing)
const riskyPrompts = [
  'SELECT * FROM users WHERE password = "admin123"',  // SQL injection attempt
  'My credit card number is 4532-1234-5678-9010',     // PII leakage
  '<script>alert("XSS")</script>',                    // XSS attempt
  'rm -rf / --no-preserve-root',                      // Dangerous command
];

function randomChoice(array) {
  return array[Math.floor(Math.random() * array.length)];
}

function makeRequest(prompt, scenario = 'normal') {
  const payload = {
    model: randomChoice(models),
    messages: [
      { role: 'user', content: prompt }
    ],
    contract: {
      app_id: randomChoice(apps),
      feature: randomChoice(features),
      action: 'generate',
      environment: randomChoice(environments),
      user_email: randomChoice(users),
    }
  };

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
  };

  const response = http.post(`${BASE_URL}/v1/chat/completions`, JSON.stringify(payload), params);

  const success = check(response, {
    'status is 200 or 400': (r) => r.status === 200 || r.status === 400 || r.status === 403,
    'response has body': (r) => r.body.length > 0,
  });

  errorRate.add(!success);

  return response;
}

export default function () {
  // Determine scenario (80% normal, 20% risky)
  const isRisky = Math.random() < 0.2;

  if (isRisky) {
    // Risky request (should be blocked)
    const riskyPrompt = randomChoice(riskyPrompts);
    const response = makeRequest(riskyPrompt, 'risky');

    check(response, {
      'risky request blocked': (r) => r.status === 403 || r.status === 400,
    });
  } else {
    // Normal request
    const normalPrompt = randomChoice(prompts);
    const response = makeRequest(normalPrompt, 'normal');

    check(response, {
      'normal request allowed': (r) => r.status === 200,
    });
  }

  // Random think time between requests
  sleep(Math.random() * 2 + 1); // 1-3 seconds
}

// Scenario-specific tests
export function scenarioNormalLoad() {
  for (let i = 0; i < 5; i++) {
    makeRequest(randomChoice(prompts), 'normal');
    sleep(0.5);
  }
}

export function scenarioRiskyRequests() {
  for (let i = 0; i < 5; i++) {
    makeRequest(randomChoice(riskyPrompts), 'risky');
    sleep(0.5);
  }
}

export function scenarioBurst() {
  // Burst of requests (tests rate limiting)
  for (let i = 0; i < 20; i++) {
    makeRequest(randomChoice(prompts), 'burst');
  }
}

export function scenarioMultiUser() {
  // Simulate multiple users from same app
  users.forEach(user => {
    const payload = {
      model: 'mock-gpt',
      messages: [{ role: 'user', content: 'Hello from ' + user }],
      contract: {
        app_id: 'test-app',
        feature: 'chat-support',
        action: 'generate',
        environment: 'production',
        user_email: user,
      }
    };

    http.post(`${BASE_URL}/v1/chat/completions`, JSON.stringify(payload), {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
    });
  });
}
