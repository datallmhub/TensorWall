import { test, expect } from '@playwright/test';

test.describe('Guardrails Creation', () => {
  test('should create a guardrail with user email', async ({ page, context }) => {
    console.log('\n=== Test: Create Guardrail with User Email ===');

    // Clear cookies first
    await context.clearCookies();

    // Login
    console.log('1. Logging in...');
    await page.goto('http://localhost:3000/login');
    await page.waitForLoadState('networkidle');

    await page.getByPlaceholder(/email/i).fill('admin@example.com');
    await page.getByPlaceholder(/password/i).fill('admin123');
    await page.getByRole('button', { name: /sign in/i }).click();

    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Navigate to Guardrails page
    console.log('2. Navigating to Guardrails page...');
    await page.goto('http://localhost:3000/policies', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check page loaded
    await expect(page.getByText(/Guardrails/i).first()).toBeVisible();
    console.log('✓ Guardrails page loaded');

    // Open modal
    console.log('3. Opening Create Guardrail modal...');
    await page.getByRole('button', { name: /New Guardrail/i }).click();
    await page.waitForTimeout(1000);

    await expect(page.getByText(/Create Guardrail/i)).toBeVisible();
    console.log('✓ Modal opened');

    // Fill form
    console.log('4. Filling form...');
    await page.getByPlaceholder(/Block GPT-4/i).fill('E2E Test Policy with User');

    // Select application
    await page.locator('select').first().selectOption('test-app');
    console.log('   - Application: test-app');

    // Fill user email
    await page.getByPlaceholder(/user@example.com/i).fill('e2etest@example.com');
    console.log('   - User email: e2etest@example.com');

    // Select action
    await page.locator('select').filter({ hasText: /Allow.*Warn.*Deny/ }).selectOption('warn');
    console.log('   - Action: warn');

    // Set priority
    await page.locator('input[type="number"]').fill('250');
    console.log('   - Priority: 250');

    // Submit
    console.log('5. Submitting...');
    await page.getByRole('button', { name: /^Create$/i }).click();
    await page.waitForTimeout(3000);

    // Check modal closed
    const modalClosed = await page.getByText(/Create Guardrail/i).isVisible().catch(() => false);
    expect(modalClosed).toBe(false);
    console.log('✓ Modal closed');

    // Check policy appears
    await page.waitForTimeout(2000);
    await expect(page.getByText('E2E Test Policy with User')).toBeVisible();
    console.log('✓ Policy appears in list');

    // Check user email is displayed
    await expect(page.getByText('e2etest@example.com')).toBeVisible();
    console.log('✓ User email is displayed');

    // Screenshot
    await page.screenshot({ path: 'test-results/guardrails-created.png', fullPage: true });
    console.log('✓ Screenshot saved');

    console.log('\n=== Test passed! ===');
  });
});
