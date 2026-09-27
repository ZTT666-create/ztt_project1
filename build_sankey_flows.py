from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "最终规范关键词_Leiden分辨率比较_1998-2025"
ASSIGNMENT = OUT_DIR / "Leiden_resolution0.3_节点社区分配_最终关键词.csv"
COMMUNITY_SUMMARY = OUT_DIR / "Leiden_resolution0.3_社区汇总_最终关键词.csv"

STAGES = {
    "A": "1998-2005",
    "B": "2006-2011",
    "C": "2012-2015",
    "D": "2016-2019",
    "E": "2020-2025",
}
STAGE_ORDER = ["A", "B", "C", "D", "E"]


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def node_id(layer: str, stage: str, community: str) -> str:
    return f"{layer}_{stage}_C{community}"


def main() -> None:
    with ASSIGNMENT.open("r", encoding="utf-8-sig", newline="") as f:
        assignment_rows = list(csv.DictReader(f))
    with COMMUNITY_SUMMARY.open("r", encoding="utf-8-sig", newline="") as f:
        summary_rows = list(csv.DictReader(f))

    # layer -> stage -> keyword -> assignment record
    records: dict[str, dict[str, dict[str, dict[str, str]]]] = defaultdict(lambda: defaultdict(dict))
    for row in assignment_rows:
        records[row["Layer"]][row["Stage"]][row["Label"]] = row

    summary_by_node: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in summary_rows:
        summary_by_node[(row["Layer"], row["Stage"], row["Community"])] = row

    node_rows: list[dict[str, object]] = []
    for layer in ["科学", "政策"]:
        for stage in STAGE_ORDER:
            communities = sorted(
                {r["Community"] for r in records[layer][stage].values()},
                key=lambda x: int(x),
            )
            for community in communities:
                s = summary_by_node.get((layer, stage, community), {})
                node_rows.append(
                    {
                        "Layer": layer,
                        "Stage": stage,
                        "Years": STAGES[stage],
                        "NodeId": node_id(layer, stage, community),
                        "Community": community,
                        "NodeCount": s.get("NodeCount", len([1 for r in records[layer][stage].values() if r["Community"] == community])),
                        "TopKeywords": s.get("TopKeywords", ""),
                    }
                )

    detail_rows: list[dict[str, object]] = []
    flow_rows: list[dict[str, object]] = []
    for layer in ["科学", "政策"]:
        for left_stage, right_stage in zip(STAGE_ORDER, STAGE_ORDER[1:]):
            left = records[layer][left_stage]
            right = records[layer][right_stage]
            shared = sorted(set(left) & set(right))
            grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
            for keyword in shared:
                source_c = left[keyword]["Community"]
                target_c = right[keyword]["Community"]
                grouped[(source_c, target_c)].append(keyword)
                detail_rows.append(
                    {
                        "Layer": layer,
                        "FromStage": left_stage,
                        "FromYears": STAGES[left_stage],
                        "FromCommunity": source_c,
                        "FromNodeId": node_id(layer, left_stage, source_c),
                        "ToStage": right_stage,
                        "ToYears": STAGES[right_stage],
                        "ToCommunity": target_c,
                        "ToNodeId": node_id(layer, right_stage, target_c),
                        "Keyword": keyword,
                    }
                )

            for (source_c, target_c), keywords in sorted(
                grouped.items(), key=lambda item: (int(item[0][0]), int(item[0][1]))
            ):
                source_node = node_id(layer, left_stage, source_c)
                target_node = node_id(layer, right_stage, target_c)
                source_size = len([1 for r in left.values() if r["Community"] == source_c])
                target_size = len([1 for r in right.values() if r["Community"] == target_c])
                value = len(keywords)
                flow_rows.append(
                    {
                        "Layer": layer,
                        "FromStage": left_stage,
                        "FromYears": STAGES[left_stage],
                        "FromCommunity": source_c,
                        "Source": source_node,
                        "ToStage": right_stage,
                        "ToYears": STAGES[right_stage],
                        "ToCommunity": target_c,
                        "Target": target_node,
                        "Value": value,
                        "SharedKeywordCount": value,
                        "SharedKeywords": ";".join(keywords),
                        "FromCommunityNodeCount": source_size,
                        "ToCommunityNodeCount": target_size,
                        "FromCommunityCoverage": round(value / source_size, 6) if source_size else 0,
                        "ToCommunityCoverage": round(value / target_size, 6) if target_size else 0,
                    }
                )

    node_fields = ["Layer", "Stage", "Years", "NodeId", "Community", "NodeCount", "TopKeywords"]
    flow_fields = [
        "Layer", "FromStage", "FromYears", "FromCommunity", "Source",
        "ToStage", "ToYears", "ToCommunity", "Target", "Value",
        "SharedKeywordCount", "SharedKeywords", "FromCommunityNodeCount",
        "ToCommunityNodeCount", "FromCommunityCoverage", "ToCommunityCoverage",
    ]
    detail_fields = [
        "Layer", "FromStage", "FromYears", "FromCommunity", "FromNodeId",
        "ToStage", "ToYears", "ToCommunity", "ToNodeId", "Keyword",
    ]
    write_csv(OUT_DIR / "桑基图_社区节点_resolution0.3.csv", node_rows, node_fields)
    write_csv(OUT_DIR / "桑基图_社区流动_resolution0.3.csv", flow_rows, flow_fields)
    write_csv(OUT_DIR / "桑基图_社区流动关键词明细_resolution0.3.csv", detail_rows, detail_fields)

    print(f"NODES|{len(node_rows)}")
    print(f"FLOWS|{len(flow_rows)}")
    print(f"DETAILS|{len(detail_rows)}")
    for layer in ["科学", "政策"]:
        for left_stage, right_stage in zip(STAGE_ORDER, STAGE_ORDER[1:]):
            rows = [
                r for r in flow_rows
                if r["Layer"] == layer and r["FromStage"] == left_stage and r["ToStage"] == right_stage
            ]
            print(f"{layer}|{left_stage}->{right_stage}|flows={len(rows)}|shared_keywords={sum(int(r['Value']) for r in rows)}")


if __name__ == "__main__":
    main()
