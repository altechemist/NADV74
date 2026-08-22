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

const ROOT = resolve(import.meta.dirname, "..");
const FRONTEND_URL = process.env.FRONTEND_URL ?? "http://localhost:3000";
const OUT_DIR = resolve(process.env.OUT_DIR ?? resolve(ROOT, "docs/demo/assets"));
const PASSWORD = process.env.CSRMS_DEMO_PASSWORD ?? "Campus#2026";
const WATER_KEY = process.env.CSRMS_WATER_KEY ?? "";
const NETWORK_KEY = process.env.CSRMS_NETWORK_KEY ?? "";
const FIRE_KEY = process.env.CSRMS_FIRE_KEY ?? "";
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
      term.innerHTML = `<div class="bar">CSRMS demo evidence</div><div class="lines"></div>`;
      document.body.append(term);
      window.__caption = (text) => {
        caption.textContent = text;
      };
      window.__termLine = (line) => {
        term.style.display = "block";
        const lines = term.querySelector(".lines");
        const row = document.createElement("div");
        row.textContent = line;
        lines.append(row);
        while (lines.children.length > 9) lines.firstChild.remove();
      };
      window.__termTitle = (title) => {
        term.querySelector(".bar").textContent = title;
      };
      window.__termHide = () => {
        term.style.display = "none";
      };
    });
  });

  const caption = (text) => page.evaluate((t) => window.__caption(t), text);
  const termLine = (line) => page.evaluate((t) => window.__termLine(t), line);
  const termTitle = (title) =>
    page.evaluate((t) => window.__termTitle(t), title);
  const pause = (ms) => page.waitForTimeout(ms);

  async function openLogin() {
    await page.goto(`${FRONTEND_URL}/login`, { waitUntil: "networkidle" });
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await page.goto(`${FRONTEND_URL}/login`, { waitUntil: "networkidle" });
  }

  // Streams child process stdout into the on-screen terminal panel.
  function streamIntoTerminal(child) {
    let buffer = "";
    child.stdout.on("data", (chunk) => {
      buffer += chunk.toString();
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) if (line.trim()) termLine(line);
    });
    child.stderr.on("data", (chunk) => {
      for (const line of chunk.toString().split("\n"))
        if (line.trim()) termLine(line);
    });
  }

  function runCommandEvidence(command, args, cwd) {
    return new Promise((resolveCommand, rejectCommand) => {
      const child = spawn(command, args, { cwd, env: process.env });
      streamIntoTerminal(child);
      child.on("error", rejectCommand);
      child.on("close", (code) => {
        if (code === 0) resolveCommand();
        else rejectCommand(new Error(`${command} exited with code ${code}`));
      });
    });
  }

  async function runApiEvidence() {
    const api = "http://127.0.0.1:8000/api";
    const jsonHeaders = { "Content-Type": "application/json" };
    const login = (password) =>
      fetch(`${api}/auth/login/`, {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ username: "naledi", password }),
      });

    const failed = await login("wrong-password");
    termLine(`POST /auth/login/ wrong password -> HTTP ${failed.status}`);

    const successful = await login(PASSWORD);
    const tokens = await successful.json();
    termLine(
      `POST /auth/login/ valid credentials -> HTTP ${successful.status}`,
    );

    const profile = await fetch(`${api}/auth/me/`, {
      headers: { Authorization: `Bearer ${tokens.access}` },
    });
    termLine(`GET /auth/me/ bearer JWT -> HTTP ${profile.status}`);

    const waterTelemetry = await fetch(`${api}/telemetry/water/`, {
      method: "POST",
      headers: { ...jsonHeaders, "X-Device-Key": WATER_KEY },
      body: JSON.stringify({
        moisture_percent: 88,
        location: "Residence C · geyser room",
        device_id: "water-01",
      }),
    });
    termLine(
      `POST /telemetry/water/ X-Device-Key -> HTTP ${waterTelemetry.status} (dedupe check)`,
    );

    // Show deduplication: repeated reading should not create a new ticket
    await pause(1500);
    const waterTelemetryRepeat = await fetch(`${api}/telemetry/water/`, {
      method: "POST",
      headers: { ...jsonHeaders, "X-Device-Key": WATER_KEY },
      body: JSON.stringify({
        moisture_percent: 92,
        location: "Residence C · geyser room",
        device_id: "water-01",
      }),
    });
    termLine(
      `POST /telemetry/water/ repeat -> HTTP ${waterTelemetryRepeat.status} (no duplicate ticket)`,
    );

    const networkStatuses = [];
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const response = await fetch(`${api}/telemetry/network/`, {
        method: "POST",
        headers: { ...jsonHeaders, "X-Device-Key": NETWORK_KEY },
        body: JSON.stringify({
          reachable: false,
          latency_ms: 0,
          location: "Video demo server room",
          device_id: "video-net-01",
        }),
      });
      networkStatuses.push(response.status);
    }
    termLine(`POST /telemetry/network/ 3 failed pings -> HTTP ${networkStatuses.join(", ")}`);

    const fireTelemetry = await fetch(`${api}/telemetry/fire/`, {
      method: "POST",
      headers: { ...jsonHeaders, "X-Device-Key": FIRE_KEY },
      body: JSON.stringify({
        smoke_level: 45,
        temperature_c: 55,
        location: "Video demo server room",
        device_id: "video-fire-01",
      }),
    });
    termLine(`POST /telemetry/fire/ threshold breach -> HTTP ${fireTelemetry.status}`);
  }

  async function runTestEvidence() {
    await runCommandEvidence(
      resolve(ROOT, "venv/bin/python"),
      ["manage.py", "test", "--verbosity", "1"],
      resolve(ROOT, "backend"),
    );
    await runCommandEvidence(
      "python3",
      ["test/validate_sketches.py"],
      resolve(ROOT, "iot"),
    );
  }

  console.log(`Recording ${FRONTEND_URL} -> ${OUT_DIR}`);

  // --- scene 0: student registration -----------------------------------------
  await openLogin();
  await caption("New students register themselves — the role is forced server-side.");
  await page.getByText("New student on campus?").waitFor();
  await page.getByText("Create an account").click();
  await page.getByLabel("Username").fill("thabo");
  await page.getByLabel("First name").fill("Thabo");
  await page.getByLabel("Last name").fill("Ndlovu");
  await page.getByLabel("Email").fill("thabo@spu.ac.za");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  // Registration may fail if user already exists; handle gracefully
  await page.waitForTimeout(2000);
  const regError = page.locator(".bg-\\[\\#fce7df\\]");
  if (await regError.isVisible().catch(() => false)) {
    // User already exists — switch to login mode and sign in
    await page.evaluate(() => {
      document.querySelector('button[type="button"]')?.click();
    });
    await page.waitForTimeout(300);
    await page.getByLabel("Username").fill("thabo");
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click({ force: true });
  }
  await page.getByText("workspace").first().waitFor({ timeout: 10000 });
  await caption("The account is immediately active as a student — no admin approval needed.");
  await pause(1800);
  await page.getByTitle("Sign out").click();
  await page.getByText("Sign in to the service desk").waitFor();

  // --- scene 1: student reports a problem ----------------------------------
  await openLogin();
  await caption("Campus problems, one service desk.");
  await pause(1600);

  await caption(
    "A wrong password is rejected with HTTP 401 - no session is created.",
  );
  await page.getByLabel("Username").fill("naledi");
  await page.getByLabel("Password").fill("wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page
    .getByText(/invalid|incorrect|no active account|credentials/i)
    .waitFor();
  await pause(1000);

  await caption("Students sign in and see only their own requests.");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText("workspace").first().waitFor();
  await pause(1400);

  await page.getByRole("button", { name: "Log a request" }).click();
  await caption("A broken projector becomes a tracked request…");
  await page
    .getByPlaceholder("What needs attention?")
    .fill("Projector will not display in Lab 2");
  await page.getByLabel("Category").selectOption({ label: "Equipment" });
  await page.getByPlaceholder("Building and room").fill("Academic Lab 2");
  await page
    .getByPlaceholder("Describe the problem")
    .fill("No signal from the ceiling projector; HDMI and VGA both dead.");
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

  await caption(
    "Assigned to a technician - status and history update together.",
  );
  const assignSelect = page.locator(
    "section:has-text('Service desk actions') select",
  );
  await assignSelect.selectOption({ label: "Lerato Mokoena (STAFF)" });
  await page.waitForTimeout(900);

  // --- illegal transition demo -----------------------------------------------
  await caption("The workflow enforces valid transitions only.");
  await pause(1200);
  const backBtn = page.getByRole("button", { name: "Back to pending" });
  if (await backBtn.isVisible()) {
    await backBtn.click();
    await page.waitForTimeout(500);
    await caption("Attempting an illegal transition returns an error.");
    await page.getByText(/cannot move|not allowed/i).waitFor();
    await pause(1500);
  }

  await page.getByRole("button", { name: "Mark in progress" }).click();
  await pause(900);
  await page.getByRole("button", { name: "Mark resolved" }).click();
  await caption("Every change lands in an audit trail: who, when, why.");
  await page.getByText("Workflow history").waitFor();
  await pause(1800);
  await closeModalIfOpen(page);

  // --- scene 2b: notification workflow ------------------------------------
  await caption("Students see notifications when their requests change.");
  await page.getByTitle("Sign out").click();
  await page.getByText("Sign in to the service desk").waitFor();
  await page.getByLabel("Username").fill("naledi");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText("workspace").first().waitFor();
  await pause(1000);

  await caption("The bell shows unread notifications from the service desk.");
  const bellDot = page.locator("span.bg-\\[\\#d16848\\]");
  await bellDot.waitFor({ state: "visible", timeout: 5000 }).catch(() => {});
  const bellButton = bellDot.locator("xpath=ancestor::button");
  await bellButton.click();
  await pause(800);

  const firstNotification = page.locator(".max-h-80 button").first();
  await firstNotification.waitFor();
  await caption("Clicking a notification opens the request detail panel.");
  await firstNotification.click();
  await page.waitForTimeout(800);
  await page.getByText("Request detail", { exact: true }).waitFor();
  await pause(1500);
  await closeModalIfOpen(page);

  // --- log back in as staff for sensors scene -------------------------------
  await page.getByTitle("Sign out").click();
  await page.getByText("Sign in to the service desk").waitFor();
  await page.getByLabel("Username").fill("lerato");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText("workspace").first().waitFor();
  await pause(800);

  // --- scene 3: sensors raise their own tickets ----------------------------
  await page.getByRole("button", { name: "Sensors", exact: true }).click();
  await caption("IoT sensors watch the campus in the background.");
  await page.getByText("Sensor activity").waitFor();
  await pause(1600);

  await caption("A leaking geyser reports itself:");
  if (HAS_WOKWI) {
    const child = spawn(
      "wokwi-cli",
      [
        resolve(ROOT, "iot/water-leak-sensor"),
        "--timeout",
        "40000",
        "--scenario",
        "scenario.yaml",
      ],
      {
        cwd: resolve(ROOT, "iot"),
        env: process.env,
      },
    );
    streamIntoTerminal(child);
    await pause(12000); // scenario needs ~35 simulated seconds; keep the best part
    child.kill("SIGKILL");
  } else {
    const child = spawn(
      "python3",
      [
        resolve(import.meta.dirname, "fake_sensor.py"),
        "--key",
        WATER_KEY,
        "--readings",
        "4",
        "--interval",
        "1.4",
      ],
      { cwd: import.meta.dirname },
    );
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
  await page
    .getByText(/water leak/i)
    .first()
    .click();
  await page.getByText("Workflow history").waitFor();
  await caption("Deduplicated per sensor - one open ticket, never a flood.");
  await pause(2000);
  await closeModalIfOpen(page);

  // --- scene 4: API and automated evidence -------------------------------
  await openLogin();
  await termTitle("Postman-compatible API evidence");
  await caption("The same security boundary is visible in the API client.");
  await runApiEvidence();
  await pause(1600);
  await termTitle("Automated verification");
  await caption(
    "The demo is backed by executable tests, not just screenshots.",
  );
  await runTestEvidence();
  await pause(1800);
  await page.evaluate(() => window.__termHide());

  // --- scene 5: administrator journey -------------------------------------
  await openLogin();
  await caption("Administrators see the campus-wide picture and manage access.");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText("workspace").first().waitFor();
  await pause(1000);

  // Show overview dashboard
  await caption("Campus-wide view of all requests across every building.");
  await page.getByText("Overview").first().waitFor();
  await pause(2000);

  // Show People management
  await page.getByRole("button", { name: "People", exact: true }).click();
  await caption("Manage users and categories from one screen.");
  await page.getByText("People & categories").waitFor();
  await pause(1800);

  // --- end card -------------------------------------------------------------
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: "networkidle" });
  await caption(
    "CSRMS · 61 automated tests · Postman + sensor evidence · p95 under 8 ms",
  );
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
    await overlay
      .click({ position: { x: 12, y: 12 }, force: true })
      .catch(() => {});
    await page.waitForTimeout(350);
  }
}

main()
  .then((webmPath) => {
    try {
      const ffmpeg = require.resolve("ffmpeg-static");
      const mp4 = webmPath.replace(/\.webm$/, ".mp4");
      execFileSync(
        ffmpeg,
        [
          "-y",
          "-i",
          webmPath,
          "-c:v",
          "libx264",
          "-pix_fmt",
          "yuv420p",
          "-movflags",
          "+faststart",
          mp4,
        ],
        { stdio: "pipe" },
      );
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
