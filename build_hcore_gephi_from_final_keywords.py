from __future__ import annotations

import csv
import json
import zipfile
from collections import Counter
from datetime import date
from itertools import combinations
from pathlib import Path
from xml.etree import ElementTree as ET

import openpyxl


INPUT = Path(r"D:\ztt-codex\codex-最新处理数据\policy_normalization_results_updated_已确认回写_摘要共同词已更新.xlsx")
OUTPUT = Path(r"D:\ztt-codex\codex-最新处理数据\最终规范关键词_H-core_Gephi_1998-2025")
STAGES = [("A", 1998, 2005), ("B", 2006, 2011), ("C", 2012, 2015), ("D", 2016, 2019), ("E", 2020, 2025)]
NS = "http://www.gexf.net/1.2draft"
ET.register_namespace("", NS)


def q(tag: str) -> str:
    return f"{{{NS}}}{tag}"


def h_index(degrees: list[int]) -> int:
    h = 0
    for rank, degree in enumerate(sorted(degrees, reverse=True), start=1):
        if degree >= rank:
            h = rank
        else:
            break
    return h


def read_records(wb, sheet_name: str) -> list[dict[str, object]]:
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(v or "") for v in rows[0]]
    idx = {h: i for i, h in enumerate(headers)}
    out = []
    for row in rows[1:]:
        terms = []
        seen = set()
        for term in str(row[idx["最终规范关键词"]] or "").split(";"):
            term = term.strip()
            if term and term not in seen:
                seen.add(term)
                terms.append(term)
        out.append({"doc_id": str(row[idx["doc_id"]] or ""), "year": int(row[idx["year"]]), "terms": terms})
    return out


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def add_attr(parent: ET.Element, attr_id: str, title: str, attr_type: str) -> None:
    ET.SubElement(parent, q("attribute"), {"id": attr_id, "title": title, "type": attr_type})


def add_value(parent: ET.Element, attr_id: str, value: object) -> None:
    ET.SubElement(parent, q("attvalue"), {"for": attr_id, "value": str(value)})


def write_gexf(path: Path, layer: str, stage: str, years: str, h: int, nodes: list[dict[str, object]], edges: list[dict[str, object]]) -> None:
    root = ET.Element(q("gexf"), {"version": "1.2"})
    meta = ET.SubElement(root, q("meta"), {"lastmodifieddate": date.today().isoformat()})
    ET.SubElement(meta, q("creator")).text = "Codex"
    ET.SubElement(meta, q("description")).text = f"{layer}{stage}阶段（{years}）最终规范关键词H-core网络，H={h}"
    graph = ET.SubElement(root, q("graph"), {"mode": "static", "defaultedgetype": "undirected"})

    node_attrs = ET.SubElement(graph, q("attributes"), {"class": "node", "mode": "static"})
    for item in [
        ("n0", "Layer", "string"), ("n1", "Stage", "string"), ("n2", "Years", "string"),
        ("n3", "HIndex", "integer"), ("n4", "Frequency", "integer"),
        ("n5", "NormalizedFrequency", "double"), ("n6", "OriginalDegree", "integer"),
        ("n7", "OriginalWeightedDegree", "integer"), ("n8", "CoreDegree", "integer"),
        ("n9", "CoreWeightedDegree", "integer"), ("n10", "CoreSelected", "boolean"),
    ]:
        add_attr(node_attrs, *item)

    edge_attrs = ET.SubElement(graph, q("attributes"), {"class": "edge", "mode": "static"})
    for item in [("e0", "Layer", "string"), ("e1", "Stage", "string"), ("e2", "Years", "string"), ("e3", "HIndex", "integer"), ("e4", "NormalizedWeight", "double")]:
        add_attr(edge_attrs, *item)

    nodes_xml = ET.SubElement(graph, q("nodes"))
    for row in nodes:
        node = ET.SubElement(nodes_xml, q("node"), {"id": str(row["Id"]), "label": str(row["Label"])})
        values = ET.SubElement(node, q("attvalues"))
        for attr_id, value in [
            ("n0", layer), ("n1", stage), ("n2", years), ("n3", h), ("n4", row["Frequency"]),
            ("n5", row["NormalizedFrequency"]), ("n6", row["OriginalDegree"]),
            ("n7", row["OriginalWeightedDegree"]), ("n8", row["CoreDegree"]),
            ("n9", row["CoreWeightedDegree"]), ("n10", "true"),
        ]:
            add_value(values, attr_id, value)

    edges_xml = ET.SubElement(graph, q("edges"))
    for index, row in enumerate(edges, start=1):
        edge = ET.SubElement(edges_xml, q("edge"), {
            "id": f"e{index:06d}", "source": str(row["Source"]), "target": str(row["Target"]), "weight": str(row["Weight"]),
        })
        values = ET.SubElement(edge, q("attvalues"))
        for attr_id, value in [("e0", layer), ("e1", stage), ("e2", years), ("e3", h), ("e4", row["NormalizedWeight"])]:
            add_value(values, attr_id, value)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    OUTPUT.mkdir()
    gexf_dir = OUTPUT / "gexf"
    table_dir = OUTPUT / "tables"
    summary_dir = OUTPUT / "summary"
    for d in (gexf_dir, table_dir, summary_dir):
        d.mkdir()

    wb = openpyxl.load_workbook(INPUT, read_only=True, data_only=True)
    summary_rows = []
    h_detail_rows = []
    manifest = []

    for layer, sheet_name, code in [("科学", "论文规范结果", "SCI"), ("政策", "政策规范结果", "POL")]:
        records = read_records(wb, sheet_name)
        for stage, start, end in STAGES:
            years = f"{start}-{end}"
            stage_records = [r for r in records if start <= r["year"] <= end]
            node_frequency: Counter[str] = Counter()
            edge_weight: Counter[tuple[str, str]] = Counter()
            for record in stage_records:
                terms = sorted(set(record["terms"]))
                node_frequency.update(terms)
                edge_weight.update(combinations(terms, 2))

            neighbors = {term: set() for term in node_frequency}
            weighted_degree = Counter()
            for (source, target), weight in edge_weight.items():
                neighbors[source].add(target)
                neighbors[target].add(source)
                weighted_degree[source] += weight
                weighted_degree[target] += weight
            degree = {term: len(values) for term, values in neighbors.items()}
            h = h_index(list(degree.values()))
            retained = {term for term, value in degree.items() if value >= h}
            core_edges_raw = {pair: weight for pair, weight in edge_weight.items() if pair[0] in retained and pair[1] in retained}
            core_degree = Counter()
            core_weighted_degree = Counter()
            for (source, target), weight in core_edges_raw.items():
                core_degree[source] += 1
                core_degree[target] += 1
                core_weighted_degree[source] += weight
                core_weighted_degree[target] += weight

            ids = {term: f"{code}_{stage}_{i:05d}" for i, term in enumerate(sorted(retained), 1)}
            node_rows = []
            for term in sorted(retained):
                node_rows.append({
                    "Id": ids[term], "Label": term, "Layer": layer, "Stage": stage, "Years": years,
                    "HIndex": h, "Frequency": node_frequency[term], "NormalizedFrequency": node_frequency[term] / len(stage_records) if stage_records else 0,
                    "OriginalDegree": degree[term], "OriginalWeightedDegree": weighted_degree[term],
                    "CoreDegree": core_degree[term], "CoreWeightedDegree": core_weighted_degree[term], "CoreSelected": "Yes",
                })
            edge_rows = []
            for (source, target), weight in sorted(core_edges_raw.items()):
                edge_rows.append({
                    "Source": ids[source], "Target": ids[target], "SourceLabel": source, "TargetLabel": target,
                    "Type": "Undirected", "Layer": layer, "Stage": stage, "Years": years, "HIndex": h,
                    "Weight": weight, "NormalizedWeight": weight / len(stage_records) if stage_records else 0,
                })

            base = f"{layer}_{stage}_{years}_H-core_H{h}"
            node_path = table_dir / f"{base}_节点.csv"
            edge_path = table_dir / f"{base}_边.csv"
            gexf_path = gexf_dir / f"{base}.gexf"
            write_csv(node_path, list(node_rows[0].keys()) if node_rows else ["Id", "Label"], node_rows)
            write_csv(edge_path, list(edge_rows[0].keys()) if edge_rows else ["Source", "Target"], edge_rows)
            write_gexf(gexf_path, layer, stage, years, h, node_rows, edge_rows)

            full_edge_weight_sum = sum(edge_weight.values())
            core_edge_weight_sum = sum(core_edges_raw.values())
            summary_rows.append({
                "Layer": layer, "Stage": stage, "Years": years, "DocumentCount": len(stage_records),
                "HIndex": h, "FullNodeCount": len(node_frequency), "HCoreNodeCount": len(retained),
                "FullEdgeCount": len(edge_weight), "HCoreEdgeCount": len(core_edges_raw),
                "FullEdgeWeightSum": full_edge_weight_sum, "HCoreEdgeWeightSum": core_edge_weight_sum,
                "NodeRetentionRate": len(retained) / len(node_frequency) if node_frequency else 0,
                "EdgeRetentionRate": len(core_edges_raw) / len(edge_weight) if edge_weight else 0,
                "EdgeWeightRetentionRate": core_edge_weight_sum / full_edge_weight_sum if full_edge_weight_sum else 0,
            })
            ranked = sorted(degree.items(), key=lambda x: (-x[1], x[0]))
            for rank, (term, value) in enumerate(ranked, 1):
                h_detail_rows.append({"Layer": layer, "Stage": stage, "Years": years, "Rank": rank, "Keyword": term, "OriginalDegree": value, "HIndex": h, "SelectedInHCore": "Yes" if term in retained else "No"})
            manifest.append({"layer": layer, "stage": stage, "years": years, "h": h, "full_nodes": len(node_frequency), "hcore_nodes": len(retained), "full_edges": len(edge_weight), "hcore_edges": len(core_edges_raw), "gexf": str(gexf_path.relative_to(OUTPUT)), "nodes_csv": str(node_path.relative_to(OUTPUT)), "edges_csv": str(edge_path.relative_to(OUTPUT))})

    write_csv(summary_dir / "H-core网络统计.csv", list(summary_rows[0].keys()), sorted(summary_rows, key=lambda r: (r["Layer"], r["Stage"])))
    write_csv(summary_dir / "H指数计算明细.csv", list(h_detail_rows[0].keys()), h_detail_rows)
    (OUTPUT / "README_方法说明.md").write_text(
        "# H-core Gephi网络\n\n"
        "数据字段：两张结果表的`最终规范关键词`。同一文档内关键词先去重，再按两两组合构建无向共词边；Weight为共同出现文档数。\n\n"
        "H-core方法：对每个层级和阶段的全网络计算无权Degree的H指数H，保留OriginalDegree≥H的节点，并保留这些节点之间的全部诱导边。该方法是一次性H指数筛选，不是迭代k-core剥离。\n\n"
        "Gephi导入：直接打开`gexf`目录下的文件；节点大小可使用Frequency或CoreWeightedDegree，边宽使用Weight。\n",
        encoding="utf-8",
    )
    (OUTPUT / "manifest.json").write_text(json.dumps({"input": str(INPUT), "networks": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")

    archive = OUTPUT.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(OUTPUT.rglob("*")):
            if path.is_file():
                z.write(path, Path(OUTPUT.name) / path.relative_to(OUTPUT))
    print(json.dumps({"output": str(OUTPUT), "archive": str(archive), "networks": len(manifest), "summary": str(summary_dir / 'H-core网络统计.csv')}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
