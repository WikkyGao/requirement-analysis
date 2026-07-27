#!/usr/bin/env python3
"""
package_skill.py - 打包技能为 .skill 文件
接收命令行参数: python package_skill.py <skill-dir> [--output <path>]
输出 stdout JSON: {"status": "ok", "package_path": "..."} 或 {"status": "error", ...}
"""
import argparse
import json
import os
import re
import shutil
import sys
import tarfile
from datetime import date


EXCLUDE_DIRS = frozenset({'evals', '__pycache__', '.git', 'node_modules'})
EXCLUDE_FILES = frozenset({'.DS_Store', 'Thumbs.db', '.gitignore'})
REQUIRED_FILES = frozenset({'SKILL.md'})


def validate_skill_dir(skill_dir: str) -> dict:
    """Validate the skill directory structure."""
    issues = []
    required_ok = True

    # Check required files
    for req in REQUIRED_FILES:
        if not os.path.isfile(os.path.join(skill_dir, req)):
            issues.append(f'Missing required file: {req}')
            required_ok = False

    # Read SKILL.md and validate frontmatter
    skill_path = os.path.join(skill_dir, 'SKILL.md')
    if os.path.isfile(skill_path):
        with open(skill_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check frontmatter
        fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not fm_match:
            issues.append('SKILL.md missing YAML frontmatter (--- ... ---)')
        else:
            fm = fm_match.group(1)
            if not re.search(r'^name:\s*\S', fm, re.MULTILINE):
                issues.append('frontmatter missing "name" field')
            if not re.search(r'^description:\s*\S', fm, re.MULTILINE):
                issues.append('frontmatter missing "description" field')

    return {
        'valid': len(issues) == 0,
        'required_ok': required_ok,
        'issues': issues
    }


def collect_files(skill_dir: str) -> list:
    """Collect all files to be included."""
    files = []
    for root, dirs, fnames in os.walk(skill_dir):
        # Skip excluded dirs
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for fname in fnames:
            if fname in EXCLUDE_FILES:
                continue
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, skill_dir)
            files.append({
                'path': full_path,
                'relative': rel_path,
                'size': os.path.getsize(full_path)
            })

    return files


def create_package(skill_dir: str, output_path: str) -> str:
    """Create the .skill tar.gz package."""
    export_name = os.path.basename(os.path.normpath(skill_dir))
    package_name = f'{export_name}.skill'

    if output_path:
        if os.path.isdir(output_path):
            package_path = os.path.join(output_path, package_name)
        else:
            package_path = output_path
    else:
        parent = os.path.dirname(os.path.normpath(skill_dir))
        package_path = os.path.join(parent or '.', package_name)

    with tarfile.open(package_path, 'w:gz') as tar:
        for root, dirs, fnames in os.walk(skill_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for fname in fnames:
                if fname in EXCLUDE_FILES:
                    continue
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, skill_dir)
                tar.add(full_path, arcname=os.path.join(export_name, rel_path))

    return os.path.abspath(package_path)


def main():
    parser = argparse.ArgumentParser(description='Package skill into .skill file')
    parser.add_argument('skill_dir', help='Path to the skill directory')
    parser.add_argument('--output', '-o', help='Output path or directory')
    args = parser.parse_args()

    try:
        skill_dir = os.path.abspath(args.skill_dir)

        if not os.path.isdir(skill_dir):
            print(json.dumps({'status': 'error', 'message': f'Directory not found: {skill_dir}'}))
            sys.exit(1)

        # Validate
        validation = validate_skill_dir(skill_dir)
        if not validation['valid']:
            print(json.dumps({
                'status': 'error',
                'message': 'Validation failed',
                'issues': validation['issues']
            }, ensure_ascii=False))
            sys.exit(1)

        # Collect file listing
        files = collect_files(skill_dir)
        total_size = sum(f['size'] for f in files)

        # Create package
        package_path = create_package(skill_dir, args.output)

        print(json.dumps({
            'status': 'ok',
            'package_path': package_path,
            'files_included': len(files),
            'total_size_bytes': total_size,
            'validation': validation
        }, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({'status': 'error', 'message': f'Unexpected error: {str(e)}'}))
        sys.exit(1)


if __name__ == '__main__':
    main()
