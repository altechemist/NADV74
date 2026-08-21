#!/usr/bin/env node
/**
 * Build the demo slide deck to PDF.
 *
 * Marp CLI's own Chromium sometimes refuses to inline local file:// images
 * during PDF export, so this does the two steps separately: marp renders the
 * deck to HTML, then Playwright's Chromium prints it to a pixel-exact
 * 1280x720 PDF (one slide per page, images embedded).
 *
 * Usage: node slides_pdf.mjs   (from tools/, after `npm install` here)
 */

import { execFileSync } from "node:child_process";
import { rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { chromium } from "playwright";

const INPUT = resolve(process.argv[2] ?? "../docs/demo/slides.md");
const OUTPUT = resolve(process.argv[3] ?? "../docs/demo/CSRMS_Slides.pdf");
async function main() {
  // The intermediate HTML must sit next to the deck: the <img> tags keep
  // their relative paths and only resolve against the source directory.
  const htmlPath = join(INPUT, "..", ".slides-build.html");

  // Run marp from this directory so npx picks up the locally installed CLI.
  execFileSync(
    "npx",
    ["--no-install", "marp", INPUT, "--allow-local-files", "-o", htmlPath],
    { stdio: "inherit", cwd: import.meta.dirname },
  );

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await page.goto(`file://${htmlPath}`, { waitUntil: "networkidle" });
  await page.pdf({
    path: OUTPUT,
    width: "1280px",
    height: "720px",
    printBackground: true,
    margin: { top: 0, bottom: 0, left: 0, right: 0 },
  });
  await browser.close();

  rmSync(htmlPath, { force: true });

  const kb = Math.round(statSync(OUTPUT).size / 1024);
  console.log(`Wrote ${OUTPUT} (${kb} KB)`);
  if (kb < 200) {
    console.warn("WARNING: file is small - screenshots may not have embedded.");
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
