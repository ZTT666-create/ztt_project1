import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const path = "D:/ztt-codex/codex-最新处理数据/policy_normalization_results_updated_已确认回写.xlsx";
const input = await FileBlob.load(path);
const workbook = await SpreadsheetFile.importXlsx(input);

for (const [sheetName, layer] of [["论文规范结果", "科学"], ["政策规范结果", "政策"]]) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const values = sheet.getUsedRange().values;
  const h = values[0].map((x) => String(x ?? ""));
  const i = Object.fromEntries(h.map((x, idx) => [x, idx]));
  let changed = 0;
  let oldOverwritten = 0;
  let statusConfirmed = 0;
  let finalCountMismatch = 0;
  for (const row of values.slice(1)) {
    const oldValue = String(row[i["规范关键词"]] ?? "");
    const original = String(row[i["原规范关键词"]] ?? "");
    const finalValue = String(row[i["最终规范关键词"]] ?? "");
    const count = Number(row[i["最终规范数量"]] ?? 0);
    if (oldValue !== original) oldOverwritten += 1;
    if (oldValue !== finalValue) changed += 1;
    if (String(row[i["审核状态"]] ?? "") === "已确认") statusConfirmed += 1;
    const finalCount = finalValue ? finalValue.split(";").filter(Boolean).length : 0;
    if (finalCount !== count) finalCountMismatch += 1;
  }
  console.log(JSON.stringify({ sheetName, layer, rows: values.length - 1, changed, oldOverwritten, statusConfirmed, finalCountMismatch, headers: h }));
}

const dict = workbook.worksheets.getItem("术语映射");
const dictValues = dict.getUsedRange().values;
const dh = dictValues[0].map((x) => String(x ?? ""));
const di = Object.fromEntries(dh.map((x, idx) => [x, idx]));
const approved = new Map();
for (const sheetName of ["论文规范结果", "政策规范结果"]) {
  const values = workbook.worksheets.getItem(sheetName).getUsedRange().values;
  const h = values[0].map((x) => String(x ?? ""));
  const i = Object.fromEntries(h.map((x, idx) => [x, idx]));
  for (const row of values.slice(1)) {
    const type = String(row[i["处理类型"]] ?? "");
    if (!type) continue;
    const note = String(row[i["审核备注"]] ?? "");
    for (const part of note.split("；")) {
      const m = part.match(/^(.+?)→(.+?)（/);
      if (m) approved.set(m[1], m[2]);
    }
  }
}
let dictMismatch = 0;
let missingDict = 0;
for (const [original, target] of approved.entries()) {
  const matches = dictValues.slice(1).filter((r) => String(r[di["原始词"]] ?? "") === original);
  if (!matches.length) {
    missingDict += 1;
  } else if (!matches.some((r) => String(r[di["规范词"]] ?? "") === target)) {
    dictMismatch += 1;
  }
}
console.log(JSON.stringify({ dictionaryRows: dictValues.length - 1, approvedMappingsInResults: approved.size, missingDict, dictMismatch, dictionaryHeaders: dh }));

const paperCheck = await workbook.inspect({ kind: "table", sheetId: "论文规范结果", range: "A1:N5", include: "values,formulas", tableMaxRows: 5, tableMaxCols: 14, maxChars: 5000 });
console.log(paperCheck.ndjson);
