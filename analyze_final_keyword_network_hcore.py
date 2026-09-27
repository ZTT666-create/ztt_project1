from __future__ import annotations

import csv
from collections import Counter
from itertools import combinations
from pathlib import Path

import openpyxl


INPUT = Path(r"D:\ztt-codex\codex-最新处理数据\policy_normalization_results_updated_已确认回写_摘要共同词已更新.xlsx")
OUT_DIR = Path(r"D:\ztt-codex\codex-最新处理数据\最终规范关键词_阶段网络统计_含H核心")
STAGES = [
    ("A", 1998, 2005),
    ("B", 2006, 2011),
    ("C", 2012, 2015),
    ("D", 2016, 2019),
    ("E", 2020, 2025),
]


def h_index(degrees: list[int]) -> int:
    h = 0
    for rank, degree in enumerate(sorted(degrees, reverse=True), start=1):
        if degree >= rank:
            h = rank
        else:
            break
    return h


def read_records(wb, sheet_name: str) -> list[dict[str, str]]:
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(v or "") for v in rows[0]]
    idx = {h: i for i, h in enumerate(headers)}
    out = []
    for row in rows[1:]:
        final = str(row[idx["最终规范关键词"]] or "")
        keywords = []
        seen = set()
        for term in final.split(";"):
            term = term.strip()
            if term and term not in seen:
                seen.add(term)
                keywords.append(term)
        out.append({
            "doc_id": str(row[idx["doc_id"]] or ""),
            "year": int(row[idx["year"]]),
            "keywords": keywords,
        })
    return out


def build(records: list[dict[str, str]]) -> dict[str, object]:
    node_frequency: Counter[str] = Counter()
    edge_weight: Counter[tuple[str, str]] = Counter()
    for record in records:
        terms = sorted(set(record["keywords"]))
        node_frequency.update(terms)
        edge_weight.update(combinations(terms, 2))

    neighbors = {term: set() for term in node_frequency}
    for (source, target), weight in edge_weight.items():
        neighbors[source].add(target)
        neighbors[target].add(source)
    degree = {term: len(values) for term, values in neighbors.items()}
    h = h_index(list(degree.values()))
    core_nodes = {term for term, value in degree.items() if value >= h}
    core_edges = {
        pair: weight for pair, weight in edge_weight.items()
        if pair[0] in core_nodes and pair[1] in core_nodes
    }
    return {
        "documents": len(records),
        "nodes": len(node_frequency),
        "edges": len(edge_weight),
        "edge_weight_sum": sum(edge_weight.values()),
        "h": h,
        "core_nodes": len(core_nodes),
        "core_edges": len(core_edges),
        "core_edge_weight_sum": sum(core_edges.values()),
        "node_retention": len(core_nodes) / len(node_frequency) if node_frequency else 0,
        "edge_retention": len(core_edges) / len(edge_weight) if edge_weight else 0,
        "weight_retention": sum(core_edges.values()) / sum(edge_weight.values()) if edge_weight else 0,
        "avg_degree": 2 * len(edge_weight) / len(node_frequency) if node_frequency else 0,
        "core_avg_degree": 2 * len(core_edges) / len(core_nodes) if core_nodes else 0,
        "node_frequency": node_frequency,
        "degree": degree,
    }


def main() -> None:
    wb = openpyxl.load_workbook(INPUT, read_only=True, data_only=True)
    all_rows = []
    for layer, sheet_name in (("科学", "论文规范结果"), ("政策", "政策规范结果")):
        records = read_records(wb, sheet_name)
        for stage, start, end in STAGES:
            stage_records = [r for r in records if start <= r["year"] <= end]
            result = build(stage_records)
            all_rows.append({
                "Layer": layer,
                "Stage": stage,
                "Years": f"{start}-{end}",
                "DocumentCount": result["documents"],
                "FullNodeCount": result["nodes"],
                "FullEdgeCount": result["edges"],
                "FullEdgeWeightSum": result["edge_weight_sum"],
                "HIndex": result["h"],
                "HCoreNodeCount": result["core_nodes"],
                "HCoreEdgeCount": result["core_edges"],
                "HCoreEdgeWeightSum": result["core_edge_weight_sum"],
                "NodeRetentionRate": result["node_retention"],
                "EdgeRetentionRate": result["edge_retention"],
                "EdgeWeightRetentionRate": result["weight_retention"],
                "FullAverageDegree": result["avg_degree"],
                "HCoreAverageDegree": result["core_avg_degree"],
            })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = list(all_rows[0].keys())
    with (OUT_DIR / "最终规范关键词_阶段全网络与H核心统计.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_rows)

    print("| 层级 | 阶段 | 年份 | 文档数 | 全网络节点 | 全网络边 | 全网络边权 | H值 | H-core节点 | H-core边 | H-core边权 | 节点保留率 | 边保留率 | 边权保留率 |")
    print("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in all_rows:
        print(
            f"| {r['Layer']} | {r['Stage']} | {r['Years']} | {r['DocumentCount']} | "
            f"{r['FullNodeCount']} | {r['FullEdgeCount']} | {r['FullEdgeWeightSum']} | {r['HIndex']} | "
            f"{r['HCoreNodeCount']} | {r['HCoreEdgeCount']} | {r['HCoreEdgeWeightSum']} | "
            f"{r['NodeRetentionRate']:.1%} | {r['EdgeRetentionRate']:.1%} | {r['EdgeWeightRetentionRate']:.1%} |"
        )
    print(f"\nCSV: {OUT_DIR / '最终规范关键词_阶段全网络与H核心统计.csv'}")


if __name__ == "__main__":
    main()
