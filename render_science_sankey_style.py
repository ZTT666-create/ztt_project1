from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "最终规范关键词_桑基图社区合并_resolution0.3"
OUT = Path(
    r"C:\Users\张甜甜的Redmi\.codex\visualizations\2026\09\20\01a0bc3a-e620-7511-b6b4-b009915a0768\science-sankey-style-weighted.png"
)
FONT = r"C:\Windows\Fonts\NotoSansSC-VF.ttf"
STAGES = ["A", "B", "C", "D", "E"]

# 与用户示例接近的低饱和蓝、绿、橙、紫、红、橄榄色系。
PALETTE = {
    "blue": (55, 111, 145, 245),
    "green": (82, 137, 110, 245),
    "orange": (199, 139, 49, 245),
    "purple": (126, 82, 157, 245),
    "red": (184, 77, 94, 245),
    "olive": (105, 124, 57, 245),
}

# 仅用于区分同一阶段的社区，不赋予颜色主题含义；连线沿用起点社区颜色。
NODE_COLORS = {
    "A": ["blue", "orange"],
    "B": ["green", "purple", "red", "blue", "orange", "olive"],
    "C": ["orange", "olive", "blue", "orange", "green", "purple"],
    "D": ["green", "purple", "red", "blue", "olive"],
    "E": ["orange", "olive", "blue", "orange"],
}


def font(size: int):
    return ImageFont.truetype(FONT, size)


def cubic(p0, p1, p2, p3, t):
    u = 1 - t
    return (
        u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1],
    )


def curve_band(x0, y0, x1, y1, width):
    bend = max(110, (x1 - x0) * 0.40)
    top, bottom = [], []
    for i in range(41):
        t = i / 40
        top.append(cubic((x0, y0), (x0 + bend, y0), (x1 - bend, y1), (x1, y1), t))
        bottom.append(cubic((x0, y0 + width), (x0 + bend, y0 + width), (x1 - bend, y1 + width), (x1, y1 + width), t))
    return [(round(x), round(y)) for x, y in top + list(reversed(bottom))]


def draw_wrapped(draw, text, xy, fnt, fill, max_chars=14, line_gap=3):
    lines = [text[i : i + max_chars] for i in range(0, len(text), max_chars)] or [""]
    x, y = xy
    for line in lines:
        draw.text((x, y), line, fill=fill, font=fnt)
        box = draw.textbbox((x, y), line, font=fnt)
        y += box[3] - box[1] + line_gap


def main():
    with (DATA_DIR / "合并后社区命名对照表.csv").open(encoding="utf-8-sig", newline="") as f:
        nodes = [r for r in csv.DictReader(f) if r["Layer"] == "科学"]
    with (DATA_DIR / "合并后桑基图社区流动.csv").open(encoding="utf-8-sig", newline="") as f:
        flows = [r for r in csv.DictReader(f) if r["Layer"] == "科学"]

    years = {r["Stage"]: r["Years"] for r in nodes}
    x_positions = dict(zip(STAGES, [155, 720, 1285, 1850, 2415]))
    width, height = 2900, 1700
    top, bottom = 190, 1535
    node_width, gap = 28, 15
    scale = 4.2
    background = (255, 255, 255, 255)
    text_color = (36, 45, 61, 255)
    muted = (103, 112, 128, 255)
    im = Image.new("RGBA", (width, height), background)
    draw = ImageDraw.Draw(im, "RGBA")

    incoming, outgoing = defaultdict(int), defaultdict(int)
    for r in flows:
        outgoing[r["Source"]] += int(r["Value"])
        incoming[r["Target"]] += int(r["Value"])

    node_color = {}
    positions = {}
    for stage in STAGES:
        stage_nodes = sorted((r for r in nodes if r["Stage"] == stage), key=lambda r: int(r["Community"]))
        heights = [
            max(15, int(max(incoming[r["NodeId"]], outgoing[r["NodeId"]], 1) * scale))
            for r in stage_nodes
        ]
        total = sum(heights) + gap * max(0, len(heights) - 1)
        y = top + max(0, (bottom - top - total) / 2)
        for r, h in zip(stage_nodes, heights):
            nid = r["NodeId"]
            positions[nid] = {"x0": x_positions[stage], "x1": x_positions[stage] + node_width, "y0": y, "y1": y + h}
            palette_name = NODE_COLORS[stage][int(r["Community"]) - 1]
            node_color[nid] = PALETTE[palette_name]
            y += h + gap

    title = "科学论文主题演化桑基图（1998–2025）"
    subtitle = "Leiden resolution=0.3｜小社区合并｜连边宽度 ∝ 相邻阶段社区间共享最终规范关键词数量"
    title_font, subtitle_font = font(39), font(21)
    title_box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((width - (title_box[2] - title_box[0])) / 2, 36), title, fill=text_color, font=title_font)
    sub_box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    draw.text(((width - (sub_box[2] - sub_box[0])) / 2, 91), subtitle, fill=muted, font=subtitle_font)

    stage_font = font(24)
    for stage in STAGES:
        label = years[stage]
        box = draw.textbbox((0, 0), label, font=stage_font)
        x = x_positions[stage] + node_width / 2 - (box[2] - box[0]) / 2
        draw.text((x, 138), label, fill=text_color, font=stage_font)

    # 先画连线，后画节点，保证节点边界清楚；宽度直接由 Value 决定。
    out_cursor = {nid: p["y0"] for nid, p in positions.items()}
    in_cursor = {nid: p["y0"] for nid, p in positions.items()}
    for r in sorted(flows, key=lambda x: (x["FromStage"], int(x["FromCommunity"]), int(x["ToCommunity"]))):
        src, dst = r["Source"], r["Target"]
        ribbon_width = max(3, int(int(r["Value"]) * scale))
        sy, ty = out_cursor[src], in_cursor[dst]
        out_cursor[src] += ribbon_width
        in_cursor[dst] += ribbon_width
        base = node_color[src]
        draw.polygon(curve_band(positions[src]["x1"], sy, positions[dst]["x0"], ty, ribbon_width), fill=(base[0], base[1], base[2], 78))

    label_font, small_font = font(19), font(15)
    for r in nodes:
        nid = r["NodeId"]
        p = positions[nid]
        color = node_color[nid]
        draw.rounded_rectangle([p["x0"], p["y0"], p["x1"], max(p["y1"], p["y0"] + 15)], radius=5, fill=color, outline=(255, 255, 255, 235), width=2)
        stage = r["Stage"]
        label = f"C{r['Community']}  {r['CommunityName']}"
        if stage == "E":
            box = draw.textbbox((0, 0), label, font=label_font)
            tx = p["x0"] - 18 - (box[2] - box[0])
            draw_wrapped(draw, label, (tx, (p["y0"] + p["y1"]) / 2 - 12), label_font, text_color, max_chars=17)
            count = f"关键词节点 {r['NodeCount']}"
            box = draw.textbbox((0, 0), count, font=small_font)
            draw.text((p["x0"] - 18 - (box[2] - box[0]), (p["y0"] + p["y1"]) / 2 + 31), count, fill=muted, font=small_font)
        else:
            tx = p["x1"] + 18
            draw_wrapped(draw, label, (tx, (p["y0"] + p["y1"]) / 2 - 12), label_font, text_color, max_chars=17)
            count = f"关键词节点 {r['NodeCount']}"
            draw.text((tx, (p["y0"] + p["y1"]) / 2 + 31), count, fill=muted, font=small_font)

    # 简洁图例：颜色用于区分社区，数字字号说明连边含义。
    legend = "颜色仅用于区分社区；连边越宽，表示共享关键词越多"
    box = draw.textbbox((0, 0), legend, font=small_font)
    draw.text(((width - (box[2] - box[0])) / 2, 1600), legend, fill=muted, font=small_font)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(OUT, quality=95)
    print(OUT)


if __name__ == "__main__":
    main()
