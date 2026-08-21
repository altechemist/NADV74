#!/usr/bin/env node
/**
 * Render docs/report/report.md to PDF without needing LaTeX.
 *
 * Pipeline: pandoc (static binary) -> styled standalone HTML -> headless
 * Chromium print-to-PDF at A4. Images referenced by the report are embedded
 * into the HTML, so the PDF is self-contained.
 *
 * Usage:
 *   PANDOC=/path/to/pandoc node report_pdf.mjs [in.md] [out.pdf]
 *
 * Defaults: ../docs/report/report.md -> ../docs/report/CSRMS_Report.pdf
 */

import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { chromium } from "playwright";

const PANDOC = process.env.PANDOC ?? "pandoc";
const INPUT = resolve(process.argv[2] ?? "../docs/report/report.md");
const OUTPUT = resolve(process.argv[3] ?? "../docs/report/CSRMS_Report.pdf");

// Print stylesheet: A4, restrained academic look, tables and figures sized
// so nothing spills over the page edge.
const CSS = `
  @page { size: A4; margin: 22mm 20mm; }
  body { font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt;
         line-height: 1.4; color: #1c2b2e; max-width: none; }
  h1 { font-size: 16pt; border-bottom: 2px solid #102a35; padding-bottom: 4px;
       margin-top: 1em; color: #102a35; }
  h2 { font-size: 13.5pt; color: #102a35; margin-top: 1.3em; }
  h3 { font-size: 11.5pt; color: #274b52; }
  code, pre { font-family: 'DejaVu Sans Mono', Consolas, monospace; font-size: 8.5pt;
              background: #f4f1ea; border-radius: 4px; }
  pre { padding: 10px; overflow-x: hidden; white-space: pre-wrap; }
  table { border-collapse: collapse; width: 100%; font-size: 9.5pt; margin: 12px 0; }
  th, td { border: 1px solid #c9c2b4; padding: 5px 8px; text-align: left; }
  th { background: #efe9dc; }
  img { max-width: 100%; max-height: 250px; display: block; margin: 14px auto; }
  figure { margin: 0; break-inside: avoid; }
  figcaption, caption { font-size: 9pt; color: #55666a; text-align: center; margin-top: 4px; }
  blockquote { border-left: 3px solid #c9c2b4; margin-left: 0; padding-left: 14px; color: #444; }
  header#title-block-header { text-align: center; margin-bottom: 40px; }
  h1.title { font-size: 22pt; border: none; margin-top: 60px; }
  p.subtitle { font-size: 13pt; color: #45616a; }
`;

async function main() {
  const work = mkdtempSync(join(tmpdir(), "csrms-report-"));
  const htmlPath = join(work, "report.html");

  execFileSync(
    PANDOC,
    [
      INPUT,
      "-o", htmlPath,
      "--standalone",
      "--embed-resources",
      "--toc", "--toc-depth=2",
      "--metadata", "lang=en-ZA",
      "-c", "",
    ],
    { stdio: "inherit" },
  );

  // Inject the print stylesheet before the browser sees the document.
  const { readFileSync, writeFileSync } = await import("node:fs");
  const html = readFileSync(htmlPath, "utf8").replace(
    "</head>",
    `<style>${CSS}</style></head>`,
  );
  writeFileSync(htmlPath, html);

  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(`file://${htmlPath}`, { waitUntil: "networkidle" });
  await page.pdf({ path: OUTPUT, format: "A4", printBackground: true });
  await browser.close();

  rmSync(work, { recursive: true, force: true });
  console.log(`Wrote ${OUTPUT}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
