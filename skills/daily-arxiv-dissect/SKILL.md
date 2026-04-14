---
name: daily-arxiv-dissect
description: 深度阅读单篇学术论文，并将其整理成一篇连续的中文精读文章；通常作为 daily-arxiv 的 worker 被委派，也可在用户直接要求精读单篇论文时独立触发。
---
# 每日 arXiv 精读

这个 skill 只负责单篇论文的精读、成文与可选保存到飞书知识库。它通常由 `daily-arxiv` 委派，但当用户明确要求“精读这篇论文”时也可以独立触发。

## 内置资源

- `assets/templates/paper_template.md`：单篇精读的写作模板。开始写作前先读取实际内容。
- `references/writing-style.md`：写作指南，包含节奏、ASCII 图示、审稿口径和文风清洁规则。
- `references/description.md`：用户自述，描述用户的研究方向、工作内容等。用于审视论文对用户实际工作的价值。

## 输入

可接受以下任一输入：

- 论文标题
- arXiv URL
- 本地 PDF 路径
- 单篇论文元数据包

父 skill 委派时，优先使用下面的契约：

- 论文元数据：`title`、`url`、`pdf_path`、`pdf_url`、`source_url`、`comment`、`authors`、`published`
- 保存上下文：`resolved_target`、`parent_url`

## 工作流

1. 获取原文PDF并读取论文内容，必要时可以读取TEX源码以获取公式、图片等信息。
2. 读取 `assets/templates/paper_template.md` 和 `references/writing-style.md`，先整理工作草稿，再织成一篇连续的中文文章。
3. 把论文当作一个“增量声明”来读：说清前人边界、本文增量、内部机制、证据力度和最终判断。
4. 如果提供了 `resolved_target`，按该目标写入飞书知识库；不要自行改写父 skill 已经解析好的落点。
5. 如果 `resolved_target.mode=wiki`，且父 skill 同时提供了 `parent_url`，则必须把单篇精读创建为该父日报的直接子文档，而不是平级创建到其他知识库位置。
6. 如果是用户直接调用且明确要求保存，但没有 `resolved_target`，只做一次轻量定位：优先使用默认知识库 `日常学习`，或根据用户给出的知识库名称、知识库节点、知识库 URL 解析；仍无法判断时向用户确认，不要猜。

## 职责边界

- 这个 skill 负责全文阅读、方法核对、实验核对和真实增量判断。
- 如果父 skill 还在筛选阶段，就不应该自己下载 PDF 或打开正文；这些动作应在论文被委派给本 skill 之后进行。
- 如果父 skill 以知识库模式委派并提供了父日报引用，本 skill 的保存职责不仅是“写入知识库”，还包括把文档挂到父日报下面。

## 标题规则

- 保存时，由子 skill 在完整阅读论文后自行命名。
- 默认命名为 `{short_title} | {organization} | {publication}`。
- `short_title` 优先选方法名、模型名或最易检索的短标题；如果没有，就用原论文标题的精简版本。
- `organization` 优先选读者最容易识别的主导机构、团队或公司名称；如果是明显的多机构合作且没有单一主导方，可写 `Multi-org`。
- `publication` 优先使用会议或期刊简称加年份；如果当前只有 arXiv 版本，则写 `arXiv`。
- 缺失值优先补成可读占位，而不是内部 id：`organization` 不明时写 `Unknown Org`，`publication` 不明时写 `arXiv`。
- 不要把 `paper_id`、文件名或内部 token 放进标题里，除非用户明确要求。

## 返回结果

保存到飞书知识库时，至少返回：

- `doc_url`
- `doc_id`
- `doc_title`
- `summary`
- `save_status`

## 约束

- 最终结果必须是连续文章，而不是 checklist 式报告。
- 不要把摘要直接粘贴成分析，也不要虚构 venue、作者、公式或实验结果。
- 如果关键材料缺失到无法支撑可信判断，要明确指出缺失项，而不是补想象。
- 所有图示默认使用 ASCII，必要时可插入原图。
- 写作目标平台是飞书文档，请主动使用飞书特有组件（高亮块、字体颜色、引用块等）增强结构与可读性，不要止步于基础 Markdown 语法。