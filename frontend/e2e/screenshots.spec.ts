import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const ADMIN_EMAIL = 'admin@example.com';
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'mmj0RqSm72Z3XUIuSgolfA';
const OUTPUT_DIR = '../docs/screenshots';

test.describe('Screenshot capture', () => {
  test('capture all pages', async ({ page }) => {
    // 1. Login page
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: `${OUTPUT_DIR}/01-login.png` });

    // Login
    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');

    // Wait for redirect
    await page.waitForTimeout(2000);

    // 2. Dashboard (home page)
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUTPUT_DIR}/02-dashboard.png` });

    // 3. Applications
    await page.goto(`${BASE_URL}/applications`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUTPUT_DIR}/03-applications.png` });

    // 4. Budgets
    await page.goto(`${BASE_URL}/budgets`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUTPUT_DIR}/04-budgets.png` });

    // 5. Security
    await page.goto(`${BASE_URL}/security`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUTPUT_DIR}/05-security.png` });

    console.log('Screenshots saved to docs/screenshots/');
  });
});
