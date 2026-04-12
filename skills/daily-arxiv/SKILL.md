---
name: daily-arxiv
description: 编排一条完整的“每日 arXiv”任务工作流：运行预配置抓取脚本召回候选论文、完成初筛、在需要时创建飞书知识库父日报，并把单篇论文委派给 daily-arxiv-dissect 生成精读与回链。
user-invocable: true
---
# 每日 arXiv 编排

这个 skill 负责“每日 arXiv”任务的编排层，而不是单篇论文的完整阅读。

## 内置资源

- `scripts/arxiv_fetch.py`：唯一候选召回器。直接运行即可输出分组后的标准化 JSON，其中候选会分为“完全关键词匹配”和“潜在关键词匹配”两组。
- `config/fetch.yaml`：抓取脚本的默认配置来源，统一维护 `keywords`、`categories`、`hours`、`candidate_pool`。
- `assets/templates/summary_template.md`：父日报模板。写汇总前必须先读取实际内容。
- `references/selection-policy.md`：默认筛选偏好和 tie-break 规则。
- `references/save-targets.md`：飞书知识库保存目标解析、父日报命名和父子文档链接约定。

## 快速开始

常规情况下直接运行：

```bash
python3 -m pip install -r requirements.txt
python3 skills/daily-arxiv/scripts/arxiv_fetch.py
```

上面的命令会直接读取 `skills/daily-arxiv/config/fetch.yaml` 作为默认抓取配置。

只有在用户明确要求调整抓取范围时，才覆盖默认参数，例如：

```bash
python3 skills/daily-arxiv/scripts/arxiv_fetch.py --hours 48 --candidate-pool 150
```

如果需要切换整套默认配置，再显式指定配置文件：

```bash
python3 skills/daily-arxiv/scripts/arxiv_fetch.py --config /path/to/fetch.yaml
```

## 工作流

1. 先判断输入属于哪条入口分支。

- 如果用户没有显式指定单篇论文，进入“默认抓取分支”。
- 如果用户通过论文标题、 arXiv URL 或本地 PDF 文件指定了单篇论文，进入“手动指定论文分支”。

2. 在“默认抓取分支”中，必须先通过运行 `scripts/arxiv_fetch.py` 召回论文。

- 该脚本输出的分组 JSON 是唯一候选池，优先查看“完全关键词匹配”组。
- 禁止在未运行脚本的情况下对候选池做任何假设，包括“候选为空”。也禁止自行构造候选论文。
- 如果脚本失败，先根据错误信息重试一次；仍失败时停止流程并汇报原因。

3. 在“默认抓取分支”中，读取 `references/selection-policy.md` 作为参考进行**摘要级初筛**，从候选池中筛出几篇最值得深读的论文。
4. 在“手动指定论文分支”中，跳过候选筛选，直接准备委派输入。

- 先使用当前可用的网络/抓取工具补齐可信元数据。
- 如果输入是本地 PDF 路径，请直接使用该 PDF 作为原文入口。
- 禁止手写论文元数据；必须通过可信入口补齐，或直接使用用户提供的本地 PDF。

5. 如果用户要求保存到飞书知识库，读取 `references/save-targets.md`，在父 skill 内完成保存目标解析并创建父日报。
6. 为每篇入选论文，或手动指定的那一篇论文，委派一个独立的 `daily-arxiv-dissect` 子任务，避免把多篇论文细节堆进同一上下文。
7. 收集子任务结果，检查返回契约是否完整，再用 `assets/templates/summary_template.md` 生成父日报或文本汇总。

父 skill 在这一步只能做“是否值得送去深读”的判断，不要把摘要级信号误写成对论文真实增量已经成立的结论。

创建父日报时，标题必须严格使用下面的格式：`YYYY-MM-DD日报`，例如 `2026-04-11日报`；不要添加任何其他的额外说明文字。

## 筛选阶段的硬边界

- 在入选名单确定之前，父 skill 只允许使用抓取脚本返回的候选字段做判断，例如 `title`、`abstract`、`comment`、`categories`、`matched_keywords`、`authors`、`published`、`url`。
- 在筛选阶段，**禁止**下载 PDF，**禁止**打开论文正文，**禁止**读取 `pdf_url` 或 `source_url`，也不要做“轻量精读核对”。
- 全文阅读、方法核对、实验核对和真实增量判断是 `daily-arxiv-dissect` 的专属职责，不属于父 skill。
- 如果用户手动指定了单篇论文，则不进入筛选阶段；父 skill 的职责变为补齐论文入口信息、处理保存目标、创建父日报并委派子 skill。

## 输入范围

这个 skill 接受四类输入：

- 抓取范围：例如 `hours`、`candidate_pool`、额外 `keywords` 或 `categories`
- 手动论文：例如 `arxiv_url`、`title` 或本地 `pdf_path`
- 保存目标：例如 `wiki_node`、`wiki_space`、知识库 URL，或用户明确给出的知识库名称
- 主题偏好：用于筛选阶段的轻量偏置，而不是替代实际召回

如果用户没有显式覆盖，直接使用 `config/fetch.yaml` 中的默认配置；当用户要求保存但没有单独指定知识库时，默认目标为 `日常学习`。

## 父子任务契约

委派给 `daily-arxiv-dissect` 时，只传递下面这些字段：

- `title`
- `url`
- `pdf_path`
- `pdf_url`
- `source_url`
- `comment`
- `authors`
- `published`
- `categories`
- `matched_keywords`
- `resolved_target`
- `parent_url`

其中：

- `url`、`pdf_path`、`pdf_url`、`source_url` 不必同时存在，但至少要给出一个可用于获取原文的可信入口
- `resolved_target` 由父 skill 解析完成，子 skill 不应再次做广泛的落点决策；在知识库模式下，它还应包含父日报对应的 `wiki_node`，或等价的可创建子页面引用
- `parent_url` 是父日报引用；在知识库模式下，子 skill 既用它识别父日报，也要据此把子精读创建为父日报的子文档。至少包含 `doc_url`、`doc_id`、`title`

子 skill 的返回契约固定为：

- `doc_url`
- `doc_id`
- `doc_title`
- `summary`
- `save_status`

## 失败处理

- 不要在未运行抓取脚本时猜测候选池内容，也不要自行构造候选论文。
- 如果抓取脚本失败，先根据错误信息重试一次；仍失败时汇报失败原因，不进入筛选阶段。
- 如果抓取脚本成功但结果为空，明确说明今日无候选论文，不要虚构补位。
- 如果用户手动指定论文但联网检索失败，先重试一次；仍失败时汇报失败原因，并建议用户改提供 arXiv URL 或本地 PDF。
- 如果保存目标无法解析，停在父 skill 并向用户确认；不要把模糊的知识库目标直接传给子 skill。
- 如果子 skill 在保存路径下返回缺失的 `doc_url` 或 `doc_id`，重新委派一次或显式报错，不要假装成功。

## 输出要求

这个 skill 的最终输出应包含：

- 当日候选概览；如果走手动指定分支，则明确说明本次跳过候选筛选
- 入选论文列表与入选原因；如果走手动指定分支，则说明“用户指定，直接精读”
- 每篇论文的 1 句总结
- 如果有保存到知识库，父日报链接与各子精读链接

把个人研究偏好、机构优先级和飞书命名细则放在 `references/` 中按需加载，不要在主流程里重复硬编码。
