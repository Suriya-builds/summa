const { chromium, devices } = require('playwright');
// Browser journey test. Start the server first (./run.sh), then: node e2e/journey.js [screenshot-dir]
const fs = require('fs');
const SP = process.argv[2] || 'e2e/out';
fs.mkdirSync(`${SP}/shots`, { recursive: true });
const BASE = process.env.SUMMA_URL || 'http://localhost:8000';
(async () => {
  const browser = await chromium.launch();
  const problems = [];
  async function run(name, ctxOpts) {
    const ctx = await browser.newContext(ctxOpts);
    const page = await ctx.newPage();
    page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') problems.push(`[${name}] console ${m.type()}: ${m.text()}`); });
    page.on('pageerror', e => problems.push(`[${name}] pageerror: ${e.message}`));
    page.on('response', r => { if (r.status() >= 500) problems.push(`[${name}] ${r.status()} ${r.url()}`); });
    await page.goto(`${BASE}/`);
    await page.screenshot({ path: `${SP}/shots/${name}-landing.png`, fullPage: true });
    await page.getByRole('button', { name: /Try the demo/ }).click();
    await page.waitForURL('**/dashboard', { timeout: 30000 });
    await page.getByText('What stands out').waitFor({ timeout: 15000 });
    await page.waitForTimeout(800);
    await page.screenshot({ path: `${SP}/shots/${name}-dashboard.png`, fullPage: true });
    for (const p of ['transactions', 'budget', 'shield', 'ask', 'import', 'settings']) {
      await page.goto(`${BASE}/${p}`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(500);
      await page.screenshot({ path: `${SP}/shots/${name}-${p}.png`, fullPage: true });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      if (overflow > 1) problems.push(`[${name}] ${p}: horizontal overflow ${overflow}px`);
    }
    if (name === 'desktop') {
      // edit a transaction category
      await page.goto(`${BASE}/transactions?q=zomato`);
      await page.locator('ul.card li button').first().click();
      await page.getByRole('dialog').getByLabel('Category').selectOption('groceries');
      await page.getByRole('button', { name: 'Save' }).click();
      await page.getByText(/Saved\./).waitFor();
      // scam checker
      await page.goto(`${BASE}/shield`);
      await page.getByLabel('Message to check').fill('You received Rs 4,999. Enter your UPI PIN to receive the money. bit.ly/x');
      await page.getByRole('button', { name: 'Check', exact: true }).click();
      await page.getByText('Says you must enter your UPI PIN').waitFor();
      await page.screenshot({ path: `${SP}/shots/desktop-shield-check.png`, fullPage: true });
      // import paste
      await page.goto(`${BASE}/import`);
      await page.getByRole('button', { name: 'Use the example' }).click();
      await page.getByRole('button', { name: 'Import', exact: true }).click();
      await page.getByText(/Read \d+ new message/).waitFor();
      await page.screenshot({ path: `${SP}/shots/desktop-import-result.png`, fullPage: true });
      // logout
      await page.goto(`${BASE}/dashboard`);
      await page.getByRole('button', { name: 'Log out' }).click();
      await page.waitForURL(`${BASE}/`);
    }
    await ctx.close();
  }
  await run('desktop', { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  await run('mobile', { ...devices['Pixel 7'] });
  await browser.close();
  console.log(problems.length ? problems.join('\n') : 'NO PROBLEMS');
  if (problems.length) process.exitCode = 1;
})().catch(e => { console.error('FAILED', e); process.exit(1); });
