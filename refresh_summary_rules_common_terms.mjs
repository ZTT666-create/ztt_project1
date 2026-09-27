import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "D:/ztt-codex/codex-最新处理数据/policy_normalization_results_updated_已确认回写.xlsx";
const path = "D:/ztt-codex/codex-最新处理数据/policy_normalization_results_updated_已确认回写_摘要共同词已更新.xlsx";
const previewDir = "D:/ztt-codex/codex-最新处理数据/_policy_summary_preview";

function terms(text) {
  const seen = new Set();
  const out = [];
  for (const x of String(text ?? "").split(";")) {
    const v = x.trim();
    if (v && !seen.has(v)) {
      seen.add(v);
      out.push(v);
    }
  }
  return out;
}

function mapSheetStats(sheet) {
  const values = sheet.getUsedRange().values;
  const h = values[0].map((x) => String(x ?? ""));
  const i = Object.fromEntries(h.map((x, idx) => [x, idx]));
  const counts = new Map();
  let totalKeywords = 0;
  for (const row of values.slice(1)) {
    const ts = terms(row[i["最终规范关键词"]]);
    totalKeywords += ts.length;
    for (const t of ts) counts.set(t, (counts.get(t) ?? 0) + 1);
  }
  return { values, headers: h, counts, unique: counts.size, totalKeywords, rows: values.length - 1, avg: totalKeywords / (values.length - 1) };
}

function round4(x) {
  return Math.round(x * 10000) / 10000;
}

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
console.log("LOADED");
const paper = mapSheetStats(workbook.worksheets.getItem("论文规范结果"));
const policy = mapSheetStats(workbook.worksheets.getItem("政策规范结果"));
const shared = [...paper.counts.keys()].filter((x) => policy.counts.has(x));
console.log("STATS", paper.unique, policy.unique, shared.length);

const summary = workbook.worksheets.getItem("统计摘要");
summary.getRange("A1:D16").values = [
  ["指标", "规范前", "规范后", "变化/说明"],
  ["科学论文记录数", 616, paper.rows, "不变"],
  ["政策记录数", 392, policy.rows, "不变"],
  ["科学端不同词数", 2443, paper.unique, paper.unique - 2443],
  ["政策端不同词数", 1279, policy.unique, policy.unique - 1279],
  ["两端精确共同词数", 220, shared.length, shared.length - 220],
  ["科学端共同词占比", 0.0901, round4(shared.length / paper.unique), round4(shared.length / paper.unique - 0.0901)],
  ["政策端共同词占比", 0.172, round4(shared.length / policy.unique), round4(shared.length / policy.unique - 0.172)],
  ["科学论文平均每篇关键词数", 7.21, round4(paper.avg), round4(paper.avg - 7.21)],
  ["政策平均每篇关键词数", 7.53, round4(policy.avg), round4(policy.avg - 7.53)],
  ["唯一词-保留", 4143, 4041, -102],
  ["唯一词-统一", 204, 306, 102],
  ["唯一词-删除", 141, 141, 0],
  ["词次-保留", 6768, 6581, -187],
  ["词次-统一", 331, 518, 187],
  ["词次-删除", 296, 296, 0],
];
console.log("SUMMARY_WRITTEN");

const rules = workbook.worksheets.getItem("规范规则");
const ruleRows = [
  ["统一", "用户确认：同义词/变体合并", "风险资本/风险投资/创业风险投资→创业投资；高科技产业→高技术产业；科技与金融结合→科技金融", "已审核确认，用于最终规范关键词"],
  ["统一", "用户确认：具体分型概括", "科技保险(财产险)/科技保险(人身险)→科技保险；知识产权被侵权保险→知识产权保险", "去除不影响主题判断的分型和责任限定"],
  ["统一", "用户确认：地区、试点、平台和机构概括", "科技金融试点城市→科技金融试点；知识产权交易平台→知识产权交易；科技金融专营事业部→科技金融机构", "去除过细的地区、载体或组织层级"],
  ["统一", "用户确认：具体基金、政策工具和模型概括", "国家科技成果转化引导基金→科技成果转化基金；不完全信息动态博弈→动态博弈", "保留核心主题，概括具体项目、工具或模型条件"],
];
for (let r = 14; r <= 17; r += 1) {
  rules.getRange(`A${r}:D${r}`).copyFrom(rules.getRange("A13:D13"), "all");
}
rules.getRange("A14:D17").values = ruleRows;
console.log("RULES_WRITTEN");

const common = workbook.worksheets.getItem("规范后共同词");
const commonRows = shared
  .map((term) => [term, paper.counts.get(term), policy.counts.get(term), paper.counts.get(term) + policy.counts.get(term)])
  .sort((a, b) => b[3] - a[3] || b[1] - a[1] || b[2] - a[2] || String(a[0]).localeCompare(String(b[0])))
  .slice(0, 199);
while (commonRows.length < 199) commonRows.push([null, null, null, null]);
common.getRange("A1:D200").values = [["规范关键词", "科学频次", "政策频次", "总频次"], ...commonRows];
console.log("COMMON_WRITTEN");

// Refresh the existing write-back note in the summary.
summary.getRange("A18:D22").values = [
  ["本次回写记录", "科学", "政策", "合计"],
  ["含最终规范关键词字段的记录数", paper.rows, policy.rows, paper.rows + policy.rows],
  ["发生合并或概括的记录数", 92, 99, 191],
  ["术语映射实际新增/更新", "0条新增，102条更新", "已确认回写", "保留原词"],
  [null, null, null, null],
];
console.log("NOTE_WRITTEN");

await workbook.recalculate();
console.log("RECALCULATED");
const checkSummary = await workbook.inspect({ kind: "table", sheetId: "统计摘要", range: "A1:D22", include: "values,formulas", tableMaxRows: 22, tableMaxCols: 4, maxChars: 8000 });
const checkRules = await workbook.inspect({ kind: "table", sheetId: "规范规则", range: "A1:D17", include: "values,formulas", tableMaxRows: 17, tableMaxCols: 4, maxChars: 8000 });
const checkCommon = await workbook.inspect({ kind: "table", sheetId: "规范后共同词", range: "A1:D10", include: "values,formulas", tableMaxRows: 10, tableMaxCols: 4, maxChars: 5000 });
console.log("SUMMARY\n" + checkSummary.ndjson);
console.log("RULES\n" + checkRules.ndjson);
console.log("COMMON\n" + checkCommon.ndjson);

await fs.mkdir(previewDir, { recursive: true });
for (const [name, range] of [["统计摘要", "A1:D22"], ["规范规则", "A1:D17"], ["规范后共同词", "A1:D20"]]) {
  const preview = await workbook.render({ sheetName: name, range, scale: 1.2, format: "png" });
  await fs.writeFile(`${previewDir}/${name}.png`, new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(path);
console.log(JSON.stringify({ path, scienceUnique: paper.unique, policyUnique: policy.unique, shared: shared.length, commonRows: commonRows.filter((r) => r[0]).length }));
