# -*- coding: utf-8 -*-
"""把笔记整理成"可以直接粘进语雀"的样子。

问题：笔记里用的是相对路径（`../screenshots/xx.png`、`[01](01-xxx.md)`），
在 GitHub 上没问题，但**粘进语雀之后图片和互链全都会断**。

做法：把所有图片/互链换成 GitHub 的绝对地址——
  - 图片、附件 → raw.githubusercontent（Yuque 会直接抓取远程图片）
  - 跨笔记链接 → github.com/blob
两种地址在 GitHub 上照样能渲染，所以一份文件同时满足仓库阅读和语雀粘贴。
"""
import io
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]          # HelloCV/
YUQUE = ROOT / "ros2" / "docs" / "yuque"

REPO = "hitxxxx/HelloCV"
BRANCH = "main"
BLOB = f"https://github.com/{REPO}/blob/{BRANCH}/"
# 图片走 jsDelivr：它在中国大陆也能直连，语雀抓取时不会因为 raw.githubusercontent 被墙而丢图
RAW = f"https://cdn.jsdelivr.net/gh/{REPO}@{BRANCH}/"

RAW_DIRS = {
    "../screenshots/": f"{RAW}ros2/docs/screenshots/",
    "../figures/": f"{RAW}ros2/docs/figures/",
    "../../docs/screenshots/": f"{RAW}ros2/docs/screenshots/",
    "../../docs/figures/": f"{RAW}ros2/docs/figures/",
}

BLOB_TARGETS = {
    "../verify-transcript.txt": f"{BLOB}ros2/docs/verify-transcript.txt",
    "../screenshots/README.md": f"{BLOB}ros2/docs/screenshots/README.md",
}


def encode_tail(url: str) -> str:
    """只对路径里的中文做百分号编码，保留 http(s):// 与已编码部分。"""
    if not url.startswith("http"):
        return url
    for scheme in ("https://", "http://"):
        if url.startswith(scheme):
            rest = url[len(scheme):]
            head, _, tail = rest.partition("/")
            return scheme + head + "/" + quote(tail, safe="/#?=&%:@!$'()*+,;~")
    return url


def convert(text: str, note_names: list[str]) -> str:
    import posixpath

    # 0) 通用兜底：任何以 .md / .txt / .png 结尾的相对链接，都按"相对本文件"解析成仓库绝对地址
    def absolutize(m: re.Match) -> str:
        label, target = m.group(1), m.group(2)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return m.group(0)
        path, _, anchor = target.partition("#")
        if not path:
            return m.group(0)
        repo_path = posixpath.normpath(posixpath.join("ros2/docs/yuque", path))
        if repo_path.startswith("../"):
            return m.group(0)          # 跑到仓库外面了，不动
        base = RAW if path.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")) else BLOB
        url = encode_tail(base + repo_path) + ("#" + anchor if anchor else "")
        return "[" + label + "](" + url + ")"

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", absolutize, text)
    return text


def main() -> None:
    names = sorted(p.name for p in YUQUE.glob("*.md"))
    for name in names:
        path = YUQUE / name
        text = io.open(path, encoding="utf-8").read()
        new = convert(text, names)
        if new != text:
            io.open(path, "w", encoding="utf-8", newline="\n").write(new)
            print(f"  已转换: {name}")
        else:
            print(f"  无变化: {name}")


if __name__ == "__main__":
    main()
