import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "D:/ztt-codex/codex-最新处理数据/policy_normalization_results_updated_已确认回写_摘要共同词已更新.xlsx";
const outputPath = "D:/ztt-codex/codex-最新处理数据/policy_normalization_results_updated_已确认回写_摘要共同词已更新_freq_refresh_tmp.xlsx";

function splitTerms(value) {
  const seen = new Set();
  const result = [];
  for (const part of String(value ?? "").split(";")) {
    const term = part.trim();
    if (term && !seen.has(term)) {
      seen.add(term);
      result.push(term);
    }
  }
  return result;
}

function readFinalCounts(sheet) {
  const values = sheet.getUsedRange().values;
  const headers = values[0].map((x) => String(x ?? ""));
  const finalIndex = headers.indexOf("最终规范关键词");
  if (finalIndex < 0) throw new Error("未找到最终规范关键词列");
  const counts = new Map();
  for (const row of values.slice(1)) {
    for (const term of splitTerms(row[finalIndex])) {
      counts.set(term, (counts.get(term) ?? 0) + 1);
    }
  }
  return { counts, rows: values.length - 1 };
}

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const science = readFinalCounts(workbook.worksheets.getItem("论文规范结果"));
const policy = readFinalCounts(workbook.worksheets.getItem("政策规范结果"));

const sharedRows = [...science.counts.keys()]
  .filter((term) => policy.counts.has(term))
  .map((term) => [term, science.counts.get(term), policy.counts.get(term), science.counts.get(term) + policy.counts.get(term)])
  .sort((a, b) => b[3] - a[3] || b[1] - a[1] || b[2] - a[2] || String(a[0]).localeCompare(String(b[0])));

const common = workbook.worksheets.getItem("规范后共同词");
common.getRange("A1:D5000").clear({ applyTo: "contents" });
common.getRange(`A1:D${sharedRows.length + 1}`).values = [["规范关键词", "科学频次", "政策频次", "总频次"], ...sharedRows];

const mapping = workbook.worksheets.getItem("术语映射");
const mappingValues = mapping.getUsedRange().values;
const mappingHeaders = mappingValues[0].map((x) => String(x ?? ""));
const canonicalIndex = mappingHeaders.indexOf("规范词");
const scienceFreqIndex = mappingHeaders.indexOf("科学频次");
const policyFreqIndex = mappingHeaders.indexOf("政策频次");
const totalFreqIndex = mappingHeaders.indexOf("总频次");
if ([canonicalIndex, scienceFreqIndex, policyFreqIndex, totalFreqIndex].some((x) => x < 0)) {
  throw new Error("术语映射缺少规范词或频次列");
}

const updatedMappingRows = mappingValues.slice(1).map((row) => {
  const next = [...row];
  const canonical = String(row[canonicalIndex] ?? "").trim();
  const s = canonical ? (science.counts.get(canonical) ?? 0) : 0;
  const p = canonical ? (policy.counts.get(canonical) ?? 0) : 0;
  next[scienceFreqIndex] = s;
  next[policyFreqIndex] = p;
  next[totalFreqIndex] = s + p;
  return next;
});

mapping.getRange("A1:G6000").clear({ applyTo: "contents" });
mapping.getRange(`A1:G${updatedMappingRows.length + 1}`).values = [mappingHeaders, ...updatedMappingRows];

await workbook.recalculate();

const commonCheck = await workbook.inspect({
  kind: "table",
  sheetId: "规范后共同词",
  range: `A1:D${Math.min(sharedRows.length + 1, 12)}`,
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 4,
  maxChars: 8000,
});
const mappingCheck = await workbook.inspect({
  kind: "table",
  sheetId: "术语映射",
  range: "A1:G12",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 7,
  maxChars: 8000,
});
console.log("COMMON_CHECK\n" + commonCheck.ndjson);
console.log("MAPPING_CHECK\n" + mappingCheck.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({
  outputPath,
  scienceRows: science.rows,
  policyRows: policy.rows,
  scienceUnique: science.counts.size,
  policyUnique: policy.counts.size,
  sharedRows: sharedRows.length,
  mappingRows: updatedMappingRows.length,
}));
