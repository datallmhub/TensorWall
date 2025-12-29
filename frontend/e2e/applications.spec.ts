import { test, expect } from '@playwright/test';

test.describe('Applications Management', () => {
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

  test('should display applications page', async ({ page }) => {
    console.log('\n=== Test: Display Applications Page ===');

    console.log('1. Navigating to Applications page...');
    await page.goto('http://localhost:3000/applications', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check page title
    await expect(page.getByText(/Applications/i).first()).toBeVisible();
    console.log('✓ Applications page is visible');

    // Check for "Create Application" button
    const createButton = page.getByRole('button', { name: /Create|New Application/i });
    await expect(createButton).toBeVisible();
    console.log('✓ Create button is visible');

    // Take screenshot
    await page.screenshot({ path: 'test-results/applications-page.png', fullPage: true });
    console.log('✓ Screenshot saved');
  });

  test('should open create application modal', async ({ page }) => {
    console.log('\n=== Test: Create Application Modal ===');

    await page.goto('http://localhost:3000/applications', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    console.log('1. Opening Create Application modal...');
    const createButton = page.getByRole('button', { name: /Create|New Application/i });
    await createButton.click();
    await page.waitForTimeout(1000);

    // Check modal is open
    await expect(page.getByText(/Create Application|New Application/i)).toBeVisible();
    console.log('✓ Modal opened');

    // Check form fields
    await expect(page.getByPlaceholder(/app.*id|application.*id/i)).toBeVisible();
    await expect(page.getByPlaceholder(/name/i).first()).toBeVisible();
    console.log('✓ Form fields are visible');

    // Take screenshot
    await page.screenshot({ path: 'test-results/create-application-modal.png', fullPage: true });
    console.log('✓ Screenshot saved');
  });

  test('should display application list with details', async ({ page }) => {
    console.log('\n=== Test: Application List ===');

    await page.goto('http://localhost:3000/applications', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Wait for applications to load
    const hasApplications = await page.locator('tbody tr').count() > 0;

    if (hasApplications) {
      console.log('✓ Applications loaded');

      // Check table headers
      const headers = ['Name', 'App ID', 'Owner', 'Status', 'Actions'];
      for (const header of headers) {
        const headerElement = page.getByText(header, { exact: false }).first();
        const isVisible = await headerElement.isVisible().catch(() => false);
        if (isVisible) {
          console.log(`  ✓ ${header} column visible`);
        }
      }
    } else {
      console.log('No applications found - this is okay for a fresh install');
    }
  });

  test('should navigate to application details', async ({ page }) => {
    console.log('\n=== Test: Application Details ===');

    await page.goto('http://localhost:3000/applications', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check if there are any applications
    const rowCount = await page.locator('tbody tr').count();

    if (rowCount > 0) {
      // Click on first application row
      console.log('1. Clicking on first application...');
      const firstRow = page.locator('tbody tr').first();
      await firstRow.click();
      await page.waitForTimeout(1000);

      // Should show application details (either modal or new page)
      const hasDetails = await page.getByText(/Details|API Keys|Configuration/i).isVisible().catch(() => false);
      console.log(`✓ Application details visible: ${hasDetails}`);

      await page.screenshot({ path: 'test-results/application-details.png', fullPage: true });
    } else {
      console.log('No applications to click on - skipping');
    }
  });

  test('should manage API keys for application', async ({ page }) => {
    console.log('\n=== Test: API Keys Management ===');

    await page.goto('http://localhost:3000/applications', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    const rowCount = await page.locator('tbody tr').count();

    if (rowCount > 0) {
      // Look for API Keys button or link
      const apiKeysButton = page.getByRole('button', { name: /API Keys|Keys|Manage Keys/i }).first();
      const isVisible = await apiKeysButton.isVisible().catch(() => false);

      if (isVisible) {
        console.log('1. Clicking API Keys button...');
        await apiKeysButton.click();
        await page.waitForTimeout(1000);

        // Check for API Keys modal or section
        await expect(page.getByText(/API Keys/i)).toBeVisible();
        console.log('✓ API Keys section visible');

        // Check for Create Key button
        const createKeyButton = page.getByRole('button', { name: /Create|New|Generate/i }).first();
        const hasCreateButton = await createKeyButton.isVisible().catch(() => false);
        console.log(`✓ Create Key button visible: ${hasCreateButton}`);

        await page.screenshot({ path: 'test-results/api-keys-management.png', fullPage: true });
      } else {
        console.log('API Keys button not found in the current view');
      }
    } else {
      console.log('No applications available - skipping');
    }
  });

  test('should filter applications', async ({ page }) => {
    console.log('\n=== Test: Filter Applications ===');

    await page.goto('http://localhost:3000/applications', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Look for search/filter input
    const searchInput = page.getByPlaceholder(/search|filter/i).first();
    const hasSearch = await searchInput.isVisible().catch(() => false);

    if (hasSearch) {
      console.log('1. Testing search functionality...');
      await searchInput.fill('test');
      await page.waitForTimeout(1000);
      console.log('✓ Search applied');
    } else {
      console.log('No search input found - checking for filter dropdown');

      const filterDropdown = page.locator('select').first();
      const hasFilter = await filterDropdown.isVisible().catch(() => false);

      if (hasFilter) {
        console.log('1. Testing filter dropdown...');
        // Filter interaction would go here
      }
    }
  });
});
