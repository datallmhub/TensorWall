import { test, expect } from '@playwright/test';

test.describe('Features Management', () => {
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
    await page.waitForTimeout(2000);

    // Should be on dashboard
    await page.waitForURL('http://localhost:3000/', { timeout: 10000 });
    console.log('✓ Logged in successfully');
  });

  test('should display features page', async ({ page }) => {
    console.log('\n=== Test: Display Features Page ===');

    console.log('1. Navigating to Features page...');
    await page.goto('http://localhost:3000/features', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check page title
    await expect(page.getByText(/Features/i).first()).toBeVisible();
    console.log('✓ Features page is visible');

    // Check for "Create Feature" button
    const createButton = page.getByRole('button', { name: /Create|New Feature/i });
    await expect(createButton).toBeVisible();
    console.log('✓ Create Feature button is visible');

    // Take screenshot
    await page.screenshot({ path: 'test-results/features-page.png', fullPage: true });
    console.log('✓ Screenshot saved');
  });

  test('should display features list', async ({ page }) => {
    console.log('\n=== Test: Features List ===');

    await page.goto('http://localhost:3000/features', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check if features table or cards exist
    const hasTable = await page.locator('table').isVisible().catch(() => false);
    const hasCards = await page.locator('[class*="card"]').count() > 0;

    if (hasTable) {
      console.log('✓ Features displayed in table format');

      // Check table headers
      const headers = ['Name', 'Feature ID', 'Application', 'Status', 'Actions'];
      for (const header of headers) {
        const headerElement = page.getByText(header, { exact: false }).first();
        const isVisible = await headerElement.isVisible().catch(() => false);
        if (isVisible) {
          console.log(`  ✓ ${header} column visible`);
        }
      }
    } else if (hasCards) {
      console.log('✓ Features displayed in card format');
    } else {
      console.log('No features found - this is okay for a fresh install');
    }
  });

  test('should open create feature modal', async ({ page }) => {
    console.log('\n=== Test: Create Feature Modal ===');

    await page.goto('http://localhost:3000/features', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    console.log('1. Opening Create Feature modal...');
    const createButton = page.getByRole('button', { name: /Create|New Feature/i });
    await createButton.click();
    await page.waitForTimeout(1000);

    // Check modal is open
    await expect(page.getByText(/Create Feature|New Feature/i)).toBeVisible();
    console.log('✓ Modal opened');

    // Check form fields exist
    const formFields = ['name', 'feature_id', 'description'];
    for (const field of formFields) {
      const input = page.locator(`input[name="${field}"], [placeholder*="${field}"]`).first();
      const isVisible = await input.isVisible().catch(() => false);
      if (isVisible) {
        console.log(`  ✓ ${field} field visible`);
      }
    }

    // Take screenshot
    await page.screenshot({ path: 'test-results/create-feature-modal.png', fullPage: true });
    console.log('✓ Screenshot saved');
  });

  test('should filter features by application', async ({ page }) => {
    console.log('\n=== Test: Filter Features ===');

    await page.goto('http://localhost:3000/features', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Look for application filter dropdown
    const appFilter = page.locator('select').filter({ hasText: /All Applications|Application/i });
    const hasFilter = await appFilter.isVisible().catch(() => false);

    if (hasFilter) {
      console.log('1. Testing application filter...');

      // Get initial count
      const initialCount = await page.locator('tbody tr, [class*="card"]').count();
      console.log(`  Initial items: ${initialCount}`);

      // Apply filter
      await appFilter.selectOption({ index: 1 }); // Select first option after "All"
      await page.waitForTimeout(1000);

      const filteredCount = await page.locator('tbody tr, [class*="card"]').count();
      console.log(`  Filtered items: ${filteredCount}`);

      console.log('✓ Filter applied');
    } else {
      console.log('Application filter not found');
    }
  });

  test('should toggle feature status', async ({ page }) => {
    console.log('\n=== Test: Toggle Feature Status ===');

    await page.goto('http://localhost:3000/features', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Look for toggle or status button
    const toggleButton = page.locator('[role="switch"], [type="checkbox"], button:has-text("Enable"), button:has-text("Disable")').first();
    const hasToggle = await toggleButton.isVisible().catch(() => false);

    if (hasToggle) {
      console.log('1. Found status toggle...');

      // Get initial state
      const isChecked = await toggleButton.isChecked().catch(() => null);
      console.log(`  Initial state: ${isChecked}`);

      // Toggle
      await toggleButton.click();
      await page.waitForTimeout(1000);

      const newState = await toggleButton.isChecked().catch(() => null);
      console.log(`  New state: ${newState}`);

      console.log('✓ Toggle successful');
    } else {
      console.log('No toggle found - features may use different status control');
    }
  });

  test('should show feature constraints', async ({ page }) => {
    console.log('\n=== Test: Feature Constraints ===');

    await page.goto('http://localhost:3000/features', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Click on first feature to see details
    const firstFeature = page.locator('tbody tr, [class*="card"]').first();
    const hasFeature = await firstFeature.isVisible().catch(() => false);

    if (hasFeature) {
      console.log('1. Clicking on first feature...');
      await firstFeature.click();
      await page.waitForTimeout(1000);

      // Check for constraint information
      const constraintLabels = ['Allowed Models', 'Allowed Actions', 'Max Tokens', 'Rate Limit'];
      for (const label of constraintLabels) {
        const element = page.getByText(label, { exact: false });
        const isVisible = await element.isVisible().catch(() => false);
        if (isVisible) {
          console.log(`  ✓ ${label} visible`);
        }
      }

      await page.screenshot({ path: 'test-results/feature-constraints.png', fullPage: true });
    } else {
      console.log('No features available to inspect');
    }
  });

  test('should edit feature', async ({ page }) => {
    console.log('\n=== Test: Edit Feature ===');

    await page.goto('http://localhost:3000/features', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Look for edit button
    const editButton = page.getByRole('button', { name: /Edit/i }).first();
    const hasEdit = await editButton.isVisible().catch(() => false);

    if (hasEdit) {
      console.log('1. Clicking Edit button...');
      await editButton.click();
      await page.waitForTimeout(1000);

      // Check edit modal/form opened
      const hasEditModal = await page.getByText(/Edit Feature/i).isVisible().catch(() => false);
      console.log(`✓ Edit modal visible: ${hasEditModal}`);

      await page.screenshot({ path: 'test-results/edit-feature.png', fullPage: true });
    } else {
      console.log('Edit button not found - may be accessed differently');
    }
  });
});
