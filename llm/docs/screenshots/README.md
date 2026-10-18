# 截图说明

这 5 张图是把**真实运行的终端输出**按终端风格渲染出来的（等宽字体 + 窗口边框），
内容与 `tools/cap/*.txt` 里记录的实际输出一致，没有改动任何数据；长行按终端习惯折行，
测试列表中间省略的部分已用 `……（中间 N 条，此处省略）……` 明确标注。

想自己重截一遍，按下面命令跑即可

| 图 | 命令 | 说明 |
| --- | --- | --- |
| `01-selfcheck-todo.png` | `python selfcheck.py`（未实现的 skeleton） | 列出 10 个待实现函数 |
| `02-mock-upstream.png` | `python mock_llm_server.py --port 8801` + `python run_gateway.py --api-base-url http://127.0.0.1:8801 --api-key test --input samples/requests.jsonl` | 12 种坏回复逐条被接住 |
| `03-real-deepseek.png` | `python play_game.py --rounds 10 --strategy counter` | 真实 DeepSeek 官方 API 对局 |
| `04-key-code.png` | `gateway/app.py` 第 76–139 行 | `handle_request`：编排 + 兜底 |
| `05-pytest-green.png` | `python -m pytest tests -v` | 93 个测试全部通过 |
