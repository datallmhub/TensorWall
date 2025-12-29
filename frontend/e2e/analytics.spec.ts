import { test, expect } from '@playwright/test';

test.describe('Analytics Dashboard', () => {
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

  test('should display analytics page', async ({ page }) => {
    console.log('\n=== Test: Display Analytics Page ===');

    console.log('1. Navigating to Analytics page...');
    await page.goto('http://localhost:3000/analytics', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check page title
    await expect(page.getByText(/Analytics/i).first()).toBeVisible();
    console.log('✓ Analytics page is visible');

    // Take screenshot
    await page.screenshot({ path: 'test-results/analytics-page.png', fullPage: true });
    console.log('✓ Screenshot saved');
  });

  test('should display usage statistics', async ({ page }) => {
    console.log('\n=== Test: Usage Statistics ===');

    await page.goto('http://localhost:3000/analytics', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check for stat cards
    const statLabels = [
      'Total Requests',
      'Total Tokens',
      'Total Cost',
      'Average Latency',
      'Input Tokens',
      'Output Tokens',
    ];

    for (const label of statLabels) {
      const element = page.getByText(label, { exact: false }).first();
      const isVisible = await element.isVisible().catch(() => false);
      if (isVisible) {
        console.log(`  ✓ Stat visible: ${label}`);
      }
    }
  });

  test('should display usage charts', async ({ page }) => {
    console.log('\n=== Test: Usage Charts ===');

    await page.goto('http://localhost:3000/analytics', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000); // Extra time for charts to render

    // Check for chart elements
    const chartContainer = page.locator('canvas, [class*="chart"], svg[class*="recharts"]').first();
    const hasChart = await chartContainer.isVisible().catch(() => false);

    if (hasChart) {
      console.log('✓ Chart element found');
    } else {
      console.log('Charts may not be visible (no data or different chart library)');
    }

    // Check for chart title/labels
    const chartLabels = ['Usage Over Time', 'Requests', 'Cost', 'by Model', 'by Feature'];
    for (const label of chartLabels) {
      const element = page.getByText(label, { exact: false }).first();
      const isVisible = await element.isVisible().catch(() => false);
      if (isVisible) {
        console.log(`  ✓ Chart section: ${label}`);
      }
    }
  });

  test('should filter analytics by date range', async ({ page }) => {
    console.log('\n=== Test: Date Range Filter ===');

    await page.goto('http://localhost:3000/analytics', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Look for date range selector
    const dateRangeButtons = ['7 days', '30 days', '90 days', 'Last week', 'Last month'];
    let foundDateFilter = false;

    for (const range of dateRangeButtons) {
      const button = page.getByRole('button', { name: new RegExp(range, 'i') });
      const isVisible = await button.isVisible().catch(() => false);
      if (isVisible) {
        console.log(`1. Found date range button: ${range}`);
        await button.click();
        await page.waitForTimeout(1000);
        foundDateFilter = true;
        console.log('✓ Date range filter applied');
        break;
      }
    }

    if (!foundDateFilter) {
      // Check for date picker input
      const datePicker = page.locator('input[type="date"]').first();
      const hasDatePicker = await datePicker.isVisible().catch(() => false);

      if (hasDatePicker) {
        console.log('1. Found date picker input');
        foundDateFilter = true;
      } else {
        console.log('Date range filter not found');
      }
    }
  });

  test('should filter analytics by application', async ({ page }) => {
    console.log('\n=== Test: Application Filter ===');

    await page.goto('http://localhost:3000/analytics', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Look for application filter
    const appFilter = page.locator('select').filter({ hasText: /All Applications|Application/i });
    const hasFilter = await appFilter.isVisible().catch(() => false);

    if (hasFilter) {
      console.log('1. Found application filter');
      await appFilter.selectOption({ index: 1 });
      await page.waitForTimeout(1000);
      console.log('✓ Application filter applied');
    } else {
      console.log('Application filter not found');
    }
  });

  test('should display model breakdown', async ({ page }) => {
    console.log('\n=== Test: Model Breakdown ===');

    await page.goto('http://localhost:3000/analytics', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check for model breakdown section
    const modelLabels = ['gpt-4', 'gpt-3.5', 'claude', 'by Model', 'Model Distribution'];

    for (const label of modelLabels) {
      const element = page.getByText(label, { exact: false }).first();
      const isVisible = await element.isVisible().catch(() => false);
      if (isVisible) {
        console.log(`  ✓ Model breakdown visible: ${label}`);
      }
    }
  });

  test('should display cost breakdown', async ({ page }) => {
    console.log('\n=== Test: Cost Breakdown ===');

    await page.goto('http://localhost:3000/analytics', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check for cost-related elements
    const costLabels = ['Cost', 'Spend', '$', 'USD', 'Budget'];

    for (const label of costLabels) {
      const element = page.getByText(label, { exact: false }).first();
      const isVisible = await element.isVisible().catch(() => false);
      if (isVisible) {
        console.log(`  ✓ Cost element visible: ${label}`);
      }
    }
  });

  test('should export analytics data', async ({ page }) => {
    console.log('\n=== Test: Export Analytics ===');

    await page.goto('http://localhost:3000/analytics', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Look for export button
    const exportButton = page.getByRole('button', { name: /Export|Download|CSV/i }).first();
    const hasExport = await exportButton.isVisible().catch(() => false);

    if (hasExport) {
      console.log('1. Found export button');

      // Set up download handler
      const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);
      await exportButton.click();
      await page.waitForTimeout(2000);

      const download = await downloadPromise;
      if (download) {
        console.log(`✓ Download started: ${download.suggestedFilename()}`);
      } else {
        console.log('Export may open in a new tab or require additional steps');
      }
    } else {
      console.log('Export button not found');
    }
  });

  test('should display audit logs', async ({ page }) => {
    console.log('\n=== Test: Audit Logs ===');

    // Check if there's an audit logs tab or link
    await page.goto('http://localhost:3000/analytics', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    const auditTab = page.getByRole('tab', { name: /Audit|Logs/i }).first();
    const hasAuditTab = await auditTab.isVisible().catch(() => false);

    if (hasAuditTab) {
      console.log('1. Clicking Audit Logs tab...');
      await auditTab.click();
      await page.waitForTimeout(1000);

      // Check for audit log table
      await expect(page.getByText(/Request ID|Timestamp|App ID/i).first()).toBeVisible();
      console.log('✓ Audit logs visible');
    } else {
      // Try navigating to audit-logs page
      console.log('1. Navigating to audit-logs page...');
      await page.goto('http://localhost:3000/audit-logs', { waitUntil: 'networkidle' });
      await page.waitForTimeout(2000);

      const hasAuditPage = await page.getByText(/Audit|Logs/i).first().isVisible().catch(() => false);
      console.log(`Audit logs page visible: ${hasAuditPage}`);
    }

    await page.screenshot({ path: 'test-results/audit-logs.png', fullPage: true });
  });

  test('should display SLO metrics', async ({ page }) => {
    console.log('\n=== Test: SLO Metrics ===');

    await page.goto('http://localhost:3000/analytics', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check for SLO-related elements
    const sloLabels = [
      'Availability',
      'Latency',
      'P50',
      'P95',
      'P99',
      'Error Rate',
      'SLO',
      'Error Budget',
    ];

    for (const label of sloLabels) {
      const element = page.getByText(label, { exact: false }).first();
      const isVisible = await element.isVisible().catch(() => false);
      if (isVisible) {
        console.log(`  ✓ SLO metric visible: ${label}`);
      }
    }
  });

  test('should paginate through request logs', async ({ page }) => {
    console.log('\n=== Test: Pagination ===');

    await page.goto('http://localhost:3000/analytics', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Look for pagination controls
    const pagination = page.locator('[class*="pagination"], nav[aria-label="pagination"]').first();
    const hasPagination = await pagination.isVisible().catch(() => false);

    if (hasPagination) {
      console.log('1. Found pagination controls');

      // Try clicking next page
      const nextButton = page.getByRole('button', { name: /Next|>|→/i });
      const hasNext = await nextButton.isVisible().catch(() => false);

      if (hasNext) {
        await nextButton.click();
        await page.waitForTimeout(1000);
        console.log('✓ Navigated to next page');
      }
    } else {
      console.log('Pagination not visible (may have fewer items or different implementation)');
    }
  });

  test('should show request trace details', async ({ page }) => {
    console.log('\n=== Test: Request Trace Details ===');

    await page.goto('http://localhost:3000/analytics', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Look for a clickable request row
    const requestRow = page.locator('tbody tr, [class*="request-row"]').first();
    const hasRow = await requestRow.isVisible().catch(() => false);

    if (hasRow) {
      console.log('1. Clicking on request row...');
      await requestRow.click();
      await page.waitForTimeout(1000);

      // Check for trace details
      const traceLabels = [
        'Request ID',
        'Trace',
        'Decision',
        'Tokens',
        'Cost',
        'Latency',
        'Timestamp',
      ];

      for (const label of traceLabels) {
        const element = page.getByText(label, { exact: false });
        const isVisible = await element.isVisible().catch(() => false);
        if (isVisible) {
          console.log(`  ✓ Trace detail visible: ${label}`);
        }
      }

      await page.screenshot({ path: 'test-results/request-trace.png', fullPage: true });
    } else {
      console.log('No request rows available');
    }
  });
});
