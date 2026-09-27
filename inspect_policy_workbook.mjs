import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "D:/ztt-codex/codex-最新处理数据/policy_normalization_results_updated.xlsx";
const previewDir = "D:/ztt-codex/codex-最新处理数据/_policy_preview";
await fs.mkdir(previewDir, { recursive: true });
const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const summary = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 12000,
  tableMaxRows: 5,
  tableMaxCols: 20,
  tableMaxCellChars: 80,
});
console.log(summary.ndjson);

const sheetInfo = await workbook.inspect({ kind: "sheet", include: "id,name" });
console.log("SHEETS");
console.log(sheetInfo.ndjson);

for (const name of ["论文规范结果", "政策规范结果"]) {
  try {
    const sheet = workbook.worksheets.getItem(name);
    const used = sheet.getUsedRange();
    console.log(`USED ${name}`, used.address ?? "");
    const values = used.values;
    console.log(`HEADER ${name}`, JSON.stringify(values?.[0] ?? []));
    console.log(`ROWS ${name}`, values?.length ?? 0, `COLS`, values?.[0]?.length ?? 0);
    const preview = await workbook.render({ sheetName: name, range: "A1:H20", scale: 1.5, format: "png" });
    await fs.writeFile(`${previewDir}/${name}.png`, new Uint8Array(await preview.arrayBuffer()));
  } catch (err) {
    console.error(`FAILED ${name}`, err?.message ?? err);
  }
}
