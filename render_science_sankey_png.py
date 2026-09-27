from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "最终规范关键词_Leiden分辨率比较_1998-2025"
OUT = Path(r"C:\Users\张甜甜的Redmi\.codex\visualizations\2026\09\20\01a0bc3a-e620-7511-b6b4-b009915a0768\science-sankey.png")
FONT = r"C:\Windows\Fonts\NotoSansSC-VF.ttf"


def font(size: int):
    return ImageFont.truetype(FONT, size)


def cubic(p0, p1, p2, p3, t):
    u = 1 - t
    return (
        u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1],
    )


def curve_band(x0, y0, x1, y1, width):
    bend = max(80, (x1 - x0) * 0.42)
    top = []
    bottom = []
    for i in range(31):
        t = i / 30
        top.append(cubic((x0, y0), (x0 + bend, y0), (x1 - bend, y1), (x1, y1), t))
        bottom.append(cubic((x0, y0 + width), (x0 + bend, y0 + width), (x1 - bend, y1 + width), (x1, y1 + width), t))
    return [(round(x), round(y)) for x, y in top + list(reversed(bottom))]


def main():
    with (DATA_DIR / "桑基图_社区节点_resolution0.3_已命名.csv").open(encoding="utf-8-sig", newline="") as f:
        nodes = [r for r in csv.DictReader(f) if r["Layer"] == "科学"]
    with (DATA_DIR / "桑基图_社区流动_resolution0.3_已命名.csv").open(encoding="utf-8-sig", newline="") as f:
        flows = [r for r in csv.DictReader(f) if r["Layer"] == "科学"]

    stage_order = ["A", "B", "C", "D", "E"]
    stage_years = {r["Stage"]: r["Years"] for r in nodes}
    x_positions = {s: x for s, x in zip(stage_order, [150, 610, 1070, 1530, 1990])}
    node_width = 26
    width, height = 2300, 1500
    top, bottom = 150, 1390
    scale = 5.0
    gap = 12
    colors = {
        "A": (67, 128, 214, 235),
        "B": (49, 153, 122, 235),
        "C": (226, 145, 57, 235),
        "D": (155, 93, 184, 235),
        "E": (206, 79, 91, 235),
    }
    bg = (249, 250, 252, 255)
    im = Image.new("RGBA", (width, height), bg)
    draw = ImageDraw.Draw(im, "RGBA")

    by_id = {r["NodeId"].replace("科学_", ""): r for r in nodes}
    incoming = defaultdict(int)
    outgoing = defaultdict(int)
    for r in flows:
        value = int(r["Value"])
        src = r["Source"].replace("科学_", "")
        dst = r["Target"].replace("科学_", "")
        outgoing[src] += value
        incoming[dst] += value

    positions = {}
    for stage in stage_order:
        stage_nodes = sorted([r for r in nodes if r["Stage"] == stage], key=lambda r: int(r["Community"]))
        heights = [max(8, int(max(incoming[r["NodeId"].replace("科学_", "")], outgoing[r["NodeId"].replace("科学_", "")], 1) * scale)) for r in stage_nodes]
        total = sum(heights) + gap * max(0, len(heights) - 1)
        y = top + max(0, (bottom - top - total) / 2)
        for r, h in zip(stage_nodes, heights):
            nid = r["NodeId"].replace("科学_", "")
            positions[nid] = {"x0": x_positions[stage], "x1": x_positions[stage] + node_width, "y0": y, "y1": y + h}
            y += h + gap

    title_font = font(34)
    subtitle_font = font(21)
    stage_font = font(23)
    label_font = font(20)
    small_font = font(16)
    draw.text((90, 36), "科学论文：五阶段社区主题演化", fill=(28, 37, 54, 255), font=title_font)
    draw.text((90, 90), "Leiden resolution=0.3｜全网络（Degree ≥ 2）｜连线宽度=共享最终规范关键词数量", fill=(92, 103, 120, 255), font=subtitle_font)

    for stage in stage_order:
        x = x_positions[stage] + node_width / 2
        label = f"{stage}  {stage_years[stage]}"
        bbox = draw.textbbox((0, 0), label, font=stage_font)
        draw.text((x - (bbox[2] - bbox[0]) / 2, 125), label, fill=(28, 37, 54, 255), font=stage_font)

    out_cursor = {nid: positions[nid]["y0"] for nid in positions}
    in_cursor = {nid: positions[nid]["y0"] for nid in positions}
    flows_sorted = sorted(flows, key=lambda r: (r["FromStage"], int(r["FromCommunity"]), int(r["ToCommunity"])))
    for r in flows_sorted:
        src = r["Source"].replace("科学_", "")
        dst = r["Target"].replace("科学_", "")
        w = max(4, int(int(r["Value"]) * scale))
        sy = out_cursor[src]
        ty = in_cursor[dst]
        out_cursor[src] += w
        in_cursor[dst] += w
        band = curve_band(positions[src]["x1"], sy, positions[dst]["x0"], ty, w)
        base = colors[r["FromStage"]]
        draw.polygon(band, fill=(base[0], base[1], base[2], 72))

    for r in nodes:
        nid = r["NodeId"].replace("科学_", "")
        p = positions[nid]
        stage = r["Stage"]
        rect = [p["x0"], p["y0"], p["x1"], max(p["y1"], p["y0"] + 8)]
        draw.rounded_rectangle(rect, radius=4, fill=colors[stage], outline=(255, 255, 255, 220), width=2)
        label = f"C{r['Community']}  {r['CommunityName']}"
        if stage == "E":
            bbox = draw.textbbox((0, 0), label, font=label_font)
            tx = p["x0"] - 12 - (bbox[2] - bbox[0])
            anchor_y = (p["y0"] + p["y1"]) / 2 - (bbox[3] - bbox[1]) / 2
        else:
            tx = p["x1"] + 12
            anchor_y = (p["y0"] + p["y1"]) / 2 - 12
        draw.text((tx, anchor_y), label, fill=(35, 44, 60, 255), font=label_font)
        if p["y1"] - p["y0"] > 30:
            count_label = f"关键词节点 {r['NodeCount']}"
            if stage == "E":
                bbox = draw.textbbox((0, 0), count_label, font=small_font)
                draw.text((p["x0"] - 12 - (bbox[2] - bbox[0]), anchor_y + 28), count_label, fill=(105, 114, 129, 255), font=small_font)
            else:
                draw.text((tx, anchor_y + 28), count_label, fill=(105, 114, 129, 255), font=small_font)

    legend_x = 90
    legend_y = 1440
    for stage in stage_order:
        label = f"{stage} {stage_years[stage]}"
        draw.rounded_rectangle([legend_x, legend_y + 5, legend_x + 18, legend_y + 23], radius=3, fill=colors[stage])
        draw.text((legend_x + 26, legend_y), label, fill=(92, 103, 120, 255), font=small_font)
        legend_x += 210

    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(OUT, quality=95)
    print(OUT)


if __name__ == "__main__":
    main()
