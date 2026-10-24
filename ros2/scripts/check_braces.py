"""静态检查：C++ 源码的括号配平（本机无编译器，只能做这种粗糙的自检）。"""
import glob
import io
import re
import sys

TARGETS = sorted(
    glob.glob("ros2_ws/src/**/*.cpp", recursive=True)
    + glob.glob("ros2_ws/src/**/*.hpp", recursive=True)
)

STR = re.compile(r'"(?:\\.|[^"\\])*"')
CHR = re.compile(r"'(?:\\.|[^'\\])*'")
LINE_COMMENT = re.compile(r"//[^\n]*")
BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)


def strip(src: str) -> str:
    src = BLOCK_COMMENT.sub("", src)
    src = LINE_COMMENT.sub("", src)
    src = STR.sub('""', src)
    src = CHR.sub("''", src)
    return src


bad = []
for path in TARGETS:
    text = strip(io.open(path, encoding="utf-8").read())
    o, c = text.count("{"), text.count("}")
    p, q = text.count("("), text.count(")")
    ok = (o == c and p == q)
    if not ok:
        bad.append(path)
    print(f"{'ok  ' if ok else 'BAD '} {path}  braces={o}/{c} parens={p}/{q}")

print()
print(f"files={len(TARGETS)} unbalanced={len(bad)}")
sys.exit(1 if bad else 0)
