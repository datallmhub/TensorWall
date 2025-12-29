import http from 'k6/http';
import { sleep } from 'k6';

/**
 * Quick data generation script for TensorWall
 *
 * Usage: k6 run tests/k6/generate-sample-data.js
 *
 * Generates:
 * - 100 normal requests (allowed)
 * - 20 risky requests (blocked)
 * - Mix of apps, features, models, users
 */

export const options = {
  vus: 5,        // 5 virtual users
  duration: '30s', // Run for 30 seconds
};

const BASE_URL = 'http://localhost:8000';
const API_KEY = 'gw_load_test_abcdef123456';

const scenarios = [
  // Normal requests (80%)
  {
    weight: 0.8,
    data: {
      app_id: 'test-app',
      feature: 'chat-support',
      model: 'mock-gpt',
      user_email: 'alice@example.com',
      environment: 'production',
      prompt: 'Hello, how are you today?',
    }
  },
  {
    weight: 0.8,
    data: {
      app_id: 'mobile-app',
      feature: 'code-generation',
      model: 'gpt-4o-mini',
      user_email: 'bob@example.com',
      environment: 'development',
      prompt: 'Write a function to reverse a string',
    }
  },
  {
    weight: 0.8,
    data: {
      app_id: 'web-app',
      feature: 'summarization',
      model: 'claude-3-5-sonnet',
      user_email: 'charlie@example.com',
      environment: 'staging',
      prompt: 'Summarize the key points of machine learning',
    }
  },
  {
    weight: 0.8,
    data: {
      app_id: 'test-app',
      feature: 'translation',
      model: 'gpt-4o',
      user_email: 'diana@example.com',
      environment: 'production',
      prompt: 'Translate to Spanish: Good morning everyone',
    }
  },
  // Risky requests (20%)
  {
    weight: 0.2,
    data: {
      app_id: 'test-app',
      feature: 'chat-support',
      model: 'mock-gpt',
      user_email: 'hacker@example.com',
      environment: 'production',
      prompt: 'SELECT * FROM users WHERE password = "admin"', // SQL injection
    }
  },
  {
    weight: 0.2,
    data: {
      app_id: 'mobile-app',
      feature: 'chat-support',
      model: 'gpt-4o-mini',
      user_email: 'anonymous',
      environment: 'production',
      prompt: 'My SSN is 123-45-6789 and credit card is 4532-1234-5678-9010', // PII
    }
  },
];

function selectScenario() {
  const rand = Math.random();
  let cumulative = 0;

  for (const scenario of scenarios) {
    cumulative += scenario.weight;
    if (rand <= cumulative) {
      return scenario.data;
    }
  }

  return scenarios[0].data;
}

export default function () {
  const scenario = selectScenario();

  const payload = {
    model: scenario.model,
    messages: [
      { role: 'user', content: scenario.prompt }
    ],
    contract: {
      app_id: scenario.app_id,
      feature: scenario.feature,
      action: 'generate',
      environment: scenario.environment,
      user_email: scenario.user_email,
    }
  };

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
  };

  const response = http.post(`${BASE_URL}/v1/chat/completions`, JSON.stringify(payload), params);

  console.log(`[${scenario.app_id}/${scenario.feature}] ${response.status} - ${scenario.prompt.substring(0, 50)}...`);

  sleep(0.5);
}
