# -*- coding: utf-8 -*-
"""把七篇笔记合并成"一篇看完"的语雀文档。

为什么要合并：语雀里发七篇要点七次"新建 → 粘贴 → 设权限"，
而任务只要求"至少一篇公开可访问"。合并成一篇，粘一次就够；
每篇的「0. 一句话总结 / 踩坑 / 验收清单」都保留，读起来仍然是一个个小节。

规则：
- 文档标题是 H1，七篇正文变成 H2（"第 N 篇 · ..."），篇内标题整体降一级；
- **只降代码块之外的标题**（`# 1) xxx` 这种写在 bash 里的注释不能动）；
- 每篇开头那段 `> **环境与验证状态**…` 只保留一次（放在文首），其余删掉；
- 00 索引里"一句话总结 / 三张示意图 / 关于实操记录 / 仓库入口"变成附录，其余（给读者看的跳转表）不要。
"""
import io
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # HelloCV/ros2/
YUQUE = ROOT / "docs" / "yuque"
OUT = ROOT / "docs" / "ROS2学习笔记-全一篇.md"

ORDER = [
    "01-工作空间与包结构.md",
    "02-C++节点与生命周期.md",
    "03-命令行工具实操.md",
    "04-Topic与QoS.md",
    "05-Service与参数.md",
    "06-TF与RViz.md",
    "07-launch文件.md",
]
NUM = "一二三四五六七"


def strip_banner(lines: list[str]) -> list[str]:
    """删掉开头的 `> **环境与验证状态**…` 引用块。"""
    out, i = [], 0
    if lines and lines[0].startswith("> **环境与验证状态**"):
        while i < len(lines) and (lines[i].startswith(">") or lines[i] == ""):
            # 引用块结束在第一个空行的后面
            if lines[i] == "":
                i += 1
                break
            i += 1
    return out + lines[i:]


def demote_headings(text: str) -> str:
    """代码块外的 `#` 标题整体降一级。"""
    out, in_fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if not in_fence:
            m = re.match(r"^(#{1,5})(\s)", line)
            if m:
                line = "#" + line
        out.append(line)
    return "\n".join(out)


def section(text: str, title: str) -> str:
    """取 `## title` 到下一个同级标题之间的正文。"""
    lines = text.split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "## " + title:
            start = i + 1
            break
    if start is None:
        raise SystemExit(f"找不到小节: {title}")
    end = len(lines)
    for j in range(start, len(lines)):
        if re.match(r"^#{1,2}\s", lines[j]):
            end = j
            break
    body = "\n".join(lines[start:end]).strip("\n")
    return demote_headings(body)


def main() -> None:
    idx = io.open(YUQUE / "00-索引与阅读顺序.md", encoding="utf-8").read()

    parts = [
        "# HelloCV · ROS 2 学习笔记",
        "",
        "> 这是 HelloCV 仓库第三次任务（ROS 2）的完整笔记：把七个学习点（工作空间与包、节点与生命周期、"
        "命令行工具、Topic 与 QoS、Service 与参数、TF 与 RViz、launch）串成一条**能跑通的视觉流水线**。",
        "> 环境是 Ubuntu 22.04.5 + ROS 2 Humble，文中所有截图、终端输出都是真机跑出来的（2026-10-24）。",
        "",
        "## 目录",
        "",
    ]
    for i, name in enumerate(ORDER):
        title = io.open(YUQUE / name, encoding="utf-8").readline().lstrip("# ").strip()
        title = re.sub(r"^0?\d+\s*[·:]?\s*", "", title)     # 去掉行首的编号
        parts.append(f"{i + 1}. 第{NUM[i]}篇 · {title}")
    parts += ["", "附录 A · 实操记录与验证", "", "附录 B · 仓库结构与入口", "", "---", ""]

    parts += ["## 这次做了什么", "", demote_headings(section(idx, "一句话总结这次做了什么")), "", "---", ""]

    for i, name in enumerate(ORDER):
        raw = io.open(YUQUE / name, encoding="utf-8").read().split("\n")
        title = raw[0].lstrip("# ").strip()
        title = re.sub(r"^0?\d+\s*[·:]?\s*", "", title)
        body_lines = raw[1:]
        while body_lines and not body_lines[0].strip():      # 跳过 H1 后面那几行空行
            body_lines.pop(0)
        body = "\n".join(strip_banner(body_lines))
        body = demote_headings(body).strip("\n")
        body = re.sub(r"^##\s", "## ", body)
        parts += [f"## 第{NUM[i]}篇 · {title}", "", body, "", "---", ""]

    parts += ["## 附录 A · 实操记录与验证", "", "### 关于实操记录（重要）", ""]
    parts += [section(idx, "关于实操记录（重要）"), "", "### 三张示意图", "", section(idx, "三张示意图"), "", "---", ""]
    parts += ["## 附录 B · 仓库结构与入口", "", section(idx, "仓库入口"), ""]

    text = "\n".join(parts)
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    # 跨篇链接在"全一篇"里没有意义：`[04](...yuque/04-Topic与QoS.md)` → `第四篇`
    def drop_cross(m: re.Match) -> str:
        return f"第{NUM[int(m.group(1)) - 1]}篇"

    text = re.sub(
        r"\[(0[1-7])(?:\s*篇)?\]\(https://github\.com/hitxxxx/HelloCV/blob/main/ros2/docs/yuque/[^)]*\)",
        drop_cross, text,
    )
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)

    n_lines = text.count("\n") + 1
    n_heads = len(re.findall(r"^#{1,2} ", text, flags=re.M))
    n_img = len(re.findall(r"!\[", text))
    n_code = text.count("```") // 2
    print(f"输出: {OUT}")
    print(f"行数 {n_lines} / 字符 {len(text)} / 一级二级标题 {n_heads} / 图片 {n_img} / 代码块 {n_code}")


if __name__ == "__main__":
    main()
