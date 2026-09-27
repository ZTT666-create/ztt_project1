from __future__ import annotations

import csv
import statistics
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import openpyxl


INPUT = Path(r"D:\ztt-codex\codex-最新处理数据\policy_normalization_results_updated_已确认回写_摘要共同词已更新.xlsx")
OUT = Path(r"D:\ztt-codex\codex-最新处理数据\最终规范关键词_Leiden分辨率比较_1998-2025")
DEPS = Path(r"C:\Users\张甜甜的Redmi\.codex\visualizations\2026\09\19\01a0bbca-bb20-7e92-abfe-ccdd5603256e\_deps\leiden")
OLD_DETAIL = Path(r"C:\Users\张甜甜的Redmi\.codex\visualizations\2026\09\20\01a0bc3a-e620-7511-b6b4-b009915a0768\Leiden_resolution比较\Leiden_resolution比较明细.csv")
LAYERS = [("科学", "论文规范结果"), ("政策", "政策规范结果")]
STAGES = [("A", 1998, 2005), ("B", 2006, 2011), ("C", 2012, 2015), ("D", 2016, 2019), ("E", 2020, 2025)]
RESOLUTIONS = [0.2, 0.3, 0.4, 0.5]
SEEDS = 100


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def ari(a: list[int], b: list[int]) -> float:
    n = len(a)
    if n < 2:
        return 1.0

    def c2(x: int) -> float:
        return x * (x - 1) / 2

    ab = Counter(zip(a, b))
    ca = Counter(a)
    cb = Counter(b)
    total = c2(n)
    cells = sum(c2(x) for x in ab.values())
    sa = sum(c2(x) for x in ca.values())
    sb = sum(c2(x) for x in cb.values())
    expected = sa * sb / total if total else 0.0
    maximum = (sa + sb) / 2
    denominator = maximum - expected
    return 1.0 if abs(denominator) < 1e-15 else (cells - expected) / denominator


def read_records(wb, sheet_name: str) -> list[dict]:
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(x or "") for x in rows[0]]
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
        out.append({"year": int(row[idx["year"]]), "keywords": terms})
    return out


def build_graph(records: list[dict]):
    node_frequency = Counter()
    edge_weight = Counter()
    for record in records:
        terms = sorted(set(record["keywords"]))
        node_frequency.update(terms)
        edge_weight.update(combinations(terms, 2))
    neighbors = {term: set() for term in node_frequency}
    for (source, target) in edge_weight:
        neighbors[source].add(target)
        neighbors[target].add(source)
    degree = {term: len(neighbors[term]) for term in node_frequency}
    kept = sorted([term for term in node_frequency if degree[term] >= 2])
    kept_set = set(kept)
    edges = [(source, target, weight) for (source, target), weight in edge_weight.items() if source in kept_set and target in kept_set]
    return kept, edges, node_frequency, degree


def run_one(graph_module, leiden_module, labels, edges, resolution):
    index = {label: i for i, label in enumerate(labels)}
    graph_edges = [(index[s], index[t]) for s, t, _ in edges]
    weights = [float(w) for _, _, w in edges]
    graph = graph_module.Graph(n=len(labels), edges=graph_edges, directed=False)
    graph.es["weight"] = weights
    runs = []
    for seed in range(SEEDS):
        partition = leiden_module.find_partition(
            graph,
            leiden_module.RBConfigurationVertexPartition,
            weights=weights,
            resolution_parameter=resolution,
            n_iterations=-1,
            seed=seed,
        )
        membership = list(partition.membership)
        modularity = float(graph.modularity(membership, weights=weights))
        runs.append((modularity, seed, membership))
    runs.sort(key=lambda x: (-x[0], x[1]))
    best_modularity, best_seed, best_membership = runs[0]
    sizes = Counter(best_membership)
    size_values = sorted(sizes.values())
    mean_ari = statistics.mean(ari(best_membership, membership) for _, _, membership in runs)
    communities = defaultdict(list)
    for label, community in zip(labels, best_membership):
        communities[community].append(label)
    return {
        "CommunityCount": len(sizes),
        "Modularity": round(best_modularity, 6),
        "MeanARI": round(mean_ari, 6),
        "MinCommunitySize": min(size_values),
        "MedianCommunitySize": statistics.median(size_values),
        "MaxCommunitySize": max(size_values),
        "SmallCommunityCount_lt10": sum(x < 10 for x in size_values),
        "SmallCommunityShare_lt10": round(sum(x < 10 for x in size_values) / len(size_values), 6),
        "LargestCommunityShare": round(max(size_values) / len(labels), 6),
        "BestSeed": best_seed,
        "membership": best_membership,
        "communities": communities,
    }


def main() -> None:
    sys.path.insert(0, str(DEPS))
    import igraph as ig
    import leidenalg as la

    wb = openpyxl.load_workbook(INPUT, read_only=True, data_only=True)
    network_data = {}
    for layer, sheet_name in LAYERS:
        records = read_records(wb, sheet_name)
        for stage, start, end in STAGES:
            stage_records = [r for r in records if start <= r["year"] <= end]
            labels, edges, node_frequency, degree = build_graph(stage_records)
            network_data[(layer, stage)] = {
                "years": f"{start}-{end}",
                "documents": len(stage_records),
                "labels": labels,
                "edges": edges,
                "node_frequency": node_frequency,
                "degree": degree,
            }

    detail_rows = []
    community_rows = []
    assignment_rows = []
    for resolution in RESOLUTIONS:
        for layer, _ in LAYERS:
            for stage, _, _ in STAGES:
                data = network_data[(layer, stage)]
                result = run_one(ig, la, data["labels"], data["edges"], resolution)
                row = {
                    "Resolution": resolution,
                    "Layer": layer,
                    "Stage": stage,
                    "Years": data["years"],
                    "DocumentCount": data["documents"],
                    "NodeCount": len(data["labels"]),
                    "EdgeCount": len(data["edges"]),
                    "CommunityCount": result["CommunityCount"],
                    "SmallCommunityCount_lt10": result["SmallCommunityCount_lt10"],
                    "SmallCommunityShare_lt10": result["SmallCommunityShare_lt10"],
                    "MinCommunitySize": result["MinCommunitySize"],
                    "MedianCommunitySize": result["MedianCommunitySize"],
                    "MaxCommunitySize": result["MaxCommunitySize"],
                    "LargestCommunityShare": result["LargestCommunityShare"],
                    "Modularity": result["Modularity"],
                    "MeanARI": result["MeanARI"],
                    "BestSeed": result["BestSeed"],
                }
                detail_rows.append(row)
                if abs(resolution - 0.3) < 1e-9:
                    for community, labels in sorted(result["communities"].items(), key=lambda x: (-len(x[1]), min(x[1]))):
                        top = sorted(labels, key=lambda x: (-data["node_frequency"][x], -data["degree"][x], x))[:12]
                        community_rows.append({
                            "Layer": layer,
                            "Stage": stage,
                            "Years": data["years"],
                            "Community": community + 1,
                            "NodeCount": len(labels),
                            "TopKeywords": ";".join(top),
                        })
                    for label, community in zip(data["labels"], result["membership"]):
                        assignment_rows.append({
                            "Layer": layer,
                            "Stage": stage,
                            "Years": data["years"],
                            "Label": label,
                            "Frequency": data["node_frequency"][label],
                            "Degree": data["degree"][label],
                            "Community": community + 1,
                            "Resolution": resolution,
                        })

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "Leiden_resolution比较明细_最终关键词.csv", detail_rows)
    write_csv(OUT / "Leiden_resolution0.3_社区汇总_最终关键词.csv", community_rows)
    write_csv(OUT / "Leiden_resolution0.3_节点社区分配_最终关键词.csv", assignment_rows)

    summary_rows = []
    for resolution in RESOLUTIONS:
        for layer, _ in LAYERS:
            rr = [r for r in detail_rows if r["Resolution"] == resolution and r["Layer"] == layer]
            counts = [int(r["CommunityCount"]) for r in rr]
            summary_rows.append({
                "Resolution": resolution,
                "Layer": layer,
                "A_to_E_CommunityCounts": "→".join(map(str, counts)),
                "MeanCommunityCount": round(statistics.mean(counts), 4),
                "MaxCommunityCount": max(counts),
                "StagesOver12Communities": sum(x > 12 for x in counts),
                "StagesOver15Communities": sum(x > 15 for x in counts),
                "MeanModularity": round(statistics.mean(float(r["Modularity"]) for r in rr), 6),
                "MeanARI": round(statistics.mean(float(r["MeanARI"]) for r in rr), 6),
                "MeanSmallCommunityShare_lt10": round(statistics.mean(float(r["SmallCommunityShare_lt10"]) for r in rr), 6),
                "MeanLargestCommunityShare": round(statistics.mean(float(r["LargestCommunityShare"]) for r in rr), 6),
            })
    write_csv(OUT / "Leiden_resolution比较汇总_最终关键词.csv", summary_rows)

    old = {(float(r["Resolution"]), r["Layer"], r["Stage"]): r for r in read_csv(OLD_DETAIL)}
    compare_rows = []
    for r in detail_rows:
        key = (float(r["Resolution"]), r["Layer"], r["Stage"])
        if key in old:
            o = old[key]
            compare_rows.append({
                "Resolution": r["Resolution"],
                "Layer": r["Layer"],
                "Stage": r["Stage"],
                "NewNodeCount": r["NodeCount"],
                "OldNodeCount": o["NodeCount"],
                "NewEdgeCount": r["EdgeCount"],
                "OldEdgeCount": o["EdgeCount"],
                "NewCommunityCount": r["CommunityCount"],
                "OldCommunityCount": o["CommunityCount"],
                "CommunityCountChange": int(r["CommunityCount"]) - int(o["CommunityCount"]),
                "NewMeanARI": r["MeanARI"],
                "OldMeanARI": o["MeanARI_toBest"],
                "NewSmallCommunityShare_lt10": r["SmallCommunityShare_lt10"],
                "OldSmallCommunityShare_lt10": o["SmallCommunityShare"],
            })
    write_csv(OUT / "与原resolution比较结果.csv", compare_rows)

    print("Resolution|Layer|A→E社群数|平均社群数|最大社群数|平均模块度|平均ARI|平均小社群占比|平均最大社群占比")
    for r in summary_rows:
        print(
            f"{r['Resolution']}|{r['Layer']}|{r['A_to_E_CommunityCounts']}|{r['MeanCommunityCount']}|"
            f"{r['MaxCommunityCount']}|{r['MeanModularity']}|{r['MeanARI']}|"
            f"{r['MeanSmallCommunityShare_lt10']}|{r['MeanLargestCommunityShare']}"
        )
    print(f"OUTPUT|{OUT}")


if __name__ == "__main__":
    main()
