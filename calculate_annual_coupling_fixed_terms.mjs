import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "D:/ztt-codex/codex-最新处理数据/policy_normalization_results_updated_已确认回写_摘要共同词已更新.xlsx";
const outputPath = "D:/ztt-codex/codex-最新处理数据/固定词表_年度科学政策网络耦合_论文方法.xlsx";
const alpha = 0.5;
const beta = 0.5;
const years = Array.from({ length: 28 }, (_, i) => 1998 + i);

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

function colLetter(index) {
  let n = index + 1;
  let result = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    result = String.fromCharCode(65 + rem) + result;
    n = Math.floor((n - 1) / 26);
  }
  return result;
}

function writeTable(sheet, rows) {
  const width = rows.reduce((max, row) => Math.max(max, row.length), 0);
  const normalized = rows.map((row) => [...row, ...Array(width - row.length).fill(null)]);
  sheet.getRange(`${colLetter(0)}1:${colLetter(width - 1)}${normalized.length}`).values = normalized;
  return { rows: normalized.length, cols: width };
}

function styleTable(sheet, dimensions, widths, numberFormatRanges = []) {
  const lastCol = colLetter(dimensions.cols - 1);
  const table = sheet.getRange(`A1:${lastCol}${dimensions.rows}`);
  const header = sheet.getRange(`A1:${lastCol}1`);
  header.format.fill = "#1F4E78";
  header.format.font = { color: "#FFFFFF", bold: true };
  header.format.horizontalAlignment = "center";
  header.format.verticalAlignment = "center";
  header.format.wrapText = true;
  table.format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };
  for (const [column, width] of Object.entries(widths)) {
    sheet.getRange(`${column}1:${column}${dimensions.rows}`).format.columnWidth = width;
  }
  for (const [range, format] of numberFormatRanges) sheet.getRange(range).format.numberFormat = format;
}

function readFixedDocs(sheet) {
  const values = sheet.getUsedRange().values;
  const headers = values[0].map((x) => String(x ?? ""));
  const yearIndex = headers.indexOf("year");
  const fixedIndex = headers.indexOf("固定全局词表筛选后关键词");
  if (yearIndex < 0 || fixedIndex < 0) throw new Error("固定词筛选结果缺少 year 或 固定全局词表筛选后关键词 列");
  return values.slice(1).map((row) => ({
    year: Number(row[yearIndex]),
    terms: splitTerms(row[fixedIndex]),
  })).filter((row) => Number.isInteger(row.year) && row.year >= years[0] && row.year <= years.at(-1));
}

function edgeKey(a, b) {
  return a < b ? `${a}\u0001${b}` : `${b}\u0001${a}`;
}

function edgeParts(key) {
  return key.split("\u0001");
}

function buildNetwork(docs) {
  const nodeDocFrequency = new Map();
  const edgeWeights = new Map();
  for (const doc of docs) {
    const terms = [...new Set(doc.terms)].sort((a, b) => a.localeCompare(b));
    for (const term of terms) nodeDocFrequency.set(term, (nodeDocFrequency.get(term) ?? 0) + 1);
    for (let i = 0; i < terms.length; i += 1) {
      for (let j = i + 1; j < terms.length; j += 1) {
        const key = edgeKey(terms[i], terms[j]);
        edgeWeights.set(key, (edgeWeights.get(key) ?? 0) + 1);
      }
    }
  }
  const weightedDegree = new Map();
  for (const term of nodeDocFrequency.keys()) weightedDegree.set(term, 0);
  for (const [key, weight] of edgeWeights) {
    const [a, b] = edgeParts(key);
    weightedDegree.set(a, (weightedDegree.get(a) ?? 0) + weight);
    weightedDegree.set(b, (weightedDegree.get(b) ?? 0) + weight);
  }
  return { nodeDocFrequency, weightedDegree, edgeWeights };
}

function cosineByUnion(mapA, mapB) {
  const keys = new Set([...mapA.keys(), ...mapB.keys()]);
  let dot = 0;
  let normA = 0;
  let normB = 0;
  for (const key of keys) {
    const a = Number(mapA.get(key) ?? 0);
    const b = Number(mapB.get(key) ?? 0);
    dot += a * b;
    normA += a * a;
    normB += b * b;
  }
  const denominator = Math.sqrt(normA) * Math.sqrt(normB);
  return denominator === 0 ? 0 : dot / denominator;
}

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const scienceDocs = readFixedDocs(workbook.worksheets.getItem("论文固定词筛选结果"));
const policyDocs = readFixedDocs(workbook.worksheets.getItem("政策固定词筛选结果"));

const annual = [];
const nodeRows = [["年度", "网络", "关键词", "文献频次", "加权度", "是否共享节点"]];
const edgeRows = [["年度", "网络", "关键词1", "关键词2", "共现边权重", "是否共享边"]];
const sharedNodeRows = [["年度", "关键词", "科学文献频次", "政策文献频次", "科学加权度", "政策加权度"]];
const sharedEdgeRows = [["年度", "关键词1", "关键词2", "科学边权重", "政策边权重", "合计边权重"]];

for (const year of years) {
  const scienceNet = buildNetwork(scienceDocs.filter((d) => d.year === year));
  const policyNet = buildNetwork(policyDocs.filter((d) => d.year === year));
  const sharedNodes = new Set([...scienceNet.weightedDegree.keys()].filter((term) => policyNet.weightedDegree.has(term)));
  const sharedEdges = new Set([...scienceNet.edgeWeights.keys()].filter((key) => policyNet.edgeWeights.has(key)));
  const nodeCoupling = cosineByUnion(scienceNet.weightedDegree, policyNet.weightedDegree);
  const edgeCoupling = cosineByUnion(scienceNet.edgeWeights, policyNet.edgeWeights);
  const finalCoupling = alpha * nodeCoupling + beta * edgeCoupling;

  annual.push([
    year,
    scienceDocs.filter((d) => d.year === year).length,
    policyDocs.filter((d) => d.year === year).length,
    scienceNet.weightedDegree.size,
    policyNet.weightedDegree.size,
    sharedNodes.size,
    scienceNet.edgeWeights.size,
    policyNet.edgeWeights.size,
    sharedEdges.size,
    [...scienceNet.weightedDegree.values()].reduce((a, b) => a + b, 0),
    [...policyNet.weightedDegree.values()].reduce((a, b) => a + b, 0),
    [...scienceNet.edgeWeights.values()].reduce((a, b) => a + b, 0),
    [...policyNet.edgeWeights.values()].reduce((a, b) => a + b, 0),
    nodeCoupling,
    edgeCoupling,
    finalCoupling,
  ]);

  for (const term of new Set([...scienceNet.weightedDegree.keys(), ...policyNet.weightedDegree.keys()])) {
    const s = scienceNet.weightedDegree.get(term) ?? 0;
    const p = policyNet.weightedDegree.get(term) ?? 0;
    if (s > 0 || scienceNet.nodeDocFrequency.has(term)) nodeRows.push([year, "科学", term, scienceNet.nodeDocFrequency.get(term) ?? 0, s, sharedNodes.has(term) ? "是" : "否"]);
    if (p > 0 || policyNet.nodeDocFrequency.has(term)) nodeRows.push([year, "政策", term, policyNet.nodeDocFrequency.get(term) ?? 0, p, sharedNodes.has(term) ? "是" : "否"]);
  }
  for (const [key, weight] of scienceNet.edgeWeights) {
    const [a, b] = edgeParts(key);
    edgeRows.push([year, "科学", a, b, weight, sharedEdges.has(key) ? "是" : "否"]);
  }
  for (const [key, weight] of policyNet.edgeWeights) {
    const [a, b] = edgeParts(key);
    edgeRows.push([year, "政策", a, b, weight, sharedEdges.has(key) ? "是" : "否"]);
  }
  for (const term of [...sharedNodes].sort((a, b) => a.localeCompare(b))) {
    sharedNodeRows.push([
      year,
      term,
      scienceNet.nodeDocFrequency.get(term) ?? 0,
      policyNet.nodeDocFrequency.get(term) ?? 0,
      scienceNet.weightedDegree.get(term) ?? 0,
      policyNet.weightedDegree.get(term) ?? 0,
    ]);
  }
  for (const key of [...sharedEdges].sort()) {
    const [a, b] = edgeParts(key);
    const s = scienceNet.edgeWeights.get(key) ?? 0;
    const p = policyNet.edgeWeights.get(key) ?? 0;
    sharedEdgeRows.push([year, a, b, s, p, s + p]);
  }
}

const summary = workbook.worksheets.add("年度耦合结果");
const summaryDimensions = writeTable(summary, [[
  "年度", "科学文献数", "政策文献数", "科学节点数", "政策节点数", "共同节点数",
  "科学边数", "政策边数", "共同边数", "科学节点总强度", "政策节点总强度",
  "科学边总权重", "政策边总权重", "节点耦合f", "边耦合g", "综合耦合ξ",
], ...annual]);
styleTable(summary, summaryDimensions, { A: 10, B: 12, C: 12, D: 12, E: 12, F: 12, G: 12, H: 12, I: 12, J: 16, K: 16, L: 16, M: 16, N: 14, O: 14, P: 14 }, [[`N2:P${summaryDimensions.rows}`, "0.0000"]]);

const nodes = workbook.worksheets.add("年度节点明细");
const nodeDimensions = writeTable(nodes, nodeRows);
styleTable(nodes, nodeDimensions, { A: 10, B: 10, C: 30, D: 12, E: 12, F: 12 });
const edges = workbook.worksheets.add("年度边明细");
const edgeDimensions = writeTable(edges, edgeRows);
styleTable(edges, edgeDimensions, { A: 10, B: 10, C: 30, D: 30, E: 14, F: 12 });
const sharedNodesSheet = workbook.worksheets.add("年度共享节点");
const sharedNodeDimensions = writeTable(sharedNodesSheet, sharedNodeRows);
styleTable(sharedNodesSheet, sharedNodeDimensions, { A: 10, B: 30, C: 14, D: 14, E: 14, F: 14 });
const sharedEdgesSheet = workbook.worksheets.add("年度共享边");
const sharedEdgeDimensions = writeTable(sharedEdgesSheet, sharedEdgeRows);
styleTable(sharedEdgesSheet, sharedEdgeDimensions, { A: 10, B: 30, C: 30, D: 14, E: 14, F: 14 });

const method = workbook.worksheets.add("耦合方法说明");
const methodDimensions = writeTable(method, [
  ["项目", "本次设定"],
  ["文献级输入", "论文固定词筛选结果、政策固定词筛选结果"],
  ["固定词字段", "固定全局词表筛选后关键词"],
  ["年度网络节点", "年度内至少出现在一篇文献中的固定关键词"],
  ["年度网络边", "同一篇文献内两个固定关键词共同出现形成一条无向边"],
  ["边权重", "年度内包含该关键词对的文献数；每篇文献内同一关键词只计一次"],
  ["节点加权度", "与该节点相连的边权重之和"],
  ["节点耦合f", "将两网节点集合取并集，缺失节点补0，对两侧加权度向量计算余弦相似度"],
  ["边耦合g", "将两网边集合取并集，缺失边补0，对两侧边权向量计算余弦相似度"],
  ["综合耦合ξ", "ξ = 0.5f + 0.5g；论文原文未给出固定α、β，本次采用等权基准"],
  ["方法对应关系", "对应论文Step 1–7；科学—政策替代论文中的科学—技术"],
  ["可比性说明", "固定词表跨年度不变，年度网络只改变文献和共现边权重"],
]);
styleTable(method, methodDimensions, { A: 20, B: 100 });
method.getRange(`B2:B${methodDimensions.rows}`).format.wrapText = true;
method.getRange(`A1:B${methodDimensions.rows}`).format.autofitRows();

await workbook.recalculate();
const check = await workbook.inspect({ kind: "table", sheetId: "年度耦合结果", range: "A1:P29", include: "values,formulas", tableMaxRows: 29, tableMaxCols: 16, maxChars: 16000 });
console.log("ANNUAL_CHECK\n" + check.ndjson);
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({ outputPath, annualRows: annual.length, scienceDocs: scienceDocs.length, policyDocs: policyDocs.length, nodeRows: nodeRows.length - 1, edgeRows: edgeRows.length - 1, sharedNodeRows: sharedNodeRows.length - 1, sharedEdgeRows: sharedEdgeRows.length - 1 }));
