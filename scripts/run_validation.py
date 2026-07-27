#!/usr/bin/env python3
"""
run_validation.py - 验证 SKILL.md 结构完整性
接收命令行参数: python run_validation.py <skill-path> [--json <stdin JSON>]
输出 stdout JSON: {"status": "success|failure", "summary": {...}, "checks": [...]}
"""
import argparse
import json
import os
import re
import sys


CHECKS = {
    'frontmatter_name': {'name': 'YAML frontmatter name 存在'},
    'frontmatter_desc': {'name': 'YAML frontmatter description 存在且不超1024字符'},
    'workflow_tag': {'name': '<workflow> 标签存在'},
    'task_tags': {'name': '<task> 标签结构完整'},
    'mermaid_exists': {'name': 'Mermaid 工作流图存在'},
    'scene_recognition': {'name': '场景识别声明存在'},
    'no_ref_section': {'name': '无独立 References/Scripts 章节（反模式 #2）'},
    'forward_slash': {'name': '路径使用正斜杠'},
    'body_line_count': {'name': 'Body 行数 <= 500'},
    'mermaid_task_match': {'name': 'Mermaid 节点与 Task 标签对应'},
    'script_ref_exists': {'name': '脚本引用路径存在'},
    'ref_ref_exists': {'name': 'References 引用路径存在'},
    'no_node_ref': {'name': '无节点级引用句式（反模式 #19）'},
    'constraint_wording': {'name': '约束措辞规范（使用 "必须"/"禁止"/"不得"）'},
    'checkpoint_exists': {'name': 'CHECKPOINT 存在'},
    'division_labor': {'name': '每个 Task 标注了分工模式'},
}


def check_frontmatter(content: str) -> dict:
    results = {}
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not fm_match:
        results['frontmatter_name'] = {'passed': False, 'message': 'Missing YAML frontmatter'}
        results['frontmatter_desc'] = {'passed': False, 'message': 'Missing YAML frontmatter'}
        return results

    fm = fm_match.group(1)

    name_match = re.search(r'^name:\s*(\S+)', fm, re.MULTILINE)
    results['frontmatter_name'] = {
        'passed': bool(name_match),
        'message': 'Found: ' + (name_match.group(1) if name_match else 'missing')
    }

    desc_match = re.search(r'^description:\s*(.+?)$', fm, re.MULTILINE)
    desc_ok = bool(desc_match) and len(desc_match.group(1)) <= 1024
    results['frontmatter_desc'] = {
        'passed': desc_ok,
        'message': 'Found' if desc_match else 'Missing',
        'length': len(desc_match.group(1)) if desc_match else 0
    }

    return results


def check_tags(content: str) -> dict:
    has_workflow = '<workflow>' in content and '</workflow>' in content
    has_constraint = '<constraint>' in content
    task_tags = re.findall(r'<task[^>]*>', content)
    task_closes = re.findall(r'</task>', content)
    task_count = len(task_tags)
    tags_match = task_count == len(task_closes) and task_count >= 2

    return {
        'workflow_tag': {'passed': has_workflow, 'message': '<workflow> tag found' if has_workflow else 'Missing <workflow>'},
        'task_tags': {'passed': tags_match, 'message': f'{task_count} task tags, {len(task_closes)} closing tags'}
    }


def check_mermaid(content: str) -> dict:
    mermaid_match = re.search(r'```mermaid\n(.*?)```', content, re.DOTALL)
    if not mermaid_match:
        return {'mermaid_exists': {'passed': False, 'message': 'No mermaid diagram found'}}

    mermaid = mermaid_match.group(1)
    has_nodes = 'Task' in mermaid or 'T0' in mermaid

    return {'mermaid_exists': {'passed': has_nodes, 'message': 'Mermaid diagram found'}}


def check_scene_recognition(content: str) -> dict:
    # Look for scene recognition table or conditional logic
    has_table = '| 条件 | 场景 |' in content
    has_sr = '场景识别' in content or 'SR{{' in content
    return {'scene_recognition': {'passed': has_table and has_sr, 'message': 'Scene recognition found' if has_table else 'Missing scene recognition'}}


def check_no_ref_section(content: str) -> dict:
    """Check that there's no standalone References/scripts section (anti-pattern #2)."""
    # The workflow section is OK - check for standalone ## references section
    body = content.split('---')[-1] if '---' in content else content
    standalone_ref_section = bool(re.search(r'^##\s*(References|参考资料|脚本清单|文件清单)\s*$', body, re.MULTILINE))
    return {'no_ref_section': {'passed': not standalone_ref_section, 'message': 'No standalone ref section' if not standalone_ref_section else 'Found standalone ref section'}}


def check_forward_slash(content: str) -> dict:
    """Check paths use forward slashes."""
    backslash_paths = re.findall(r'(?:scripts\\)|(?:references\\)', content)
    return {'forward_slash': {'passed': len(backslash_paths) == 0, 'message': f'Found {len(backslash_paths)} backslash paths' if backslash_paths else 'All paths use forward slashes'}}


def check_body_line_count(content: str) -> dict:
    """Check body lines <= 500."""
    lines = content.split('\n')
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip() == '---':
            body_start = i + 1
            break

    body_lines = len(lines) - body_start
    return {'body_line_count': {'passed': body_lines <= 500, 'message': f'{body_lines} lines in body' if body_lines <= 500 else f'Body is {body_lines} lines (max 500)'}}


def check_mermaid_task_match(content: str) -> dict:
    """Check Mermaid nodes match Task labels."""
    mermaid_match = re.search(r'```mermaid\n(.*?)```', content, re.DOTALL)
    if not mermaid_match:
        return {'mermaid_task_match': {'passed': False, 'message': 'No mermaid to check'}}

    mermaid = mermaid_match.group(1)
    # Extract task numbers from mermaid labels like ["T0: 标准模式"] or ["T1.5: ..."]
    mermaid_task_labels = set(re.findall(r'\["(T\d+(?:\.\d+)?):', mermaid))

    # Extract task numbers from task sections
    task_sections = set(re.findall(r'### Task (\d+(?:\.\d+)?):', content))

    if not mermaid_task_labels and not task_sections:
        return {'mermaid_task_match': {'passed': True, 'message': 'No discrete tasks to check'}}

    # Compare by stripping T prefix
    mermaid_nums = set(n.lstrip('T') for n in mermaid_task_labels)
    has_overlap = bool(mermaid_nums & task_sections)
    all_match = mermaid_nums == task_sections
    return {
        'mermaid_task_match': {
            'passed': has_overlap,
            'message': 'All match' if all_match else f'Mermaid labels: {sorted(mermaid_nums)}, Task sections: {sorted(task_sections)}'
        }
    }


def check_script_refs(content: str, skill_dir: str) -> dict:
    """Check that referenced scripts exist."""
    script_refs = re.findall(r'scripts/([\w_]+\.py)', content)
    missing = []
    for ref in set(script_refs):
        full_path = os.path.join(skill_dir, 'scripts', ref)
        if not os.path.isfile(full_path):
            missing.append(ref)

    return {'script_ref_exists': {'passed': len(missing) == 0, 'message': f'Missing: {", ".join(missing)}' if missing else f'All {len(set(script_refs))} script refs exist'}}


def check_ref_refs(content: str, skill_dir: str) -> dict:
    """Check that referenced reference files exist."""
    ref_refs = re.findall(r'references/([\w_-]+\.md)', content)
    missing = []
    for ref in set(ref_refs):
        full_path = os.path.join(skill_dir, 'references', ref)
        if not os.path.isfile(full_path):
            missing.append(ref)

    return {'ref_ref_exists': {'passed': len(missing) == 0, 'message': f'Missing: {", ".join(missing)}' if missing else f'All {len(set(ref_refs))} ref refs exist'}}


def check_no_node_ref(content: str) -> dict:
    """Check for node-level reference (anti-pattern #19)."""
    node_refs = re.findall(r'references/[\w_/-]+\.md\s+中的\s+\S+', content)
    return {'no_node_ref': {'passed': len(node_refs) == 0, 'message': f'Found {len(node_refs)} node-level refs' if node_refs else 'No node-level references'}}


def check_constraint_wording(content: str) -> dict:
    """Check constraints use strong wording (must/must not)."""
    # Find constraints section
    constraint_match = re.search(r'<constraint[^>]*>(.*?)</constraint>', content, re.DOTALL)
    if not constraint_match:
        return {'constraint_wording': {'passed': False, 'message': 'No <constraint> section'}}

    constraint_text = constraint_match.group(1)

    # Check for fuzzy wording in constraint context (not in example/description text)
    fuzzy = re.findall(r'(可以考虑|适当|尽量|合理)', constraint_text)
    strong = re.findall(r'(必须|禁止|不得|MUST|SHALL)', constraint_text)

    return {'constraint_wording': {'passed': len(fuzzy) == 0, 'message': f'Fuzzy wording: {fuzzy}' if fuzzy else f'Strong wording count: {len(strong)}'}}


def check_checkpoint(content: str) -> dict:
    checkpoint_count = len(re.findall(r'🔴\s*CHECKPOINT', content))
    return {'checkpoint_exists': {'passed': checkpoint_count >= 2, 'message': f'{checkpoint_count} 🔴 CHECKPOINTs found' if checkpoint_count >= 2 else f'Only {checkpoint_count} CHECKPOINTs (need >=2)'}}


def check_division_labor(content: str) -> dict:
    """Check each task has division of labor annotation."""
    task_sections = re.findall(r'\*\*分工\*\*:\s*\[([^\]]+)\]', content)
    return {'division_labor': {'passed': len(task_sections) >= 3, 'message': f'{len(task_sections)} tasks with division of labor'}}


def validate(skill_dir: str) -> dict:
    """Run all validation checks."""
    skill_path = os.path.join(skill_dir, 'SKILL.md')
    if not os.path.isfile(skill_path):
        return {
            'status': 'failure',
            'summary': {'total': 0, 'passed': 0, 'failed': 1, 'warnings': 0},
            'checks': [{'id': 'file_exists', 'name': 'SKILL.md exists', 'passed': False, 'message': 'File not found'}]
        }

    with open(skill_path, 'r', encoding='utf-8') as f:
        content = f.read()

    all_checks = {}

    # Run all checks
    all_checks.update(check_frontmatter(content))
    all_checks.update(check_tags(content))
    all_checks.update(check_mermaid(content))
    all_checks.update(check_scene_recognition(content))
    all_checks.update(check_no_ref_section(content))
    all_checks.update(check_forward_slash(content))
    all_checks.update(check_body_line_count(content))
    all_checks.update(check_mermaid_task_match(content))
    all_checks.update(check_script_refs(content, skill_dir))
    all_checks.update(check_ref_refs(content, skill_dir))
    all_checks.update(check_no_node_ref(content))
    all_checks.update(check_constraint_wording(content))
    all_checks.update(check_checkpoint(content))
    all_checks.update(check_division_labor(content))

    # Format results
    checks = []
    passed = 0
    failed = 0
    for cid, info in all_checks.items():
        c = {
            'id': cid,
            'name': CHECKS.get(cid, {}).get('name', cid),
            'passed': info.get('passed', False)
        }
        if 'message' in info:
            c['message'] = info['message']
        if info.get('passed', False):
            passed += 1
        else:
            failed += 1
        checks.append(c)

    status = 'success' if failed == 0 else 'failure'

    return {
        'status': status,
        'summary': {'total': len(checks), 'passed': passed, 'failed': failed, 'warnings': 0},
        'checks': checks
    }


def main():
    parser = argparse.ArgumentParser(description='Validate skill structure')
    parser.add_argument('skill_dir', help='Path to skill directory')
    parser.add_argument('--json', action='store_true', help='Expect JSON context from stdin')
    args = parser.parse_args()

    result = validate(args.skill_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result['status'] == 'failure':
        sys.exit(1)


if __name__ == '__main__':
    main()
