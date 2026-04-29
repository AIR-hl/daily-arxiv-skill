---
name: daily-arxiv-dissect
description: 深度阅读单篇学术论文，并将其整理成一篇连续的中文精读文章；可以作为 daily-arxiv 的 worker 被委派，也可在用户直接要求精读单篇论文时独立触发。
---
# 每日 arXiv 精读

这个 skill 只负责单篇论文的精读、成文与可选保存到飞书知识库。它通常由 `daily-arxiv` 委派，但当用户明确要求“精读这篇论文”时也可以独立触发。

## 内置资源

- `assets/templates/paper_template.md`：单篇精读的写作模板。开始写作前先读取实际内容。
- `references/writing-style.md`：写作指南，包含节奏、ASCII 图示、审稿口径和文风清洁规则。
- `references/lark-rendering.md`：飞书保存渲染指南。只有在需要保存到飞书文档时读取，用于把按模板组织好的内容转换为适合飞书阅读的发布稿。
- `references/description.md`：用户自述，描述用户的研究方向、工作内容等。用于审视论文对用户实际工作的价值。

## 输入

可接受以下任一输入：

- 论文标题
- arXiv URL
- 本地 PDF 路径
- 单篇论文元数据包

父 skill 委派时，优先使用下面的契约：

- 论文元数据：`title`、`url`、`html_url`、`pdf_path`、`pdf_url`、`source_url`、`comment`、`authors`、`published`
- 保存上下文：`save_mode`、`parent_doc`

## 工作流

1. 获取原文入口并优先读取 arXiv HTML：`html_url` 为真实 URL 时先读 HTML；为 `unknown` 时先重试一次可用性检查，若仍不确定或 HTML 关键内容不足，则回退到 `pdf_path` / `pdf_url`；为 `unavailable` 时直接走 PDF。只有当公式、表格、图注、源码图片或实现细节仍不足时，才继续读取 `source_url` / TEX 源码。
2. 以"增量声明"为阅读视角贯穿全文进行阅读理解：厘清前人边界、本文增量、内部机制、证据力度与最终判断。
3. ⚠ 读取 `assets/templates/paper_template.md` 和 `references/writing-style.md`，严格根据模板结构而非上一步的阅读角度组织出一篇精读报告，并遵照写作规范成文。
4. 如果接收到了 `save_mode=wiki` 时保存到飞书知识库，`none` 时跳过；不要擅自改写父 skill 已经解析好的落点。知识库模式下，以 `parent_doc` 为**唯一**挂载依据，**必须**把单篇精读创建为父日报的直接子文档，而不是平级创建到其他知识库位置。
5. 如果是用户直接调用且明确要求保存，但没有 `save_mode`，只做一次轻量定位：优先使用默认知识库 `日常学习`，或根据用户给出的知识库名称、知识库节点、知识库 URL 做轻量解析；仍无法判断时向用户确认，不要猜。
6. ⚠ 保存到飞书前必须根据 `references/lark-rendering.md` 执行 Compose -> Render -> Publish 流程，并把 Render 后的内容作为飞书文档发布内容。
7. 保存后请务必读回并核对段落中公式（这里经常容易犯错）以及各组件是否正确。

如果是用户直接调用而不是父 skill 委派：

- 当输入是 arXiv URL 或能可靠定位到 arXiv 论文标题时，先补齐 `html_url`，语义与父 skill 契约保持一致：真实 URL、`unavailable`、`unknown`。
- 当输入只有本地 PDF 路径或无法可靠解析出 arXiv ID 时，不要猜测 `html_url`；直接按 PDF 入口处理。

## 论文读取约定

- 传入 `html_url=unknown` 表示抓取时出现错误，不等于没有 HTML 版本；因此允许轻量重试一次，再决定是否回退使用PDF。
- HTML 解析必须按结构读取（标题、章节、段落、图注、表格、数学节点 `alttext`/TeX annotation），不得做纯文本粗抽；若关键数字、公式或表格仍有缺失，才回退到 PDF / TEX 核对。
- ⚠ 禁止同时读取网页与 PDF / TEX 两条入口；确认 HTML 入口不可用或关键内容缺失时，再使用 PDF / TEX，不可并行读取。

## 职责边界

- 这个 skill 负责全文阅读、方法核对、实验核对和真实增量判断。
- 如果父 skill 还在筛选阶段，就不应该自己下载 PDF 或打开正文；这些动作应在论文被委派给本 skill 之后进行。
- 如果父 skill 以知识库模式委派并提供了父日报引用，本 skill 的保存职责不仅是“写入知识库”，还包括把文档挂到父日报下面。
- 只要存在可信的 `html_url`，优先使用 HTML 正文作为主阅读入口；PDF 和 TEX 主要承担回退与核对职责。

## 标题规则

- 保存时，由子 skill 在完整阅读论文后自行命名。
- 默认命名为 `{short_title} | {organization} | {publication}`。
- `short_title` 优先选方法名、模型名或最易检索的短标题；如果没有，就用原论文标题的精简版本。
- `organization` 根据作者身份或论文标识优先选读者最容易识别的主导机构、团队或公司名称（比如：Alibaba Tongyi、FDU & Shanghai AI Lab）
- `publication` 优先使用会议或期刊简称加年份；如果当前只有 arXiv 版本，则写 `arXiv`。
- 缺失值优先补成可读占位，而不是内部 id：`organization` 不明时写 `Unknown Org`，`publication` 不明时写 `arXiv`。
- 不要把 `paper_id`、文件名或内部 token 放进标题里，除非用户明确要求。

## 返回结果

保存到飞书知识库时，至少返回：

- `doc_url`
- `doc_id`
- `doc_title`
- `summary`
- `save_status`：说明保存是否成功；如果保存到飞书，简要说明已按飞书阅读场景做过渲染处理。具体使用哪些组件不要求逐项列举。

## 约束

- 不要把摘要直接粘现成分析，也不要虚构 venue、作者、公式或实验结果。
- 如果关键材料缺失到无法支撑可信判断，要明确指出缺失项，而不是补想象。
- 保存为飞书文档时必须要对内容排版进行调整/渲染以增强可读性。
- 不要把 `unknown` 误写成“该论文没有 HTML 版本”；它只表示当前尚未确认。
