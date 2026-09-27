import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "D:/ztt-codex/codex-最新处理数据/policy_normalization_results_updated.xlsx";
const outputPath = "D:/ztt-codex/codex-最新处理数据/policy_normalization_results_updated_已确认回写.xlsx";
const synonymPath = "C:/Users/张甜甜的Redmi/.codex/visualizations/2026/09/20/01a0bc3a-e620-7511-b6b4-b009915a0768/关键词合并与概括建议_1998-2025/同义词_变体合并建议.csv";
const generalizePath = "C:/Users/张甜甜的Redmi/.codex/visualizations/2026/09/20/01a0bc3a-e620-7511-b6b4-b009915a0768/关键词合并与概括建议_1998-2025/过于具体关键词_概括建议.csv";
const previewDir = "D:/ztt-codex/codex-最新处理数据/_policy_updated_preview";
const changeLogPath = "D:/ztt-codex/codex-最新处理数据/policy_normalization_results_updated_已确认回写_变更记录.csv";

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') {
        field += '"';
        i += 1;
      } else if (c === '"') {
        quoted = false;
      } else {
        field += c;
      }
    } else if (c === '"') {
      quoted = true;
    } else if (c === ",") {
      row.push(field);
      field = "";
    } else if (c === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += c;
    }
  }
  if (field.length || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }
  if (!rows.length) return [];
  const headers = rows[0].map((h, i) => i === 0 ? h.replace(/^\uFEFF/, "") : h);
  return rows.slice(1).filter((r) => r.some((x) => x !== "")).map((r) => {
    const o = {};
    headers.forEach((h, i) => { o[h] = r[i] ?? ""; });
    return o;
  });
}

function uniqueInOrder(values) {
  const seen = new Set();
  const out = [];
  for (const value of values) {
    const v = String(value ?? "").trim();
    if (!v || seen.has(v)) continue;
    seen.add(v);
    out.push(v);
  }
  return out;
}

function buildMap(rows, type) {
  const map = new Map();
  for (const r of rows) {
    const key = `${r.Layer}\u0000${r.OriginalKeyword}`;
    map.set(key, {
      target: r.SuggestedKeyword,
      type,
      confidence: r.Confidence,
      basis: r.Basis,
    });
  }
  return map;
}

function mapKeywordList(layer, text, mapping) {
  const originalTerms = uniqueInOrder(String(text ?? "").split(";"));
  const finalTerms = [];
  const actions = [];
  for (const term of originalTerms) {
    const hit = mapping.get(`${layer}\u0000${term}`);
    if (!hit) {
      finalTerms.push(term);
      continue;
    }
    finalTerms.push(hit.target);
    actions.push(`${term}→${hit.target}（${hit.type}）`);
  }
  const types = uniqueInOrder(actions.map((a) => a.includes("过于具体关键词概括") ? "过于具体关键词概括" : "同义词或变体合并"));
  return {
    original: originalTerms.join(";"),
    final: uniqueInOrder(finalTerms).join(";"),
    count: uniqueInOrder(finalTerms).length,
    types: types.join("；"),
    status: actions.length ? "已确认" : "无需处理",
    note: actions.join("；"),
  };
}

function csvEscape(value) {
  const s = String(value ?? "");
  return /[",\r\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
}

function rowsToCsv(rows, headers) {
  return [headers.join(","), ...rows.map((r) => headers.map((h) => csvEscape(r[h])).join(","))].join("\n") + "\n";
}

async function copyStyleFromH(sheet, lastRow) {
  for (const col of ["I", "J", "K", "L", "M", "N"]) {
    sheet.getRange(`${col}1:${col}${lastRow}`).copyFrom(sheet.getRange(`H1:H${lastRow}`), "all");
  }
  sheet.getRange("I:I").format.columnWidth = 26;
  sheet.getRange("J:J").format.columnWidth = 30;
  sheet.getRange("K:K").format.columnWidth = 14;
  sheet.getRange("L:L").format.columnWidth = 22;
  sheet.getRange("M:M").format.columnWidth = 12;
  sheet.getRange("N:N").format.columnWidth = 42;
}

const synonymRows = parseCsv(await fs.readFile(synonymPath, "utf8"));
const generalizeRows = parseCsv(await fs.readFile(generalizePath, "utf8"));
const synonymMap = buildMap(synonymRows, "同义词或变体合并");
const generalizeMap = buildMap(generalizeRows, "过于具体关键词概括");
const mapping = new Map([...synonymMap, ...generalizeMap]);
console.log("MAPPING_DEBUG", synonymRows.length, generalizeRows.length, synonymRows[0], generalizeRows[0], mapping.size);

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const changeLog = [];
const sheetStats = [];

for (const [sheetName, layer] of [["论文规范结果", "科学"], ["政策规范结果", "政策"]]) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const used = sheet.getUsedRange();
  const values = used.values;
  const header = values[0].map((x) => String(x ?? ""));
  const col = Object.fromEntries(header.map((h, i) => [h, i]));
  const oldRows = values.slice(1);
  const newRows = [];
  let changed = 0;
  let mappedTermCount = 0;
  for (const row of oldRows) {
    const oldNorm = String(row[col["规范关键词"]] ?? "");
    const result = mapKeywordList(layer, oldNorm, mapping);
    if (result.types) {
      changed += 1;
      mappedTermCount += result.note.split("；").filter(Boolean).length;
      changeLog.push({
        层级: layer,
        工作表: sheetName,
        doc_id: row[col.doc_id],
        year: row[col.year],
        title: row[col.title],
        原规范关键词: oldNorm,
        最终规范关键词: result.final,
        最终规范数量: result.count,
        处理类型: result.types,
        审核状态: result.status,
        审核备注: result.note,
      });
    }
    newRows.push([
      ...row,
      oldNorm,
      result.final,
      result.count,
      result.types,
      result.status,
      result.note,
    ]);
  }
  const newHeaders = [...header, "原规范关键词", "最终规范关键词", "最终规范数量", "处理类型", "审核状态", "审核备注"];
  await copyStyleFromH(sheet, values.length);
  sheet.getRange(`I1:N${values.length}`).values = [
    newHeaders.slice(8),
    ...newRows.map((r) => r.slice(8)),
  ];
  sheetStats.push({ 层级: layer, 工作表: sheetName, 记录数: oldRows.length, 有映射记录数: changed, 映射词数: mappedTermCount });
}

// Update the existing terminology dictionary without removing any rows.
const dictSheet = workbook.worksheets.getItem("术语映射");
const dictRange = dictSheet.getUsedRange();
const dictValues = dictRange.values;
const dictHeader = dictValues[0].map((x) => String(x ?? ""));
const dictRows = dictValues.slice(1).map((r) => [...r]);
const dictCol = Object.fromEntries(dictHeader.map((h, i) => [h, i]));
const dictIndex = new Map();
dictRows.forEach((r, i) => {
  const raw = String(r[dictCol["原始词"]] ?? "");
  if (raw) dictIndex.set(raw, i);
});

const docCounts = { 科学: new Map(), 政策: new Map() };
for (const [sheetName, layer] of [["论文规范结果", "科学"], ["政策规范结果", "政策"]]) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const values = sheet.getUsedRange().values;
  const h = values[0].map((x) => String(x ?? ""));
  const idx = Object.fromEntries(h.map((x, i) => [x, i]));
  for (const row of values.slice(1)) {
    const terms = uniqueInOrder(String(row[idx["规范关键词"]] ?? "").split(";"));
    for (const term of terms) docCounts[layer].set(term, (docCounts[layer].get(term) ?? 0) + 1);
  }
}

const mappingByOriginal = new Map();
for (const r of [...synonymRows, ...generalizeRows]) {
  if (!mappingByOriginal.has(r.OriginalKeyword)) mappingByOriginal.set(r.OriginalKeyword, r);
}
let dictUpdated = 0;
let dictAppended = 0;
for (const [original, suggestion] of mappingByOriginal.entries()) {
  const scienceFreq = docCounts.科学.get(original) ?? 0;
  const policyFreq = docCounts.政策.get(original) ?? 0;
  const basis = `用户审核确认：${suggestion.MappingType}；${suggestion.Basis}`;
  const existingIndex = dictIndex.get(original);
  if (existingIndex !== undefined) {
    const r = dictRows[existingIndex];
    const oldTarget = String(r[dictCol["规范词"]] ?? "");
    r[dictCol["处理"]] = "统一";
    r[dictCol["规范词"]] = suggestion.SuggestedKeyword;
    const oldBasis = String(r[dictCol["处理依据"]] ?? "");
    r[dictCol["处理依据"]] = oldBasis.includes("用户审核确认") ? oldBasis : `${oldBasis ? `${oldBasis}；` : ""}${basis}`;
    if (oldTarget !== suggestion.SuggestedKeyword || !oldBasis.includes("用户审核确认")) dictUpdated += 1;
  } else {
    dictRows.push([
      original,
      "统一",
      suggestion.SuggestedKeyword,
      scienceFreq,
      policyFreq,
      scienceFreq + policyFreq,
      basis,
    ]);
    dictAppended += 1;
  }
}

const dictNewValues = [dictHeader, ...dictRows];
dictSheet.getRange(`A1:G${dictNewValues.length}`).values = dictNewValues;
if (dictNewValues.length > dictValues.length) {
  dictSheet.getRange(`A${dictValues.length}:G${dictNewValues.length}`).copyFrom(dictSheet.getRange(`A${dictValues.length}:G${dictValues.length}`), "all");
  dictSheet.getRange(`A1:G${dictNewValues.length}`).values = dictNewValues;
}

// Add a compact note to the existing summary without changing its existing metrics.
const summarySheet = workbook.worksheets.getItem("统计摘要");
const summaryUsed = summarySheet.getUsedRange();
const summaryValues = summaryUsed.values;
const summaryHeader = summaryValues[0].map((x) => String(x ?? ""));
const summaryRows = summaryValues.slice(1).map((r) => [...r]);
const summaryStart = summaryRows.length + 3;
summarySheet.getRange(`A${summaryStart}:D${summaryStart + 3}`).values = [
  ["本次回写记录", "科学", "政策", "合计"],
  ["新增最终规范关键词字段的记录数", sheetStats[0].记录数, sheetStats[1].记录数, sheetStats[0].记录数 + sheetStats[1].记录数],
  ["发生合并或概括的记录数", sheetStats[0].有映射记录数, sheetStats[1].有映射记录数, sheetStats[0].有映射记录数 + sheetStats[1].有映射记录数],
  ["术语映射词典新增/更新", `${dictAppended}条新增，${dictUpdated}条更新`, "已确认回写", "保留原词"],
];

await workbook.recalculate();

const checkPaper = await workbook.inspect({ kind: "table", sheetId: "论文规范结果", range: "A1:N5", include: "values,formulas", tableMaxRows: 5, tableMaxCols: 14, maxChars: 5000 });
const checkPolicy = await workbook.inspect({ kind: "table", sheetId: "政策规范结果", range: "A1:N5", include: "values,formulas", tableMaxRows: 5, tableMaxCols: 14, maxChars: 5000 });
const checkDict = await workbook.inspect({ kind: "table", sheetId: "术语映射", range: `A${Math.max(1, dictNewValues.length - 4)}:G${dictNewValues.length}`, include: "values,formulas", tableMaxRows: 6, tableMaxCols: 7, maxChars: 5000 });
console.log("CHECK_PAPER\n" + checkPaper.ndjson);
console.log("CHECK_POLICY\n" + checkPolicy.ndjson);
console.log("CHECK_DICT_TAIL\n" + checkDict.ndjson);

await fs.mkdir(previewDir, { recursive: true });
for (const name of ["论文规范结果", "政策规范结果"]) {
  const preview = await workbook.render({ sheetName: name, range: "A1:N20", scale: 1, format: "png" });
  await fs.writeFile(`${previewDir}/${name}.png`, new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
const logHeaders = ["层级", "工作表", "doc_id", "year", "title", "原规范关键词", "最终规范关键词", "最终规范数量", "处理类型", "审核状态", "审核备注"];
await fs.writeFile(changeLogPath, rowsToCsv(changeLog, logHeaders), "utf8");
console.log(JSON.stringify({ outputPath, changeLogPath, sheetStats, dictUpdated, dictAppended, mappingRows: mappingByOriginal.size }));
