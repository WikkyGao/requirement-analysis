# 需求分析技能 (Requirement Analysis Skill)

[![skills.sh](https://skills.sh/b/WikkyGao/requirement-analysis)](https://skills.sh/WikkyGao/requirement-analysis)

> **版本**: v1.3.0 | **许可**: MIT

## 简介

多格式需求文档分析与整合技能。自动解析 Markdown、Excel、Word、思维导图文件，智能去重和补充需求信息，生成标准化的开发交付文档，内置 PRD、系统概要说明书、详细说明书、数据库设计说明书四类模板。

支持三种工作模式：**标准模式**（完整流程含澄清交互）、**快速模式**（跳过逐条提问，自动填默认值）、**增量模式**（检测已有 PRD.md 并输出变更）。

## 快速开始

### 安装

```bash
# 通过 skills.sh 一键安装（推荐，支持 Claude Code / Codex / Cursor / Gemini CLI 等 20+ agent）
npx skills add WikkyGao/requirement-analysis

# 或手动复制到技能目录
cp -r requirement-analysis ~/.claude/skills/

# 安装可选依赖（增强文档解析能力）
cd ~/.claude/skills/requirement-analysis
pip install python-docx openpyxl    # 增强 Word/Excel 解析
# 或 npm install                    # 备选依赖
```

### 使用

打开你的项目，说：
- "进行需求分析"
- "分析需求"
- "整理需求文档"

### 工作模式说明

| 模式 | 触发条件 | 特点 |
|------|----------|------|
| 标准模式 | 无 PRD.md + 默认选择 | 逐条澄清、完整交互 |
| 快速模式 | 无 PRD.md + 用户选择 | 自动填默认值、批量确认 |
| 增量模式 | 检测到已有 PRD.md | 输出变更差异、版本递增 |

## 支持的文档格式

| 格式 | 扩展名 | 优先级 | 解析方式 |
|------|--------|--------|----------|
| Markdown | `.md`, `.markdown` | 1 | AI 读取，标题/表格/列表解析 |
| Word | `.docx` | 2 | 系统命令 (`python-docx`) |
| Excel | `.xlsx`, `.xls` | 3 | 系统命令 (`openpyxl` / `in2csv`) |
| 思维导图 | `.xmind`, `.mm`, `.mmap` | 4 | XML 解析 + 节点层级映射 |

## 工作流程

```
文档扫描 → 文档解析 → 功能提取 → 智能整合(含质量评估) → 需求澄清 → 用户确认 → 生成交付文档
```

## 内置交付文档模板

| doc_type | 文档 | 默认文件名 | 适用场景 |
|----------|------|------------|----------|
| `prd` | 产品需求文档 | `PRD.md` | 需求评审、功能范围确认 |
| `system-overview` | 系统概要说明书 | `系统概要说明书.md` | 架构评审、项目立项 |
| `detailed-design` | 详细说明书 | `详细说明书.md` | 开发编码、测试用例设计 |
| `database-design` | 数据库设计说明书 | `数据库设计说明书.md` | 建表、数据访问层开发、DBA 评审 |

生成命令：

```bash
echo '{"features": [...], "doc_type": "database-design", "project_name": "电商平台"}' \
  | python scripts/prd_generator.py --doc-type database-design --output docs/数据库设计说明书.md
```

模板结构说明见 `references/` 下的四份模板文件。

## 核心特性

- **语义去重**: AI 语义理解识别重复功能，合并冗余信息
- **冲突检测**: 标注文档间不一致，不自动解决
- **需求质量评估 (INVEST)**: 从独立性、价值、可测试性等 6 维评分
- **来源追溯**: 每项功能标注来源文档
- **增量更新**: 检测已有 PRD.md 自动进入增量模式
- **快速模式**: 跳过逐条提问，自动填充合理默认值

## 输出结构

| 文档 | 核心章节 |
|------|----------|
| `PRD.md` | 需求概述 → 功能清单（字段/操作/交互/验收标准）→ 附录（变更历史 + 待确认事项 + INVEST 质量评估） |
| `系统概要说明书.md` | 引言 → 系统概述 → 总体设计 → 功能概要 → 接口概要 → 数据概要 → 非功能需求 → 约束与假设 |
| `详细说明书.md` | 引言 → 总体说明 → 模块详细设计 → 功能明细 → 接口详细设计 → 数据设计 → 日志/异常/安全 |
| `数据库设计说明书.md` | 引言 → 设计概述 → 逻辑数据模型 → 物理表设计 → 数据字典 → 索引与约束 → 初始化与迁移 → 安全与权限 |

## 常见问题

**Q: .doc 文件无法解析？**
A: 仅支持 `.docx`。请先转换格式。

**Q: 缺少 Word/Excel 解析依赖？**
A: 运行 `pip install python-docx openpyxl` 或继续（AI 会尝试直接读取）。

**Q: 相似度阈值可以调整吗？**
A: 采用 AI 语义判断而非固定阈值，没有硬编码的百分比限制。

**Q: 冲突会自动解决吗？**
A: 不会。所有冲突需用户确认，确保需求准确性。

**Q: 已经生成过 PRD 了，再运行会怎样？**
A: 自动进入增量模式，对比差异输出变更。

## 目录结构

```
requirement-analysis/
├── _meta.json       # 技能元数据
├── SKILL.md         # 核心执行指令
├── README.md        # 本文件
├── package.json     # npm 依赖（备选）
├── references/      # 模板与格式示例
└── scripts/         # 解析、提取、评估、文档生成脚本
```
