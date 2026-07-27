#!/usr/bin/env node
/* Build and visually verify the required review workbook sheets and sample. */

import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.env.SSD_ROOT
  ? path.resolve(process.env.SSD_ROOT)
  : path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const fullInput = path.join(root, "external", "review", "review_pack_rows.json");
const sampleInput = path.join(
  root,
  "external",
  "review",
  "remap_manual_review_sample_rows.json"
);
const previewRoot = path.join(root, "external", "review", "previews");
const partRoot = path.join(root, "external", "review", "workbook-parts");
const partManifest = path.join(partRoot, "manifest.json");
const maxRowsPerSheet = 20_000;

const palette = {
  navy: "#24324A",
  yellow: "#FFEAA6",
  line: "#DED8CF"
};

const widths = [
  170, 170, 185, 95, 85, 95, 420, 220, 145, 145, 145,
  190, 260, 390, 85, 110, 240, 190, 110, 90, 150, 320,
  95, 240, 125, 320, 120, 165, 180, 180, 360, 125, 105, 280
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

async function buildWorkbook({
  headers,
  rows,
  outputPath,
  previewName,
  tableName,
  sheetName,
  summaryMetadata = null
}) {
  const workbook = Workbook.create();
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;

  const values = [headers, ...rows];
  const lastColumn = columnName(headers.length - 1);
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
    sheet.getRange(
      `${columnName(index)}1:${columnName(index)}${lastRow}`
    ).format.columnWidthPx = widths[index];
  }
  for (const column of [
    "G", "H", "M", "N", "U", "V", "Z", "AC", "AD", "AE", "AH"
  ]) {
    sheet.getRange(`${column}2:${column}${lastRow}`).format.wrapText = true;
  }
  sheet.getRange(`O2:O${lastRow}`).format.numberFormat = "0.00";
  sheet.getRange(`AG2:AG${lastRow}`).format.numberFormat = "yyyy-mm-dd";
  sheet.getRange(`AB2:AB${lastRow}`).format.fill = palette.yellow;
  sheet.getRange(`AC2:AE${lastRow}`).format.fill = "#FFF8E4";
  sheet.getRange(`AF2:AH${lastRow}`).format.fill = "#F2FBF7";
  sheet.getRange(`AB2:AB${lastRow}`).dataValidation = {
    rule: { type: "list", values: ["accept", "correct", "reject"] }
  };
  sheet.getRange(`AB2:AB${lastRow}`).conditionalFormats.add(
    "containsText",
    { text: "reject", format: { fill: "#FDEAEA", font: { color: "#A63D3D" } } }
  );
  sheet.getRange(`AB2:AB${lastRow}`).conditionalFormats.add(
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
    range: `${sheetName}!A1:AH6`,
    include: "values,formulas",
    tableMaxRows: 6,
    tableMaxCols: 34,
    maxChars: 7000
  });
  process.stdout.write(`${inspection.ndjson}\n`);
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 50 },
    summary: `${sheetName} formula error scan`
  });
  process.stdout.write(`${errors.ndjson}\n`);

  if (summaryMetadata) {
    const summary = workbook.worksheets.add("Summary");
    summary.showGridLines = false;
    summary.getRange("A1:D1").merge();
    summary.getRange("A1:D1").values = [[
      "Formal remap manual-review sample"
    ]];
    summary.getRange("A1:D1").format = {
      fill: palette.navy,
      font: {
        name: "Aptos Display",
        size: 18,
        bold: true,
        color: "#FFFFFF"
      },
      verticalAlignment: "center"
    };
    summary.getRange("A1:D1").format.rowHeightPx = 42;
    summary.getRange("A3:B13").values = [
      ["Profile", summaryMetadata.profile_id],
      ["Profile SHA-256", summaryMetadata.profile_sha256],
      ["All presentation candidates", summaryMetadata.candidate_count],
      [
        "All review-only candidates",
        summaryMetadata.candidate_review_category_counts["manual guard"]
          + summaryMetadata.candidate_review_category_counts.conflict
          + summaryMetadata.candidate_review_category_counts["parser mismatch"]
      ],
      ["", ""],
      ["Sample rows", null],
      ["Manual guards", null],
      ["Conflict downgrades", null],
      ["Parser mismatches", null],
      ["", ""],
      ["Stratified by", summaryMetadata.stratification.join(", ")]
    ];
    summary.getRange("B8").formulas = [[
      "=COUNTA('Manual review sample'!$A$2:$A$101)"
    ]];
    summary.getRange("B9").formulas = [[
      '=COUNTIF(\'Manual review sample\'!$AA$2:$AA$101,"manual guard")'
    ]];
    summary.getRange("B10").formulas = [[
      '=COUNTIF(\'Manual review sample\'!$AA$2:$AA$101,"conflict")'
    ]];
    summary.getRange("B11").formulas = [[
      '=COUNTIF(\'Manual review sample\'!$AA$2:$AA$101,"parser mismatch")'
    ]];
    summary.getRange("A3:A13").format = {
      fill: "#E8EEF7",
      font: { name: "Aptos", size: 11, bold: true, color: palette.navy }
    };
    summary.getRange("B3:B13").format = {
      font: { name: "Aptos", size: 11, color: palette.navy },
      wrapText: true
    };
    summary.getRange("A3:B13").format.borders = {
      insideHorizontal: { style: "thin", color: palette.line }
    };
    summary.getRange("A1:A13").format.columnWidthPx = 210;
    summary.getRange("B1:B13").format.columnWidthPx = 520;
    summary.getRange("B5:B11").format.numberFormat = "#,##0";
    const summaryInspection = await workbook.inspect({
      kind: "table",
      range: "Summary!A1:B13",
      include: "values,formulas",
      tableMaxRows: 13,
      tableMaxCols: 2,
      maxChars: 3000
    });
    process.stdout.write(`${summaryInspection.ndjson}\n`);
    const summaryPreview = await workbook.render({
      sheetName: "Summary",
      range: "A1:B13",
      scale: 1.5,
      format: "png"
    });
    await fs.mkdir(previewRoot, { recursive: true });
    await fs.writeFile(
      path.join(previewRoot, "remap-manual-review-summary.png"),
      new Uint8Array(await summaryPreview.arrayBuffer())
    );
  }

  const preview = await workbook.render({
    sheetName,
    range: "A1:AH12",
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
  return { rows: rows.length, outputPath, sheetName, tableName };
}

const fullPayload = JSON.parse(await fs.readFile(fullInput, "utf8"));
await fs.mkdir(partRoot, { recursive: true });
const parts = [];
for (
  let start = 0, partNumber = 1;
  start < fullPayload.rows.length;
  start += maxRowsPerSheet, partNumber += 1
) {
  const suffix = String(partNumber).padStart(2, "0");
  const rows = fullPayload.rows.slice(start, start + maxRowsPerSheet);
  parts.push(
    await buildWorkbook({
      headers: fullPayload.headers,
      rows,
      outputPath: path.join(partRoot, `review-pack-part-${suffix}.xlsx`),
      previewName: `review-pack-${suffix}.png`,
      tableName: `ReviewCandidates${suffix}`,
      sheetName: `Review ${suffix}`
    })
  );
  global.gc?.();
}

const samplePayload = JSON.parse(await fs.readFile(sampleInput, "utf8"));
const sample = await buildWorkbook({
  headers: samplePayload.headers,
  rows: samplePayload.rows,
  outputPath: path.join(root, "reports", "remap_manual_review_sample.xlsx"),
  previewName: "remap-manual-review-sample.png",
  tableName: "RemapManualReviewSample",
  sheetName: "Manual review sample",
  summaryMetadata: samplePayload.metadata
});
await fs.writeFile(
  partManifest,
  `${JSON.stringify(
    {
      headers: fullPayload.headers,
      rowCount: fullPayload.rows.length,
      parts
    },
    null,
    2
  )}\n`,
  "utf8"
);
process.stdout.write(
  `Created ${parts.length} verified workbook sheets `
  + `(${fullPayload.rows.length} rows) and ${sample.outputPath} `
  + `(${sample.rows} rows).\n`
);
