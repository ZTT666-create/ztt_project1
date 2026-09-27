from __future__ import annotations

import csv
from pathlib import Path


BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "最终规范关键词_Leiden分辨率比较_1998-2025"

STAGES = ["A", "B", "C", "D", "E"]
YEARS = {
    "A": "1998-2005",
    "B": "2006-2011",
    "C": "2012-2015",
    "D": "2016-2019",
    "E": "2020-2025",
}

# Short labels are based on the dominant keywords in each community.
# They are labels for communities, not replacements for the original keywords.
NAMES: dict[tuple[str, str, str], str] = {
    # Science
    ("科学", "A", "1"): "创业投融资",
    ("科学", "A", "2"): "中小企信用",
    ("科学", "A", "3"): "科技信贷",
    ("科学", "B", "1"): "创投资本",
    ("科学", "B", "2"): "科技保险风控",
    ("科学", "B", "3"): "知识产权融资",
    ("科学", "B", "4"): "科技金融体系",
    ("科学", "B", "5"): "创投基金支持",
    ("科学", "B", "6"): "融资租赁制度",
    ("科学", "B", "7"): "船舶租赁创新",
    ("科学", "C", "1"): "科技金融体系",
    ("科学", "C", "2"): "多元科技融资",
    ("科学", "C", "3"): "中小企知识产权融资",
    ("科学", "C", "4"): "高企创投融资",
    ("科学", "C", "5"): "产业特色金融",
    ("科学", "C", "6"): "科技金融服务",
    ("科学", "C", "7"): "区域创新环境",
    ("科学", "C", "8"): "融资服务模式",
    ("科学", "C", "9"): "成果证券化",
    ("科学", "D", "1"): "科技金融主干",
    ("科学", "D", "2"): "知识产权融资",
    ("科学", "D", "3"): "科技保险风控",
    ("科学", "D", "4"): "科技金融效率",
    ("科学", "D", "5"): "数字金融监管",
    ("科学", "D", "6"): "科创板监管",
    ("科学", "D", "7"): "融资租赁税务",
    ("科学", "D", "8"): "农业科技金融",
    ("科学", "D", "9"): "高新产业配置",
    ("科学", "D", "10"): "创投项目决策",
    ("科学", "D", "11"): "数据匹配评价",
    ("科学", "D", "12"): "创新生态治理",
    ("科学", "D", "13"): "投资者权益监管",
    ("科学", "D", "14"): "技术转移支持",
    ("科学", "D", "15"): "金融服务创新",
    ("科学", "E", "1"): "科技金融发展",
    ("科学", "E", "2"): "科技金融政策",
    ("科学", "E", "3"): "金融科技监管",
    ("科学", "E", "4"): "知识产权融资",
    ("科学", "E", "5"): "知识产权质押风控",
    ("科学", "E", "6"): "专利融资证券化",
    ("科学", "E", "7"): "融资租赁司法",
    ("科学", "E", "8"): "绿色数字金融",
    ("科学", "E", "9"): "数字供应链金融",
    ("科学", "E", "10"): "科技金融耦合",
    ("科学", "E", "11"): "科技创新主体",
    # Policy
    ("政策", "A", "1"): "科技金融支持",
    ("政策", "A", "2"): "税收债券融资",
    ("政策", "A", "3"): "融资担保风险",
    ("政策", "A", "4"): "技术改造贴息",
    ("政策", "A", "5"): "中小企银行信贷",
    ("政策", "B", "1"): "科技金融综合支持",
    ("政策", "B", "2"): "高企创投保险",
    ("政策", "B", "3"): "外贸科技融资",
    ("政策", "B", "4"): "银行科技治理",
    ("政策", "B", "5"): "金融业务体系",
    ("政策", "B", "6"): "产业研发资金",
    ("政策", "C", "1"): "科技金融政策工具",
    ("政策", "C", "2"): "多元融资工具",
    ("政策", "C", "3"): "质押供应链融资",
    ("政策", "C", "4"): "信息科技风控",
    ("政策", "C", "5"): "创新服务支持",
    ("政策", "C", "6"): "境外科技融资",
    ("政策", "C", "7"): "知识产权交易",
    ("政策", "C", "8"): "光伏金融试点",
    ("政策", "D", "1"): "科技金融综合支持",
    ("政策", "D", "2"): "科创板直接融资",
    ("政策", "D", "3"): "专利保险风控",
    ("政策", "D", "4"): "知识产权运营",
    ("政策", "D", "5"): "海洋专利融资",
    ("政策", "E", "1"): "科技金融综合支持",
    ("政策", "E", "2"): "融资租赁创新",
    ("政策", "E", "3"): "知识产权评估服务",
    ("政策", "E", "4"): "创新生态支撑",
    ("政策", "E", "5"): "科技企业上市",
    ("政策", "E", "6"): "人工智能金融风控",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    nodes = read_csv(OUT_DIR / "桑基图_社区节点_resolution0.3.csv")
    flows = read_csv(OUT_DIR / "桑基图_社区流动_resolution0.3.csv")
    details = read_csv(OUT_DIR / "桑基图_社区流动关键词明细_resolution0.3.csv")

    expected = {(r["Layer"], r["Stage"], r["Community"]) for r in nodes}
    missing = sorted(expected - set(NAMES))
    extra = sorted(set(NAMES) - expected)
    if missing or extra:
        raise RuntimeError(f"Community name mapping mismatch. missing={missing}, extra={extra}")

    def name(layer: str, stage: str, community: str) -> str:
        return NAMES[(layer, stage, community)]

    named_nodes = []
    for r in nodes:
        community_name = name(r["Layer"], r["Stage"], r["Community"])
        named_nodes.append(
            {
                **r,
                "CommunityName": community_name,
                "NodeLabel": f"{r['Stage']}{r['Community']} {community_name}",
            }
        )

    named_flows = []
    for r in flows:
        source_name = name(r["Layer"], r["FromStage"], r["FromCommunity"])
        target_name = name(r["Layer"], r["ToStage"], r["ToCommunity"])
        named_flows.append(
            {
                **r,
                "SourceName": source_name,
                "TargetName": target_name,
                "SourceLabel": f"{r['FromStage']}{r['FromCommunity']} {source_name}",
                "TargetLabel": f"{r['ToStage']}{r['ToCommunity']} {target_name}",
            }
        )

    named_details = []
    for r in details:
        source_name = name(r["Layer"], r["FromStage"], r["FromCommunity"])
        target_name = name(r["Layer"], r["ToStage"], r["ToCommunity"])
        named_details.append(
            {
                **r,
                "FromCommunityName": source_name,
                "ToCommunityName": target_name,
            }
        )

    mapping_rows = []
    for r in nodes:
        mapping_rows.append(
            {
                "Layer": r["Layer"],
                "Stage": r["Stage"],
                "Years": r["Years"],
                "Community": r["Community"],
                "NodeId": r["NodeId"],
                "CommunityName": name(r["Layer"], r["Stage"], r["Community"]),
                "NodeLabel": f"{r['Stage']}{r['Community']} {name(r['Layer'], r['Stage'], r['Community'])}",
                "NodeCount": r["NodeCount"],
                "TopKeywords": r["TopKeywords"],
            }
        )

    write_csv(
        OUT_DIR / "桑基图_社区节点_resolution0.3_已命名.csv",
        named_nodes,
        ["Layer", "Stage", "Years", "NodeId", "Community", "NodeCount", "TopKeywords", "CommunityName", "NodeLabel"],
    )
    write_csv(
        OUT_DIR / "桑基图_社区流动_resolution0.3_已命名.csv",
        named_flows,
        [
            "Layer", "FromStage", "FromYears", "FromCommunity", "Source", "SourceName", "SourceLabel",
            "ToStage", "ToYears", "ToCommunity", "Target", "TargetName", "TargetLabel", "Value",
            "SharedKeywordCount", "SharedKeywords", "FromCommunityNodeCount", "ToCommunityNodeCount",
            "FromCommunityCoverage", "ToCommunityCoverage",
        ],
    )
    write_csv(
        OUT_DIR / "桑基图_社区流动关键词明细_resolution0.3_已命名.csv",
        named_details,
        [
            "Layer", "FromStage", "FromYears", "FromCommunity", "FromCommunityName", "FromNodeId",
            "ToStage", "ToYears", "ToCommunity", "ToCommunityName", "ToNodeId", "Keyword",
        ],
    )
    write_csv(
        OUT_DIR / "桑基图_社区命名对照表_resolution0.3.csv",
        mapping_rows,
        ["Layer", "Stage", "Years", "Community", "NodeId", "CommunityName", "NodeLabel", "NodeCount", "TopKeywords"],
    )
    print(f"NAMED_NODES|{len(named_nodes)}")
    print(f"NAMED_FLOWS|{len(named_flows)}")
    print(f"NAMED_DETAILS|{len(named_details)}")


if __name__ == "__main__":
    main()
