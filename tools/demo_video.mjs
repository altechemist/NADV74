#!/usr/bin/env node
/**
 * Record the CSRMS demo video with Playwright.
 *
 * Drives the real frontend through the whole story - student report, staff
 * workflow, and a sensor raising its own ticket - while a caption bar narrates
 * each step. The device scene streams either real Wokwi serial output (when
 * WOKWI_CLI_TOKEN is set) or tools/fake_sensor.py into an on-screen terminal
 * panel, so the recording always shows the "device talks to API" moment.
 *
 * Output: docs/demo/assets/csrms-demo.webm, converted to csrms-demo.mp4 when
 * ffmpeg-static is installed.
 *
 * Prerequisites: backend + frontend dev servers running, seeded database.
 * Optional env: WOKWI_CLI_TOKEN, CSRMS_WATER_KEY, FRONTEND_URL, CSRMS_DEMO_PASSWORD.
 */

import { execFileSync, spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { createRequire } from "node:module";
import { chromium } from "playwright";

const require = createRequire(import.meta.url);

const FRONTEND_URL = process.env.FRONTEND_URL ?? "http://localhost:3000";
const OUT_DIR = resolve(process.env.OUT_DIR ?? "../docs/demo/assets");
const PASSWORD = process.env.CSRMS_DEMO_PASSWORD ?? "Campus#2026";
const WATER_KEY = process.env.CSRMS_WATER_KEY ?? "";
const HAS_WOKWI = Boolean(process.env.WOKWI_CLI_TOKEN);

const VIEW = { width: 1280, height: 720 };

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: VIEW,
    recordVideo: { size: VIEW },
  });
  const page = await context.newPage();

  // --- on-screen narration helpers -----------------------------------------
  await page.addInitScript(() => {
    document.addEventListener("DOMContentLoaded", () => {
      const style = document.createElement("style");
      style.textContent = `
        #csrms-caption { position: fixed; left: 50%; bottom: 18px; transform: translateX(-50%);
          z-index: 9999; background: #102a35ee; color: #f5f0e8; font: 600 17px/1.4 Georgia, serif;
          padding: 10px 26px; border-radius: 999px; box-shadow: 0 8px 30px rgba(0,0,0,.35);
          transition: opacity .25s; white-space: nowrap; }
        #csrms-term { position: fixed; right: 16px; top: 84px; z-index: 9999; width: 430px;
          max-height: 300px; overflow: hidden; background: #0b1416f2; border-radius: 12px;
          box-shadow: 0 10px 34px rgba(0,0,0,.45); font: 12px/1.55 'DejaVu Sans Mono', monospace;
          color: #7ee2a8; padding: 10px 14px; display: none; }
        #csrms-term .bar { color: #e6a649; font-weight: bold; margin-bottom: 4px; }
      `;
      document.head.append(style);
      const caption = document.createElement("div");
      caption.id = "csrms-caption";
      document.body.append(caption);
      const term = document.createElement("div");
      term.id = "csrms-term";
      term.innerHTML = `<div class="bar">device · water-leak-01</div><div class="lines"></div>`;
      document.body.append(term);
      window.__caption = (text) => { caption.textContent = text; };
      window.__termLine = (line) => {
        term.style.display = "block";
        const lines = term.querySelector(".lines");
        const row = document.createElement("div");
        row.textContent = line;
        lines.append(row);
        while (lines.children.length > 9) lines.firstChild.remove();
      };
      window.__termHide = () => { term.style.display = "none"; };
    });
  });

  const caption = (text) => page.evaluate((t) => window.__caption(t), text);
  const termLine = (line) => page.evaluate((t) => window.__termLine(t), line);
  const pause = (ms) => page.waitForTimeout(ms);

  // Streams child process stdout into the on-screen terminal panel.
  function streamIntoTerminal(child) {
    let buffer = "";
    child.stdout.on("data", (chunk) => {
      buffer += chunk.toString();
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) if (line.trim()) termLine(line);
    });
  }

  console.log(`Recording ${FRONTEND_URL} -> ${OUT_DIR}`);

  // --- scene 1: student reports a problem ----------------------------------
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: "networkidle" });
  await caption("Campus problems, one service desk.");
  await pause(1600);

  await caption("Students sign in and see only their own requests.");
  await page.getByLabel("Username").fill("naledi");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText("workspace").first().waitFor();
  await pause(1400);

  await page.getByRole("button", { name: "Log a request" }).click();
  await caption("A broken projector becomes a tracked request…");
  await page.getByPlaceholder("What needs attention?").fill("Projector will not display in Lab 2");
  await page.getByLabel("Category").selectOption({ label: "Equipment" });
  await page.getByPlaceholder("Building and room").fill("Academic Lab 2");
  await page.getByPlaceholder("Describe the problem").fill("No signal from the ceiling projector; HDMI and VGA both dead.");
  await pause(900);
  await page.getByRole("button", { name: "Submit request" }).click();
  await page.waitForTimeout(700);
  await closeModalIfOpen(page);
  await pause(600);

  await page.getByRole("button", { name: "Requests", exact: true }).click();
  await caption("…queued as PENDING, visible to the service desk.");
  await page.getByText("Projector will not display in Lab 2").first().waitFor();
  await pause(1500);

  // --- scene 2: staff work the queue ---------------------------------------
  await page.getByTitle("Sign out").click();
  await page.getByText("Sign in to the service desk").waitFor();
  await caption("Staff pick it up and drive it to resolved.");
  await page.getByLabel("Username").fill("lerato");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText("workspace").first().waitFor();
  await pause(1200);

  await page.getByRole("button", { name: "Requests", exact: true }).click();
  await page.getByText("Projector will not display in Lab 2").first().click();
  await page.getByText("Service desk actions").waitFor();

  await caption("Assigned to a technician - status and history update together.");
  const assignSelect = page.locator("section:has-text('Service desk actions') select");
  await assignSelect.selectOption({ label: "Lerato Mokoena (STAFF)" });
  await page.waitForTimeout(900);
  await page.getByRole("button", { name: "Mark in progress" }).click();
  await pause(900);
  await page.getByRole("button", { name: "Mark resolved" }).click();
  await caption("Every change lands in an audit trail: who, when, why.");
  await page.getByText("Workflow history").waitFor();
  await pause(1800);
  await closeModalIfOpen(page);

  // --- scene 3: sensors raise their own tickets ----------------------------
  await page.getByRole("button", { name: "Sensors", exact: true }).click();
  await caption("IoT sensors watch the campus in the background.");
  await page.getByText("Sensor activity").waitFor();
  await pause(1600);

  await caption("A leaking geyser reports itself:");
  if (HAS_WOKWI) {
    const child = spawn("wokwi-cli", [resolve("../iot/water-leak-sensor"), "--timeout", "40000", "--scenario", "scenario.yaml"], {
      cwd: resolve("..", "iot"),
      env: process.env,
    });
    streamIntoTerminal(child);
    await pause(12000); // scenario needs ~35 simulated seconds; keep the best part
    child.kill("SIGKILL");
  } else {
    const child = spawn("python3", [
      resolve("fake_sensor.py"), "--key", WATER_KEY,
      "--readings", "4", "--interval", "1.4",
    ], { cwd: resolve(".") });
    streamIntoTerminal(child);
    await new Promise((resolveChild) => child.on("close", resolveChild));
  }
  await pause(800);

  await page.evaluate(() => window.__termHide());
  // The SPA fetched its request list before the sensor posted; a reload makes
  // it pick up the freshly raised ticket.
  await page.reload({ waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Requests", exact: true }).click();
  await caption("…and the same workflow opens a SYSTEM ticket automatically.");
  await page.getByText("SYSTEM").first().waitFor();
  await pause(1200);
  await page.getByText(/water leak/i).first().click();
  await page.getByText("Workflow history").waitFor();
  await caption("Deduplicated per sensor - one open ticket, never a flood.");
  await pause(2000);
  await closeModalIfOpen(page);

  // --- end card -------------------------------------------------------------
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: "networkidle" });
  await caption("CSRMS · 59 automated tests · p95 under 8 ms · built by team NADV74");
  await pause(2600);

  const targetWebm = resolve(OUT_DIR, "csrms-demo.webm");
  // saveAs waits for the recording to be flushed; path()+rename races with
  // Playwright's temp-artifact cleanup.
  await page.video().saveAs(targetWebm);
  await context.close();
  await browser.close();
  console.log(`Saved ${targetWebm}`);
  return targetWebm;
}

async function closeModalIfOpen(page) {
  const overlay = page.locator("div.fixed.inset-0");
  if (await overlay.count()) {
    await overlay.click({ position: { x: 12, y: 12 }, force: true }).catch(() => {});
    await page.waitForTimeout(350);
  }
}

main()
  .then((webmPath) => {
    try {
      const ffmpeg = require.resolve("ffmpeg-static");
      const mp4 = webmPath.replace(/\.webm$/, ".mp4");
      execFileSync(ffmpeg, ["-y", "-i", webmPath, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4], { stdio: "pipe" });
      console.log(`Converted to ${mp4}`);
    } catch (error) {
      console.log(`Keeping WebM (${error.message.split("\n")[0]})`);
    }
    // Chromium's recording pipes keep the loop alive; exit explicitly.
    process.exit(0);
  })
  .catch((error) => {
    console.error(`FAILED: ${error.message}`);
    process.exit(1);
  });
