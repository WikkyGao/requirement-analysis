#!/usr/bin/env python3
"""
prd_generator.py - 按内置模板生成 PRD / 概要说明书 / 详细说明书 / 数据库设计说明书
接收 stdin JSON: {"features": [...], "assessments": [...], "conflicts": [...],
                  "mode": "standard|quick|incremental", "template": "full|summary",
                  "doc_type": "prd|system-overview|detailed-design|database-design",
                  "version": "1.0.0", "project_name": "...", "pending_items": [...],
                  "nfr_baseline": [{name, default, trigger}], "need_feature_map": [{need, feature, solution}],
                  "entities": [...], "interfaces": [...], "architecture": {...},
                  "roles": [...], "glossary": [...], "purpose": "...", "scope": "...",
                  "assumptions": [...], "constraints": [...], "database": "...",
                  "existing_prd": "..." (incremental mode)
                  每个功能项可含 screenshots: [{path, caption, description}] → 渲染为「截图」小节
                  每个功能项可含 related_pages: [{name, path, caption, description}] → 渲染为「相关页面」小节（原型页面截图）}
接收命令行参数: --output, --template full|summary, --doc-type <type>
输出 stdout JSON: {"status": "ok", "path": "...", "doc_type": "..."} 或 {"status": "error", ...}
"""
import argparse
import json
import os
import re
import sys
from datetime import date


ALLOWED_MODES = frozenset({'standard', 'quick', 'incremental'})
ALLOWED_TEMPLATES = frozenset({'full', 'summary'})
ALLOWED_DOC_TYPES = frozenset({'prd', 'system-overview', 'detailed-design', 'database-design'})

DOC_TITLES = {
    'prd': '产品需求文档',
    'system-overview': '系统概要说明书',
    'detailed-design': '详细说明书',
    'database-design': '数据库设计说明书',
}

DEFAULT_OUTPUTS = {
    'prd': 'PRD.md',
    'system-overview': '系统概要说明书.md',
    'detailed-design': '详细说明书.md',
    'database-design': '数据库设计说明书.md',
}

DEFAULT_NFR = [
    {'name': '并发量', 'default': '按日均 1000 UV 设计', 'trigger': '大促/高并发场景'},
    {'name': '数据保留', 'default': '永久保留 / 按合规保留 3 年', 'trigger': '金融、审计、隐私合规特殊要求'},
    {'name': '删除操作', 'default': '软删除 + 操作日志', 'trigger': '不可恢复/强审计需求'},
    {'name': '安全加密', 'default': '常规传输加密', 'trigger': '金融级加密、支付密钥等'},
    {'name': '可用性', 'default': '常规（99.9%）', 'trigger': '用户明确 SLA 要求'},
]


def validate_input(data: dict) -> None:
    if 'features' not in data:
        raise ValueError('"features" is required')
    if not isinstance(data['features'], list):
        raise ValueError('"features" must be an array')
    if 'mode' in data and data['mode'] not in ALLOWED_MODES:
        raise ValueError(f'"mode" must be one of: {", ".join(sorted(ALLOWED_MODES))}')
    if 'template' in data and data['template'] not in ALLOWED_TEMPLATES:
        raise ValueError(f'"template" must be one of: {", ".join(sorted(ALLOWED_TEMPLATES))}')
    if 'doc_type' in data and data['doc_type'] not in ALLOWED_DOC_TYPES:
        raise ValueError(f'"doc_type" must be one of: {", ".join(sorted(ALLOWED_DOC_TYPES))}')


def render_frontmatter(project_name: str, version: str) -> str:
    today = date.today().isoformat()
    return f"""---
title: {project_name} 产品需求文档
version: v{version}
date: {today}
---

# {project_name} 产品需求文档

> 版本: v{version} | 更新日期: {today}
"""


def render_overview(features: list, template: str = 'full') -> str:
    """Render the requirements overview section."""
    modules = set(f['module'] for f in features if f.get('module'))
    doc_type = '完整版' if template == 'full' else '业务摘要版'
    return f"""## 需求概述

### 核心目标

通过整合多来源需求，生成标准化产品需求文档。

### 功能范围

- **模块数**: {len(modules)} 个
- **功能项**: {len(features)} 个
- **文档类型**: {doc_type}
- **覆盖模块**: {', '.join(sorted(modules)) if modules else '待确定'}
"""


def render_feature_list(features: list, template: str = 'full') -> str:
    """Render the feature list section."""
    lines = ['## 功能清单\n']

    # Group by module
    modules = {}
    for f in features:
        module = f.get('module', '未分类')
        if module not in modules:
            modules[module] = []
        modules[module].append(f)

    module_num = 0
    for module_name, module_features in modules.items():
        module_num += 1
        lines.append(f'### 模块 {module_num}: {module_name}\n')

        for feat in module_features:
            fid = feat.get('id', '')
            fname = feat.get('name', '')
            fdesc = feat.get('description', '')
            fpriority = feat.get('priority', 'medium')
            fields = feat.get('fields', [])
            actions = feat.get('actions', [])
            interact = feat.get('interactions', [])
            acceptance = feat.get('acceptance_criteria', [])
            details = feat.get('details', [])

            lines.append(f'---\n')
            lines.append(f'#### {fid} {fname}\n')
            lines.append(f'**基本信息**\n')
            lines.append(f'| 属性 | 值 |')
            lines.append(f'|------|-----|')
            lines.append(f'| 所属模块 | {module_name} |')
            lines.append(f'| 优先级 | {fpriority} |')
            lines.append(f'\n**功能描述**\n')
            lines.append(f'{fdesc if fdesc else "待补充"}\n')

            # 截图（业务上下文，完整版与摘要版均保留）
            screenshots = feat.get('screenshots', [])
            if screenshots:
                lines.append(f'\n**截图**\n')
                for s in screenshots:
                    spath = s.get('path', '')
                    scaption = s.get('caption', '')
                    sdesc = s.get('description', '')
                    if spath:
                        lines.append(f'![{scaption or fname}]({spath})')
                        if scaption or sdesc:
                            lines.append(f'> {scaption}{"：" if scaption and sdesc else ""}{sdesc}')
                        lines.append('')

            # 相关页面（原型/设计稿页面截图，完整版与摘要版均保留）
            related_pages = feat.get('related_pages', [])
            if related_pages:
                lines.append(f'\n**相关页面**\n')
                for p in related_pages:
                    pname = p.get('name', '')
                    ppath = p.get('path', '')
                    pcaption = p.get('caption', '')
                    pdesc = p.get('description', '')
                    lines.append(f'- **{pname}**' if pname else '- **待命名页面**')
                    if ppath:
                        lines.append(f'  ![{pcaption or pname}]({ppath})')
                    if pcaption or pdesc:
                        lines.append(f'  > {pcaption}{"：" if pcaption and pdesc else ""}{pdesc}')
                lines.append('')

            # 完整版才输出字段/动作/交互等实现细节；摘要版删减这些技术细节
            if template == 'full':
                # Fields
                if fields:
                    lines.append(f'\n**字段说明**\n')
                    lines.append(f'| 字段名 | 类型 | 必填 | 校验规则 | 默认值 | 说明 |')
                    lines.append(f'|--------|------|------|----------|--------|------|')
                    for field in fields:
                        f = {
                            'name': field.get('name', ''),
                            'type': field.get('type', 'string'),
                            'required': '是' if field.get('required', False) else '否',
                            'validation': field.get('validation', '-'),
                            'default': field.get('default', '-'),
                            'description': field.get('description', '-')
                        }
                        lines.append(
                            f'| {f["name"]} | {f["type"]} | {f["required"]} '
                            f'| {f["validation"]} | {f["default"]} | {f["description"]} |'
                        )

                # Actions
                if actions:
                    lines.append(f'\n**按钮/操作逻辑**\n')
                    lines.append(f'| 按钮/操作 | 触发条件 | 操作行为 | 异常处理 |')
                    lines.append(f'|-----------|----------|----------|----------|')
                    for action in actions:
                        lines.append(
                            f'| {action.get("name", "-")} '
                            f'| {action.get("condition", "-")} '
                            f'| {action.get("behavior", "-")} '
                            f'| {action.get("error_handling", "-")} |'
                        )

                # Interactions
                if interact:
                    lines.append(f'\n**交互说明**\n')
                    for item in interact:
                        lines.append(f'- {item}')

            # Acceptance criteria (business-relevant, kept in both versions)
            if acceptance:
                lines.append(f'\n**验收标准**\n')
                for ac in acceptance:
                    lines.append(f'- [ ] {ac}')
            elif not acceptance and details:
                lines.append(f'\n**验收标准**\n')
                lines.append(f'- [ ] 待补充 (参考: {"; ".join(details[:3])})')
            else:
                lines.append(f'\n**验收标准**\n')
                lines.append(f'- [ ] 待补充\n')

        lines.append('')

    return '\n'.join(lines)


def render_conflict(c: dict) -> str:
    """Render a single conflict, using the impact-analysis table when available."""
    ctype = c.get('type', 'unknown')
    severity = c.get('severity', 'medium')
    fname = c.get('feature_name', '')
    marker = '🔴' if severity == 'high' else '⚠️'
    out = [f'- **{fname}** 存在 {ctype}:']

    source_a = c.get('source_a')
    source_b = c.get('source_b')
    impact = c.get('impact')
    suggestion = c.get('suggestion')

    if (source_a or source_b) and (impact or suggestion):
        a_label = (source_a or {}).get('label', '来源 A')
        a_value = (source_a or {}).get('value', '-')
        b_label = (source_b or {}).get('label', '来源 B')
        b_value = (source_b or {}).get('value', '-')
        out.append(f'| 来源 A（{a_label}） | 来源 B（{b_label}） | 业务影响 | 建议方案 |')
        out.append(f'|---|---|---|---|')
        out.append(f'| {a_value} | {b_value} | {impact or "-"} | **{suggestion or "-"}** |')
    else:
        details = c.get('details', {})
        if 'versions' in details:
            for v in details['versions']:
                out.append(f'  - {v.get("source", "?")}: "{v.get("type", v.get("required", "?"))}"')
        if 'version_a' in details and 'version_b' in details:
            va = details['version_a']
            vb = details['version_b']
            out.append(f'  - {va.get("source", "?")}: "{va.get("description", "?")}"')
            out.append(f'  - {vb.get("source", "?")}: "{vb.get("description", "?")}"')
        if impact:
            out.append(f'  - 业务影响: {impact}')
        if suggestion:
            out.append(f'  - 建议: {suggestion}')
    out.append(f'  - {marker} 待确认')
    return '\n'.join(out)


def render_pending_items(pending: list, conflicts: list) -> str:
    """Render pending items and conflicts section (appendix subsection)."""
    lines = ['### 待确认事项\n']

    if conflicts:
        lines.append(f'#### 冲突项\n')
        for c in conflicts:
            lines.append(render_conflict(c))

    if pending:
        lines.append(f'#### 待补充项\n')
        for item in pending:
            lines.append(f'- {item}\n')

    return '\n'.join(lines)


def render_nfr_table(nfr: list) -> str:
    """Render the NFR baseline as a standalone table."""
    lines = ['| NFR 项 | 默认基线 | 触发特殊提问的条件 |']
    lines.append('|--------|----------|--------------------|')
    for item in nfr:
        lines.append(f'| {item.get("name", "-")} | {item.get("default", "-")} | {item.get("trigger", "-")} |')
    return '\n'.join(lines)


def render_nfr_baseline(nfr: list) -> str:
    """Render the NFR baseline section (appendix subsection)."""
    if not nfr:
        return ''
    return '### NFR 基线（默认值）\n\n' + render_nfr_table(nfr)


def render_need_feature_map(need_map: list) -> str:
    """Render the need→feature→solution mapping (appendix subsection)."""
    if not need_map:
        return ''
    lines = ['### 需求 → 功能 → 方案 映射\n']
    lines.append('| 需求 (Need) | 功能 (Feature) | 方案 (Solution) |')
    lines.append('|-------------|----------------|-----------------|')
    for item in need_map:
        lines.append(f'| {item.get("need", "-")} | {item.get("feature", "-")} | {item.get("solution", "-")} |')
    return '\n'.join(lines)


def render_quality_report(assessments: list) -> str:
    """Render the INVEST quality assessment report."""
    if not assessments:
        return ''

    lines = ['### 需求质量评估\n']
    lines.append('| 功能项 | 独立性 | 可协商性 | 价值 | 可估算 | 小巧 | 可测试 | 总分 |')
    lines.append('|--------|--------|----------|------|--------|------|--------|------|')

    for a in assessments:
        dims = a.get('dimensions', {})
        fname = a.get('feature_name', '')
        total = a.get('total_score', 0)
        max_score = a.get('max_score', 18)

        def star_str(d):
            s = dims.get(d, {}).get('stars', 1)
            return '★' * s + '☆' * (3 - s)

        lines.append(
            f'| {fname} '
            f'| {star_str("independent")} '
            f'| {star_str("negotiable")} '
            f'| {star_str("valuable")} '
            f'| {star_str("estimable")} '
            f'| {star_str("small")} '
            f'| {star_str("testable")} '
            f'| {total}/{max_score} |'
        )

    # Suggestions
    suggestions = [s for s in assessments if 'suggestion' in s]
    if suggestions:
        lines.append('')
        lines.append('**总体建议**:')
        for s in suggestions:
            fname = s.get('feature_name', '')
            lines.append(f'- 🟡 "{fname}" - {s.get("suggestion", "")}')

    return '\n'.join(lines)


def render_incremental_diff(new_features: list, existing_prd: str) -> str:
    """In incremental mode, compute the diff."""
    lines = ['### 变更说明\n']

    # Extract existing feature names from existing PRD (simple heuristic)
    existing_names = set()
    for line in existing_prd.split('\n'):
        m = re.match(r'####\s+F-[\w-]+\s+(.+)', line)
        if m:
            existing_names.add(m.group(1).strip())

    new_names = set(f.get('name', '') for f in new_features)

    added = new_names - existing_names
    kept = new_names & existing_names

    lines.append(f'- **新增功能**: {len(added)} 个')
    for name in sorted(added):
        lines.append(f'  - + {name}')
    lines.append(f'- **未变更**: {len(kept)} 个')
    lines.append('')

    return '\n'.join(lines)


def _as_text(value, fallback: str = '待补充') -> str:
    """Normalize arbitrary input values into readable text."""
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() or fallback
    if isinstance(value, (list, tuple, set)):
        items = [_as_text(v, '') for v in value]
        return '、'.join(i for i in items if i) or fallback
    if isinstance(value, dict):
        for key in ('name', 'description', 'value', 'text', 'title'):
            if value.get(key):
                return _as_text(value[key], fallback)
        return fallback
    return str(value)


def _cell(value, fallback: str = '-') -> str:
    """Make a value safe for a Markdown table cell."""
    return _as_text(value, fallback).replace('|', '\\|').replace('\n', ' ')


def _slug(value) -> str:
    return re.sub(r'[^0-9a-zA-Z]+', '_', str(value or '')).strip('_').lower()


def group_features(features: list) -> dict:
    modules = {}
    for feat in features:
        modules.setdefault(feat.get('module') or '未分类', []).append(feat)
    return modules


def collect_entities(data: dict) -> list:
    """Use explicit entities when provided, otherwise derive tables from feature fields."""
    provided = data.get('entities') or []
    entities = []
    if provided:
        for idx, entity in enumerate(provided, 1):
            name = entity.get('name') or entity.get('table_name') or f'实体{idx}'
            entities.append({
                'name': name,
                'table_name': entity.get('table_name') or ('t_' + (_slug(name) or f'e{idx:02d}')),
                'description': entity.get('description', ''),
                'fields': entity.get('fields') or [],
                'primary_key': entity.get('primary_key') or 'id',
                'indexes': entity.get('indexes') or [],
                'relations': entity.get('relations') or [],
            })
        return entities

    for idx, feat in enumerate(data.get('features', []), 1):
        fields = feat.get('fields') or []
        if not fields:
            continue
        name = feat.get('name') or f'功能{idx}'
        entities.append({
            'name': name,
            'table_name': feat.get('table_name') or ('t_' + (_slug(feat.get('id')) or _slug(name) or f'f{idx:02d}')),
            'description': feat.get('description', ''),
            'fields': fields,
            'primary_key': feat.get('primary_key') or 'id',
            'indexes': feat.get('indexes') or [],
            'relations': feat.get('relations') or [],
        })
    return entities


def normalize_field(field: dict, index: int = 0) -> dict:
    if not isinstance(field, dict):
        field = {'name': str(field)}
    return {
        'name': field.get('name') or field.get('field') or field.get('code') or f'field_{index + 1}',
        'type': field.get('type') or field.get('data_type') or 'string',
        'length': field.get('length') or field.get('max_length') or '-',
        'required': field.get('required', field.get('nullable') is False),
        'default': field.get('default', '-'),
        'validation': field.get('validation') or field.get('constraint') or '-',
        'description': field.get('description') or field.get('comment') or '-',
        'primary_key': bool(field.get('primary_key')) or bool(field.get('pk')),
        'index': bool(field.get('index')) or bool(field.get('indexed')),
    }


def render_doc_frontmatter(project_name: str, version: str, doc_title: str) -> str:
    today = date.today().isoformat()
    return f"""---
title: {project_name} {doc_title}
version: v{version}
date: {today}
---

# {project_name} {doc_title}

> 版本: v{version} | 更新日期: {today} | 文档类型: {doc_title}
"""


def render_intro(data: dict, doc_title: str) -> list:
    project_name = data.get('project_name', '未命名项目')
    purpose = data.get('purpose') or (
        f'本文档用于说明 {project_name} 的{doc_title}相关内容，'
        f'作为设计评审、开发实现、测试验收与上线运维的依据。'
    )
    scope = data.get('scope') or '待补充（覆盖的业务范围、系统边界与不在本期范围内的内容）'
    glossary = data.get('glossary') or []
    references = data.get('references') or []

    lines = ['## 1. 引言', '', '### 1.1 编写目的', '', purpose, '', '### 1.2 适用范围', '', scope, '', '### 1.3 术语与缩略语', '']
    if glossary:
        lines.append('| 术语 | 说明 |')
        lines.append('|------|------|')
        for item in glossary:
            if isinstance(item, dict):
                lines.append(f'| {_cell(item.get("term") or item.get("name"))} | {_cell(item.get("definition") or item.get("description"))} |')
            else:
                lines.append(f'| {_cell(item)} | - |')
    else:
        lines.append('待补充。')

    lines.extend(['', '### 1.4 参考资料', ''])
    if references:
        for item in references:
            lines.append(f'- {_as_text(item)}')
    else:
        lines.append('待补充。')
    lines.append('')
    return lines


def render_roles_table(roles: list) -> list:
    lines = ['| 角色 | 职责说明 |', '|------|----------|']
    if roles:
        for role in roles:
            if isinstance(role, dict):
                lines.append(f'| {_cell(role.get("name"))} | {_cell(role.get("description") or role.get("duty"))} |')
            else:
                lines.append(f'| {_cell(role)} | - |')
    else:
        lines.append('| 待补充 | - |')
    return lines


def render_module_table(modules: dict) -> list:
    lines = ['| 序号 | 模块 | 功能项数 | 主要功能 |', '|------|------|----------|----------|']
    for idx, (module_name, feats) in enumerate(modules.items(), 1):
        names = '、'.join(f.get('name', '') for f in feats[:4])
        if len(feats) > 4:
            names += ' 等'
        lines.append(f'| {idx} | {_cell(module_name)} | {len(feats)} | {_cell(names)} |')
    if not modules:
        lines.append('| - | 待补充 | 0 | - |')
    return lines


def render_interfaces_table(interfaces: list) -> list:
    lines = ['| 接口名称 | 类型 | 提供方 | 调用方 | 说明 |', '|----------|------|--------|--------|------|']
    if interfaces:
        for item in interfaces:
            if isinstance(item, dict):
                lines.append(
                    f'| {_cell(item.get("name"))} | {_cell(item.get("type"))} '
                    f'| {_cell(item.get("provider"))} | {_cell(item.get("caller"))} '
                    f'| {_cell(item.get("description") or item.get("path") or item.get("method"))} |'
                )
            else:
                lines.append(f'| {_cell(item)} | - | - | - | - |')
    else:
        lines.append('| 待补充 | - | - | - | - |')
    return lines


def render_architecture(data: dict) -> list:
    architecture = data.get('architecture') or {}
    style = architecture.get('style') or '待补充（如单体分层、微服务、事件驱动等）'
    layers = architecture.get('layers') or []
    components = architecture.get('components') or []
    tech_stack = architecture.get('tech_stack') or []
    deployment = architecture.get('deployment') or '待补充'

    lines = ['- **架构风格**: ' + _as_text(style)]
    lines.append('- **技术栈**: ' + _as_text(tech_stack))
    lines.append('- **部署方式**: ' + _as_text(deployment))
    lines.append('')
    if layers:
        lines.append('**分层结构**')
        lines.append('')
        lines.append('| 层次 | 职责 |')
        lines.append('|------|------|')
        for layer in layers:
            if isinstance(layer, dict):
                lines.append(f'| {_cell(layer.get("name"))} | {_cell(layer.get("description"))} |')
            else:
                lines.append(f'| {_cell(layer)} | - |')
    if components:
        lines.append('')
        lines.append('**核心组件**')
        lines.append('')
        lines.append('| 组件 | 说明 |')
        lines.append('|------|------|')
        for comp in components:
            if isinstance(comp, dict):
                lines.append(f'| {_cell(comp.get("name"))} | {_cell(comp.get("description"))} |')
            else:
                lines.append(f'| {_cell(comp)} | - |')
    return lines


def render_entity_summary(entities: list) -> list:
    lines = ['| 实体 | 表名 | 说明 | 字段数 |', '|------|------|------|--------|']
    if entities:
        for entity in entities:
            lines.append(
                f'| {_cell(entity["name"])} | {_cell(entity["table_name"])} '
                f'| {_cell(entity.get("description"))} | {len(entity.get("fields") or [])} |'
            )
    else:
        lines.append('| 待补充 | - | - | 0 |')
    return lines


def render_doc_appendix(data: dict, version: str, mode: str) -> str:
    appendix = ['## 附录', '', '### 待确认事项', '']
    pending = data.get('pending_items', [])
    if pending:
        for item in pending:
            appendix.append(f'- {item}')
    else:
        appendix.append('- 暂无')
    appendix.append('')
    appendix.append(render_change_history(version, mode))
    return '\n'.join(appendix)


def render_change_history(version: str, mode: str) -> str:
    today = date.today().isoformat()
    return '\n'.join([
        '### 变更历史',
        '',
        '| 版本 | 日期 | 变更内容 | 变更人 |',
        '|------|------|----------|--------|',
        f'| v{version} | {today} | {"增量更新" if mode == "incremental" else "初始版本"} | - |',
        '',
    ])


def render_system_overview(data: dict) -> str:
    """Render the system outline specification (系统概要说明书)."""
    project_name = data.get('project_name', '未命名项目')
    features = data.get('features', [])
    modules = group_features(features)
    entities = collect_entities(data)
    nfr = data.get('nfr_baseline') or DEFAULT_NFR

    lines = render_intro(data, DOC_TITLES['system-overview'])

    lines.extend(['## 2. 系统概述', '', '### 2.1 项目背景', ''])
    lines.append(_as_text(data.get('background'), '待补充（业务背景、现状问题与建设动因）'))
    lines.extend(['', '### 2.2 建设目标', ''])
    goals = data.get('goals') or []
    if goals:
        for goal in goals:
            lines.append(f'- {_as_text(goal)}')
    else:
        lines.append('- 待补充')
    lines.extend(['', '### 2.3 用户角色', ''])
    lines.extend(render_roles_table(data.get('roles') or []))
    lines.extend(['', '### 2.4 运行环境', ''])
    architecture = data.get('architecture') or {}
    lines.append(f'- **技术栈**: {_as_text(architecture.get("tech_stack"))}')
    lines.append(f'- **部署方式**: {_as_text(architecture.get("deployment"))}')
    lines.append(f'- **运行环境**: {_as_text(data.get("runtime_env"), "待补充（服务器、操作系统、中间件、网络要求）")}')

    lines.extend(['', '## 3. 总体设计', '', '### 3.1 设计原则', ''])
    principles = data.get('design_principles') or [
        '职责单一：模块边界清晰，避免跨模块耦合',
        '可扩展：预留功能扩展与容量扩展能力',
        '安全合规：敏感数据加密传输与最小权限访问',
        '可运维：统一日志、监控与告警',
    ]
    for item in principles:
        lines.append(f'- {_as_text(item)}')
    lines.extend(['', '### 3.2 系统架构', ''])
    lines.extend(render_architecture(data))
    lines.extend(['', '### 3.3 模块划分', ''])
    lines.extend(render_module_table(modules))

    lines.extend(['', '## 4. 功能概要', '', '### 4.1 功能清单', ''])
    lines.append('| 编号 | 功能 | 所属模块 | 优先级 | 功能描述 |')
    lines.append('|------|------|----------|--------|----------|')
    for feat in features:
        lines.append(
            f'| {_cell(feat.get("id"))} | {_cell(feat.get("name"))} | {_cell(feat.get("module"))} '
            f'| {_cell(feat.get("priority", "medium"))} | {_cell(feat.get("description"))} |'
        )
    if not features:
        lines.append('| - | 待补充 | - | - | - |')

    lines.extend(['', '### 4.2 核心业务流程', ''])
    flow_lines = []
    for feat in features:
        flow = feat.get('flow') or feat.get('interactions') or feat.get('details') or []
        if flow:
            flow_lines.append(f'- **{_as_text(feat.get("name"))}**: {_as_text(flow)}')
    lines.extend(flow_lines or ['- 待补充'])

    lines.extend(['', '## 5. 接口概要', ''])
    lines.extend(render_interfaces_table(data.get('interfaces') or []))

    lines.extend(['', '## 6. 数据概要', '', '### 6.1 主要实体', ''])
    lines.extend(render_entity_summary(entities))
    lines.extend(['', '### 6.2 实体关系', ''])
    relation_lines = []
    for entity in entities:
        for rel in entity.get('relations') or []:
            relation_lines.append(f'- **{entity["name"]}**: {_as_text(rel)}')
    lines.extend(relation_lines or ['- 待补充（详见《数据库设计说明书》）'])

    lines.extend(['', '## 7. 非功能需求', '', '> 以下为默认基线（待确认），如无特殊场景可直接沿用。', ''])
    lines.extend(render_nfr_table(nfr).split('\n'))

    lines.extend(['', '## 8. 约束与假设', '', '### 8.1 约束条件', ''])
    constraints = data.get('constraints') or []
    lines.extend([f'- {_as_text(c)}' for c in constraints] or ['- 待补充'])
    lines.extend(['', '### 8.2 前提假设', ''])
    assumptions = data.get('assumptions') or []
    lines.extend([f'- {_as_text(a)}' for a in assumptions] or ['- 待补充'])
    lines.append('')

    return '\n'.join(lines)


def render_feature_fields(feat: dict) -> list:
    fields = feat.get('fields') or []
    if not fields:
        return []
    lines = ['**字段说明**', '', '| 字段名 | 类型 | 必填 | 校验规则 | 默认值 | 说明 |', '|--------|------|------|----------|--------|------|']
    for idx, raw in enumerate(fields):
        field = normalize_field(raw, idx)
        lines.append(
            f'| {_cell(field["name"])} | {_cell(field["type"])} '
            f'| {"是" if field["required"] else "否"} | {_cell(field["validation"])} '
            f'| {_cell(field["default"])} | {_cell(field["description"])} |'
        )
    lines.append('')
    return lines


def render_feature_actions(feat: dict) -> list:
    actions = feat.get('actions') or []
    if not actions:
        return []
    lines = ['**按钮/操作逻辑**', '', '| 按钮/操作 | 触发条件 | 操作行为 | 异常处理 |', '|-----------|----------|----------|----------|']
    for action in actions:
        if not isinstance(action, dict):
            action = {'name': str(action)}
        lines.append(
            f'| {_cell(action.get("name"))} | {_cell(action.get("condition"))} '
            f'| {_cell(action.get("behavior"))} | {_cell(action.get("error_handling"))} |'
        )
    lines.append('')
    return lines


def render_feature_acceptance(feat: dict) -> list:
    acceptance = feat.get('acceptance_criteria') or []
    lines = ['**验收标准**', '']
    if acceptance:
        lines.extend([f'- [ ] {ac}' for ac in acceptance])
    else:
        lines.append('- [ ] 待补充')
    lines.append('')
    return lines


def render_detailed_design(data: dict) -> str:
    """Render the detailed specification (详细说明书)."""
    features = data.get('features', [])
    modules = group_features(features)

    lines = render_intro(data, DOC_TITLES['detailed-design'])

    lines.extend(['## 2. 总体说明', '', '### 2.1 设计范围', ''])
    lines.append(_as_text(data.get('scope'), '待补充（本次详细设计覆盖的模块与功能）'))
    lines.extend(['', '### 2.2 模块划分', ''])
    lines.extend(render_module_table(modules))
    lines.extend(['', '### 2.3 设计约定', ''])
    conventions = data.get('design_conventions') or [
        '接口统一采用 RESTful 风格，返回结构统一为 {code, message, data}',
        '错误码按模块分段管理，异常信息不得向前端暴露堆栈细节',
        '关键操作记录操作日志，敏感字段脱敏后输出',
        '统一使用 UTC+8 时区，时间字段精确到秒',
    ]
    lines.extend([f'- {_as_text(c)}' for c in conventions])
    lines.append('')

    lines.extend(['## 3. 模块详细设计', ''])
    if modules:
        for m_idx, (module_name, feats) in enumerate(modules.items(), 1):
            lines.append(f'### 3.{m_idx} {module_name}')
            lines.append('')
            lines.append('#### 3.%d.1 模块职责' % m_idx)
            lines.append('')
            module_duties = data.get('module_duties') or {}
            duty = module_duties.get(module_name) if isinstance(module_duties, dict) else None
            lines.append(_as_text(duty, f'负责{module_name}相关的业务处理与数据维护。'))
            lines.append('')
            lines.append('#### 3.%d.2 功能构成' % m_idx)
            lines.append('')
            lines.append('| 编号 | 功能 | 优先级 | 功能描述 |')
            lines.append('|------|------|--------|----------|')
            for feat in feats:
                lines.append(
                    f'| {_cell(feat.get("id"))} | {_cell(feat.get("name"))} '
                    f'| {_cell(feat.get("priority", "medium"))} | {_cell(feat.get("description"))} |'
                )
            lines.append('')
            lines.append('#### 3.%d.3 处理流程与交互' % m_idx)
            lines.append('')
            for feat in feats:
                steps = feat.get('flow') or feat.get('interactions') or feat.get('details') or []
                lines.append(f'**{_as_text(feat.get("id"))} {_as_text(feat.get("name"))}**')
                lines.append('')
                if steps:
                    lines.extend([f'- {_as_text(step)}' for step in steps])
                else:
                    lines.append('- 待补充')
                lines.append('')
            lines.append('#### 3.%d.4 业务规则与异常处理' % m_idx)
            lines.append('')
            rules = []
            for feat in feats:
                for rule in feat.get('business_rules') or []:
                    rules.append(f'- **{_as_text(feat.get("name"))}**: {_as_text(rule)}')
                for rule in feat.get('error_handling') or []:
                    rules.append(f'- **{_as_text(feat.get("name"))}（异常）**: {_as_text(rule)}')
            lines.extend(rules or ['- 待补充'])
            lines.append('')
    else:
        lines.extend(['待补充', ''])

    lines.extend(['## 4. 功能明细', ''])
    if features:
        for idx, feat in enumerate(features, 1):
            lines.append(f'### 4.{idx} {_as_text(feat.get("id"))} {_as_text(feat.get("name"))}')
            lines.append('')
            lines.append('| 属性 | 值 |')
            lines.append('|------|-----|')
            lines.append(f'| 所属模块 | {_cell(feat.get("module"))} |')
            lines.append(f'| 优先级 | {_cell(feat.get("priority", "medium"))} |')
            lines.append('')
            lines.append('**功能描述**')
            lines.append('')
            lines.append(_as_text(feat.get('description')))
            lines.append('')
            lines.extend(render_feature_fields(feat))
            lines.extend(render_feature_actions(feat))
            lines.extend(render_feature_acceptance(feat))
    else:
        lines.extend(['待补充', ''])

    lines.extend(['## 5. 接口详细设计', ''])
    lines.extend(render_interfaces_table(data.get('interfaces') or []))
    lines.append('')

    lines.extend(['## 6. 数据设计', ''])
    lines.extend(render_entity_summary(collect_entities(data)))
    lines.extend(['', '> 完整字段、索引与约束详见《数据库设计说明书》。', ''])

    lines.extend(['## 7. 日志、异常与安全', '', '### 7.1 日志设计', ''])
    lines.append(_as_text(data.get('logging'), '关键业务操作、登录行为与异常错误均需记录日志，日志保留不少于 180 天。'))
    lines.extend(['', '### 7.2 异常处理', ''])
    lines.append(_as_text(data.get('error_strategy'), '统一异常拦截，按错误码返回友好提示；不可恢复异常记录上下文并告警。'))
    lines.extend(['', '### 7.3 安全设计', ''])
    lines.append(_as_text(data.get('security'), '传输层加密、登录态校验、接口鉴权、敏感数据脱敏与最小权限控制。'))
    lines.append('')

    return '\n'.join(lines)


def render_database_design(data: dict) -> str:
    """Render the database design specification (数据库设计说明书)."""
    project_name = data.get('project_name', '未命名项目')
    entities = collect_entities(data)
    database = data.get('database') or 'MySQL 8.0（默认，待确认）'
    nfr = data.get('nfr_baseline') or DEFAULT_NFR

    lines = render_intro(data, DOC_TITLES['database-design'])

    lines.extend(['## 2. 设计概述', '', '### 2.1 设计原则', ''])
    principles = data.get('db_principles') or [
        '满足第三范式，必要时为查询性能做冗余',
        '所有表统一主键、创建时间与更新时间字段',
        '不使用物理外键，关联关系由应用层保证',
        '敏感字段加密存储，禁止明文落库',
    ]
    lines.extend([f'- {_as_text(p)}' for p in principles])
    lines.extend(['', '### 2.2 数据库选型与环境', ''])
    lines.append(f'- **数据库**: {_as_text(database)}')
    lines.append(f'- **字符集**: {_as_text(data.get("charset"), "utf8mb4")}')
    lines.append(f'- **排序规则**: {_as_text(data.get("collation"), "utf8mb4_general_ci")}')
    lines.append(f'- **时区**: {_as_text(data.get("timezone"), "UTC+8")}')
    lines.extend(['', '### 2.3 命名规范', ''])
    lines.append('| 对象 | 规范 | 示例 |')
    lines.append('|------|------|------|')
    lines.append('| 表名 | `t_` 前缀 + 小写下划线 | `t_user` |')
    lines.append('| 字段名 | 小写下划线 | `created_at` |')
    lines.append('| 主键 | 统一 `id` | `id` |')
    lines.append('| 外键 | `<实体>_id` | `user_id` |')
    lines.append('| 索引 | `idx_表名_字段` / `uk_表名_字段` | `idx_user_phone` |')
    lines.extend(['', '### 2.4 数据类型规范', ''])
    lines.append('| 场景 | 类型 | 说明 |')
    lines.append('|------|------|------|')
    lines.append('| 主键 | `bigint unsigned` | 自增或雪花 ID |')
    lines.append('| 短文本 | `varchar(n)` | 按实际长度设置，避免滥用 text |')
    lines.append('| 长文本 | `text` / `longtext` | 富文本、日志等 |')
    lines.append('| 金额 | `decimal(18,2)` | 禁止使用浮点类型 |')
    lines.append('| 时间 | `datetime` | 精确到秒 |')
    lines.append('| 布尔 | `tinyint(1)` | 0/1 |')
    lines.append('| 枚举 | `varchar` + 字典表 | 避免数据库原生 enum |')
    lines.append('')

    lines.extend(['## 3. 逻辑数据模型', '', '### 3.1 实体清单', ''])
    lines.extend(render_entity_summary(entities))
    lines.extend(['', '### 3.2 实体关系', ''])
    relations = data.get('entity_relations') or []
    rel_lines = []
    for rel in relations:
        if isinstance(rel, dict):
            rel_lines.append(
                f'- **{_cell(rel.get("from"))} → {_cell(rel.get("to"))}**'
                f'（{_as_text(rel.get("type"), "1:N")}）: {_as_text(rel.get("description"))}'
            )
        else:
            rel_lines.append(f'- {_as_text(rel)}')
    for entity in entities:
        for rel in entity.get('relations') or []:
            rel_lines.append(f'- **{entity["name"]}**: {_as_text(rel)}')
    lines.extend(rel_lines or ['- 待补充'])

    lines.extend(['', '## 4. 物理表设计', ''])
    if entities:
        for idx, entity in enumerate(entities, 1):
            lines.append(f'### 4.{idx} {entity["table_name"]}（{entity["name"]}）')
            lines.append('')
            lines.append('| 属性 | 值 |')
            lines.append('|------|-----|')
            lines.append(f'| 表名 | `{_cell(entity["table_name"])}` |')
            lines.append(f'| 中文名 | {_cell(entity["name"])} |')
            lines.append(f'| 说明 | {_cell(entity.get("description"))} |')
            lines.append(f'| 主键 | `{_cell(entity.get("primary_key", "id"))}` |')
            lines.append('')
            fields = entity.get('fields') or []
            if fields:
                lines.append('| 序号 | 字段名 | 类型 | 长度 | 允许空 | 默认值 | 约束/索引 | 说明 |')
                lines.append('|------|--------|------|------|--------|--------|-----------|------|')
                for f_idx, raw in enumerate(fields, 1):
                    field = normalize_field(raw, f_idx - 1)
                    flags = []
                    if field['primary_key'] or (raw.get('name') == entity.get('primary_key')):
                        flags.append('PK')
                    if field['index']:
                        flags.append('IDX')
                    if field['validation'] not in ('-', ''):
                        flags.append(_as_text(field['validation'], ''))
                    lines.append(
                        f'| {f_idx} | `{_cell(field["name"])}` | {_cell(field["type"])} '
                        f'| {_cell(field["length"])} | {"否" if field["required"] else "是"} '
                        f'| {_cell(field["default"])} | {_cell(" / ".join(flags) or "-")} '
                        f'| {_cell(field["description"])} |'
                    )
            else:
                lines.append('待补充字段定义。')
            indexes = entity.get('indexes') or []
            if indexes:
                lines.append('')
                lines.append('**索引设计**')
                lines.append('')
                lines.append('| 索引名 | 类型 | 字段 | 说明 |')
                lines.append('|--------|------|------|------|')
                for index in indexes:
                    if isinstance(index, dict):
                        fields_text = index.get('fields') or index.get('columns') or []
                        lines.append(
                            f'| {_cell(index.get("name"))} | {_cell(index.get("type"), "普通索引")} '
                            f'| {_cell(fields_text)} | {_cell(index.get("description"))} |'
                        )
                    else:
                        lines.append(f'| {_cell(index)} | 普通索引 | - | - |')
            lines.append('')
    else:
        lines.extend(['待补充（需求中未识别到字段定义，请补充实体或字段信息）', ''])

    lines.extend(['## 5. 数据字典', ''])
    dictionary = {}
    for entity in entities:
        for raw in entity.get('fields') or []:
            field = normalize_field(raw)
            key = field['name']
            if key not in dictionary:
                dictionary[key] = {
                    'name': field['name'],
                    'type': f'{field["type"]}({field["length"]})' if field['length'] not in ('-', None) else field['type'],
                    'description': field['description'],
                    'tables': [entity['table_name']],
                }
            elif entity['table_name'] not in dictionary[key]['tables']:
                dictionary[key]['tables'].append(entity['table_name'])
    if dictionary:
        lines.append('| 字段名 | 类型 | 说明 | 所属表 |')
        lines.append('|--------|------|------|--------|')
        for item in dictionary.values():
            lines.append(
                f'| `{_cell(item["name"])}` | {_cell(item["type"])} '
                f'| {_cell(item["description"])} | {_cell(item["tables"])} |'
            )
    else:
        lines.append('待补充。')

    lines.extend(['', '## 6. 索引与约束设计', '', '### 6.1 索引策略', ''])
    lines.append(_as_text(data.get('index_strategy'), '高频查询字段建立普通索引；唯一业务标识建立唯一索引；组合索引遵循最左前缀原则。'))
    lines.extend(['', '### 6.2 约束策略', ''])
    lines.append(_as_text(data.get('constraint_strategy'), '主键非空唯一；业务唯一键由唯一索引保证；关联完整性由应用层校验。'))
    lines.extend(['', '## 7. 初始化与迁移', '', '### 7.1 初始化数据', ''])
    init_data = data.get('init_data') or []
    lines.extend([f'- {_as_text(item)}' for item in init_data] or ['- 字典表、系统配置等基础数据随版本初始化。'])
    lines.extend(['', '### 7.2 版本迁移', ''])
    lines.append(_as_text(data.get('migration_strategy'), '每次结构变更提供可回滚的迁移脚本，按版本号顺序执行。'))

    lines.extend(['', '## 8. 安全与权限', '', '### 8.1 数据安全', ''])
    lines.append(_as_text(data.get('data_security'), '敏感字段加密存储，导出与查询遵循最小必要原则，操作留痕。'))
    lines.extend(['', '### 8.2 权限设计', ''])
    lines.append(_as_text(data.get('permission_design'), '按角色分配数据访问权限，应用账号仅授予必需的表级读写权限。'))
    lines.extend(['', '### 8.3 容量与备份', ''])
    lines.append('以下为默认基线（待确认）：')
    lines.append('')
    lines.extend(render_nfr_table(nfr).split('\n'))
    lines.append('')

    return '\n'.join(lines)


def generate_document(data: dict) -> str:
    """Dispatch to the renderer matching doc_type."""
    doc_type = data.get('doc_type', 'prd')
    if doc_type == 'prd':
        return generate_prd(data)

    project_name = data.get('project_name', '未命名项目')
    version = data.get('version', '1.0.0')
    mode = data.get('mode', 'standard')

    parts = [render_doc_frontmatter(project_name, version, DOC_TITLES[doc_type])]
    if doc_type == 'system-overview':
        parts.append(render_system_overview(data))
    elif doc_type == 'detailed-design':
        parts.append(render_detailed_design(data))
    elif doc_type == 'database-design':
        parts.append(render_database_design(data))
    parts.append(render_doc_appendix(data, version, mode))
    return '\n\n'.join(parts)


def generate_prd(data: dict) -> str:
    """Generate the full PRD markdown."""
    features = data.get('features', [])
    assessments = data.get('assessments', [])
    conflicts = data.get('conflicts', [])
    mode = data.get('mode', 'standard')
    template = data.get('template', 'full')
    version = data.get('version', '1.0.0')
    project_name = data.get('project_name', '未命名项目')
    pending = data.get('pending_items', [])
    existing_prd = data.get('existing_prd', '')

    parts = []

    # Frontmatter + Overview
    parts.append(render_frontmatter(project_name, version))
    parts.append(render_overview(features, template))

    # Incremental diff
    if mode == 'incremental' and existing_prd:
        parts.append(render_incremental_diff(features, existing_prd))

    # Feature list
    parts.append(render_feature_list(features, template))

    # Appendix
    appendix = ['## 附录\n']
    nfr_section = render_nfr_baseline(data.get('nfr_baseline', []))
    if nfr_section:
        appendix.append(nfr_section)
    need_map = render_need_feature_map(data.get('need_feature_map', []))
    if need_map:
        appendix.append(need_map)
    appendix.append(render_pending_items(pending, conflicts))
    if template == 'full':
        quality = render_quality_report(assessments)
        if quality:
            appendix.append(quality)
    parts.append('\n'.join(appendix))

    # Change history
    today = date.today().isoformat()
    parts.append(f'\n### 变更历史\n')
    parts.append(f'| 版本 | 日期 | 变更内容 | 变更人 |')
    parts.append(f'|------|------|----------|--------|')
    parts.append(f'| v{version} | {today} | {"增量更新" if mode == "incremental" else "初始版本"} | - |\n')

    return '\n\n'.join(parts)


def main():
    parser = argparse.ArgumentParser(description='Generate delivery documents from structured data')
    parser.add_argument('--output', '-o', default=None,
                        help='Output file path (defaults to a name based on --doc-type)')
    parser.add_argument('--template', '-t', choices=sorted(ALLOWED_TEMPLATES), default=None,
                        help='PRD template: full (complete) or summary (business summary)')
    parser.add_argument('--doc-type', '-d', choices=sorted(ALLOWED_DOC_TYPES), default=None,
                        help='Document type: prd | system-overview | detailed-design | database-design')
    args = parser.parse_args()

    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({'status': 'error', 'message': 'Empty stdin input'}))
            sys.exit(1)

        data = json.loads(raw)
        validate_input(data)

        if args.template:
            data['template'] = args.template
        if args.doc_type:
            data['doc_type'] = args.doc_type

        doc_type = data.get('doc_type', 'prd')
        document = generate_document(data)

        output_path = args.output or ('./' + DEFAULT_OUTPUTS[doc_type])
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(document)

        print(json.dumps({
            'status': 'ok',
            'path': os.path.abspath(output_path),
            'doc_type': doc_type,
            'size': len(document)
        }))

    except json.JSONDecodeError as e:
        print(json.dumps({'status': 'error', 'message': f'Invalid JSON input: {str(e)}'}))
        sys.exit(1)
    except ValueError as e:
        print(json.dumps({'status': 'error', 'message': str(e)}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({'status': 'error', 'message': f'Unexpected error: {str(e)}'}))
        sys.exit(1)


if __name__ == '__main__':
    main()
