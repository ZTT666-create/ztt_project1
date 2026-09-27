from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "最终规范关键词_桑基图社区合并_resolution0.3"
OUT_DIR = Path(r"C:\Users\张甜甜的Redmi\.codex\visualizations\2026\09\20\01a0bc3a-e620-7511-b6b4-b009915a0768")
FONT = r"C:\Windows\Fonts\NotoSansSC-VF.ttf"
STAGES = ["A", "B", "C", "D", "E"]
COLORS = {"A": (67, 128, 214, 235), "B": (49, 153, 122, 235), "C": (226, 145, 57, 235), "D": (155, 93, 184, 235), "E": (206, 79, 91, 235)}


def font(size: int):
    return ImageFont.truetype(FONT, size)


def cubic(p0, p1, p2, p3, t):
    u = 1 - t
    return (u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0], u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1])


def curve_band(x0, y0, x1, y1, width):
    bend = max(80, (x1 - x0) * 0.42)
    top = [cubic((x0, y0), (x0 + bend, y0), (x1 - bend, y1), (x1, y1), i / 30) for i in range(31)]
    bottom = [cubic((x0, y0 + width), (x0 + bend, y0 + width), (x1 - bend, y1 + width), (x1, y1 + width), i / 30) for i in range(31)]
    return [(round(x), round(y)) for x, y in top + list(reversed(bottom))]


def render(layer: str, title: str, prefix: str):
    with (DATA_DIR / "合并后社区命名对照表.csv").open(encoding="utf-8-sig", newline="") as f:
        nodes = [r for r in csv.DictReader(f) if r["Layer"] == layer]
    with (DATA_DIR / "合并后桑基图社区流动.csv").open(encoding="utf-8-sig", newline="") as f:
        flows = [r for r in csv.DictReader(f) if r["Layer"] == layer]

    years = {r["Stage"]: r["Years"] for r in nodes}
    x_positions = dict(zip(STAGES, [150, 610, 1070, 1530, 1990]))
    node_width, width, height, top, bottom, scale, gap = 26, 2300, 1500, 150, 1390, 5.0, 12
    im = Image.new("RGBA", (width, height), (249, 250, 252, 255))
    draw = ImageDraw.Draw(im, "RGBA")
    incoming, outgoing = defaultdict(int), defaultdict(int)
    for r in flows:
        outgoing[r["Source"]] += int(r["Value"])
        incoming[r["Target"]] += int(r["Value"])

    positions = {}
    for stage in STAGES:
        stage_nodes = sorted([r for r in nodes if r["Stage"] == stage], key=lambda r: int(r["Community"]))
        heights = [max(8, int(max(incoming[r["Layer"] + "_" + stage + "_M" + r["Community"]], outgoing[r["Layer"] + "_" + stage + "_M" + r["Community"]], 1) * scale)) for r in stage_nodes]
        total = sum(heights) + gap * max(0, len(heights) - 1)
        y = top + max(0, (bottom - top - total) / 2)
        for r, h in zip(stage_nodes, heights):
            nid = f"{layer}_{stage}_M{r['Community']}"
            positions[nid] = {"x0": x_positions[stage], "x1": x_positions[stage] + node_width, "y0": y, "y1": y + h}
            y += h + gap

    draw.text((90, 36), title, fill=(28, 37, 54, 255), font=font(34))
    draw.text((90, 90), "Leiden resolution=0.3｜小社区合并｜全网络（Degree ≥ 2）｜连线宽度=共享最终规范关键词数量", fill=(92, 103, 120, 255), font=font(21))
    for stage in STAGES:
        x = x_positions[stage] + node_width / 2
        label = f"{stage}  {years[stage]}"
        bbox = draw.textbbox((0, 0), label, font=font(23))
        draw.text((x - (bbox[2] - bbox[0]) / 2, 125), label, fill=(28, 37, 54, 255), font=font(23))

    out_cursor = {nid: p["y0"] for nid, p in positions.items()}
    in_cursor = {nid: p["y0"] for nid, p in positions.items()}
    for r in sorted(flows, key=lambda r: (r["FromStage"], int(r["FromCommunity"]), int(r["ToCommunity"]))):
        src, dst = r["Source"], r["Target"]
        w = max(4, int(int(r["Value"]) * scale))
        sy, ty = out_cursor[src], in_cursor[dst]
        out_cursor[src] += w
        in_cursor[dst] += w
        base = COLORS[r["FromStage"]]
        draw.polygon(curve_band(positions[src]["x1"], sy, positions[dst]["x0"], ty, w), fill=(base[0], base[1], base[2], 72))

    for r in nodes:
        nid = f"{layer}_{r['Stage']}_M{r['Community']}"
        p = positions[nid]
        rect = [p["x0"], p["y0"], p["x1"], max(p["y1"], p["y0"] + 8)]
        draw.rounded_rectangle(rect, radius=4, fill=COLORS[r["Stage"]], outline=(255, 255, 255, 220), width=2)
        label = f"C{r['Community']}  {r['CommunityName']}"
        label_font = font(20)
        if r["Stage"] == "E":
            bbox = draw.textbbox((0, 0), label, font=label_font)
            tx = p["x0"] - 12 - (bbox[2] - bbox[0])
            anchor_y = (p["y0"] + p["y1"]) / 2 - (bbox[3] - bbox[1]) / 2
        else:
            tx = p["x1"] + 12
            anchor_y = (p["y0"] + p["y1"]) / 2 - 12
        draw.text((tx, anchor_y), label, fill=(35, 44, 60, 255), font=label_font)
        if p["y1"] - p["y0"] > 30:
            small = f"关键词节点 {r['NodeCount']}"
            if r["Stage"] == "E":
                bbox = draw.textbbox((0, 0), small, font=font(16))
                draw.text((p["x0"] - 12 - (bbox[2] - bbox[0]), anchor_y + 28), small, fill=(105, 114, 129, 255), font=font(16))
            else:
                draw.text((tx, anchor_y + 28), small, fill=(105, 114, 129, 255), font=font(16))

    legend_x = 90
    for stage in STAGES:
        label = f"{stage} {years[stage]}"
        draw.rounded_rectangle([legend_x, 1445, legend_x + 18, 1463], radius=3, fill=COLORS[stage])
        draw.text((legend_x + 26, 1440), label, fill=(92, 103, 120, 255), font=font(16))
        legend_x += 210
    output = OUT_DIR / f"{prefix}-sankey-merged.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(output, quality=95)
    print(output)


if __name__ == "__main__":
    render("科学", "科学论文：小社区合并后的五阶段主题演化", "science")
    render("政策", "政策文本：小社区合并后的五阶段主题演化", "policy")
