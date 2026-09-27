from __future__ import annotations

import csv
import itertools
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "最终规范关键词_桑基图社区合并_resolution0.3"
OUT_DIR = BASE / "科学政策主题交互_resolution0.3"
IMAGE_OUT = Path(r"C:\Users\张甜甜的Redmi\.codex\visualizations\2026\09\20\01a0bc3a-e620-7511-b6b4-b009915a0768\science-policy-interactions.png")
FONT_PATH = r"C:\Windows\Fonts\NotoSansSC-VF.ttf"
STAGES = [("A", "1998-2005"), ("B", "2006-2011"), ("C", "2012-2015"), ("D", "2016-2019"), ("E", "2020-2025")]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def font(size: int):
    return ImageFont.truetype(FONT_PATH, size)


def cubic(p0, p1, p2, p3, t):
    u = 1 - t
    return (
        u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1],
    )


def curve_band(x0, y0, x1, y1, width):
    bend = max(42, (x1 - x0) * 0.4)
    top = [cubic((x0, y0), (x0 + bend, y0), (x1 - bend, y1), (x1, y1), i / 24) for i in range(25)]
    bottom = [cubic((x0, y0 + width), (x0 + bend, y0 + width), (x1 - bend, y1 + width), (x1, y1 + width), i / 24) for i in range(25)]
    return [(round(x), round(y)) for x, y in top + list(reversed(bottom))]


def main():
    rows = read_csv(DATA_DIR / "合并后节点社区分配.csv")
    assignment = defaultdict(dict)
    names = {}
    sizes = {}
    for r in rows:
        key = (r["Layer"], r["Stage"])
        assignment[key][r["Label"]] = r["Community"]
        names[(r["Layer"], r["Stage"], r["Community"])] = r["CommunityName"]
    for r in read_csv(DATA_DIR / "合并后社区命名对照表.csv"):
        sizes[(r["Layer"], r["Stage"], r["Community"])] = r["NodeCount"]

    flow_rows = []
    detail_rows = []
    stage_stats = []
    for stage, years in STAGES:
        science = assignment[("科学", stage)]
        policy = assignment[("政策", stage)]
        grouped = defaultdict(list)
        for kw in sorted(set(science) & set(policy)):
            grouped[(science[kw], policy[kw])].append(kw)
        for (s_comm, p_comm), kws in sorted(grouped.items(), key=lambda x: (int(x[0][0]), int(x[0][1]))):
            flow_rows.append(
                {
                    "Stage": stage, "Years": years,
                    "ScienceCommunity": s_comm, "ScienceName": names[("科学", stage, s_comm)],
                    "ScienceNodeId": f"科学_{stage}_M{s_comm}",
                    "PolicyCommunity": p_comm, "PolicyName": names[("政策", stage, p_comm)],
                    "PolicyNodeId": f"政策_{stage}_M{p_comm}",
                    "Value": len(kws), "SharedKeywordCount": len(kws), "SharedKeywords": ";".join(kws),
                }
            )
            for kw in kws:
                detail_rows.append(
                    {
                        "Stage": stage, "Years": years,
                        "ScienceCommunity": s_comm, "ScienceName": names[("科学", stage, s_comm)],
                        "PolicyCommunity": p_comm, "PolicyName": names[("政策", stage, p_comm)], "Keyword": kw,
                    }
                )
        s_totals = Counter()
        p_totals = Counter()
        for r in flow_rows:
            if r["Stage"] == stage:
                s_totals[r["ScienceCommunity"]] += int(r["Value"])
                p_totals[r["PolicyCommunity"]] += int(r["Value"])
        stage_stats.append(
            {
                "Stage": stage, "Years": years, "InteractionCount": sum(int(r["Value"]) for r in flow_rows if r["Stage"] == stage),
                "InteractionEdgeCount": sum(1 for r in flow_rows if r["Stage"] == stage),
                "ScienceCommunitiesWithInteraction": len(s_totals), "PolicyCommunitiesWithInteraction": len(p_totals),
            }
        )

    node_rows = []
    for layer in ["科学", "政策"]:
        for stage, years in STAGES:
            communities = sorted({r["Community"] for r in rows if r["Layer"] == layer and r["Stage"] == stage}, key=int)
            for community in communities:
                node_rows.append(
                    {
                        "Layer": layer, "Stage": stage, "Years": years, "Community": community,
                        "NodeId": f"{layer}_{stage}_M{community}", "CommunityName": names[(layer, stage, community)],
                        "NodeCount": sizes[(layer, stage, community)],
                    }
                )

    fields_flow = ["Stage", "Years", "ScienceCommunity", "ScienceName", "ScienceNodeId", "PolicyCommunity", "PolicyName", "PolicyNodeId", "Value", "SharedKeywordCount", "SharedKeywords"]
    fields_detail = ["Stage", "Years", "ScienceCommunity", "ScienceName", "PolicyCommunity", "PolicyName", "Keyword"]
    fields_node = ["Layer", "Stage", "Years", "Community", "NodeId", "CommunityName", "NodeCount"]
    fields_stats = ["Stage", "Years", "InteractionCount", "InteractionEdgeCount", "ScienceCommunitiesWithInteraction", "PolicyCommunitiesWithInteraction"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_DIR / "科学政策社区交互流动.csv", flow_rows, fields_flow)
    write_csv(OUT_DIR / "科学政策社区交互关键词明细.csv", detail_rows, fields_detail)
    write_csv(OUT_DIR / "科学政策交互节点.csv", node_rows, fields_node)
    write_csv(OUT_DIR / "科学政策交互阶段统计.csv", stage_stats, fields_stats)

    # Static five-panel bipartite interaction figure.
    W, H = 2700, 1750
    im = Image.new("RGBA", (W, H), (249, 250, 252, 255))
    draw = ImageDraw.Draw(im, "RGBA")
    title_font, subtitle_font, stage_font, label_font, small_font = font(34), font(20), font(24), font(17), font(14)
    draw.text((70, 32), "科学—政策：五阶段主题交互", fill=(28, 37, 54, 255), font=title_font)
    draw.text((70, 82), "Leiden resolution=0.3｜小社区合并｜连线宽度=科学社区与政策社区共享的最终规范关键词数量", fill=(92, 103, 120, 255), font=subtitle_font)
    panel_w = 510
    panel_xs = [50 + i * 530 for i in range(5)]
    top, bottom = 160, 1560
    science_color = (67, 128, 214, 235)
    policy_color = (226, 145, 57, 235)
    link_color = (112, 126, 145, 90)
    for panel_x, (stage, years) in zip(panel_xs, STAGES):
        draw.rounded_rectangle([panel_x, 125, panel_x + panel_w - 20, bottom + 30], radius=10, outline=(218, 223, 230, 255), width=2)
        draw.text((panel_x + 18, 138), f"{stage}  {years}", fill=(28, 37, 54, 255), font=stage_font)
        stage_flows = [r for r in flow_rows if r["Stage"] == stage]
        s_nodes = sorted([n for n in node_rows if n["Layer"] == "科学" and n["Stage"] == stage], key=lambda r: int(r["Community"]))
        p_nodes = sorted([n for n in node_rows if n["Layer"] == "政策" and n["Stage"] == stage], key=lambda r: int(r["Community"]))
        s_total = Counter(); p_total = Counter()
        for r in stage_flows:
            s_total[r["ScienceCommunity"]] += int(r["Value"])
            p_total[r["PolicyCommunity"]] += int(r["Value"])
        s_heights = [max(10, s_total[n["Community"]] * 4) for n in s_nodes]
        p_heights = [max(10, p_total[n["Community"]] * 4) for n in p_nodes]
        s_gap = 14; p_gap = 14
        def place(node_list, heights, x):
            total = sum(heights) + max(0, len(heights) - 1) * 14
            y = top + max(0, (bottom - top - total) / 2)
            pos = {}
            for n, h in zip(node_list, heights):
                nid = n["NodeId"]
                pos[nid] = {"x0": x, "x1": x + 18, "y0": y, "y1": y + h}
                y += h + 14
            return pos
        s_pos = place(s_nodes, s_heights, panel_x + 125)
        p_pos = place(p_nodes, p_heights, panel_x + 330)
        s_cursor = {nid: p["y0"] for nid, p in s_pos.items()}
        p_cursor = {nid: p["y0"] for nid, p in p_pos.items()}
        for r in sorted(stage_flows, key=lambda x: (int(x["ScienceCommunity"]), int(x["PolicyCommunity"]))):
            sid, pid = r["ScienceNodeId"], r["PolicyNodeId"]
            w = max(4, int(r["Value"]) * 4)
            sy, py = s_cursor[sid], p_cursor[pid]
            s_cursor[sid] += w
            p_cursor[pid] += w
            draw.polygon(curve_band(s_pos[sid]["x1"], sy, p_pos[pid]["x0"], py, w), fill=link_color)
        for n in s_nodes:
            p = s_pos[n["NodeId"]]
            draw.rounded_rectangle([p["x0"], p["y0"], p["x1"], max(p["y1"], p["y0"] + 8)], radius=3, fill=science_color, outline=(255, 255, 255, 220), width=2)
            draw.text((p["x0"] - 8, (p["y0"] + p["y1"]) / 2 - 9), f"C{n['Community']} {n['CommunityName']}", fill=(35, 44, 60, 255), font=label_font, anchor="rm")
        for n in p_nodes:
            p = p_pos[n["NodeId"]]
            draw.rounded_rectangle([p["x0"], p["y0"], p["x1"], max(p["y1"], p["y0"] + 8)], radius=3, fill=policy_color, outline=(255, 255, 255, 220), width=2)
            draw.text((p["x1"] + 8, (p["y0"] + p["y1"]) / 2 - 9), f"C{n['Community']} {n['CommunityName']}", fill=(35, 44, 60, 255), font=label_font)
        draw.text((panel_x + 120, 1510), "科学", fill=science_color, font=small_font)
        draw.text((panel_x + 330, 1510), "政策", fill=policy_color, font=small_font)
    draw.rounded_rectangle([70, 1650, 88, 1668], radius=3, fill=science_color)
    draw.text((98, 1647), "科学社区", fill=(92, 103, 120, 255), font=small_font)
    draw.rounded_rectangle([260, 1650, 278, 1668], radius=3, fill=policy_color)
    draw.text((288, 1647), "政策社区", fill=(92, 103, 120, 255), font=small_font)
    draw.text((470, 1647), "连线越宽，表示共享关键词越多", fill=(92, 103, 120, 255), font=small_font)
    IMAGE_OUT.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(IMAGE_OUT, quality=95)
    print(f"FLOWS|{len(flow_rows)}")
    print(f"DETAILS|{len(detail_rows)}")
    print(f"IMAGE|{IMAGE_OUT}")


if __name__ == "__main__":
    main()
