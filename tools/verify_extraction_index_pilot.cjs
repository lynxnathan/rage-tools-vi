#!/usr/bin/env node
// Verify the standalone extraction pilot in headless Chromium with Playwright.
const assert = require('node:assert/strict');
const { resolve } = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

async function selectRange(page, index, count) {
  const tiles = page.locator('#tiles .tile');
  while (count > 4) {
    const size = Math.ceil(count / 4);
    const group = Math.floor(index / size);
    await tiles.nth(group).click();
    index -= group * size;
    count = Math.min(size, count - group * size);
  }
  await tiles.nth(index).click();
  return page.locator('#details').innerText();
}

async function returnToRoot(page) {
  const back = page.locator('#back');
  while (await back.isEnabled()) await back.click();
  assert.equal(await page.locator('#tiles .tile').count(), 2);
}

async function verify() {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const artifact = process.argv[2] ?? 'output/extraction-index-pilot/index.html';
    await page.goto(pathToFileURL(resolve(artifact)).href);
    const archives = JSON.parse(await page.locator('#data').textContent());

    await page.getByText('audio.rpf', { exact: true }).click();
    const audio = await selectRange(page, 2, archives[0].children.length);
    assert.match(audio, /Decoded \/ verified · zlib/);
    assert.match(audio, /0x5000.*0x6316/);
    assert.match(audio, /725398e5f5267e1da78a82b8582a68950d72c3dc8adb0d97b54eda40274c19f2/);
    await returnToRoot(page);

    await page.getByText('audio.rpf', { exact: true }).click();
    const unresolved = await selectRange(page, 1, archives[0].children.length);
    assert.match(unresolved, /Unresolved · unclassified/);
    assert.match(unresolved, /No extracted file is listed/);
    await returnToRoot(page);

    await page.getByText('levels.rpf', { exact: true }).click();
    assert.match(await page.locator('#unresolved').innerText(), /96 of 2,199,213/);
    await page.getByText('Index rows 1–32', { exact: true }).click();
    const levels = await selectRange(page, 2, archives[1].children[0].children.length);
    assert.match(levels, /Indexed only · zlib/);
    assert.match(levels, /0x1d000.*0x1d701/);
    assert.match(levels, /No extracted file is listed/);
    await returnToRoot(page);
    assert.deepEqual(errors, []);
    console.log('Archive drill-down, all three statuses, and back navigation passed.');
  } finally {
    await browser.close();
  }
}

verify().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
