#!/usr/bin/env python3
"""
chunked_extractor.py - 大文件分层提取策略（避免超出上下文窗口）

当解析结果过大时，将功能项按模块/批次切分为多个"层"：
  - skeleton 层: 仅输出模块名、功能名与数量，用于快速确认结构
  - chunk 层:   按批次输出具体功能项细节（字段/动作/验收标准），供 LLM 逐批消费
  - merge 层:   合并所有批次的功能项并去重

接收 stdin JSON（mode 决定输入字段）:
  {"mode": "analyze", "parsed_data": {...}, "chunk_size": 20}
  {"mode": "chunk",   "parsed_data": {...}, "chunk_index": 0, "chunk_size": 20}
  {"mode": "merge",   "chunks": [[feature, ...], ...]}

输出 stdout JSON:
  {"status": "ok", "layer": "skeleton|chunk|merge", ...}
  或 {"status": "error", "message": "..."}
"""
import json
import sys
import feature_extractor


# 功能项超过该阈值即判定为"大文件"，启用分层提取
LARGE_FEATURE_THRESHOLD = 60
# 单批最多提取的功能项数
CHUNK_FEATURES = 20
# 序列化后的解析数据超过该字节数也判定为"大文件"
LARGE_BYTE_THRESHOLD = 200 * 1024


def all_features(parsed_data: dict) -> list:
    """复用 feature_extractor 的提取逻辑，返回完整功能项列表。"""
    if 'modules' in parsed_data:
        return feature_extractor.extract_from_markdown(parsed_data)
    if 'sheets' in parsed_data:
        return feature_extractor.extract_from_excel(parsed_data)
    return feature_extractor.extract_from_mindmap(parsed_data)


def estimated_size(parsed_data: dict) -> int:
    """估算解析数据的序列化大小（字节）。"""
    try:
        return len(json.dumps(parsed_data, ensure_ascii=False).encode('utf-8'))
    except Exception:
        return 0


def chunk_count(total: int, size: int) -> int:
    return (total + size - 1) // size if total > 0 else 0


def render_skeleton(parsed_data: dict, chunk_size: int) -> dict:
    feats = all_features(parsed_data)
    size = estimated_size(parsed_data)
    total = len(feats)
    too_large = total > LARGE_FEATURE_THRESHOLD or size > LARGE_BYTE_THRESHOLD

    modules = {}
    for f in feats:
        modules.setdefault(f.get('module', '未分类'), []).append(f)

    skeleton = []
    for mod, mod_feats in modules.items():
        skeleton.append({
            'module': mod,
            'feature_count': len(mod_feats),
            'features': [{'id': f.get('id', ''), 'name': f.get('name', '')} for f in mod_feats]
        })

    return {
        'status': 'ok',
        'layer': 'skeleton',
        'too_large': too_large,
        'total_features': total,
        'estimated_size': size,
        'chunk_size': chunk_size,
        'chunk_count': chunk_count(total, chunk_size),
        'modules': skeleton
    }


def render_chunk(parsed_data: dict, chunk_index: int, chunk_size: int) -> dict:
    feats = all_features(parsed_data)
    start = chunk_index * chunk_size
    end = start + chunk_size
    chunk = feats[start:end]
    return {
        'status': 'ok',
        'layer': 'chunk',
        'chunk_index': chunk_index,
        'count': len(chunk),
        'features': chunk
    }


def _richer(new: dict, old: dict) -> bool:
    """判断新功能项是否比旧项更丰富（字段/动作/验收标准更多）。"""
    def score(f):
        return (len(f.get('fields', [])), len(f.get('actions', [])),
                len(f.get('acceptance_criteria', [])), len(f.get('interactions', [])))
    return score(new) > score(old)


def render_merge(chunks: list) -> dict:
    seen = {}
    for chunk in chunks:
        for f in chunk:
            fid = f.get('id')
            if not fid:
                continue
            if fid not in seen or _richer(f, seen[fid]):
                seen[fid] = f
    return {
        'status': 'ok',
        'layer': 'merge',
        'count': len(seen),
        'features': list(seen.values())
    }


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({'status': 'error', 'message': 'Empty stdin input'}))
            sys.exit(1)

        data = json.loads(raw)
        mode = data.get('mode', 'analyze')

        if mode == 'analyze':
            if 'parsed_data' not in data:
                raise ValueError('"parsed_data" is required for mode=analyze')
            print(json.dumps(render_skeleton(data['parsed_data'], data.get('chunk_size', CHUNK_FEATURES)),
                             ensure_ascii=False))
        elif mode == 'chunk':
            if 'parsed_data' not in data:
                raise ValueError('"parsed_data" is required for mode=chunk')
            idx = int(data.get('chunk_index', 0))
            print(json.dumps(render_chunk(data['parsed_data'], idx, data.get('chunk_size', CHUNK_FEATURES)),
                             ensure_ascii=False))
        elif mode == 'merge':
            if 'chunks' not in data:
                raise ValueError('"chunks" is required for mode=merge')
            print(json.dumps(render_merge(data['chunks']), ensure_ascii=False))
        else:
            raise ValueError(f'Unknown mode: {mode} (expect analyze|chunk|merge)')

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
