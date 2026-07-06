#!/usr/bin/env python3
"""
invest_assessor.py - INVEST 六维质量评估
接收 stdin JSON: {"features": [{"id": "...", "name": "...", "description": "...", ...}]}
输出 stdout JSON: {"status": "ok", "assessments": [...]} 或 {"status": "error", ...}
"""
import json
import sys


INVEST_DIMENSIONS = frozenset({
    'independent', 'negotiable', 'valuable', 'estimable', 'small', 'testable'
})

DIMENSION_LABELS = {
    'independent': '独立性 (Independent)',
    'negotiable': '可协商性 (Negotiable)',
    'valuable': '价值 (Valuable)',
    'estimable': '可估算 (Estimable)',
    'small': '小巧 (Small)',
    'testable': '可测试 (Testable)',
}


def validate_input(data: dict) -> None:
    if 'features' not in data:
        raise ValueError('"features" is required')
    if not isinstance(data['features'], list):
        raise ValueError('"features" must be an array')
    if len(data['features']) == 0:
        raise ValueError('"features" array is empty')


def assess_independent(feature: dict) -> dict:
    """Assess how independent the feature is (1-3)."""
    desc = (feature.get('description', '') + ' ' + ' '.join(feature.get('details', []))).lower()

    # Indicators of dependency
    dependency_markers = ['depends on', 'requires', 'after', '前提', '依赖', '之后']
    dependency_count = sum(1 for m in dependency_markers if m in desc)

    if dependency_count >= 2:
        stars = 1
        reason = 'Strong dependency on other features detected'
    elif dependency_count == 1:
        stars = 2
        reason = 'Minor dependency on other features'
    else:
        stars = 3
        reason = 'Appears self-contained and independent'

    return {'dimension': 'independent', 'stars': stars, 'reason': reason}


def assess_negotiable(feature: dict) -> dict:
    """Assess negotiability (1-3)."""
    desc = feature.get('description', '').lower()
    details = ' '.join(feature.get('details', [])).lower()
    all_text = desc + ' ' + details

    # Rigid indicators
    rigid_markers = ['must use', '必须使用', 'only', '只能', 'fixed', 'exact']
    if any(m in all_text for m in rigid_markers):
        return {'dimension': 'negotiable', 'stars': 1, 'reason': 'Rigid implementation requirements'}
    elif len(all_text) < 20:
        return {'dimension': 'negotiable', 'stars': 3, 'reason': 'Highly negotiable, minimal constraints'}
    else:
        return {'dimension': 'negotiable', 'stars': 2, 'reason': 'Some flexibility in implementation'}


def assess_valuable(feature: dict) -> dict:
    """Assess business/user value clarity (1-3)."""
    desc = feature.get('description', '').lower()
    details = ' '.join(feature.get('details', [])).lower()
    all_text = desc + ' ' + details

    value_markers = ['user can', 'allow', 'enable', 'support', '用户可', '允许', '支持']
    purpose_markers = ['to', 'so that', 'in order to', 'for', '以便', '用于', '为了']

    has_value_word = any(m in all_text for m in value_markers)
    has_purpose = any(m in all_text for m in purpose_markers)

    if has_value_word and has_purpose:
        return {'dimension': 'valuable', 'stars': 3, 'reason': 'Clear business/user value'}
    elif has_value_word:
        return {'dimension': 'valuable', 'stars': 2, 'reason': 'Value implied but not explicit'}
    else:
        return {'dimension': 'valuable', 'stars': 1, 'reason': 'No clear value statement'}


def assess_estimable(feature: dict) -> dict:
    """Assess if the feature is estimable (1-3)."""
    desc = feature.get('description', '')
    fields = feature.get('fields', [])
    details = feature.get('details', [])
    all_text = (desc + ' ' + ' '.join(details)).lower()

    # Detail indicators
    has_fields = len(fields) > 0
    has_specs = any(m in all_text for m in ['size', 'limit', 'max', 'min', 'format', 'type',
                                             '大小', '限制', '最大', '最小', '格式'])

    detail_count = len(details)
    desc_length = len(desc)

    if has_fields and has_specs:
        return {'dimension': 'estimable', 'stars': 3, 'reason': 'Well-specified with fields and constraints'}
    elif desc_length > 50 and detail_count >= 3:
        return {'dimension': 'estimable', 'stars': 2, 'reason': 'Moderately detailed'}
    else:
        return {'dimension': 'estimable', 'stars': 1, 'reason': 'Too vague to estimate'}


def assess_small(feature: dict) -> dict:
    """Assess feature granularity (1-3)."""
    desc = feature.get('description', '')
    details = feature.get('details', [])
    all_text = (desc + ' ' + ' '.join(details)).lower()

    # Feature size indicators
    compound_markers = ['and', 'or', 'also', '同时', '以及', '和']
    compound_count = sum(1 for m in compound_markers if m in all_text)

    sub_feature_markers = ['manage', '管理', 'administer', 'system']
    has_sub = any(m in all_text for m in sub_feature_markers)

    total_length = len(desc) + sum(len(d) for d in details)

    if has_sub or compound_count >= 3 or total_length > 300:
        return {'dimension': 'small', 'stars': 1, 'reason': 'Large module-level scope, covers multiple sub-features'}
    elif compound_count >= 1 or total_length > 100:
        return {'dimension': 'small', 'stars': 2, 'reason': 'Single responsibility but with some scope creep'}
    else:
        return {'dimension': 'small', 'stars': 3, 'reason': 'Single-responsibility, atomic feature'}


def assess_testable(feature: dict) -> dict:
    """Assess testability (1-3)."""
    acceptance = feature.get('acceptance_criteria', [])
    details = feature.get('details', [])
    desc = feature.get('description', '')

    # Check for acceptance criteria or test indicators
    test_markers = ['verify', 'validate', 'check', 'ensure', '验收', '验证', '确认']
    all_text = desc + ' ' + ' '.join(details)

    has_acceptance = len(acceptance) >= 2
    has_test_words = any(m in all_text.lower() for m in test_markers)
    has_expected_result = any(m in all_text.lower() for m in ['display', 'show', 'return', '提示', '显示', '跳转'])

    if has_acceptance and has_expected_result:
        return {'dimension': 'testable', 'stars': 3, 'reason': 'Clear acceptance criteria with expected results'}
    elif has_acceptance or has_test_words:
        return {'dimension': 'testable', 'stars': 2, 'reason': 'Some test indicators present'}
    else:
        return {'dimension': 'testable', 'stars': 1, 'reason': 'No acceptance criteria or expected results'}


def assess_feature(feature: dict) -> dict:
    """Run all INVEST assessments on a single feature."""
    assessors = [
        assess_independent,
        assess_negotiable,
        assess_valuable,
        assess_estimable,
        assess_small,
        assess_testable,
    ]

    dimensions = {}
    total_stars = 0

    for assessor in assessors:
        result = assessor(feature)
        dimensions[result['dimension']] = {
            'stars': result['stars'],
            'reason': result['reason']
        }
        total_stars += result['stars']

    return {
        'feature_id': feature.get('id', ''),
        'feature_name': feature.get('name', ''),
        'dimensions': dimensions,
        'total_score': total_stars,
        'max_score': 18
    }


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({'status': 'error', 'message': 'Empty stdin input'}))
            sys.exit(1)

        data = json.loads(raw)
        validate_input(data)

        features = data['features']
        assessments = []

        for feature in features:
            assessment = assess_feature(feature)
            assessments.append(assessment)

        # Generate suggestions
        suggestions = []
        for a in assessments:
            low_dims = [d for d, v in a['dimensions'].items() if v['stars'] <= 1]
            if low_dims:
                dim_names = [DIMENSION_LABELS[d] for d in low_dims]
                suggestions.append({
                    'feature_name': a['feature_name'],
                    'issue_dimensions': low_dims,
                    'suggestion': f'Improve {", ".join(dim_names)}'
                })

        output = {
            'status': 'ok',
            'total_assessed': len(assessments),
            'assessments': assessments,
            'suggestions': suggestions
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
