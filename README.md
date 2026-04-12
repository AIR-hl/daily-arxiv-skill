# daily-arxiv-skill

这个仓库提供两个围绕“每日 arXiv”任务协作的 Skills，适合挂到 OpenClaw、Codex、Claude Code 等 Agent 环境中，通过定时任务每天自动拉取候选论文、完成摘要级筛选，并把结果整理成便于快速学习的日报与单篇精读。

- `daily-arxiv`：对外公开的编排 skill，负责候选召回、初筛、知识库目标解析、父日报创建、子任务委派和最终汇总。
- `daily-arxiv` 也支持在用户显式指定单篇论文时跳过筛选，并在补齐可信论文入口后直接委派精读。
- `daily-arxiv-dissect`：内部 worker skill，负责单篇论文精读、成文和按既定目标写入飞书知识库。

默认保存落点为 `日常学习` 知识库下的 `每日Arxiv` 节点。也支持在 prompt 中直接指定其他知识库或节点，例如"保存到「研究笔记」知识库"或"保存到「研究笔记」知识库的「LLM」节点下"。无论落点层级如何，父日报始终作为落点节点的直接子文档创建，子精读再挂在父日报下。

## 快速使用

提示你的 Agent 获取仓库：`https://github.com/AIR-hl/daily-arxiv-skill` 并安装该 skill。

⚠️ 安装后，请进入 skill 安装目录，例如 `~/.codex/skills/daily-arxiv/`，手动修改以下配置文件：

1. `config/fetch.yaml`：召回论文的相关配置，`categories` 可参考 [arXiv taxonomy](https://arxiv.org/category_taxonomy)。
2. `references/description.md`：用户对自身工作内容、研究兴趣和筛选偏好的说明，可帮助模型更准确地筛选论文。

## 适用场景

- 作为日常快速学习的辅助流程，每天自动汇总值得关注的新论文。
- 作为 Agent 的定时任务目标，在固定时间触发 `daily-arxiv` 生成当日论文摘要与精读入口。
- 作为个人研究跟踪工具，把筛选结果和精读结果统一沉淀到飞书知识库。

定时调度由宿主 Agent 平台负责，这个仓库负责提供可复用的 skill 工作流与产出结构。

## 示例 Prompt

**设置每日定时任务（推荐入口）：**

```text
每个工作日上午 08:00，执行「每日 arXiv」任务，结果保存到飞书「日常学习」知识库中的「每日Arxiv」文件下。
```

**临时手动触发：**

```text
精读这篇论文：https://arxiv.org/abs/2504.xxxxx 作为今天的「每日Arxiv」任务，保存到「日常学习」知识库。
```

**覆盖抓取范围：**

```text
执行今天的「每日 arXiv」任务，使用最近 48 小时窗口，candidate pool 调整到 150，结果保存到飞书「日常学习」知识库。
```

## 目录结构

```text
skills/
  daily-arxiv/
    SKILL.md
    assets/templates/summary_template.md
    config/
      fetch.yaml
    references/
      description.md
      save-targets.md
      selection-policy.md
    scripts/
      arxiv_fetch.py
  daily-arxiv-dissect/
    SKILL.md
    assets/templates/paper_template.md
    references/writing-style.md
```

## 设计约定

- 只有 `daily-arxiv` 承担完整的“每日 arXiv 日报”工作流。
- `daily-arxiv-dissect` 只处理单篇论文，不负责父级日报创建和广泛的保存目标决策。
- 父 skill 委派子 skill 时，统一使用真实 skill 名 `daily-arxiv-dissect`。
- 保存到飞书知识库时，父日报是父 skill 创建的顶层文档；每篇子精读必须作为父日报的直接子文档创建。
- 个人偏好和写作口味放在 `references/`，主 `SKILL.md` 只保留核心工作流与契约。
- 不保留平台专属的 UI 元数据文件，尽量让 skill 目录保持可移植、平台中立。
