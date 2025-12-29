import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page, context }) => {
    // Clear all cookies before each test
    await context.clearCookies();
    console.log('✓ Cookies cleared');
  });

  test('should redirect to login when not authenticated', async ({ page }) => {
    console.log('\n=== Test: Redirect to Login ===');

    // Navigate to home page without authentication
    console.log('1. Navigating to http://localhost:3000/');
    await page.goto('http://localhost:3000/');

    // Wait for navigation to complete
    await page.waitForLoadState('networkidle');

    // Check current URL
    const currentUrl = page.url();
    console.log(`2. Current URL: ${currentUrl}`);

    // Should be redirected to /login
    expect(currentUrl).toContain('/login');
    console.log('✓ Successfully redirected to /login');

    // Should see login form
    await expect(page.getByRole('heading', { name: /LLM Gateway/i })).toBeVisible();
    await expect(page.getByPlaceholder(/email/i)).toBeVisible();
    await expect(page.getByPlaceholder(/password/i)).toBeVisible();
    console.log('✓ Login form is visible');
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    console.log('\n=== Test: Login Flow ===');

    // Go to login page
    console.log('1. Navigating to login page');
    await page.goto('http://localhost:3000/login');
    await page.waitForLoadState('networkidle');

    // Fill in credentials
    console.log('2. Filling credentials (admin@example.com)');
    await page.getByPlaceholder(/email/i).fill('admin@example.com');
    await page.getByPlaceholder(/password/i).fill('admin123');

    // Click login button
    console.log('3. Clicking Sign In button');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Wait for navigation
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000); // Extra wait for auth to settle

    // Check current URL after login
    const currentUrl = page.url();
    console.log(`4. Current URL after login: ${currentUrl}`);

    // Check cookies
    const cookies = await page.context().cookies();
    console.log(`5. Cookies after login: ${JSON.stringify(cookies.map(c => ({ name: c.name, value: c.value.substring(0, 20) + '...' })), null, 2)}`);

    const accessTokenCookie = cookies.find(c => c.name === 'access_token');
    if (accessTokenCookie) {
      console.log('✓ access_token cookie found');
    } else {
      console.log('✗ access_token cookie NOT found');
    }

    // Should be redirected to dashboard
    expect(currentUrl).toBe('http://localhost:3000/');
    console.log('✓ Redirected to dashboard');

    // Should see dashboard content (sidebar)
    await expect(page.getByText(/Dashboard/i).first()).toBeVisible({ timeout: 5000 });
    console.log('✓ Dashboard is visible');
  });

  test('should stay on dashboard when authenticated', async ({ page }) => {
    console.log('\n=== Test: Authenticated Access ===');

    // First login
    console.log('1. Logging in first...');
    await page.goto('http://localhost:3000/login');
    await page.getByPlaceholder(/email/i).fill('admin@example.com');
    await page.getByPlaceholder(/password/i).fill('admin123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Verify we're logged in
    let currentUrl = page.url();
    console.log(`2. After login URL: ${currentUrl}`);
    expect(currentUrl).toBe('http://localhost:3000/');

    // Now navigate to dashboard again
    console.log('3. Navigating to / again (should stay on dashboard)');
    await page.goto('http://localhost:3000/');
    await page.waitForLoadState('networkidle');

    currentUrl = page.url();
    console.log(`4. Final URL: ${currentUrl}`);

    // Should stay on dashboard, not redirect to login
    expect(currentUrl).toBe('http://localhost:3000/');
    console.log('✓ Stayed on dashboard (not redirected)');

    // Should see dashboard content
    await expect(page.getByText(/Dashboard/i).first()).toBeVisible();
    console.log('✓ Dashboard content visible');
  });

  test('should show login form when accessing without token', async ({ page }) => {
    console.log('\n=== Test: Access Without Token ===');

    // Try to access dashboard directly
    console.log('1. Accessing dashboard without token');
    await page.goto('http://localhost:3000/');

    // Wait for page to load
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    const currentUrl = page.url();
    console.log(`2. Current URL: ${currentUrl}`);

    // Check if we see login form or loading screen
    const hasLoginForm = await page.getByPlaceholder(/email/i).isVisible().catch(() => false);
    const hasLoadingScreen = await page.getByText(/loading/i).isVisible().catch(() => false);

    console.log(`3. Has login form: ${hasLoginForm}`);
    console.log(`3. Has loading screen: ${hasLoadingScreen}`);

    // Should either be on /login or see login form
    const isOnLoginPage = currentUrl.includes('/login');
    console.log(`4. Is on login page: ${isOnLoginPage}`);

    if (!isOnLoginPage && !hasLoginForm) {
      console.log('✗ ERROR: Not on login page and no login form visible!');
      console.log(`   Current page content: ${await page.content()}`);
    }

    expect(isOnLoginPage || hasLoginForm).toBeTruthy();
  });

  test('should handle invalid credentials', async ({ page }) => {
    console.log('\n=== Test: Invalid Credentials ===');

    await page.goto('http://localhost:3000/login');
    await page.getByPlaceholder(/email/i).fill('wrong@example.com');
    await page.getByPlaceholder(/password/i).fill('wrongpassword');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Should stay on login page
    await page.waitForTimeout(2000);
    const currentUrl = page.url();
    console.log(`Current URL: ${currentUrl}`);

    expect(currentUrl).toContain('/login');
    console.log('✓ Stayed on login page');

    // Should show error message
    await expect(page.getByText(/invalid credentials|login failed/i)).toBeVisible();
    console.log('✓ Error message shown');
  });
});
