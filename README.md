# HelloCV

本仓库用于记录 **Linux 学习与实践**、**ROS2 环境配置**，以及创新平台培训的实践任务
（第二次任务 · LLM 部分见 [`llm/`](llm/)）。

## 目录结构

```text
HelloCV/
├── README.md              # 本文件：项目说明 + 语雀笔记汇总
└── llm/                   # 第二次任务 · LLM 实践任务：石头剪刀布决策网关
    ├── gateway/           #   网关核心：JSON 容错 / 规则 / 上游转发 / 编排
    ├── tests/             #   93 个测试
    ├── docs/              #   任务书、设计说明、语雀笔记草稿
    ├── run_gateway.py     #   一行 JSON 进、一行 JSON 出
    ├── play_game.py       #   和本地对手打 N 轮
    └── mock_llm_server.py #   本地假上游（故意返回坏数据）
```

## 第二次任务 · LLM：石头剪刀布决策网关

把一行 JSON 请求转发给 **DeepSeek 官方 API**，再把模型返回的任意文本整理成一行严格合法的
JSON 决策（`{"time": …, "option": "rock|scissor|paper"}`）。重点是**不可信输出的容错**与
**永不崩溃的兜底**。

```bash
cd llm
pip install -r requirements.txt
export DEEPSEEK_API_KEY=sk-...          # PowerShell: $env:DEEPSEEK_API_KEY="sk-..."
python selfcheck.py                     # 93 passed
python play_game.py --rounds 10         # 和 DeepSeek 玩 10 轮
```

- 详细说明：[`llm/README.md`](llm/README.md)
- 设计说明（三级容错 / 重试分类 / time 归属）：[`llm/docs/design.md`](llm/docs/design.md)
- 语雀笔记草稿：[`llm/docs/yuque-note.md`](llm/docs/yuque-note.md)

## 环境与工具链记录

- ROS2：使用一键脚本安装
- 基础工具：`sudo apt install nmap ssh git ...`
- Node.js 与 PM2：`sudo apt install nodejs npm` ...

## 语雀笔记汇总

| 笔记 | 链接 |
| --- | --- |
| Linux 学习与实践记录 | <https://www.yuque.com/g/yuqueyonghu-8qsy6m/vkceqs/collaborator/join?token=agDjvvPviBf3dKcU> |
| 《git traning》 | <https://www.yuque.com/yuqueyonghu-8qsy6m/dgvebc/> |
| LLM 实践任务：决策网关实现笔记 | <https://www.yuque.com/>（发布后替换为你的链接） |
