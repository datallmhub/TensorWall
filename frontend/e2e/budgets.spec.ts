import { test, expect } from '@playwright/test';

test.describe('Budgets Page', () => {
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

  test('should display budgets page with table view', async ({ page }) => {
    console.log('\n=== Test: Display Budgets Page ===');

    console.log('1. Navigating to Budgets page...');
    await page.goto('http://localhost:3000/budgets', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check page title
    await expect(page.getByText(/Cost Management/i).first()).toBeVisible();
    console.log('✓ Budgets page is visible');

    // Check for "Create Budget" button
    const createButton = page.getByRole('button', { name: /Create Budget/i });
    await expect(createButton).toBeVisible();
    console.log('✓ "Create Budget" button is visible');

    // Check for table headers
    await expect(page.getByText(/Scope/i)).toBeVisible();
    await expect(page.getByText(/Target/i)).toBeVisible();
    await expect(page.getByText(/Application/i)).toBeVisible();
    await expect(page.getByText(/Period/i)).toBeVisible();
    console.log('✓ Table headers are visible');
  });

  test('should open budget details modal when clicking on a row', async ({ page }) => {
    console.log('\n=== Test: Open Budget Details Modal ===');

    console.log('1. Navigating to Budgets page...');
    await page.goto('http://localhost:3000/budgets', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Wait for budgets to load
    await page.waitForSelector('tbody tr', { timeout: 5000 });
    console.log('✓ Budgets loaded');

    // Click on the first budget row (but not on buttons)
    console.log('2. Clicking on first budget row...');
    const firstRow = page.locator('tbody tr').first();
    const firstCell = firstRow.locator('td').first();
    await firstCell.click();
    await page.waitForTimeout(1000);

    // Check if modal opened
    await expect(page.getByText(/Budget Details/i)).toBeVisible();
    console.log('✓ Budget Details modal opened');

    // Check for stats cards
    await expect(page.getByText(/Current Spend/i)).toBeVisible();
    await expect(page.getByText(/Remaining/i)).toBeVisible();
    await expect(page.getByText(/Soft Limit/i)).toBeVisible();
    await expect(page.getByText(/Hard Limit/i)).toBeVisible();
    console.log('✓ Stats cards are visible');

    // Check for Period Information
    await expect(page.getByText(/Period Information/i)).toBeVisible();
    console.log('✓ Period Information is visible');

    // Check for Alert Configuration
    await expect(page.getByText(/Alert Configuration/i)).toBeVisible();
    console.log('✓ Alert Configuration is visible');

    // Take screenshot
    await page.screenshot({ path: 'test-results/budget-details-modal.png', fullPage: true });
    console.log('✓ Screenshot saved');
  });

  test('should close budget details modal when clicking close button', async ({ page }) => {
    console.log('\n=== Test: Close Budget Details Modal ===');

    await page.goto('http://localhost:3000/budgets', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Open modal
    const firstRow = page.locator('tbody tr').first();
    const firstCell = firstRow.locator('td').first();
    await firstCell.click();
    await page.waitForTimeout(1000);

    // Check modal is open
    await expect(page.getByText(/Budget Details/i)).toBeVisible();
    console.log('✓ Modal opened');

    // Click close button
    console.log('2. Clicking close button...');
    await page.getByRole('button', { name: /close/i }).click();
    await page.waitForTimeout(500);

    // Check modal is closed
    const modalVisible = await page.getByText(/Budget Details/i).isVisible().catch(() => false);
    expect(modalVisible).toBe(false);
    console.log('✓ Modal closed successfully');
  });

  test('should not open modal when clicking action buttons', async ({ page }) => {
    console.log('\n=== Test: Action Buttons Do Not Open Modal ===');

    await page.goto('http://localhost:3000/budgets', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Click on Edit button in first row
    console.log('1. Clicking Edit button...');
    const editButton = page.locator('tbody tr').first().getByTitle('Edit');
    await editButton.click();
    await page.waitForTimeout(1000);

    // Check that Edit Modal opened (not Details Modal)
    const editModalVisible = await page.getByText(/Edit Budget/i).isVisible();
    const detailsModalVisible = await page.getByText(/Budget Details/i).isVisible().catch(() => false);

    expect(editModalVisible).toBe(true);
    expect(detailsModalVisible).toBe(false);
    console.log('✓ Edit modal opened, details modal did not open');

    // Close edit modal
    await page.getByRole('button', { name: /cancel/i }).click();
    await page.waitForTimeout(500);
  });

  test('should filter budgets by application', async ({ page }) => {
    console.log('\n=== Test: Filter Budgets ===');

    await page.goto('http://localhost:3000/budgets', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Count initial budgets
    const initialCount = await page.locator('tbody tr').count();
    console.log(`Initial budget count: ${initialCount}`);

    // Select application filter
    console.log('1. Applying application filter...');
    const appFilter = page.locator('select').filter({ hasText: /All Applications/i });
    await appFilter.selectOption('test-app');
    await page.waitForTimeout(1000);

    // Count filtered budgets
    const filteredCount = await page.locator('tbody tr').count();
    console.log(`Filtered budget count: ${filteredCount}`);

    // Should have fewer or equal budgets
    expect(filteredCount).toBeLessThanOrEqual(initialCount);
    console.log('✓ Filter applied successfully');

    // Clear filter
    console.log('2. Clearing filter...');
    await page.getByRole('button', { name: /Clear filters/i }).click();
    await page.waitForTimeout(1000);

    const clearedCount = await page.locator('tbody tr').count();
    expect(clearedCount).toBe(initialCount);
    console.log('✓ Filter cleared successfully');
  });

  test('should display summary statistics cards', async ({ page }) => {
    console.log('\n=== Test: Summary Statistics ===');

    await page.goto('http://localhost:3000/budgets', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check for summary cards
    await expect(page.getByText(/Total Spend/i)).toBeVisible();
    await expect(page.getByText(/Total Limit/i)).toBeVisible();
    await expect(page.getByText(/Over Budget/i)).toBeVisible();
    await expect(page.getByText(/Warnings/i)).toBeVisible();
    console.log('✓ All summary cards are visible');

    // Take screenshot
    await page.screenshot({ path: 'test-results/budgets-summary.png', fullPage: true });
    console.log('✓ Screenshot saved');
  });
});
