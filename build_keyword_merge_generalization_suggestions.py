from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(
    r"C:\Users\张甜甜的Redmi\.codex\visualizations\2026\09\20\01a0bc3a-e620-7511-b6b4-b009915a0768"
)
INPUT = ROOT / "全网络_Leiden_Frequency1_Degree2_resolution0.3_1998-2025" / "tables" / "全网络Leiden节点分配_Frequency1_Degree2.csv"
OUT = ROOT / "关键词合并与概括建议_1998-2025"


# These are reviewable suggestions, not automatic changes to the source data.
# The first section contains terms that are close enough to merge at the
# vocabulary level. The second section contains terms that should be shortened
# or generalized because they encode a region, organization, subtype, policy
# program, model detail, or other narrow context.
SYNONYM_MAP: dict[str, tuple[str, str, str]] = {
    "创投": ("创业投资", "高", "缩写与全称"),
    "风险投资": ("创业投资", "中", "风险投资与创业投资通常作为同类概念使用，需确认研究口径"),
    "创业风险投资": ("创业投资", "中", "复合表述归并到创业投资"),
    "风险资本": ("创业投资", "中", "资本表述与创业投资概念接近，需确认口径"),
    "高科技产业": ("高技术产业", "中", "高科技与高技术的词形变体"),
    "高科技企业": ("高新技术企业", "中", "高科技企业与高新技术企业的词形变体"),
    "高新科技企业": ("高新技术企业", "中", "词序变体"),
    "高技术企业": ("高新技术企业", "中", "高技术企业与高新技术企业的近义表述"),
    "中小科技企业": ("科技型中小企业", "中", "词序变体"),
    "科技中小企业": ("科技型中小企业", "中", "词形变体"),
    "创投基金": ("创业投资基金", "高", "缩写与全称"),
    "天使基金": ("天使投资基金", "高", "简称与全称"),
    "私募股权基金": ("私募股权投资基金", "中", "省略投资二字的变体"),
    "股权众筹": ("股权众筹融资", "中", "股权众筹与股权众筹融资的近义表述"),
    "互联网股权众筹": ("股权众筹融资", "中", "场景限定词可归并"),
    "互联网股权众筹融资": ("股权众筹融资", "中", "场景限定词可归并"),
    "科技与金融结合": ("科技金融", "中", "概念表达变体，需确认是否与科技金融同口径"),
    "科技金融结合": ("科技金融", "中", "概念表达变体"),
    "科技成果转移转化": ("科技成果转化", "高", "转移转化与成果转化的常用变体"),
    "知识产权权利质押": ("知识产权质押", "高", "权利二字属于限定性重复表述"),
    "知识产权质押贷款": ("知识产权质押融资", "中", "贷款属于质押融资的一种实现方式"),
    "融资性保证保险": ("融资保证保险", "高", "词序变体"),
    "融资性信用保险": ("信用保险", "中", "融资性限定词可归并，需确认研究口径"),
    "金融创新体系": ("金融创新", "中", "体系后缀可在词汇层面归并"),
    "金融服务机构": ("金融机构", "中", "服务机构与金融机构有交叉，需人工确认"),
    "科技金融体制": ("科技金融制度", "中", "体制与制度的近义表述"),
}


GENERALIZE_MAP: dict[str, tuple[str, str, str]] = {
    # Subtypes and detailed forms
    "科技保险(财产险)": ("科技保险", "高", "保险分险种，主题网络保留上位概念"),
    "科技保险(人身险)": ("科技保险", "高", "保险分险种，主题网络保留上位概念"),
    "知识产权被侵权保险": ("知识产权保险", "高", "具体责任类型概括为知识产权保险"),
    "知识产权风险类保险": ("知识产权保险", "高", "具体风险类型概括为知识产权保险"),
    "知识产权相关保险产品": ("知识产权保险", "高", "产品表述概括为知识产权保险"),
    "知识产权海外侵权责任险": ("知识产权保险", "中", "地域和责任类型过于具体"),
    "贷款保证保险": ("融资保证保险", "中", "具体贷款场景概括为融资保证保险"),
    "小额贷款保证保险": ("融资保证保险", "高", "贷款规模限定词过细"),
    "小微企业贷款保证保险": ("融资保证保险", "高", "企业类型和产品场景限定词过细"),
    "短期出口信用保险": ("出口信用保险", "高", "期限限定词过细"),
    "中长期出口信用保险": ("出口信用保险", "高", "期限限定词过细"),
    "新能源汽车研发保险": ("科技保险", "中", "行业和研发场景过细"),
    "首台(套)重大技术装备保险": ("科技保险", "中", "产品类别和政策场景过细"),
    "首台（套）重大技术装备保险": ("科技保险", "中", "产品类别和政策场景过细"),
    "新材料首批次应用保险补偿机制": ("科技保险", "中", "行业、批次和补偿机制过细"),
    # Pilot, region, center, platform and organization details
    "科技保险试点城市": ("科技保险试点", "高", "城市限定词过细"),
    "科技金融试点城市": ("科技金融试点", "高", "城市限定词过细"),
    "科技金融试点政策": ("科技金融政策", "中", "政策载体限定词过细"),
    "科技与金融结合试点": ("科技与金融结合", "高", "试点限定词过细"),
    "科技金融改革试点": ("科技金融改革", "高", "试点限定词过细"),
    "科技保险创新试点": ("科技保险创新", "高", "试点限定词过细"),
    "私募股权投资基金跨境投资试点": ("私募股权投资基金", "高", "跨境和试点限定词过细"),
    "国有高新技术企业股权激励试点": ("高新技术企业股权激励", "中", "企业属性和试点限定词过细"),
    "东湖科技保险创新示范区": ("科技保险创新", "高", "地区和示范区名称过细"),
    "中关村西区科技金融产业区": ("科技金融产业集聚", "高", "地区和园区名称过细"),
    "关中高新技术产业带": ("高新技术产业", "高", "区域名称过细"),
    "高新科技园区": ("科技园区", "高", "高新限定词可概括"),
    "高科技园区": ("科技园区", "高", "高科技限定词可概括"),
    "国家高新区": ("高新技术产业开发区", "中", "行政级别限定词过细"),
    "国家科技金融创新中心": ("科技金融创新", "中", "国家和中心名称过细"),
    "互联网金融创新中心": ("互联网金融创新", "高", "中心名称过细"),
    "科技金融创新服务中心": ("科技金融服务", "中", "中心组织形态过细"),
    "科技金融服务中心": ("科技金融服务", "中", "中心组织形态过细"),
    "科技金融区域协同创新中心": ("科技金融区域协同", "高", "中心组织形态过细"),
    "科技金融专营事业部": ("科技金融机构", "高", "部门名称过细"),
    "科技信贷专营事业部": ("科技信贷", "高", "部门名称过细"),
    "银行系金融租赁公司": ("金融租赁公司", "高", "机构隶属关系过细"),
    "商业银行科技支行": ("科技银行", "中", "机构层级和隶属关系过细"),
    # Named funds, programs and policy instruments
    "国家科技成果转化引导基金": ("科技成果转化基金", "高", "基金名称过细"),
    "国家科技成果转化引导基金创业投资子基金": ("科技成果转化基金", "高", "国家、子基金和投资形式过细"),
    "国防工业科技成果转化引导基金": ("科技成果转化基金", "高", "行业和基金名称过细"),
    "科技成果转化引导基金": ("科技成果转化基金", "高", "引导属性过细"),
    "科技成果转移转化基金": ("科技成果转化基金", "高", "转移转化表述概括为成果转化基金"),
    "战略性新兴产业创业投资引导基金": ("创业投资引导基金", "高", "产业名称过细"),
    "新兴产业创业投资基金": ("创业投资基金", "高", "产业名称过细"),
    "国家集成电路产业发展投资基金": ("产业投资基金", "高", "具体产业基金名称过细"),
    "光伏发电投资基金": ("产业投资基金", "高", "具体产业基金名称过细"),
    "乡村振兴专项股权投资基金": ("股权投资基金", "高", "政策专项和产业场景过细"),
    "重点产业知识产权运营基金": ("知识产权运营基金", "高", "产业范围限定词过细"),
    "知识产权质押融资风险补偿基金": ("知识产权质押融资风险补偿", "高", "基金载体过细"),
    "知识产权质押融资担保基金": ("知识产权质押融资担保", "高", "基金载体过细"),
    "知识产权质押风险补偿基金": ("知识产权质押风险补偿", "高", "基金载体过细"),
    "专利质押融资风险补偿基金": ("知识产权质押融资风险补偿", "中", "专利限定词概括为知识产权"),
    # Detailed SME and tax/loan policy expressions
    "科技型农村中小企业": ("科技型中小企业", "高", "地区和行业场景过细"),
    "初创期科技型中小企业": ("科技型中小企业", "高", "生命周期限定词过细"),
    "科技型中小企业成长路线图计划": ("科技型中小企业", "高", "计划名称过细"),
    "科技型中小企业研发费用加计扣除": ("科技型中小企业税收优惠", "高", "具体税收工具过细"),
    "高新技术企业税收优惠政策": ("高新技术企业税收优惠", "高", "政策载体限定词过细"),
    "科技型中小企业贷款平台": ("科技型中小企业贷款", "高", "平台载体过细"),
    "普惠型小微企业贷款": ("小微企业贷款", "高", "普惠属性过细"),
    "中小企业信用再担保机构": ("中小企业融资担保机构", "中", "再担保层级过细"),
    "创业板上市公司估值": ("企业估值", "高", "板块和上市状态过细"),
    "高新技术企业在资本市场融资": ("高新技术企业融资", "高", "融资市场限定词过细"),
    # IP services and transaction details
    "知识产权交易平台": ("知识产权交易", "高", "平台载体过细"),
    "知识产权综合交易平台": ("知识产权交易", "高", "平台载体和综合属性过细"),
    "知识产权投融资服务平台": ("知识产权投融资", "高", "平台载体过细"),
    "知识产权质押处置平台": ("知识产权质押", "高", "平台载体和处置环节过细"),
    "知识产权质押信息平台": ("知识产权质押", "高", "平台载体过细"),
    "知识产权运营服务体系建设": ("知识产权运营服务", "高", "建设动作和体系表述过细"),
    "知识产权评估与交易市场": ("知识产权评估", "中", "交易市场场景过细"),
    "中医药知识产权质押贷款": ("知识产权质押融资", "高", "行业限定词过细"),
    # Method/model details in scientific papers
    "不完全信息动态博弈": ("动态博弈", "高", "模型条件限定词过细"),
    "属性匹配满意度函数": ("匹配函数", "中", "函数对象和评价维度过细"),
    "风险损失量测算模型": ("风险测度模型", "高", "测算对象和模型表述过细"),
    "双构面有限理性理论": ("有限理性理论", "高", "理论结构限定词过细"),
    "投入-产出指标体系": ("投入产出分析", "中", "指标体系表述过细"),
    # Specific technology/industry cases
    "数字供应链金融资源配置效率": ("供应链金融", "高", "数字化和效率指标过细"),
    "数字供应链金融发展结构": ("供应链金融", "高", "数字化和发展维度过细"),
    "海洋经济供应链金融服务模式": ("供应链金融", "高", "行业场景和模式表述过细"),
    "农业科技金融发展专项资金": ("农业科技金融", "高", "专项资金载体过细"),
    "现代农业科技金融": ("农业科技金融", "高", "现代农业限定词可概括"),
}


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


def aggregate(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    stages: dict[tuple[str, str], set[str]] = defaultdict(set)
    years: dict[tuple[str, str], set[str]] = defaultdict(set)
    for r in rows:
        key = (r["Layer"], r["Label"])
        if key not in out:
            out[key] = {
                "Layer": r["Layer"],
                "OriginalKeyword": r["Label"],
                "OccurrenceCount": "0",
                "StageCount": "0",
                "Stages": "",
                "Years": "",
                "TotalFrequency": "0",
                "MaxDegree": "0",
                "MaxWeightedDegree": "0",
            }
        x = out[key]
        x["OccurrenceCount"] = str(int(x["OccurrenceCount"]) + 1)
        x["TotalFrequency"] = str(int(x["TotalFrequency"]) + int(float(r["Frequency"])))
        x["MaxDegree"] = str(max(int(float(x["MaxDegree"])), int(float(r["Degree"]))))
        x["MaxWeightedDegree"] = str(max(float(x["MaxWeightedDegree"]), float(r["WeightedDegree"])))
        stages[key].add(r["Stage"])
        years[key].add(r["Years"])
    for key, x in out.items():
        x["StageCount"] = str(len(stages[key]))
        x["Stages"] = "；".join(sorted(stages[key]))
        x["Years"] = "；".join(sorted(years[key]))
        if x["MaxWeightedDegree"].endswith(".0"):
            x["MaxWeightedDegree"] = x["MaxWeightedDegree"][:-2]
    return out


def make_rows(index: dict[tuple[str, str], dict[str, str]], mapping: dict[str, tuple[str, str, str]], mapping_type: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for (layer, original), stats in sorted(index.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if original not in mapping:
            continue
        target, confidence, basis = mapping[original]
        if target == original:
            continue
        target_exists = "是" if (layer, target) in index else "否"
        row = dict(stats)
        row.update(
            {
                "SuggestedKeyword": target,
                "MappingType": mapping_type,
                "Confidence": confidence,
                "Basis": basis,
                "TargetExistsInSameLayer": target_exists,
                "ReviewerDecision": "待审核",
                "ReviewerNote": "确认后再回写规范化词典；本文件不自动修改原始关键词",
            }
        )
        rows.append(row)
    return rows


def make_cluster_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        grouped[(r["Layer"], r["SuggestedKeyword"], r["MappingType"])].append(r)
    out = []
    for (layer, target, mapping_type), rr in sorted(grouped.items()):
        originals = sorted({r["OriginalKeyword"] for r in rr})
        out.append(
            {
                "Layer": layer,
                "SuggestedKeyword": target,
                "MappingType": mapping_type,
                "OriginalKeywordCount": str(len(originals)),
                "OriginalKeywords": "；".join(originals),
                "OriginalOccurrenceCount": str(sum(int(r["OccurrenceCount"]) for r in rr)),
                "TargetExistsInSameLayer": "是" if all(r["TargetExistsInSameLayer"] == "是" for r in rr) else "否",
            }
        )
    return out


def main() -> None:
    rows = read_csv(INPUT)
    index = aggregate(rows)
    synonym_rows = make_rows(index, SYNONYM_MAP, "同义词或变体合并")
    generalize_rows = make_rows(index, GENERALIZE_MAP, "过于具体关键词概括")
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "同义词_变体合并建议.csv", synonym_rows)
    write_csv(OUT / "过于具体关键词_概括建议.csv", generalize_rows)
    write_csv(OUT / "同义词_变体合并后词簇.csv", make_cluster_summary(synonym_rows))
    write_csv(OUT / "过于具体关键词_概括后词簇.csv", make_cluster_summary(generalize_rows))

    both = {(r["Layer"], r["OriginalKeyword"]) for r in synonym_rows} & {
        (r["Layer"], r["OriginalKeyword"]) for r in generalize_rows
    }
    lines = [
        "# 科学与政策关键词合并、概括建议",
        "",
        "## 使用范围",
        "",
        "本次建议基于当前主网络（Frequency≥1、Degree≥2、Leiden resolution=0.3）中的4272条阶段节点记录生成。相同关键词在不同阶段分别保留统计信息。",
        "",
        "## 两类文件",
        "",
        f"- `同义词_变体合并建议.csv`：词形、缩写、近义表达的合并建议，共{len(synonym_rows)}条记录。",
        f"- `过于具体关键词_概括建议.csv`：地区、机构、试点、基金、平台、分险种、模型条件或具体政策工具的上位化建议，共{len(generalize_rows)}条记录。",
        "- 两个词簇文件：按建议词汇总，便于直接检查一个概括词会吸收哪些原词。",
        "",
        "## 判定原则",
        "",
        "1. 只输出建议，不自动改写原始规范关键词。",
        "2. `高`置信度表示词面关系明确，通常可以优先审核；`中`置信度表示存在概念边界，需要结合论文或政策文本确认。",
        "3. `TargetExistsInSameLayer=否` 表示建议词目前没有在该层级出现，回写前需确认是否要新增该规范词。",
        "4. 同义词合并与上位化概括不能完全替代人工语义审核，尤其是“科技企业/科技型企业/科技型中小企业”“金融租赁/融资租赁”“风险投资/创业投资”等边界词。",
        "",
        "## 统计",
        "",
        f"- 科学同义词/变体建议：{sum(r['Layer']=='科学' for r in synonym_rows)}条；政策：{sum(r['Layer']=='政策' for r in synonym_rows)}条。",
        f"- 科学过于具体概括建议：{sum(r['Layer']=='科学' for r in generalize_rows)}条；政策：{sum(r['Layer']=='政策' for r in generalize_rows)}条。",
        f"- 同时出现在两类建议中的词：{len(both)}条层级-关键词记录，主要是既有词形变体又包含具体限定词的情况，需优先人工确认。",
        "",
        "## 建议使用顺序",
        "",
        "先审核同义词/变体合并表，确定规范词典的唯一入口；再审核过于具体概括表，确定桑基图和社区命名所需的主题粒度。审核完成后再重新计算频次、Degree、Leiden社区和桑基流量。",
    ]
    (OUT / "说明.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"out={OUT}")
    print(f"nodes={len(rows)} unique_layer_keywords={len(index)} synonym_rows={len(synonym_rows)} generalize_rows={len(generalize_rows)}")
    print(f"synonym_science={sum(r['Layer']=='科学' for r in synonym_rows)} synonym_policy={sum(r['Layer']=='政策' for r in synonym_rows)}")
    print(f"generalize_science={sum(r['Layer']=='科学' for r in generalize_rows)} generalize_policy={sum(r['Layer']=='政策' for r in generalize_rows)}")


if __name__ == "__main__":
    main()
