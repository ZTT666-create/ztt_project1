from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(
    r"C:\Users\张甜甜的Redmi\.codex\visualizations\2026\09\20\01a0bc3a-e620-7511-b6b4-b009915a0768"
)
REVIEW_DIR = ROOT / "频次1关键词审核_1998-2025"
OUT_DIR = ROOT / "规范关键词_保守处理_1998-2025"
INPUT = REVIEW_DIR / "Frequency1关键词启发式分类.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.1f}%" if d else "0.0%"


def main() -> None:
    rows = read_csv(INPUT)
    processed: list[dict[str, str]] = []
    for r in rows:
        degree = int(float(r["Degree"]))
        category = r.get("HeuristicCategory", "")
        long_phrase = r.get("LongPhrase_12plus") == "是"
        has_latin_digit = r.get("HasLatin") == "是" or r.get("HasDigit") == "是"
        has_method = "方法或机制词" in category
        has_context = "产业或场景词" in category
        has_generic = "通用学术词" in category

        if degree < 2:
            decision = "排除主分析网络（结构性噪声）"
            review_status = "已排除，不进入主网络"
            review_reason = "Degree<2"
        else:
            decision = "保留主分析网络"
            reasons = []
            if long_phrase:
                reasons.append("过长短语")
            if has_latin_digit:
                reasons.append("含英文或数字")
            if has_method:
                reasons.append("方法或机制词")
            if has_context:
                reasons.append("产业或场景词")
            if has_generic:
                reasons.append("通用学术词")
            if reasons:
                review_status = "保留，建议人工复核"
                review_reason = "；".join(reasons)
            else:
                review_status = "保留，无需优先复核"
                review_reason = "专业词或政策工具词，且Degree≥2"

        out = dict(r)
        out.update(
            {
                "ProcessingDecision": decision,
                "ReviewStatus": review_status,
                "ReviewReason": review_reason,
                "AutoMerge": "否",
                "AutoDelete": "是" if degree < 2 else "否",
            }
        )
        processed.append(out)

    kept = [r for r in processed if r["ProcessingDecision"] == "保留主分析网络"]
    excluded = [r for r in processed if r["ProcessingDecision"] != "保留主分析网络"]
    review = [r for r in kept if r["ReviewStatus"] == "保留，建议人工复核"]
    no_priority = [r for r in kept if r["ReviewStatus"] == "保留，无需优先复核"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_DIR / "规范关键词_保守处理结果.csv", processed)
    write_csv(OUT_DIR / "主分析保留_频次1.csv", kept)
    write_csv(OUT_DIR / "结构性噪声_频次1_排除.csv", excluded)
    write_csv(OUT_DIR / "待人工审核_频次1.csv", review)
    write_csv(OUT_DIR / "无需优先审核_频次1.csv", no_priority)

    summary_rows: list[dict[str, str]] = []
    for layer in ("科学", "政策"):
        rr = [r for r in processed if r["Layer"] == layer]
        kk = [r for r in rr if r in kept]
        ee = [r for r in rr if r in excluded]
        rv = [r for r in rr if r in review]
        summary_rows.append(
            {
                "Layer": layer,
                "Frequency1总数": str(len(rr)),
                "主分析保留数": str(len(kk)),
                "主分析保留占比": pct(len(kk), len(rr)),
                "Degree<2排除数": str(len(ee)),
                "排除占比": pct(len(ee), len(rr)),
                "保留但建议人工复核数": str(len(rv)),
                "保留且无需优先复核数": str(len(kk) - len(rv)),
            }
        )
    summary_rows.append(
        {
            "Layer": "合计",
            "Frequency1总数": str(len(processed)),
            "主分析保留数": str(len(kept)),
            "主分析保留占比": pct(len(kept), len(processed)),
            "Degree<2排除数": str(len(excluded)),
            "排除占比": pct(len(excluded), len(processed)),
            "保留但建议人工复核数": str(len(review)),
            "保留且无需优先复核数": str(len(no_priority)),
        }
    )
    write_csv(OUT_DIR / "处理汇总.csv", summary_rows)

    by_reason = Counter(r["ReviewReason"] for r in review)
    by_stage = defaultdict(lambda: {"all": 0, "keep": 0, "exclude": 0})
    for r in processed:
        key = f"{r['Layer']}-{r['Stage']}"
        by_stage[key]["all"] += 1
        if r in kept:
            by_stage[key]["keep"] += 1
        else:
            by_stage[key]["exclude"] += 1

    lines = [
        "# 规范关键词保守处理说明",
        "",
        "## 处理口径",
        "",
        "1. 仅将 `Degree<2` 的频次为1关键词判定为结构性噪声，并排除出主分析网络。",
        "2. `Frequency=1` 且 `Degree≥2` 的关键词全部保留，不因低频自动删除。",
        "3. 方法词、产业/场景词、通用学术词、过长短语和含英文/数字词只做审核标记，不自动删除。",
        "4. 不自动合并同义词或近义变体；如需合并，应回到规范化词典逐项确认。",
        "5. 本次处理针对频次为1词；主分析的全网络规则仍为 `Frequency≥1 + Degree≥2`。",
        "",
        "## 处理结果",
        "",
        f"- 频次为1关键词总数：{len(processed)}",
        f"- 主分析保留：{len(kept)}（{pct(len(kept), len(processed))}）",
        f"- 结构性噪声排除：{len(excluded)}（{pct(len(excluded), len(processed))}）",
        f"- 保留但建议人工复核：{len(review)}",
        f"- 保留且无需优先审核：{len(no_priority)}",
        "",
        "| 层级 | 频次1总数 | 主分析保留 | 排除(Degree<2) | 保留但建议复核 |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in summary_rows:
        lines.append(
            f"| {r['Layer']} | {r['Frequency1总数']} | {r['主分析保留数']} "
            f"({r['主分析保留占比']}) | {r['Degree<2排除数']} ({r['排除占比']}) | "
            f"{r['保留但建议人工复核数']} |"
        )

    lines += [
        "",
        "## 复核清单的含义",
        "",
        "`待人工审核_频次1.csv` 不是待删除清单，而是建议优先检查的清单。重点检查：",
        "",
        "- 是否为同义词、缩写、单复数或词形变体；",
        "- 是否为过于具体的机构、区域、项目或政策名称；",
        "- 方法词和场景词是否需要在主题命名时降权，而不是从网络删除；",
        "- 是否存在把一个完整政策工具短语拆成多个词的问题。",
        "",
        "## 各阶段处理数量",
        "",
        "| 层级-阶段 | 频次1总数 | 保留 | 排除 |",
        "|---|---:|---:|---:|",
    ]
    for key in sorted(by_stage):
        d = by_stage[key]
        lines.append(f"| {key} | {d['all']} | {d['keep']} | {d['exclude']} |")

    lines += [
        "",
        "## 结论",
        "",
        "当前数据不支持把频次为1整体判定为抽词质量差。科学和政策频次为1词中，绝大多数仍有至少2条共词连接；因此本次采用保守处理，保留其长尾信息，只剔除10个Degree<2的结构性噪声词。后续若需要进一步减少桑基图节点，应优先在社区命名或可视化层面做合并，而不是直接删除原始规范关键词。",
        "",
        "启发式复核原因统计（允许一词多类）：",
    ]
    for reason, count in by_reason.most_common():
        lines.append(f"- {reason}：{count}")

    (OUT_DIR / "处理说明.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"out_dir={OUT_DIR}")
    print(f"total={len(processed)} keep={len(kept)} excluded={len(excluded)} review={len(review)}")
    for r in summary_rows:
        print(r)


if __name__ == "__main__":
    main()
