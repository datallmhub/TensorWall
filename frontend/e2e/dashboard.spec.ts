import { test, expect } from '@playwright/test';

test.describe('Dashboard API Calls', () => {
  test.beforeEach(async ({ page, context }) => {
    // Clear cookies and login
    await context.clearCookies();
    console.log('✓ Cookies cleared');

    // Login first
    console.log('1. Logging in...');
    await page.goto('http://localhost:3000/login');
    await page.waitForLoadState('networkidle');

    await page.getByPlaceholder(/email/i).fill('admin@example.com');
    await page.getByPlaceholder(/password/i).fill('admin123');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Wait for redirect to dashboard
    await page.waitForURL('http://localhost:3000/', { timeout: 10000 });
    await page.waitForLoadState('networkidle');
    console.log('✓ Logged in successfully');
  });

  test('should load dashboard without 404 errors', async ({ page }) => {
    console.log('\n=== Test: Dashboard API Calls ===');

    // Track all network requests
    const requests: { url: string; status: number; method: string }[] = [];
    const failedRequests: { url: string; status: number }[] = [];

    page.on('response', async (response) => {
      const url = response.url();
      const status = response.status();
      const method = response.request().method();

      // Track API calls
      if (url.includes('/api/')) {
        requests.push({ url, status, method });
        console.log(`API Call: ${method} ${url} -> ${status}`);

        // Track failed requests (4xx, 5xx)
        if (status >= 400) {
          failedRequests.push({ url, status });
          console.log(`❌ FAILED: ${method} ${url} -> ${status}`);
        }
      }
    });

    console.log('2. Navigating to dashboard...');
    await page.goto('http://localhost:3000/', { waitUntil: 'networkidle' });

    // Wait for page to fully load
    await page.waitForTimeout(3000);

    console.log('\n=== API Requests Summary ===');
    console.log(`Total API requests: ${requests.length}`);

    // Group requests by endpoint
    const byEndpoint: Record<string, number[]> = {};
    requests.forEach(req => {
      const endpoint = req.url.replace(/^.*\/api/, '/api');
      if (!byEndpoint[endpoint]) {
        byEndpoint[endpoint] = [];
      }
      byEndpoint[endpoint].push(req.status);
    });

    console.log('\n=== Requests by Endpoint ===');
    Object.entries(byEndpoint).forEach(([endpoint, statuses]) => {
      const hasFailure = statuses.some(s => s >= 400);
      const symbol = hasFailure ? '❌' : '✅';
      console.log(`${symbol} ${endpoint}: ${statuses.join(', ')}`);
    });

    // Print failed requests details
    if (failedRequests.length > 0) {
      console.log('\n=== Failed Requests Details ===');
      failedRequests.forEach((req, idx) => {
        console.log(`${idx + 1}. ${req.url}`);
        console.log(`   Status: ${req.status}`);
      });
    }

    // Check for specific problematic endpoints
    const usageEndpoint = requests.find(r => r.url.includes('/admin/analytics/usage'));
    const auditEndpoint = requests.find(r => r.url.includes('/admin/analytics/audit'));
    const auditLogsEndpoint = requests.find(r => r.url.includes('/admin/analytics/audit-logs'));

    console.log('\n=== Specific Endpoints Check ===');
    if (usageEndpoint) {
      console.log(`Usage endpoint: ${usageEndpoint.status} (${usageEndpoint.status < 400 ? '✓' : '✗'})`);
    } else {
      console.log('Usage endpoint: NOT CALLED');
    }

    if (auditEndpoint) {
      console.log(`Audit endpoint: ${auditEndpoint.status} (${auditEndpoint.status < 400 ? '✓' : '✗'})`);
    } else {
      console.log('Audit endpoint: NOT CALLED');
    }

    if (auditLogsEndpoint) {
      console.log(`Audit-logs endpoint: ${auditLogsEndpoint.status} (${auditLogsEndpoint.status < 400 ? '✓' : '✗'})`);
    } else {
      console.log('Audit-logs endpoint: NOT CALLED');
    }

    // Assertions
    expect(failedRequests.length, `Found ${failedRequests.length} failed API requests`).toBe(0);

    // Check dashboard is visible
    await expect(page.getByText(/Dashboard/i).first()).toBeVisible();
    console.log('✓ Dashboard is visible');
  });

  test('should display correct data on dashboard', async ({ page }) => {
    console.log('\n=== Test: Dashboard Data Display ===');

    await page.goto('http://localhost:3000/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check for stat cards
    const hasRequestsCard = await page.getByText(/Total Requests|Requests/i).isVisible().catch(() => false);
    const hasCostCard = await page.getByText(/Cost|Spend/i).isVisible().catch(() => false);
    const hasTokensCard = await page.getByText(/Tokens/i).isVisible().catch(() => false);

    console.log(`Stats cards visible:`);
    console.log(`  - Requests: ${hasRequestsCard ? '✓' : '✗'}`);
    console.log(`  - Cost: ${hasCostCard ? '✓' : '✗'}`);
    console.log(`  - Tokens: ${hasTokensCard ? '✓' : '✗'}`);

    // Take screenshot for debugging
    await page.screenshot({ path: 'test-results/dashboard-screenshot.png', fullPage: true });
    console.log('✓ Screenshot saved to test-results/dashboard-screenshot.png');
  });

  test('should navigate to analytics page without errors', async ({ page }) => {
    console.log('\n=== Test: Analytics Page ===');

    const failedRequests: { url: string; status: number }[] = [];

    page.on('response', async (response) => {
      const url = response.url();
      const status = response.status();

      if (url.includes('/api/') && status >= 400) {
        failedRequests.push({ url, status });
        console.log(`❌ FAILED: ${url} -> ${status}`);
      }
    });

    console.log('1. Navigating to Analytics page...');
    await page.goto('http://localhost:3000/analytics', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    console.log(`2. Failed requests on Analytics page: ${failedRequests.length}`);

    if (failedRequests.length > 0) {
      console.log('\n=== Failed Requests ===');
      failedRequests.forEach((req, idx) => {
        console.log(`${idx + 1}. ${req.url} -> ${req.status}`);
      });
    }

    // Check Analytics page loaded
    await expect(page.getByText(/Analytics/i).first()).toBeVisible();
    console.log('✓ Analytics page loaded');

    expect(failedRequests.length, `Found ${failedRequests.length} failed API requests`).toBe(0);
  });

  test('should test backend endpoints directly', async ({ request }) => {
    console.log('\n=== Test: Direct Backend Endpoint Tests ===');

    // First login to get token
    const loginResponse = await request.post('http://localhost:3000/api/auth/login', {
      data: {
        email: 'admin@example.com',
        password: 'admin123'
      }
    });

    expect(loginResponse.ok()).toBeTruthy();
    const cookies = await loginResponse.headerValue('set-cookie');
    console.log('✓ Login successful');

    // Test various endpoints
    const endpoints = [
      '/api/admin/analytics/overview',
      '/api/admin/analytics/audit-logs?page=1&page_size=10',
      '/api/health',
    ];

    console.log('\n=== Testing Endpoints ===');
    for (const endpoint of endpoints) {
      const response = await request.get(`http://localhost:3000${endpoint}`, {
        headers: {
          'Cookie': cookies || ''
        }
      });

      const status = response.status();
      const symbol = status < 400 ? '✅' : '❌';
      console.log(`${symbol} ${endpoint} -> ${status}`);

      if (status >= 400) {
        const body = await response.text();
        console.log(`   Response: ${body.substring(0, 200)}`);
      }
    }
  });
});
