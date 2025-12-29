import { test, expect } from '@playwright/test';

test.describe('Debug Policy Creation - Applications Dropdown', () => {
  test.beforeEach(async ({ page, context }) => {
    await context.clearCookies();

    // Login
    await page.goto('http://localhost:3000/login');
    await page.waitForLoadState('networkidle');
    await page.getByPlaceholder('admin@example.com').fill('admin@example.com');
    await page.getByPlaceholder('Enter your password').fill('admin123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForURL('http://localhost:3000/', { timeout: 10000 });
    console.log('✓ Logged in');
  });

  test('debug: check applications API response', async ({ page }) => {
    console.log('\n=== Debug: Applications API ===');

    // Listen to all API responses
    const apiResponses: { url: string; status: number; body?: any }[] = [];

    page.on('response', async (response) => {
      const url = response.url();
      if (url.includes('/admin/applications') || url.includes('/api/')) {
        const status = response.status();
        let body = null;
        try {
          body = await response.json();
        } catch (e) {
          // Not JSON
        }
        apiResponses.push({ url, status, body });
        console.log(`API Response: ${url} -> ${status}`);
        if (body) {
          console.log(`  Body: ${JSON.stringify(body).substring(0, 200)}...`);
        }
      }
    });

    // Navigate to policies page
    console.log('1. Navigating to policies page...');
    await page.goto('http://localhost:3000/policies', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Click New Guardrail button
    console.log('2. Opening modal...');
    await page.getByRole('button', { name: /New Guardrail/i }).click();
    await page.waitForTimeout(2000);

    // Check if modal is visible
    const modalVisible = await page.getByText(/Create Guardrail/i).isVisible();
    console.log(`Modal visible: ${modalVisible}`);

    // Find all select elements
    const selects = await page.locator('select').all();
    console.log(`\n3. Found ${selects.length} select elements`);

    for (let i = 0; i < selects.length; i++) {
      const select = selects[i];
      const options = await select.locator('option').all();
      console.log(`\n   Select #${i + 1}:`);
      console.log(`   - Options count: ${options.length}`);

      for (const option of options) {
        const text = await option.textContent();
        const value = await option.getAttribute('value');
        console.log(`     - "${text}" (value: ${value})`);
      }
    }

    // Take screenshot
    await page.screenshot({ path: 'test-results/policies-modal-debug.png', fullPage: true });
    console.log('\n✓ Screenshot saved to test-results/policies-modal-debug.png');

    // Check API responses
    console.log('\n4. API Responses Summary:');
    const appResponses = apiResponses.filter(r => r.url.includes('/admin/applications'));
    console.log(`   Applications API calls: ${appResponses.length}`);
    for (const r of appResponses) {
      console.log(`   - ${r.url} -> ${r.status}`);
      if (r.body && Array.isArray(r.body)) {
        console.log(`     Found ${r.body.length} applications`);
      }
    }
  });

  test('debug: check network requests during modal open', async ({ page }) => {
    console.log('\n=== Debug: Network Requests ===');

    // Track all requests
    const requests: string[] = [];
    page.on('request', (request) => {
      if (request.url().includes('localhost:8000')) {
        requests.push(`${request.method()} ${request.url()}`);
      }
    });

    await page.goto('http://localhost:3000/policies', { waitUntil: 'networkidle' });
    console.log('Page loaded');

    // Clear requests array
    requests.length = 0;

    // Open modal
    await page.getByRole('button', { name: /New Guardrail/i }).click();
    await page.waitForTimeout(3000);

    console.log('\nRequests made after opening modal:');
    requests.forEach(r => console.log(`  - ${r}`));

    // Check select options again
    const appSelect = page.locator('select').first();
    const options = await appSelect.locator('option').allTextContents();
    console.log(`\nApplication select options: ${JSON.stringify(options)}`);
  });

  test('should create policy for RAG Chat Production', async ({ page }) => {
    console.log('\n=== Test: Create Policy for RAG Chat Production ===');

    // Track API calls
    page.on('response', async (response) => {
      if (response.url().includes('/admin/')) {
        console.log(`API: ${response.request().method()} ${response.url()} -> ${response.status()}`);
      }
    });

    await page.goto('http://localhost:3000/policies', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Click New Guardrail
    await page.getByRole('button', { name: /New Guardrail/i }).click();
    await page.waitForTimeout(2000);

    // Screenshot of modal
    await page.screenshot({ path: 'test-results/create-policy-modal.png' });

    // Check what's in the select
    const appSelect = page.locator('select').first();
    const optionCount = await appSelect.locator('option').count();
    console.log(`Found ${optionCount} options in application select`);

    // Try to find rag-chat-prod
    const options = await appSelect.locator('option').allTextContents();
    console.log('Options:', options);

    // If rag-chat-prod exists, select it
    if (options.some(o => o.includes('rag-chat-prod') || o.includes('RAG Chat'))) {
      console.log('Found RAG Chat Production, selecting...');
      await appSelect.selectOption({ label: /RAG Chat Production/i });
    } else if (optionCount > 1) {
      // Select second option (first is usually empty/placeholder)
      const secondOption = await appSelect.locator('option').nth(1).getAttribute('value');
      if (secondOption) {
        await appSelect.selectOption(secondOption);
        console.log(`Selected: ${secondOption}`);
      }
    }

    // Fill other fields
    await page.getByPlaceholder(/Block GPT-4/i).fill('RAG Rate Limit Policy');

    // Take final screenshot
    await page.screenshot({ path: 'test-results/create-policy-filled.png' });
    console.log('✓ Screenshots saved');
  });
});
