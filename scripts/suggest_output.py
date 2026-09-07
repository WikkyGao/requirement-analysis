#!/usr/bin/env python3
"""
suggest_output.py - 基于当前文件目录结构推荐 PRD 输出路径

扫描工作区，识别已有的文档类子目录（docs/文档/PRD 等），给出推荐输出路径，
供用户选择是否输出到指定子目录或工作区根目录。

接收 stdin JSON:
  {"cwd": "...", "default": "PRD.md", "project_name": "..."}

输出 stdout JSON:
  {"status": "ok", "cwd": "...", "dirs": [...], "doc_dirs": [...],
   "recommended": "...", "reason": "...", "choices": [...], "existing_prd": bool}
"""
import json
import os
import sys


# 视为"文档类"子目录的命名特征
DOC_DIR_NAMES = {'docs', 'doc', 'document', 'documents', 'documentation',
                 'prd', 'prds', 'requirements', 'requirement', 'output', 'out',
                 '文档', '需求', '需求文档', '产物', '输出'}
DOC_KEYWORDS = ('doc', 'prd', 'requirement', '文档', '需求', '输出', '产物')
# 系统/依赖目录，跳过
EXCLUDED_DIRS = {'node_modules', '.git', 'dist', 'build', '.venv', 'venv',
                 '__pycache__', '.idea', '.vscode', 'target', 'bin', 'obj'}


def scan_dirs(cwd: str) -> list:
    dirs = []
    try:
        for name in sorted(os.listdir(cwd)):
            full = os.path.join(cwd, name)
            if not os.path.isdir(full):
                continue
            if name.startswith('.') or name in EXCLUDED_DIRS:
                continue
            dirs.append(name)
    except Exception:
        pass
    return dirs


def is_doc_like(name: str) -> bool:
    low = name.lower()
    return low in DOC_DIR_NAMES or any(k in low for k in DOC_KEYWORDS)


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({'status': 'error', 'message': 'Empty stdin input'}))
            sys.exit(1)

        data = json.loads(raw)
        cwd = data.get('cwd') or os.getcwd()
        default = data.get('default', 'PRD.md')

        dirs = scan_dirs(cwd)
        doc_dirs = [d for d in dirs if is_doc_like(d)]
        existing_prd = os.path.isfile(os.path.join(cwd, 'PRD.md'))

        # 推荐路径：优先落到第一个文档类子目录，否则输出到工作区根目录
        if doc_dirs:
            recommended = os.path.join(cwd, doc_dirs[0], default)
            reason = f'检测到文档类子目录 `{doc_dirs[0]}`，建议输出到该子目录'
        else:
            recommended = os.path.join(cwd, default)
            reason = '未检测到文档类子目录，建议输出到工作区根目录'

        choices = []
        root_path = os.path.join(cwd, default)
        choices.append({
            'path': root_path,
            'label': '工作区根目录',
            'exists': os.path.isfile(root_path)
        })
        for d in doc_dirs:
            p = os.path.join(cwd, d, default)
            choices.append({
                'path': p,
                'label': f'子目录 `{d}`',
                'exists': os.path.isfile(p)
            })

        print(json.dumps({
            'status': 'ok',
            'cwd': cwd,
            'dirs': dirs,
            'doc_dirs': doc_dirs,
            'recommended': recommended,
            'reason': reason,
            'choices': choices,
            'existing_prd': existing_prd
        }, ensure_ascii=False))

    except json.JSONDecodeError as e:
        print(json.dumps({'status': 'error', 'message': f'Invalid JSON input: {str(e)}'}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({'status': 'error', 'message': f'Unexpected error: {str(e)}'}))
        sys.exit(1)


if __name__ == '__main__':
    main()
