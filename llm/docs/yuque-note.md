# LLM 实践任务：石头剪刀布决策网关

> 这是一篇可以直接粘贴到语雀的笔记草稿。发布前请：
> 1. 把 `【截图：…】` 换成你自己的截图（终端输出、代码、测试结果）；
> 2. 把末尾「真实 API 联调」一节的输出换成你自己机器上的实际结果；
> 3. 在文末补上仓库链接。

## 0. 一句话总结

写一个**网关**：把一行 JSON 请求转发给 DeepSeek 官方 API，再把模型返回的**任意文本**整理成
**一行严格合法的 JSON**。核心不是「调用 API」，而是**不可信输出的容错**与**永不崩溃的兜底**。

协议：

```text
输入  {"time": "2026-01-01T00:00:00+00:00", "history": ["rock", "paper"]}   # history 可选
输出  {"time": "2026-01-01T00:00:00+00:00", "option": "rock"}              # 只允许这两个键
```

## 1. 我在这个任务里学到了什么

| 概念 | 我的理解 |
| --- | --- |
| 网关（gateway） | 本地程序与外部模型之间的适配层：把请求整理成 API 要的格式，把响应整理成本地要的格式 |
| Agent | LLM 是"大脑"，Agent 是"手脚"：能自己找目录、读写文件、把上一步输出变成下一步输入 |
| 不可信输入 | 模型输出、`history`、模型自报的 `time` 全都不可信，必须在网关这一层做最终裁决 |
| fail-closed | 出错时不是抛异常，而是退化到一个**合法**的值（`{"time": …, "option": "rock"}`） |

## 2. 环境准备

```bash
git clone https://github.com/hitxxxx/HelloCV.git
cd HelloCV/llm
python -m venv .venv && . .venv/Scripts/activate     # Linux: source .venv/bin/activate
pip install -r requirements.txt
```

【截图：pip install 完成】

领 Key 并充值 1 元后，把 Key 放进环境变量（**不写进代码**）：

```powershell
$env:DEEPSEEK_API_KEY="sk-..."     # Linux/macOS: export DEEPSEEK_API_KEY=sk-...
```

【截图：环境变量已设置（Key 打码）】

## 3. 和 AI 协作的过程

任务书说「建议大大方方使用 agent」，我的做法不是让它"帮我写一个网关"，而是**先自己读测试**，
再用 AI 讨论设计、由测试来判定对错。

1. **先跑 baseline**：`python selfcheck.py` 列出 10 个 `NotImplementedError`；此时 93 个测试全红。
2. **读测试反推契约**：比如 `test_validate_decision_request_time_wins` 里
   `assert "丢弃模型的 time" in notes` —— 这里的 `in` 是**列表元素精确匹配**，不是子串，
   所以说明文案必须一字不差。这个坑我踩了一次，改完测试才绿。
3. **按依赖顺序实现**：`json_guard`（纯文本处理，最好测）→ `rules`（纯逻辑）→
   `client`（HTTP + 重试）→ `app`（编排）。每实现一个函数就单独跑对应测试文件。
4. **让 AI 解释而不是代写**：对 `find_first_json_object` 的字符串状态机、`decide` 的重试分支，
   我让它逐行讲状态怎么变，再自己重写一遍，确保助教问起来答得上。
5. **用假上游做压力测试**：`mock_llm_server.py` 预设了 12 种坏回复（围栏、废话、`SPOCK`、
   空回复、缺括号……），跑一遍就知道容错到底有没有生效。

【截图：selfcheck 列出 10 个 TODO】

## 4. 核心设计

### 4.1 四层结构

```text
app.handle_request   编排：一行进一行出，永不抛异常
├── client.decide    传输：组装请求、鉴权、分类重试、只取 content
├── json_guard       容错：文本 → dict（三级阶梯）
├── rules            规则：枚举归一化、time 归属、兜底、裁判
└── rules.fallback   兜底：上游彻底失败也能出一手
```

分层的好处是**每层都能单独测**：容错层是纯字符串函数，传输层用 `FakeSession` 注入响应，
编排层用 `ScriptedClient` 注入任意异常，整条链路再用本地假上游跑真 HTTP。

### 4.2 三级 JSON 容错

```python
# 1) 剥 markdown 围栏：split("```") 后取下标 1、3、5…，丢掉 json/JSON 这样的语言标记行
# 2) 字符串感知的括号配对：维护 depth / in_string / escaped
# 3) 文本级修复：去注释 → None/True/False → 尾随逗号 → 引号归一化 → 补右括号
```

为什么不用 `eval`？模型输出是不可信输入，`eval` 等于把执行权交出去；而且文本级修复每一步都
能解释，失败时还能给出可读原因。

### 4.3 重试要分类

```python
if status in (401, 403):  raise LlmAuthError(...)   # Key 错，立刻失败
if status == 400:         raise LlmFatalError(...)  # 模型名/参数错，立刻失败
if status in RETRY_STATUS: 退避重试                 # 429 / 5xx
# 200 但 content 为空 / 只有 reasoning_content / finish_reason=length → 也重试
```

退避：`min(0.5 * 2^(n-1), 4) + jitter`，`Retry-After` 优先。

### 4.4 time 以请求为准

模型没有时钟，它返回的 `time` 是复述或臆造（假上游第 9 条场景就返回 1999 年）。
`time` 是对局的关联键，必须由网关这个**可信边界**裁决：请求有就用请求的，没有才用模型的，
再没有才用 `now_iso()` —— 每种情况都记一条说明，方便事后复盘。

【截图：json_guard.py / rules.py 的关键代码，带注释】

## 5. 踩坑记录

| # | 坑 | 现象 | 解决 |
| --- | --- | --- | --- |
| 1 | 测试的 `in notes` 是元素精确匹配 | 我写「丢弃模型的 time（模型=…）」被判失败 | 说明文案与测试约定的字符串一字不差 |
| 2 | 空回复不能直接兜底 | 假上游第 10 条空回复若直接兜底，就浪费了一次重试机会 | 把空回复当**可重试错误**，重试后往往就正常了 |
| 3 | 思维链不是答案 | `reasoning_content` 里也写着 `{"option":"rock"}` | 只取 `content`；只有思维链时单独报错 |
| 4 | `finish_reason=length` 是另一类失败 | 与"空回复"混成一个错误，无法对症下药 | 分开报错，提示调大 `max_tokens` |
| 5 | 坏输入不该转发上游 | 非 JSON 行也发请求，既花钱又污染日志 | `handle_line` 先解析，失败直接本地兜底 |
| 6 | 字符串里的 `}` 会骗过括号配对 | `{"reason": "a } b"}` 被提前截断 | 维护 `in_string` / `escaped` 状态 |
| 7 | 出口字段会"漏" | 模型多返回 `reason`、`confidence` | `build_decision` 只构造两个键 + `is_valid_decision` 自检 |

【截图：pytest 93 passed】

## 6. 联调结果

### 6.1 离线兜底（不花钱，先验证协议）

```text
$ printf '%s\n' '{"time":"t1"}' '{"time":"t2","history":["rock"]}' | python run_gateway.py --offline --quiet
{"time":"t1","option":"rock"}
{"time":"t2","option":"paper"}
```

有历史时出「能赢对手上一手」的拳：上一手 `rock` → 出 `paper`。

### 6.2 假上游：12 种坏回复全接住

```text
$ python mock_llm_server.py --port 8801 &
$ python run_gateway.py --api-base-url http://127.0.0.1:8801 --api-key test \
        --input samples/requests.jsonl --quiet
{"time":"2026-01-01T00:00:00+00:00","option":"rock"}
{"time":"2026-01-01T00:00:01+00:00","option":"scissor"}
{"time":"2026-01-01T00:00:02+00:00","option":"scissor"}
{"time":"2026-01-01T00:00:03+00:00","option":"rock"}
...
处理 7 行：直接可用 3 / 已修正 1 / 本地兜底 3 / 输入非法 1
```

【截图：假上游联调输出（含统计行）】

### 6.3 完整对局（假上游，10 轮）

```text
$ python play_game.py --rounds 10 --api-base-url http://127.0.0.1:8801 --api-key test --seed 7
共 10 轮：模型赢 2 / 平 4 / 输 4（其中本地兜底 0 轮）
```

【截图：对局输出】

### 6.4 真实 DeepSeek 官方 API

```text
$ $env:DEEPSEEK_API_KEY="sk-..."     # 已充值 1 元
$ python play_game.py --rounds 10 --strategy counter
【截图：真实 API 对局输出】
```

> 说明：默认模型 `deepseek-flash`，`temperature=0.2`，`max_tokens=256`，
> `response_format={"type":"json_object"}`，`thinking={"type":"disabled"}`（省时间、省 token）。

## 7. 如果继续做（扩展思路）

- 给 `GatewayConfig` 加 `deadline`：上游超过 N 秒没回就放弃并兜底；
- 支持并发调用多行（注意保持输出顺序、不要打爆限流）；
- `history` 从"对手历史"扩展成"双方历史"，让提示词做频率分析；
- 增加指标：`ok / repaired / fallback` 比例，导出成一行报告。

## 8. 仓库

- 代码：<https://github.com/hitxxxx/HelloCV>（`llm/` 目录）
- 本文档同步一份在仓库 `llm/docs/yuque-note.md`
