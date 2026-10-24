"""检查 Markdown 里的相对链接是否都指向真实文件（防止改名后留下死链）。"""
import glob
import io
import os
import re
import sys

LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")


def strip_code(text: str) -> str:
    """代码块/行内代码里的 "链接" 不是链接，先挖掉。"""
    text = FENCE.sub("", text)
    text = INLINE_CODE.sub("", text)
    return text

files = sorted(glob.glob("**/*.md", recursive=True))
bad = []
total = 0
for path in files:
    base = os.path.dirname(path)
    text = strip_code(io.open(path, encoding="utf-8").read())
    for target in LINK.findall(text):
        if target.startswith(("http://", "https://", "mailto:", "<")):
            continue
        total += 1
        resolved = os.path.normpath(os.path.join(base, target))
        if not os.path.exists(resolved):
            bad.append((path, target, resolved))

print(f"markdown files={len(files)}  relative links={total}")
for path, target, resolved in bad:
    print(f"MISSING  {path}  ->  {target}   (resolved: {resolved})")
print("ALL LINKS OK" if not bad else f"BROKEN: {len(bad)}")
sys.exit(1 if bad else 0)
