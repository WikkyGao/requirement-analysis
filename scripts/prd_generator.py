#!/usr/bin/env python3
"""
prd_generator.py - 按标准模板生成 PRD.md
接收 stdin JSON: {"features": [...], "assessments": [...], "conflicts": [...],
                  "mode": "standard|quick|incremental", "version": "1.0.0",
                  "project_name": "...", "pending_items": [...],
                  "existing_prd": "..." (incremental mode)}
接收命令行参数: --output ./PRD.md
输出 stdout JSON: {"status": "ok", "path": "PRD.md"} 或 {"status": "error", ...}
"""
import argparse
import json
import os
import re
import sys
from datetime import date


ALLOWED_MODES = frozenset({'standard', 'quick', 'incremental'})


def validate_input(data: dict) -> None:
    if 'features' not in data:
        raise ValueError('"features" is required')
    if not isinstance(data['features'], list):
        raise ValueError('"features" must be an array')
    if 'mode' in data and data['mode'] not in ALLOWED_MODES:
        raise ValueError(f'"mode" must be one of: {", ".join(sorted(ALLOWED_MODES))}')


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


def render_overview(features: list) -> str:
    """Render the requirements overview section."""
    modules = set(f['module'] for f in features if f.get('module'))
    return f"""## 需求概述

### 核心目标

通过整合多来源需求，生成标准化产品需求文档。

### 功能范围

- **模块数**: {len(modules)} 个
- **功能项**: {len(features)} 个
- **覆盖模块**: {', '.join(sorted(modules)) if modules else '待确定'}
"""


def render_feature_list(features: list) -> str:
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

            # Acceptance criteria
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


def render_pending_items(pending: list, conflicts: list) -> str:
    """Render pending items and conflicts section."""
    lines = ['## 附录\n', '### 待确认事项\n']

    if conflicts:
        lines.append(f'#### 冲突项\n')
        for c in conflicts:
            ctype = c.get('type', 'unknown')
            severity = c.get('severity', 'medium')
            fname = c.get('feature_name', '')
            marker = '🔴' if severity == 'high' else '⚠️'
            lines.append(f'- **{fname}** 存在 {ctype}:')

            details = c.get('details', {})
            if 'versions' in details:
                for v in details['versions']:
                    lines.append(f'  - {v.get("source", "?")}: "{v.get("type", v.get("required", "?"))}"')
            if 'version_a' in details and 'version_b' in details:
                va = details['version_a']
                vb = details['version_b']
                lines.append(f'  - {va.get("source", "?")}: "{va.get("description", "?")}"')
                lines.append(f'  - {vb.get("source", "?")}: "{vb.get("description", "?")}"')
            lines.append(f'  - {marker} 待确认\n')

    if pending:
        lines.append(f'#### 待补充项\n')
        for item in pending:
            lines.append(f'- {item}\n')

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


def generate_prd(data: dict) -> str:
    """Generate the full PRD markdown."""
    features = data.get('features', [])
    assessments = data.get('assessments', [])
    conflicts = data.get('conflicts', [])
    mode = data.get('mode', 'standard')
    version = data.get('version', '1.0.0')
    project_name = data.get('project_name', '未命名项目')
    pending = data.get('pending_items', [])
    existing_prd = data.get('existing_prd', '')

    parts = []

    # Frontmatter + Overview
    parts.append(render_frontmatter(project_name, version))
    parts.append(render_overview(features))

    # Incremental diff
    if mode == 'incremental' and existing_prd:
        parts.append(render_incremental_diff(features, existing_prd))

    # Feature list
    parts.append(render_feature_list(features))

    # Pending items & conflicts
    parts.append(render_pending_items(pending, conflicts))

    # Quality report
    quality = render_quality_report(assessments)
    if quality:
        parts.append(quality)

    # Change history
    today = date.today().isoformat()
    parts.append(f'\n### 变更历史\n')
    parts.append(f'| 版本 | 日期 | 变更内容 | 变更人 |')
    parts.append(f'|------|------|----------|--------|')
    parts.append(f'| v{version} | {today} | {"增量更新" if mode == "incremental" else "初始版本"} | - |\n')

    return '\n\n'.join(parts)


def main():
    parser = argparse.ArgumentParser(description='Generate PRD.md from structured data')
    parser.add_argument('--output', '-o', default='./PRD.md', help='Output file path')
    args = parser.parse_args()

    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({'status': 'error', 'message': 'Empty stdin input'}))
            sys.exit(1)

        data = json.loads(raw)
        validate_input(data)

        prd_content = generate_prd(data)

        output_path = args.output
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(prd_content)

        print(json.dumps({
            'status': 'ok',
            'path': os.path.abspath(output_path),
            'size': len(prd_content)
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
