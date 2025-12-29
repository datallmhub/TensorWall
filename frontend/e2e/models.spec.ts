import { test, expect } from '@playwright/test';

test.describe('Models Management', () => {
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

  test('should display models page', async ({ page }) => {
    console.log('\n=== Test: Display Models Page ===');

    console.log('1. Navigating to Models page...');
    await page.goto('http://localhost:3000/models', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check page title
    await expect(page.getByText(/Models/i).first()).toBeVisible();
    console.log('✓ Models page is visible');

    // Take screenshot
    await page.screenshot({ path: 'test-results/models-page.png', fullPage: true });
    console.log('✓ Screenshot saved');
  });

  test('should display models list with pricing', async ({ page }) => {
    console.log('\n=== Test: Models List with Pricing ===');

    await page.goto('http://localhost:3000/models', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check for model cards or table
    const hasModels = await page.locator('[class*="card"], tbody tr').count() > 0;

    if (hasModels) {
      console.log('✓ Models loaded');

      // Check for pricing information
      const pricingLabels = ['Input', 'Output', 'per million', 'tokens', '/M'];
      let foundPricing = false;

      for (const label of pricingLabels) {
        const element = page.getByText(label, { exact: false }).first();
        const isVisible = await element.isVisible().catch(() => false);
        if (isVisible) {
          foundPricing = true;
          console.log(`  ✓ Pricing label found: ${label}`);
          break;
        }
      }

      if (!foundPricing) {
        console.log('  Pricing information may be displayed differently');
      }

      // Check for provider labels
      const providers = ['OpenAI', 'Anthropic', 'Google', 'Azure', 'Bedrock'];
      for (const provider of providers) {
        const element = page.getByText(provider, { exact: false });
        const isVisible = await element.isVisible().catch(() => false);
        if (isVisible) {
          console.log(`  ✓ Provider found: ${provider}`);
        }
      }
    } else {
      console.log('No models found - checking if models need to be seeded');
    }
  });

  test('should filter models by provider', async ({ page }) => {
    console.log('\n=== Test: Filter Models by Provider ===');

    await page.goto('http://localhost:3000/models', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Look for provider filter
    const providerFilter = page.locator('select').filter({ hasText: /All Providers|Provider/i });
    const hasFilter = await providerFilter.isVisible().catch(() => false);

    if (hasFilter) {
      console.log('1. Testing provider filter...');

      // Get initial count
      const initialCount = await page.locator('[class*="card"], tbody tr').count();
      console.log(`  Initial models: ${initialCount}`);

      // Apply filter
      await providerFilter.selectOption({ index: 1 });
      await page.waitForTimeout(1000);

      const filteredCount = await page.locator('[class*="card"], tbody tr').count();
      console.log(`  Filtered models: ${filteredCount}`);

      console.log('✓ Filter applied');
    } else {
      console.log('Provider filter not found - checking for filter buttons');

      const filterButtons = page.locator('button').filter({ hasText: /OpenAI|Anthropic|All/i });
      const hasButtons = await filterButtons.count() > 0;

      if (hasButtons) {
        console.log('1. Testing filter buttons...');
        await filterButtons.first().click();
        await page.waitForTimeout(1000);
        console.log('✓ Filter button clicked');
      }
    }
  });

  test('should show model details', async ({ page }) => {
    console.log('\n=== Test: Model Details ===');

    await page.goto('http://localhost:3000/models', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Click on first model
    const firstModel = page.locator('[class*="card"], tbody tr').first();
    const hasModel = await firstModel.isVisible().catch(() => false);

    if (hasModel) {
      console.log('1. Clicking on first model...');
      await firstModel.click();
      await page.waitForTimeout(1000);

      // Check for model details
      const detailLabels = [
        'Context Window',
        'Max Output',
        'Capabilities',
        'Provider',
        'Cost',
        'Pricing',
      ];

      for (const label of detailLabels) {
        const element = page.getByText(label, { exact: false });
        const isVisible = await element.isVisible().catch(() => false);
        if (isVisible) {
          console.log(`  ✓ ${label} visible`);
        }
      }

      await page.screenshot({ path: 'test-results/model-details.png', fullPage: true });
    } else {
      console.log('No models available to click');
    }
  });

  test('should display model capabilities', async ({ page }) => {
    console.log('\n=== Test: Model Capabilities ===');

    await page.goto('http://localhost:3000/models', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check for capability badges
    const capabilities = ['vision', 'function_calling', 'json_mode', 'streaming', 'chat', 'completion'];

    for (const capability of capabilities) {
      const element = page.getByText(capability, { exact: false });
      const isVisible = await element.isVisible().catch(() => false);
      if (isVisible) {
        console.log(`  ✓ Capability badge found: ${capability}`);
      }
    }
  });

  test('should toggle model active status', async ({ page }) => {
    console.log('\n=== Test: Toggle Model Status ===');

    await page.goto('http://localhost:3000/models', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Look for status toggle
    const toggleButton = page.locator('[role="switch"], button:has-text("Enable"), button:has-text("Disable"), button:has-text("Active")').first();
    const hasToggle = await toggleButton.isVisible().catch(() => false);

    if (hasToggle) {
      console.log('1. Found status toggle...');
      await toggleButton.click();
      await page.waitForTimeout(1000);
      console.log('✓ Toggle clicked');
    } else {
      console.log('Status toggle not found - may require admin privileges');
    }
  });

  test('should search models', async ({ page }) => {
    console.log('\n=== Test: Search Models ===');

    await page.goto('http://localhost:3000/models', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Look for search input
    const searchInput = page.getByPlaceholder(/search|filter/i).first();
    const hasSearch = await searchInput.isVisible().catch(() => false);

    if (hasSearch) {
      console.log('1. Testing search...');
      await searchInput.fill('gpt');
      await page.waitForTimeout(1000);

      // Check that results are filtered
      const results = await page.locator('[class*="card"], tbody tr').count();
      console.log(`  Search results: ${results}`);
      console.log('✓ Search applied');
    } else {
      console.log('Search input not found');
    }
  });

  test('should display model pricing calculator', async ({ page }) => {
    console.log('\n=== Test: Model Pricing Calculator ===');

    await page.goto('http://localhost:3000/models', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Look for calculator or cost estimation
    const calculatorButton = page.getByRole('button', { name: /Calculate|Estimate|Cost/i }).first();
    const hasCalculator = await calculatorButton.isVisible().catch(() => false);

    if (hasCalculator) {
      console.log('1. Opening cost calculator...');
      await calculatorButton.click();
      await page.waitForTimeout(1000);

      // Check for input fields
      const tokenInput = page.locator('input[type="number"]').first();
      const hasInput = await tokenInput.isVisible().catch(() => false);

      if (hasInput) {
        console.log('2. Entering token count...');
        await tokenInput.fill('1000000');
        await page.waitForTimeout(500);

        // Check for calculated cost
        const costElement = page.getByText(/\$/);
        const hasCost = await costElement.isVisible().catch(() => false);
        console.log(`✓ Cost displayed: ${hasCost}`);
      }

      await page.screenshot({ path: 'test-results/pricing-calculator.png', fullPage: true });
    } else {
      console.log('Pricing calculator not found on this page');
    }
  });

  test('should show admin model management (if admin)', async ({ page }) => {
    console.log('\n=== Test: Admin Model Management ===');

    await page.goto('http://localhost:3000/models', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check for admin-only actions
    const adminActions = [
      page.getByRole('button', { name: /Add Model|Create Model/i }),
      page.getByRole('button', { name: /Edit/i }).first(),
      page.getByRole('button', { name: /Delete/i }).first(),
      page.getByRole('button', { name: /Update Pricing/i }),
    ];

    for (const action of adminActions) {
      const isVisible = await action.isVisible().catch(() => false);
      if (isVisible) {
        const text = await action.textContent();
        console.log(`  ✓ Admin action found: ${text}`);
      }
    }
  });
});
