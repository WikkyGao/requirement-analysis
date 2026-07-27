#!/usr/bin/env python3
"""
feature_extractor.py - 从解析后的中间 JSON 提取结构化功能项
接收 stdin JSON: {"parsed_data": {...}}
输出 stdout JSON: {"status": "ok", "features": [...]} 或 {"status": "error", ...}
"""
import json
import sys
import uuid


def validate_input(data: dict) -> None:
    if 'parsed_data' not in data:
        raise ValueError('"parsed_data" is required')
    if not isinstance(data['parsed_data'], dict):
        raise ValueError('"parsed_data" must be a dict')


def extract_from_markdown(parsed: dict) -> list:
    """Extract features from markdown-parsed structure."""
    features = []
    for module in parsed.get('modules', []):
        module_name = module.get('name', 'Unnamed Module')
        for feat in module.get('features', []):
            feature = {
                'id': _generate_id(module_name, feat.get('name', '')),
                'name': feat.get('name', ''),
                'description': feat.get('description', ''),
                'module': module_name,
                'priority': _infer_priority(feat.get('details', [])),
                'fields': _extract_fields(feat.get('fields', [])),
                'actions': _infer_actions(feat.get('details', [])),
                'interactions': [],
                'acceptance_criteria': [],
                'details': feat.get('details', []),
                'source': parsed.get('source', {})
            }
            features.append(feature)
    return features


def extract_from_excel(parsed: dict) -> list:
    """Extract features from Excel sheets."""
    features = []
    for sheet in parsed.get('sheets', []):
        headers = sheet.get('headers', [])
        rows = sheet.get('rows', [])

        # Heuristic: find module, function name, description columns
        module_col = _find_column(headers, ['module', '模块', 'mod'])
        name_col = _find_column(headers, ['feature name', '功能名称', 'name', '功能名'])
        desc_col = _find_column(headers, ['description', '功能描述', '描述', 'desc'])
        priority_col = _find_column(headers, ['priority', '优先级', 'pri'])

        sheet_name = sheet.get('name', 'Sheet1')
        # Treat sheet name as module if no module column
        if module_col is None:
            module_name = sheet_name
        else:
            module_name = ''

        for row in rows:
            if module_col is not None:
                module_name = row.get(headers[module_col], sheet_name)
            feat_name = row.get(headers[name_col], '') if name_col is not None else ''
            feat_desc = row.get(headers[desc_col], '') if desc_col is not None else ''
            feat_priority = row.get(headers[priority_col], 'medium').lower() if priority_col is not None else 'medium'

            if not feat_name:
                continue

            # Normalize priority
            if feat_priority in ('high', 'h', '高'):
                feat_priority = 'high'
            elif feat_priority in ('low', 'l', '低'):
                feat_priority = 'low'
            else:
                feat_priority = 'medium'

            feature = {
                'id': _generate_id(module_name, feat_name),
                'name': feat_name,
                'description': feat_desc,
                'module': module_name,
                'priority': feat_priority,
                'fields': [],
                'actions': [],
                'interactions': [],
                'acceptance_criteria': [],
                'details': [],
                'source': parsed.get('source', {})
            }
            features.append(feature)

    return features


def extract_from_mindmap(parsed: dict) -> list:
    """Extract features from mind map structure."""
    features = []
    for module in parsed.get('modules', []):
        module_name = module.get('name', 'Unnamed Module')
        for feat in module.get('features', []):
            feature = {
                'id': _generate_id(module_name, feat.get('name', '')),
                'name': feat.get('name', ''),
                'description': feat.get('description', ''),
                'module': module_name,
                'priority': 'medium',
                'fields': [],
                'actions': [],
                'interactions': [],
                'acceptance_criteria': [],
                'details': feat.get('details', []),
                'source': parsed.get('source', {})
            }
            features.append(feature)
    return features


def _generate_id(module: str, name: str) -> str:
    """Generate a feature ID from module and name."""
    base = f'{module}-{name}'
    # Keep Chinese characters, replace spaces/special chars with hyphens
    clean = re.sub(r'[^\w\u4e00-\u9fff\-]', '-', base)
    clean = re.sub(r'-+', '-', clean).strip('-')
    return f'F-{clean}' if clean else f'F-{uuid.uuid4().hex[:8]}'


def _infer_priority(details: list) -> str:
    """Infer priority from detail text."""
    high_keywords = {'high', '高', 'critical', 'urgent', '核心', '必须', 'p0', 'p1'}
    low_keywords = {'low', '低', 'optional', 'nice to have', '可选', 'p3', 'p4'}

    for d in details:
        d_lower = d.lower()
        if any(k in d_lower for k in high_keywords):
            return 'high'
        if any(k in d_lower for k in low_keywords):
            return 'low'
    return 'medium'


def _find_column(headers: list, candidates: list) -> int | None:
    """Find column index by header name matching."""
    for i, h in enumerate(headers):
        h_clean = h.strip().lower()
        for c in candidates:
            if c.lower() in h_clean or h_clean in c.lower():
                return i
    return None


def _extract_fields(raw_fields: list) -> list:
    """Extract structured field definitions."""
    fields = []
    for field in raw_fields:
        if isinstance(field, dict):
            f = {
                'name': field.get('name') or field.get('字段名', ''),
                'type': field.get('type') or field.get('类型', 'string'),
                'required': _parse_required(field.get('required') or field.get('必填', False)),
                'validation': field.get('validation') or field.get('校验规则', ''),
                'default': field.get('default') or field.get('默认值', ''),
                'description': field.get('description') or field.get('说明', '')
            }
            fields.append(f)
    return fields


def _parse_required(val) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ('yes', 'y', 'true', 't', '1', '是', '必填')
    return False


def _infer_actions(details: list) -> list:
    """Infer button/operation actions from detail text."""
    action_keywords = {
        'register': '注册',
        'login': '登录',
        'logout': '退出',
        'create': '创建',
        'add': '添加',
        'edit': '编辑',
        'update': '更新',
        'delete': '删除',
        'save': '保存',
        'submit': '提交',
        'cancel': '取消',
        'export': '导出',
        'import': '导入',
        'search': '搜索',
        'filter': '筛选',
        'approve': '审批',
        'reject': '驳回',
        'upload': '上传',
        'download': '下载',
    }
    actions = []
    for d in details:
        d_lower = d.lower()
        for eng, cn in action_keywords.items():
            if eng in d_lower or cn in d:
                actions.append({
                    'name': d.strip(),
                    'condition': '',
                    'behavior': d.strip(),
                    'error_handling': ''
                })
                break
    return actions


def main():
    # Import re here to avoid top-level shadowing
    global re
    import re

    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({'status': 'error', 'message': 'Empty stdin input'}))
            sys.exit(1)

        data = json.loads(raw)

        # Check if this is raw parse_document output or already a parsed structure
        if 'parsed_data' in data:
            parsed_data = data['parsed_data']
        else:
            parsed_data = data

        # Determine the source format from the data structure
        if 'modules' in parsed_data:
            features = extract_from_markdown(parsed_data)
        elif 'sheets' in parsed_data:
            features = extract_from_excel(parsed_data)
        else:
            features = extract_from_mindmap(parsed_data)

        output = {
            'status': 'ok',
            'count': len(features),
            'features': features
        }
        print(json.dumps(output, ensure_ascii=False))

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
