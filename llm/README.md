# 石头剪刀布决策网关（LLM 实践任务）

把**一行 JSON 请求**转发给大模型，再把模型返回的**任意文本**整理成**一行严格合法的 JSON**。

```
stdin  ──► 解析请求 ──► 组装 Chat Completions ──► DeepSeek 官方 API
                                                        │
stdout ◄── {time, option} ◄── 出口自检 ◄── 校验/兜底 ◄── JSON 容错 ◄── 模型原文
```

不变式只有一条：**一行进、一行出**。坏输入、上游挂掉、模型胡说、返回空回复，
都必须回一行合法 JSON，且 `option` 只能是 `rock` / `scissor` / `paper`。

## 功能一览

| 能力 | 说明 |
| --- | --- |
| 协议严格 | 输出恰好 `{time, option}` 两个键，多余字段一律丢弃 |
| 三级 JSON 容错 | 剥 markdown 围栏 → 字符串感知括号配对 → 文本级修复（单引号/尾逗号/注释/裸换行/缺括号） |
| 分类重试 | 429/5xx/网络错误/空回复退避重试；401/403/400 立刻失败，不浪费额度 |
| 只取 content | 明确丢弃 `reasoning_content`（思维链不是答案） |
| 兜底出拳 | 上游彻底失败时用本地策略：反制对手上一手，没有历史则出 `rock` |
| 可观测 | 每行日志带修正说明，跑完输出 `ok / repaired / fallback / bad_input` 统计 |

## 目录结构

```
llm/
├── gateway/                 # 网关核心（本次实现的部分）
│   ├── json_guard.py        # ① 容错层：把任意文本整理成 dict
│   ├── rules.py             # ② 规则层：枚举归一化、time 归属、兜底、裁判
│   ├── client.py            # ③ 传输层：请求体、鉴权、重试、取 content
│   ├── app.py               # ④ 编排层：一行进一行出，永不抛异常
│   ├── config.py            #    配置（脚手架）
│   ├── prompts.py           #    系统提示词（脚手架）
│   └── game.py              #    对局逻辑（脚手架）
├── tests/                   # 93 个测试（脚手架，用来验收实现）
├── samples/requests.jsonl   # 样例输入（含坏输入）
├── run_gateway.py           # CLI：文件/管道进，文件/管道出
├── play_game.py             # CLI：和本地对手打 N 轮
├── mock_llm_server.py       # 本地假上游：故意返回 12 种坏回复
├── selfcheck.py             # 自检：列 TODO + 跑测试
├── docs/
│   ├── task-book.md         # 原任务书（skeleton README）
│   ├── design.md            # 设计说明：三级容错 / 重试分类 / time 归属
│   └── yuque-note.md        # 语雀笔记草稿（提交用）
├── requirements.txt
└── .env.example
```

## 环境准备

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

配置 API Key（**不要写进代码**，`.env` 与 `*.key` 都已在 `.gitignore` 里）：

```bash
export DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx        # Windows PowerShell: $env:DEEPSEEK_API_KEY="sk-..."
```

## 快速开始

```bash
# 1) 离线：完全不调用 API，先确认流水线通
echo '{"time": "2026-01-01T00:00:00+00:00"}' | python run_gateway.py --offline
# {"time":"2026-01-01T00:00:00+00:00","option":"rock"}

# 2) 假上游：不花钱、结果可复现，专门用来验证容错
python mock_llm_server.py --port 8801 &
python run_gateway.py --api-base-url http://127.0.0.1:8801 --api-key test \
       --input samples/requests.jsonl

# 3) 真实 DeepSeek API
python run_gateway.py --input samples/requests.jsonl
python play_game.py --rounds 10 --strategy counter

# 4) 文件进文件出
python run_gateway.py --input samples/requests.jsonl --output decisions.jsonl

# 5) 验收
python selfcheck.py          # 应为「所有 TODO 都实现完了」+ 93 passed
```

## 协议

| | 内容 |
| --- | --- |
| 输入 | `{"time": "<本轮时间>", "history": ["rock", "paper"]}`，`history` 可选 |
| 输出 | `{"time": "<与输入一致>", "option": "rock\|scissor\|paper"}`，只允许这两个键 |

胜负：`rock` 赢 `scissor`，`scissor` 赢 `paper`，`paper` 赢 `rock`。

## 设计要点

1. **容错分三级，而不是只靠 `json.loads`**：真实模型会套 markdown 围栏、夹带自然语言、
   写单引号/尾逗号/Python 的 `None`、被 `max_tokens` 截断少一个 `}`。每一级只做文本层面
   的、可解释的修复，失败就降级，绝不用 `eval` / `ast.literal_eval` 去"救"不可信输入。
2. **重试要分类**：429/5xx/连接超时/空回复值得指数退避重试；401/403（Key 错）、400（模型名
   或参数错）重试一万次也一样，必须立刻失败——既省钱也省排障时间。
3. **`time` 以请求为准**：模型自报的时间不可信，网关是做最终裁决的可信边界；请求没有 `time`
   才退而用模型的，再没有就用当前时间。
4. **思维链不是答案**：思考模型会同时返回 `reasoning_content`（甚至里面就写着一个"答案"），
   网关只取 `content`，并把"只有思维链"与"空回复"、"被截断"区分成不同错误。

详细拆解见 [`docs/design.md`](docs/design.md)。

## 测试

```bash
python -m pytest tests -q     # 93 passed
python selfcheck.py           # TODO 检查 + 全套测试
```

覆盖四层：容错层 20 个、规则层 25 个、传输层 17 个、编排层 15 个（含真 HTTP 端到端），
另有对局逻辑与采样一致性测试。

## 常见问题

| 现象 | 原因 / 处理 |
| --- | --- |
| `LlmAuthError: 未配置 API Key` | 没设 `DEEPSEEK_API_KEY`，或 `--api-key` 为空 |
| `HTTP 400 Model Not Exist` | `--model` 写错；默认 `deepseek-flash` |
| 大量 `本地兜底` | 看 stderr 的 `上游异常` / `模型输出无法整理成 JSON` 说明 |
| 回复被截断 | 调大 `--max-tokens`，或保持 `thinking=disabled` |
| 想复现某次对局 | `play_game.py --seed 42` |

## 语雀文档

- [LLM 实践任务：决策网关实现笔记（语雀）](https://www.yuque.com/)   ← 占位，发布后替换为你的链接
- 原任务书见 [`docs/task-book.md`](docs/task-book.md)
