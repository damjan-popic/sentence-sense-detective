#!/usr/bin/env node
/* Build and visually verify the two required review workbooks. */

import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.env.SSD_ROOT
  ? path.resolve(process.env.SSD_ROOT)
  : path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const fullInput = path.join(root, "external", "review", "review_pack_rows.json");
const sampleInput = path.join(root, "external", "review", "review_sample_100_rows.json");
const previewRoot = path.join(root, "external", "review", "previews");

const palette = {
  navy: "#24324A",
  navy2: "#314767",
  mint: "#CFEee5",
  yellow: "#FFEAA6",
  paper: "#FFFDF8",
  line: "#DED8CF",
  inkSoft: "#5D6878"
};

const widths = [
  170, 185, 95, 420, 220, 145, 145, 190, 260, 390,
  85, 190, 165, 180, 180, 360, 125, 105, 280
];

function columnName(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    const digit = (value - 1) % 26;
    result = String.fromCharCode(65 + digit) + result;
    value = Math.floor((value - 1) / 26);
  }
  return result;
}

async function buildWorkbook(inputPath, outputPath, previewName, tableName) {
  const payload = JSON.parse(await fs.readFile(inputPath, "utf8"));
  const workbook = Workbook.create();
  const sheet = workbook.worksheets.add("Review");
  sheet.showGridLines = false;

  const values = [payload.headers, ...payload.rows];
  const lastColumn = columnName(payload.headers.length - 1);
  const lastRow = values.length;
  const used = sheet.getRange(`A1:${lastColumn}${lastRow}`);
  used.values = values;
  used.format = {
    font: { name: "Aptos", size: 10, color: palette.navy },
    verticalAlignment: "top"
  };
  used.format.borders = {
    insideHorizontal: { style: "thin", color: palette.line }
  };

  const header = sheet.getRange(`A1:${lastColumn}1`);
  header.format = {
    fill: palette.navy,
    font: { name: "Aptos Display", size: 10, bold: true, color: "#FFFFFF" },
    verticalAlignment: "center",
    wrapText: true
  };
  header.format.rowHeightPx = 38;

  for (let index = 0; index < widths.length; index += 1) {
    sheet.getRange(`${columnName(index)}1:${columnName(index)}${lastRow}`).format.columnWidthPx = widths[index];
  }
  for (const column of ["D", "E", "I", "J", "N", "O", "P", "S"]) {
    sheet.getRange(`${column}2:${column}${lastRow}`).format.wrapText = true;
  }
  sheet.getRange(`K2:K${lastRow}`).format.numberFormat = "0.00";
  sheet.getRange(`R2:R${lastRow}`).format.numberFormat = "yyyy-mm-dd";
  sheet.getRange(`M2:M${lastRow}`).format.fill = palette.yellow;
  sheet.getRange(`N2:P${lastRow}`).format.fill = "#FFF8E4";
  sheet.getRange(`Q2:S${lastRow}`).format.fill = "#F2FBF7";
  sheet.getRange(`M2:M${lastRow}`).dataValidation = {
    rule: { type: "list", values: ["accept", "correct", "reject"] }
  };
  sheet.getRange(`M2:M${lastRow}`).conditionalFormats.add(
    "containsText",
    { text: "reject", format: { fill: "#FDEAEA", font: { color: "#A63D3D" } } }
  );
  sheet.getRange(`M2:M${lastRow}`).conditionalFormats.add(
    "containsText",
    { text: "accept", format: { fill: "#E4F6F0", font: { color: "#16725F" } } }
  );
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(3);
  const table = sheet.tables.add(`A1:${lastColumn}${lastRow}`, true, tableName);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;

  const inspection = await workbook.inspect({
    kind: "table",
    range: "Review!A1:S6",
    include: "values,formulas",
    tableMaxRows: 6,
    tableMaxCols: 19,
    maxChars: 5000
  });
  process.stdout.write(`${inspection.ndjson}\n`);
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 50 },
    summary: "review workbook formula error scan"
  });
  process.stdout.write(`${errors.ndjson}\n`);

  const preview = await workbook.render({
    sheetName: "Review",
    range: "A1:S12",
    scale: 1,
    format: "png"
  });
  await fs.mkdir(previewRoot, { recursive: true });
  await fs.writeFile(
    path.join(previewRoot, previewName),
    new Uint8Array(await preview.arrayBuffer())
  );
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const xlsx = await SpreadsheetFile.exportXlsx(workbook);
  await xlsx.save(outputPath);
  return { rows: payload.rows.length, outputPath };
}

const full = await buildWorkbook(
  fullInput,
  path.join(root, "data", "review", "review_pack.xlsx"),
  "review-pack.png",
  "ReviewCandidates"
);
const sample = await buildWorkbook(
  sampleInput,
  path.join(root, "reports", "review_sample_100.xlsx"),
  "review-sample-100.png",
  "ReviewSample100"
);
process.stdout.write(
  `Created ${full.outputPath} (${full.rows} rows) and ${sample.outputPath} (${sample.rows} rows).\n`
);
