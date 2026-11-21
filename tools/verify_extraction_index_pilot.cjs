#!/usr/bin/env node
// Verify the local extraction pilot in headless Chromium using Playwright.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

async function verify() {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    const base = process.argv[2] ?? 'http://127.0.0.1:8766';
    await page.goto(base);

    await page.getByRole('link', { name: 'audio.rpf', exact: true }).click();
    await page.getByRole('link', { name: '0x5000', exact: true }).click();
    const audio = await page.locator('pre').innerText();
    assert.match(audio, /Status: verified/);
    assert.match(audio, /0x5000.*0x6316/);
    assert.match(audio, /725398e5f5267e1da78a82b8582a68950d72c3dc8adb0d97b54eda40274c19f2/);
    await page.getByRole('link', { name: '← audio pages' }).first().click();
    assert.equal(new URL(page.url()).searchParams.get('page'), '1');

    await page.getByRole('link', { name: '← archives' }).first().click();
    await page.getByRole('link', { name: 'levels.rpf', exact: true }).click();
    await page.getByRole('link', { name: '0x1d000', exact: true }).click();
    const levels = await page.locator('pre').innerText();
    assert.match(levels, /Status: indexed-only/);
    assert.match(levels, /0x1d000.*0x1d701/);
    assert.match(levels, /No extracted file/);

    await page.goto(new URL('/archive?name=levels&page=1000', base).href);
    assert.equal(await page.locator('tbody tr').count(), 100);
    await page.locator('tbody a').first().click();
    await page.getByRole('link', { name: '← levels pages' }).first().click();
    assert.equal(new URL(page.url()).searchParams.get('page'), '1000');
    assert.equal(await page.locator('tbody tr').count(), 100);
    console.log('Both archive controls and page-1000 back navigation passed.');
  } finally {
    await browser.close();
  }
}

verify().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
