from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "科学政策主题交互_resolution0.3"
OUT = Path(r"C:\Users\张甜甜的Redmi\.codex\visualizations\2026\09\20\01a0bc3a-e620-7511-b6b4-b009915a0768\science-policy-A-interaction.png")
FONT_PATH = r"C:\Windows\Fonts\NotoSansSC-VF.ttf"


def font(size: int):
    return ImageFont.truetype(FONT_PATH, size)


def cubic(p0, p1, p2, p3, t):
    u = 1 - t
    return (
        u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1],
    )


def main():
    with (DATA_DIR / "科学政策社区交互流动.csv").open(encoding="utf-8-sig", newline="") as f:
        flows = [r for r in csv.DictReader(f) if r["Stage"] == "A"]
    with (DATA_DIR / "科学政策交互节点.csv").open(encoding="utf-8-sig", newline="") as f:
        nodes = [r for r in csv.DictReader(f) if r["Stage"] == "A"]

    W, H = 1800, 1100
    im = Image.new("RGBA", (W, H), (249, 250, 252, 255))
    draw = ImageDraw.Draw(im, "RGBA")
    science = [r for r in nodes if r["Layer"] == "科学"]
    policy = [r for r in nodes if r["Layer"] == "政策"]
    s_x, p_x = 420, 1360
    s_y, p_y = 500, 500
    node_w = 34
    science_color = (67, 128, 214, 235)
    policy_color = (226, 145, 57, 235)
    link_color = (112, 126, 145, 125)

    draw.text((90, 45), "1998–2005：科学与政策主题交互", fill=(28, 37, 54, 255), font=font(40))
    draw.text((90, 105), "Leiden resolution=0.3｜小社区合并｜连线宽度=共享最终规范关键词数量", fill=(92, 103, 120, 255), font=font(22))
    draw.text((s_x - 20, 180), "科学社区", fill=science_color, font=font(28))
    draw.text((p_x - 20, 180), "政策社区", fill=policy_color, font=font(28))

    # Position nodes. This period has one merged science community and two policy communities.
    s_pos = {}
    p_pos = {}
    for i, r in enumerate(sorted(science, key=lambda x: int(x["Community"]))):
        y = s_y + (i - (len(science) - 1) / 2) * 120
        s_pos[r["NodeId"]] = (s_x, y)
    for i, r in enumerate(sorted(policy, key=lambda x: int(x["Community"]))):
        y = p_y + (i - (len(policy) - 1) / 2) * 160
        p_pos[r["NodeId"]] = (p_x, y)

    for r in flows:
        sx, sy = s_pos[r["ScienceNodeId"]]
        px, py = p_pos[r["PolicyNodeId"]]
        value = int(r["Value"])
        width = max(12, value * 10)
        pts_top = []
        pts_bottom = []
        bend = (px - (sx + node_w)) * 0.43
        for i in range(31):
            t = i / 30
            top = cubic((sx + node_w, sy - width / 2), (sx + node_w + bend, sy - width / 2), (px - bend, py - width / 2), (px, py - width / 2), t)
            bottom = cubic((sx + node_w, sy + width / 2), (sx + node_w + bend, sy + width / 2), (px - bend, py + width / 2), (px, py + width / 2), t)
            pts_top.append((round(top[0]), round(top[1])))
            pts_bottom.append((round(bottom[0]), round(bottom[1])))
        draw.polygon(pts_top + list(reversed(pts_bottom)), fill=link_color)
        mid_x = (sx + px) / 2
        mid_y = (sy + py) / 2 - width / 2 - 14
        draw.text((mid_x, mid_y), f"共享关键词：{value}", fill=(76, 87, 103, 255), font=font(20), anchor="mm")

    for r in science:
        x, y = s_pos[r["NodeId"]]
        draw.rounded_rectangle([x, y - 28, x + node_w, y + 28], radius=5, fill=science_color, outline=(255, 255, 255, 255), width=2)
        draw.text((x - 18, y - 22), f"C{r['Community']}  {r['CommunityName']}", fill=(35, 44, 60, 255), font=font(25), anchor="rm")
        draw.text((x - 18, y + 13), f"关键词节点：{r['NodeCount']}", fill=(105, 114, 129, 255), font=font(17), anchor="rm")
    for r in policy:
        x, y = p_pos[r["NodeId"]]
        draw.rounded_rectangle([x, y - 28, x + node_w, y + 28], radius=5, fill=policy_color, outline=(255, 255, 255, 255), width=2)
        draw.text((x + node_w + 18, y - 22), f"C{r['Community']}  {r['CommunityName']}", fill=(35, 44, 60, 255), font=font(25), anchor="lm")
        draw.text((x + node_w + 18, y + 13), f"关键词节点：{r['NodeCount']}", fill=(105, 114, 129, 255), font=font(17), anchor="lm")

    keywords = flows[0]["SharedKeywords"] if flows else ""
    draw.text((90, 900), "共享关键词：", fill=(28, 37, 54, 255), font=font(22))
    draw.multiline_text((90, 945), keywords.replace(";", "、"), fill=(92, 103, 120, 255), font=font(20), spacing=10)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(OUT, quality=95)
    print(OUT)


if __name__ == "__main__":
    main()
