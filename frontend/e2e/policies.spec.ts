import { test, expect } from '@playwright/test';

test.describe('Guardrails (Policies)', () => {
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

    // Wait for navigation
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000); // Extra wait for auth to settle

    // Should be on dashboard
    await page.waitForURL('http://localhost:3000/', { timeout: 10000 });
    console.log('✓ Logged in successfully');
  });

  test('should display guardrails page', async ({ page }) => {
    console.log('\n=== Test: Display Guardrails Page ===');

    console.log('1. Navigating to Guardrails page...');
    await page.goto('http://localhost:3000/policies', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check page title
    await expect(page.getByText(/Guardrails/i).first()).toBeVisible();
    console.log('✓ Guardrails page is visible');

    // Check for "New Guardrail" button
    const newButton = page.getByRole('button', { name: /New Guardrail/i });
    await expect(newButton).toBeVisible();
    console.log('✓ "New Guardrail" button is visible');

    // Check for table headers
    await expect(page.getByText(/App ID/i)).toBeVisible();
    await expect(page.getByText(/User Email/i)).toBeVisible();
    await expect(page.getByText(/Priority/i)).toBeVisible();
    console.log('✓ Table headers are visible');
  });

  test('should create a guardrail without user email', async ({ page }) => {
    console.log('\n=== Test: Create Guardrail (All Users) ===');

    // Track API requests
    const requests: { url: string; status: number; method: string }[] = [];
    page.on('response', async (response) => {
      const url = response.url();
      const status = response.status();
      const method = response.request().method();

      if (url.includes('/api/admin/policies')) {
        requests.push({ url, status, method });
        console.log(`API Call: ${method} ${url} -> ${status}`);
      }
    });

    console.log('1. Navigating to Guardrails page...');
    await page.goto('http://localhost:3000/policies', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    console.log('2. Opening Create Guardrail modal...');
    await page.getByRole('button', { name: /New Guardrail/i }).click();
    await page.waitForTimeout(1000);

    // Check modal is open
    await expect(page.getByText(/Create Guardrail/i)).toBeVisible();
    console.log('✓ Modal opened');

    // Fill in form
    console.log('3. Filling form...');
    await page.getByPlaceholder(/Block GPT-4/i).fill('E2E Test Policy');

    // Select application from dropdown
    await page.locator('select').first().selectOption('test-app');
    console.log('   - Selected application: test-app');

    // Leave user email empty (applies to all users)
    console.log('   - User email: empty (all users)');

    // Select action
    await page.locator('select').filter({ hasText: /Allow.*Warn.*Deny/ }).selectOption('deny');
    console.log('   - Action: deny');

    // Set priority
    await page.locator('input[type="number"]').fill('150');
    console.log('   - Priority: 150');

    console.log('4. Submitting form...');
    await page.getByRole('button', { name: /^Create$/i }).click();

    // Wait for modal to close
    await page.waitForTimeout(3000);

    // Check modal is closed
    const modalVisible = await page.getByText(/Create Guardrail/i).isVisible().catch(() => false);
    expect(modalVisible).toBe(false);
    console.log('✓ Modal closed after creation');

    // Check API requests
    const createRequest = requests.find(r => r.method === 'POST' && r.url.includes('/admin/policies'));
    if (createRequest) {
      console.log(`✓ POST request sent: ${createRequest.status}`);
      expect(createRequest.status).toBe(201);
    } else {
      console.log('✗ No POST request found');
    }

    // Check the policy appears in the table
    await page.waitForTimeout(2000);
    await expect(page.getByText('E2E Test Policy')).toBeVisible();
    console.log('✓ New policy appears in the table');

    // Verify "All users" is displayed
    const allUsersText = page.locator('text=All users').first();
    await expect(allUsersText).toBeVisible();
    console.log('✓ "All users" label is visible for policy without user_email');
  });

  test('should create a guardrail with specific user email', async ({ page }) => {
    console.log('\n=== Test: Create Guardrail (Specific User) ===');

    // Track API requests
    const requests: { url: string; status: number; method: string; body?: any }[] = [];
    page.on('request', async (request) => {
      if (request.url().includes('/api/admin/policies') && request.method() === 'POST') {
        try {
          const body = request.postDataJSON();
          console.log('Request body:', JSON.stringify(body, null, 2));
        } catch (e) {
          // Ignore if not JSON
        }
      }
    });

    page.on('response', async (response) => {
      const url = response.url();
      const status = response.status();
      const method = response.request().method();

      if (url.includes('/api/admin/policies')) {
        requests.push({ url, status, method });
        console.log(`API Call: ${method} ${url} -> ${status}`);
      }
    });

    console.log('1. Navigating to Guardrails page...');
    await page.goto('http://localhost:3000/policies', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    console.log('2. Opening Create Guardrail modal...');
    await page.getByRole('button', { name: /New Guardrail/i }).click();
    await page.waitForTimeout(1000);

    // Fill in form with user email
    console.log('3. Filling form with user email...');
    await page.getByPlaceholder(/Block GPT-4/i).fill('User-Specific Policy');

    // Select application
    await page.locator('select').first().selectOption('test-app');
    console.log('   - Selected application: test-app');

    // Enter user email
    await page.getByPlaceholder(/user@example.com/i).fill('testuser@example.com');
    console.log('   - User email: testuser@example.com');

    // Select action
    await page.locator('select').filter({ hasText: /Allow.*Warn.*Deny/ }).selectOption('warn');
    console.log('   - Action: warn');

    // Set priority
    await page.locator('input[type="number"]').fill('200');
    console.log('   - Priority: 200');

    console.log('4. Submitting form...');
    await page.getByRole('button', { name: /^Create$/i }).click();

    // Wait for modal to close
    await page.waitForTimeout(3000);

    // Check API request was successful
    const createRequest = requests.find(r => r.method === 'POST');
    if (createRequest) {
      console.log(`✓ POST request sent: ${createRequest.status}`);
      expect(createRequest.status).toBe(201);
    }

    // Check the policy appears in the table
    await page.waitForTimeout(2000);
    await expect(page.getByText('User-Specific Policy')).toBeVisible();
    console.log('✓ New user-specific policy appears in the table');

    // Verify user email is displayed
    await expect(page.getByText('testuser@example.com')).toBeVisible();
    console.log('✓ User email is displayed in the table');

    // Take screenshot
    await page.screenshot({ path: 'test-results/policies-with-user-email.png', fullPage: true });
    console.log('✓ Screenshot saved');
  });

  test('should display all policy fields correctly', async ({ page }) => {
    console.log('\n=== Test: Display Policy Fields ===');

    await page.goto('http://localhost:3000/policies', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check table columns
    const columns = [
      'Name',
      'App ID',
      'User Email',
      'Type',
      'Action',
      'Priority',
      'Status',
      'Actions'
    ];

    console.log('Checking table columns:');
    for (const column of columns) {
      const columnHeader = page.getByText(column, { exact: false }).first();
      await expect(columnHeader).toBeVisible();
      console.log(`  ✓ ${column}`);
    }

    // Take screenshot
    await page.screenshot({ path: 'test-results/policies-table.png', fullPage: true });
    console.log('✓ Screenshot saved');
  });

  test('should show validation when required fields are missing', async ({ page }) => {
    console.log('\n=== Test: Form Validation ===');

    await page.goto('http://localhost:3000/policies', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    console.log('1. Opening Create Guardrail modal...');
    await page.getByRole('button', { name: /New Guardrail/i }).click();
    await page.waitForTimeout(1000);

    // Check Create button is disabled when form is empty
    const createButton = page.getByRole('button', { name: /^Create$/i });
    const isDisabled = await createButton.isDisabled();
    expect(isDisabled).toBe(true);
    console.log('✓ Create button is disabled when form is empty');

    // Fill only name
    await page.getByPlaceholder(/Block GPT-4/i).fill('Test');
    const stillDisabled = await createButton.isDisabled();
    expect(stillDisabled).toBe(true);
    console.log('✓ Create button is disabled when app is not selected');

    // Select app
    await page.locator('select').first().selectOption('test-app');
    await page.waitForTimeout(500);

    const nowEnabled = await createButton.isDisabled();
    expect(nowEnabled).toBe(false);
    console.log('✓ Create button is enabled when required fields are filled');
  });

  test('should handle API errors gracefully', async ({ page }) => {
    console.log('\n=== Test: Error Handling ===');

    await page.goto('http://localhost:3000/policies', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    console.log('1. Opening Create Guardrail modal...');
    await page.getByRole('button', { name: /New Guardrail/i }).click();
    await page.waitForTimeout(1000);

    // Fill form with invalid data (very long name to trigger validation error)
    await page.getByPlaceholder(/Block GPT-4/i).fill('a'.repeat(300)); // Exceeds max_length=255
    await page.locator('select').first().selectOption('test-app');

    console.log('2. Submitting form with invalid data...');
    await page.getByRole('button', { name: /^Create$/i }).click();
    await page.waitForTimeout(2000);

    // Check if error message appears or modal stays open
    const modalStillOpen = await page.getByText(/Create Guardrail/i).isVisible();
    console.log(`Modal still open after error: ${modalStillOpen}`);

    // Modal should stay open on error
    expect(modalStillOpen).toBe(true);
    console.log('✓ Modal stays open when there is an error');
  });
});
