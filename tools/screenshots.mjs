#!/usr/bin/env node
/**
 * End-to-end walkthrough of CSRMS that doubles as a screenshot generator.
 *
 * Drives the real React frontend against a running Django API: logs in as all
 * three roles, visits every section, opens the request drawer and the new
 * request modal, and saves a PNG of each stop to docs/screenshots/. Any failed
 * assertion exits non-zero, so CI or a pre-demo check can run this as a smoke
 * test.
 *
 * Prerequisites:
 *   - backend:  python manage.py runserver          (port 8000, seeded)
 *   - frontend: npm run dev                          (port 3000)
 *   - playwright installed in tools/ (npm install here, then npx playwright install chromium)
 *
 * Usage: node screenshots.mjs
 */

import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { chromium } from "playwright";

const FRONTEND_URL = process.env.FRONTEND_URL ?? "http://localhost:3000";
const OUT_DIR = resolve(process.env.OUT_DIR ?? "../docs/screenshots");
const PASSWORD = process.env.CSRMS_DEMO_PASSWORD ?? "Campus#2026";

const VIEW = { width: 1440, height: 900 };

async function expectText(page, text, timeout = 15000) {
  await page.getByText(text, { exact: false }).first().waitFor({ timeout });
}

async function shoot(page, name) {
  await page.waitForTimeout(600); // let charts/transitions settle
  await page.screenshot({ path: resolve(OUT_DIR, `${name}.png`) });
  console.log(`  saved ${name}.png`);
}

async function login(page, username) {
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: "networkidle" });
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expectText(page, "workspace"); // header renders only when authed
}

async function gotoSection(page, label) {
  await page.getByRole("button", { name: label, exact: true }).click();
  await page.waitForTimeout(400);
}

// Modals close on a backdrop click rather than Escape.
async function closeModal(page) {
  await page.locator("div.fixed.inset-0").click({ position: { x: 12, y: 12 } });
  await page.waitForTimeout(300);
}

async function logout(page) {
  await page.getByTitle("Sign out").click();
  await expectText(page, "Sign in to the service desk");
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: VIEW, deviceScaleFactor: 2 });

  console.log(`Driving ${FRONTEND_URL} (screenshots -> ${OUT_DIR})`);

  // --- student journey -----------------------------------------------------
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: "networkidle" });
  await shoot(page, "01-login-page");

  await login(page, "naledi");
  await expectText(page, "Hello, Naledi");
  await shoot(page, "02-student-overview");

  await gotoSection(page, "Requests");
  await expectText(page, "Projector will not display in Lab 2");
  await shoot(page, "03-student-requests");

  await page.getByRole("button", { name: "Log a request" }).first().click();
  await expectText(page, "Manual report");
  await shoot(page, "04-new-request-modal");
  await closeModal(page);

  await logout(page);

  // --- staff journey -------------------------------------------------------
  await login(page, "lerato");
  await expectText(page, "Hello, Lerato");
  await shoot(page, "05-staff-overview");

  await gotoSection(page, "Requests");
  await page.getByText("WiFi drops out every evening").first().click();
  await expectText(page, "Workflow history");
  await shoot(page, "06-request-detail-workflow");
  await closeModal(page);

  await gotoSection(page, "Sensors");
  await expectText(page, "Sensor activity");
  await shoot(page, "07-sensor-charts");

  // notifications bell (the icon button inside its own relative wrapper)
  await page.locator("header div.relative > button").click();
  await expectText(page, "Notifications");
  await shoot(page, "08-notifications");

  await logout(page);

  // --- admin journey -------------------------------------------------------
  await login(page, "admin");
  await expectText(page, "Hello, Thabo");
  await gotoSection(page, "People");
  await expectText(page, "lerato");
  await shoot(page, "09-admin-people");

  await browser.close();
  console.log("Walkthrough complete - every step asserted.");
}

main().catch((error) => {
  console.error(`FAILED: ${error.message}`);
  process.exit(1);
});
