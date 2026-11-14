# har-brief：少带数据的 HAR 排查摘要

给前端开发者和技术支持人员使用的离线命令行工具。把浏览器 HAR 文件转成
Markdown / JSON 摘要，先回答“哪些请求慢、哪些返回错误”，而不把原始流量交出去。

它**不是另一份脱敏 HAR，也不能重新导入浏览器**。不保留原始域名、路径、查询参数、
请求或响应内容、请求头、Cookie、绝对时间、页面标题及扩展字段。只输出新生成的端点
别名、请求序号、固定方法枚举和有限数值。

## 使用

要求 Python 3.10+。下载本仓库后，在 macOS / Linux 中无需安装依赖即可试用：

```sh
PYTHONPATH=src python -m har_brief examples/demo.har
PYTHONPATH=src python -m har_brief capture.har -o brief.md
PYTHONPATH=src python -m har_brief capture.har --format json -o brief.json
PYTHONPATH=src python -m unittest discover -s tests -v
```

也可在虚拟环境中 `python -m pip install .` 后使用 `har-brief` 命令。
详见 [English README](README.md)。尚未发布到 PyPI，不要用同名包名推断来源。

## 怎么用于实际沟通

1. 原始 HAR 留在自己电脑，先本地生成摘要。
2. 自己检查摘要内容及单位的数据分享规定，然后仅分享摘要。
3. 对方说“第 37 个请求耗时很长”，你再在原始 `log.entries[36]` 中核对。
4. 确有需要时，再提供有权分享的细节，不自动生成带 URL 的映射表。

`E001` 等别名在单份文件内稳定，按 HTTP(S) 源、准确路径、固定方法分组。
查询参数和片段不参与分组，所以同一路径上不同查询操作可能合并；动态路径不会自动
归并为接口模板。请求序号是文件数组位置，不一定对应浏览器排序后的行号。

## 不能承诺的事

- **不保证匿名或绝对安全。** 请求数量、关联模式、状态码、耗时和大小仍可能敏感。
- 适合第一轮排查，不替代认证、CORS、请求头、业务内容等详细诊断。
- 请求耗时总和不等于页面加载时间；`wait` 不直接等于服务器执行时间。
- `-1`、缺失或异常数值记为未知，不用 0 冒充；SSL 不重复累加。
- 不宣称已有用户、付费需求或市场验证。当前是基于公开问题制作并测试的早期实用工具。

上限为 32 MiB、100,000 条请求，内存占用可能显著高于输入大小。
输出路径已存在时拒绝写入；建议使用 `-o`，不要用可能事先覆盖文件的 shell 重定向。
运行时无第三方依赖，不联网、不上传、不重放请求、不保存历史。

[合成样例报告](examples/demo.md) · [隐私边界](docs/privacy.md) · [调研证据与竞品](docs/research.md) · [测试状态](docs/validation.md)
