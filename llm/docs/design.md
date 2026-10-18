# 设计说明

这份文档回答三个「助教必问」的问题，并给出每个模块的职责边界。代码按 **容错层 → 规则层 → 传输层 → 编排层**
自底向上依赖，上层只信任下层给出的结构化结果。

```
                ┌────────────────────────────────────────────────┐
stdin 一行 ───► │ app.handle_line                                │
                │   ├─ rules.parse_request      坏输入不转发上游  │
                │   └─ app.handle_request                        │
                │        ├─ client.decide       重试 / 取 content │
                │        ├─ json_guard.loads_object   三级容错    │
                │        ├─ rules.validate_decision   字段闸门    │
                │        └─ rules.fallback_decision   本地兜底    │
                └────────────────────────────────────────────────┘
                                    │
                             stdout 一行 {time, option}
```

## 1. 为什么容错要分「剥围栏 / 括号配对 / 文本修复」三级？

`json.loads` 只接受**严格合法**的 JSON。而模型的实际输出是「看起来像 JSON 的文本」，典型偏差有：

| 偏差 | 例子 | 单靠 `json.loads` |
| --- | --- | --- |
| markdown 围栏 | ```` ```json\n{...}\n``` ```` | 直接抛 `JSONDecodeError` |
| 前后夹带自然语言 | `好的，我出剪刀：{"option": "scissor"}` | 抛异常 |
| 单引号 / Python 字面量 | `{'option': 'rock', 'x': None}` | 抛异常 |
| 尾随逗号 | `{"option": "rock",}` | 抛异常 |
| 被截断 | `{"option": "rock"` | 抛异常 |

三级容错各自解决一类问题，且**每一级都是幂等的**（失败就交给下一级）：

1. **剥围栏**（`strip_code_fence`）：只处理"外面裹了什么"，解决 markdown 与自然语言包裹；
2. **括号配对**（`find_first_json_object`）：从自由文本中切出**配平**的 `{...}`，且必须**字符串感知**
   —— `{"reason": "a } b"}` 里的 `}` 不是对象结束，`\"` 也不结束字符串；
3. **文本修复**（`repair_json_text`）：去注释 → Python 字面量转 JSON → 去尾随逗号 → 引号归一化
   → 补右引号/右括号。

**为什么不用 `eval` / `ast.literal_eval` 一步到位？** 模型输出是不可信输入。`eval` 等于把执行权
交给上游（甚至是一次提示词注入）；`literal_eval` 也只在"碰巧是合法 Python 字面量"时有效，且同样是
"黑盒猜测"。文本级修复每一步都能解释清楚改了什么，失败也能给出可读原因（`JsonGuardError` 里带
最后一次解析错误），方便排障。

三级之后仍然失败 → **不猜**，直接交给兜底出拳。容错不等于瞎猜：这里只负责"把明显是 JSON 的文本
救回来"，字段缺失、取值非法是 `rules` 的事，两个阶段职责分开。

## 2. 哪些错误要重试，哪些必须立刻失败？

| 情况 | 处理 | 理由 |
| --- | --- | --- |
| 连接超时 / DNS 失败 / 连接重置 | 退避重试 | 网络抖动，重试常能成功 |
| HTTP 429 | 听 `Retry-After`，否则指数退避 | 限流是临时的，立刻重试只会继续被限 |
| HTTP 408/409/425/5xx | 退避重试 | 服务端临时不可用 |
| HTTP 200 但 `content` 为空 / 只有 `reasoning_content` / `finish_reason=length` | 重试 | 采样偶然性，重试可能拿到正常回复 |
| HTTP 400（模型名 / 参数错） | **立刻失败** | 请求本身有问题，重试结果一样 |
| HTTP 401/403（Key 错 / 无权限） | **立刻失败** | 重试无意义，还会拉长排障时间 |
| 其它 4xx（404/422…） | **立刻失败** | 通常是地址或参数配错 |

退避公式：`min(backoff_base * 2^(attempt-1), backoff_max) + jitter`，默认
`base=0.5s`、`cap=4s`、`max_retries=2`（即最多 3 次请求）。`Retry-After` 优先，但仍受 `backoff_max` 限制。

`extract_content` 把三类"200 但没答案"的情况分开报错，因为它们对应不同的修法：

- **只有 `reasoning_content`**：思维链不是答案，说明模型把 token 全花在思考上 → 关掉 thinking 或调大 `max_tokens`；
- **`finish_reason=length`**：被 `max_tokens` 截断 → 调大 `max_tokens`；
- **`content` 为空**：上游异常 → 重试或换模型。

## 3. 为什么输出的 `time` 用请求里的，而不是模型返回的？

`time` 是对局的**关联键**：下游用它把"这一轮请求"和"这一轮决策"对上。模型没有时钟，
它写的 `time` 是**根据输入复述或臆造**的（README 的场景 9 就是模型返回 1999 年的时间）。
如果采信模型，快照对不上、回放错位，而且给了模型一个"篡改协议"的入口。

因此网关是**可信边界**：

```
请求有 time  → 用请求的；若模型写了不同的 time，记一条「丢弃模型的 time」
请求无 time  → 用模型给的（并记「请求无 time->用模型的 time」）
都没有      → now_iso()（并记「请求无 time->用当前时间」）
```

同理，模型的 `extra` / `reason` / `confidence` 等字段全部丢弃，出口只保留 `time` 与 `option`
（`build_decision` + `is_valid_decision` 双重保证）。`history` 也是不可信输入，只用 `normalize_option`
过滤出合法出拳后再给兜底策略用。

## 模块职责

| 模块 | 只做这件事 | 不做的事 |
| --- | --- | --- |
| `json_guard` | 文本 → `dict` | 不判断字段对错 |
| `rules` | 字段归一化 / 兜底 / 胜负判定 | 不发网络请求 |
| `client` | 组装请求、鉴权、重试、取 `content` | 不解析业务字段 |
| `app` | 编排、统计、异常兜底 | 不关心 HTTP 细节 |

## 异常漏斗（为什么 `handle_request` 永不抛异常）

```
client.decide      → LlmAuthError / LlmFatalError / LlmError / requests.*
loads_object       → JsonGuardError
validate_decision  → 不抛：一律 (决策, 说明)
fallback_decision  → 不抛：没有历史也给 rock
is_valid_decision  → 出口最后一道闸门，失败退化为 {now_iso(), rock}
```

`run()` 里还有最后一道 `except Exception`：即使前面全崩，也写一行
`{"time": <now>, "option": "rock"}`。这叫**fail-closed 到合法值**——下游消息总线的约束是
"必须是合法 JSON"，而不是"必须来自模型"。
