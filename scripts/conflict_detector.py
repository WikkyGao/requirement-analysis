#!/usr/bin/env python3
"""
conflict_detector.py - 跨文档冲突检测
接收 stdin JSON: {"features_by_source": {"doc1.md": [...], "doc2.xlsx": [...]}}
输出 stdout JSON: {"status": "ok", "conflicts": [...]} 或 {"status": "error", ...}
"""
import json
import sys


CONFLICT_TYPES = frozenset({'description_conflict', 'field_type_conflict',
                            'required_conflict', 'logic_contradiction'})


def validate_input(data: dict) -> None:
    if 'features_by_source' not in data:
        raise ValueError('"features_by_source" is required')
    sources = data['features_by_source']
    if not isinstance(sources, dict) or len(sources) < 2:
        raise ValueError('Need at least 2 document sources to detect conflicts')


def normalize_name(name: str) -> str:
    """Normalize feature name for comparison (remove spaces, lowercase)."""
    return ''.join(name.split()).lower()


def group_features_by_normalized_name(sources: dict) -> dict:
    """Group features across documents by normalized name."""
    groups = {}
    for doc_name, features in sources.items():
        for feat in features:
            key = normalize_name(feat.get('name', ''))
            if not key:
                continue
            if key not in groups:
                groups[key] = []
            groups[key].append({
                'source': doc_name,
                'feature': feat
            })
    # Only return groups that appear in multiple sources
    return {k: v for k, v in groups.items() if len(v) >= 2}


def detect_description_conflicts(group: list) -> list:
    """Detect description inconsistencies."""
    conflicts = []
    descriptions = [(item['source'], item['feature'].get('description', '').strip())
                    for item in group]

    # Compare each pair
    for i in range(len(descriptions)):
        for j in range(i + 1, len(descriptions)):
            src_a, desc_a = descriptions[i]
            src_b, desc_b = descriptions[j]
            if desc_a and desc_b and desc_a != desc_b:
                conflicts.append({
                    'type': 'description_conflict',
                    'severity': 'medium',
                    'feature_name': group[0]['feature'].get('name', ''),
                    'details': {
                        'version_a': {'source': src_a, 'description': desc_a},
                        'version_b': {'source': src_b, 'description': desc_b}
                    }
                })
    return conflicts


def detect_field_type_conflicts(group: list) -> list:
    """Detect field type inconsistencies."""
    conflicts = []
    feature_name = group[0]['feature'].get('name', '')

    # Collect fields by name across sources
    field_map = {}
    for item in group:
        source = item['source']
        for field in item['feature'].get('fields', []):
            fname = field.get('name', '')
            if not fname:
                continue
            if fname not in field_map:
                field_map[fname] = []
            field_map[fname].append({
                'source': source,
                'type': field.get('type', 'string'),
                'required': field.get('required', False)
            })

    # Check for type conflicts
    for fname, entries in field_map.items():
        if len(entries) < 2:
            continue
        types = set(e['type'] for e in entries)
        if len(types) > 1:
            conflicts.append({
                'type': 'field_type_conflict',
                'severity': 'high',
                'feature_name': feature_name,
                'field_name': fname,
                'details': {
                    'versions': [{'source': e['source'], 'type': e['type']} for e in entries]
                }
            })

        # Check required conflicts
        required_vals = set(str(e['required']) for e in entries)
        if len(required_vals) > 1:
            conflicts.append({
                'type': 'required_conflict',
                'severity': 'medium',
                'feature_name': feature_name,
                'field_name': fname,
                'details': {
                    'versions': [{'source': e['source'], 'required': e['required']} for e in entries]
                }
            })

    return conflicts


def detect_all_conflicts(sources: dict) -> list:
    """Run all conflict detection strategies."""
    groups = group_features_by_normalized_name(sources)
    all_conflicts = []

    for normalized_name, group in groups.items():
        desc_conflicts = detect_description_conflicts(group)
        field_conflicts = detect_field_type_conflicts(group)
        all_conflicts.extend(desc_conflicts)
        all_conflicts.extend(field_conflicts)

    return all_conflicts


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({'status': 'error', 'message': 'Empty stdin input'}))
            sys.exit(1)

        data = json.loads(raw)
        validate_input(data)

        sources = data['features_by_source']
        conflicts = detect_all_conflicts(sources)

        output = {
            'status': 'ok',
            'total_conflicts': len(conflicts),
            'conflicts': conflicts
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
