import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000';
const ADMIN_EMAIL = 'admin@example.com';
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin123';
const OUTPUT_DIR = '../docs/screenshots';

async function captureScreenshots() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
  });
  const page = await context.newPage();

  console.log('Starting screenshot capture...');

  // 1. Login page
  console.log('1. Capturing login page...');
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: `${OUTPUT_DIR}/01-login.png`, fullPage: false });

  // Login
  console.log('   Logging in...');
  await page.fill('input[type="email"]', ADMIN_EMAIL);
  await page.fill('input[type="password"]', ADMIN_PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard**', { timeout: 10000 }).catch(() => {
    console.log('   Redirect timeout, continuing...');
  });
  await page.waitForLoadState('networkidle');

  // 2. Dashboard
  console.log('2. Capturing dashboard...');
  await page.goto(`${BASE_URL}/dashboard`);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${OUTPUT_DIR}/02-dashboard.png`, fullPage: false });

  // 3. Applications
  console.log('3. Capturing applications...');
  await page.goto(`${BASE_URL}/applications`);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${OUTPUT_DIR}/03-applications.png`, fullPage: false });

  // 4. Budgets
  console.log('4. Capturing budgets...');
  await page.goto(`${BASE_URL}/budgets`);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${OUTPUT_DIR}/04-budgets.png`, fullPage: false });

  // 5. Security
  console.log('5. Capturing security...');
  await page.goto(`${BASE_URL}/security`);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${OUTPUT_DIR}/05-security.png`, fullPage: false });

  await browser.close();
  console.log('\nScreenshots saved to docs/screenshots/');
}

captureScreenshots().catch(console.error);
