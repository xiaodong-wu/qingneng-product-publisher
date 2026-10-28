#!/usr/bin/env python3
"""Reconcile saved campaigns with actual Sheet reads; never contact or mutate services."""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from common import (HEADERS, PAGE_ID, SHEET_ID, SHANGHAI, SKILL, digest, manifest,
                    now, post_url, product_url, read, require, timestamp, write)


def fresh(value, seconds=7200):
    age = (datetime.now(SHANGHAI) - timestamp(value)).total_seconds()
    require(0 <= age <= seconds, 'Refresh publication history: evidence is stale or future-dated')


def post_key(url):
    post_url(url)
    parsed = urlparse(url)
    return parse_qs(parsed.query)['story_fbid'][0] if parsed.path in {'/permalink.php', '/story.php'} else parsed.path.strip('/').split('/')[2]


def product_id(url):
    return str(int(parse_qs(urlparse(product_url(url)).query)['pId'][0]))


def scan_local(runs_root, exclude=None):
    """Published posts count even when reporting failed; any submitted outcome is reserved."""
    root = Path(runs_root).resolve()
    require(root.is_dir(), 'History runs root must exist (create it for a first run)')
    entries = []
    for path in sorted(root.glob('*/candidates/*/manifest.json')):
        if exclude and path.resolve() == Path(exclude).resolve():
            continue
        raw = read(path)
        if raw.get('skill') != SKILL or raw.get('mode') != 'live':
            continue
        data = manifest(path)
        fb = data['channels']['facebook']
        if fb['status'] != 'published' and not data.get('submission_history'):
            continue
        pid = product_id(data['product']['url'])
        require(pid == str(int(data['product']['id'])), 'Historical product identity mismatch: ' + str(path))
        entry = {'product_id': pid, 'product_url': data['product']['url'],
                 'state': 'published' if fb['status'] == 'published' else 'submitted_unresolved',
                 'manifest': str(path.resolve()), 'post_url': fb.get('url'),
                 'at': fb.get('verified_at', data.get('created_at', ''))}
        if entry['state'] == 'published':
            post_key(entry['post_url'])
            copy_path = path.parent / 'facebook.txt'
            if copy_path.is_file():
                entry['copy'] = copy_path.read_text(encoding='utf-8')
        entries.append(entry)
    return entries


def evidence_file(root, relative):
    require(isinstance(relative, str) and bool(relative), 'Missing actual history readback evidence')
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()) and path.is_file(), 'History evidence file is missing or outside evidence directory')
    return {'path': str(path), 'sha256': digest(path)}


def build(runs_root, sheet_path):
    sheet_path = Path(sheet_path).resolve()
    sheet = read(sheet_path)
    require(sheet.get('spreadsheet_id') == SHEET_ID and sheet.get('sheet_title') == '工作表1', 'Wrong history spreadsheet or worksheet')
    require(sheet.get('headers') == HEADERS, 'History sheet headers changed')
    fresh(sheet['checked_at'])
    require(sheet.get('complete') is True and bool(sheet.get('checked_ranges')), 'Read all populated Sheet rows before selection')
    raw = evidence_file(sheet_path.parent, sheet.get('raw_readback_file'))
    entries = scan_local(runs_root)
    known = {}
    for entry in entries:
        if entry['state'] == 'published':
            key = post_key(entry['post_url'])
            known.setdefault(key, set()).add(entry['product_id'])
    require(all(len(ids) == 1 for ids in known.values()), 'Conflicting product identities for one local post')
    resolutions = {}
    proofs = [raw, {'path': str(sheet_path), 'sha256': digest(sheet_path)}]
    for item in sheet.get('resolved_posts', []):
        key = post_key(item['post_url'])
        require(key not in resolutions, 'Duplicate post resolution')
        require(item.get('author_verified') is True, 'History post author not verified')
        proofs.append(evidence_file(sheet_path.parent, item.get('evidence_file')))
        urls = item.get('product_urls', [])
        require(isinstance(urls, list), 'History product_urls must be a list')
        require(bool(urls) != (item.get('non_product') is True), 'Resolve post to product URLs or verified non-product content')
        ids = {product_id(url) for url in urls}
        if ids:
            require(isinstance(item.get('copy'), str) and bool(item['copy'].strip()), 'Save actual product-post copy for editorial comparison')
        if key in known:
            require(ids == known[key], 'Sheet/platform product identity conflicts with local history')
        resolutions[key] = item
    seen_rows, seen_posts, unresolved = set(), set(), []
    require(isinstance(sheet.get('rows'), list), 'Missing Sheet row readback')
    last_row = sheet.get('last_row')
    require(type(last_row) is int and last_row >= 1, 'Missing actual last populated Sheet row')
    for row in sheet['rows']:
        number, values = row['row_number'], row['values']
        require(type(number) is int and number >= 2 and number not in seen_rows, 'Duplicate/invalid history row number')
        seen_rows.add(number)
        require(isinstance(values, list) and len(values) == 5, 'History rows must contain five cells')
        if str(values[0]).strip().lower() != 'en.tsino-dynatron.com':
            continue
        url = values[3]
        if not url:
            unresolved.append({'row': number, 'reason': 'Qingneng record has no Facebook permalink'})
            continue
        key = post_key(url)
        if key in seen_posts:
            continue  # Duplicate Sheet rows cannot make a product eligible again.
        seen_posts.add(key)
        if key in known:
            continue
        item = resolutions.get(key)
        if not item:
            unresolved.append({'row': number, 'post_url': url, 'reason': 'No verified product mapping'})
            continue
    require(seen_rows == set(range(2, last_row + 1)), 'History row coverage is incomplete; include all read chunks and blank rows')
    # Also account for encountered manual/unreported posts outside the Sheet.
    for key, item in resolutions.items():
        if key in known:
            continue
        for product in item.get('product_urls', []):
            entries.append({'product_id': product_id(product), 'product_url': product_url(product),
                            'state': 'published', 'post_url': item['post_url'],
                            'at': item.get('published_at', sheet['checked_at']), 'copy': item['copy']})
    require(not unresolved, 'Unresolved historical posts; inspect platform before selection: ' + json.dumps(unresolved, ensure_ascii=False))
    return {'schema_version': 1, 'page_id': PAGE_ID, 'checked_at': sheet['checked_at'],
            'built_at': now(), 'complete': True, 'runs_root': str(Path(runs_root).resolve()),
            'checked_ranges': sheet['checked_ranges'], 'sheet_posts_checked': len(seen_posts),
            'evidence_files': proofs, 'entries': entries}


def load_history(path, runs_root=None, max_age=7200):
    history = read(path)
    require(history.get('schema_version') == 1 and history.get('page_id') == PAGE_ID and history.get('complete') is True, 'Incomplete/wrong publication history')
    fresh(history['checked_at'], max_age)
    root = Path(history['runs_root']).resolve()
    if runs_root is not None:
        require(root == Path(runs_root).resolve(), 'History belongs to a different runs root')
    require(bool(history.get('evidence_files')), 'Missing history evidence files')
    for proof in history['evidence_files']:
        path = Path(proof['path'])
        require(path.is_file() and digest(path) == proof['sha256'], 'History source evidence missing or changed')
    for entry in history['entries']:
        require(entry['state'] in {'published', 'submitted_unresolved'}, 'Unknown publication history state')
        require(entry['product_id'] == product_id(entry['product_url']), 'History product identity mismatch')
    return history


def eligible_pool(catalog, entries, target=None):
    blocked = {}
    for item in entries:
        blocked.setdefault(item['product_id'], set()).add(item['state'])
    pool, skipped = [], []
    for product in catalog['products']:
        pid = str(int(product['productId']))
        if pid in blocked:
            skipped.append({'product_id': pid, 'reason': ', '.join(sorted(blocked[pid]))})
        else:
            pool.append(pid)
    if target:
        require(target not in blocked, 'Target already published or submission unresolved; do not repost')
        require(target in pool, 'Target product is absent from active public catalog')
        pool = [target]
    require(bool(pool), 'No unpublished eligible products remain; stop without automatic repeats')
    return pool, skipped


def recent_posts(history, limit=5):
    posts = {}
    for entry in sorted(history['entries'], key=lambda e: e.get('at', ''), reverse=True):
        if entry['state'] == 'published' and entry.get('copy'):
            posts.setdefault(post_key(entry['post_url']), entry)
    return list(posts.values())[:limit]


def copy_tokens(text):
    text = re.sub(r'https?://\S+|#[A-Za-z][A-Za-z0-9_]*', '', text)
    return re.findall(r"[a-z0-9]+(?:['’][a-z]+)?", text.lower())


def copy_overlap(text, previous):
    """Fraction of draft five-word sequences copied verbatim; exclude URL/hashtag changes."""
    def shingles(value):
        tokens = copy_tokens(value)
        return {tuple(tokens[i:i + 5]) for i in range(max(0, len(tokens) - 4))}
    current, old = shingles(text), shingles(previous)
    return len(current & old) / len(current) if current else 0.0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs-root', type=Path, required=True)
    parser.add_argument('--sheet-evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.runs_root, args.sheet_evidence)
        write(args.output, result)
        print(json.dumps({'status': 'history_ready', 'output': str(args.output.resolve()),
                          'excluded_product_ids': sorted({e['product_id'] for e in result['entries']}),
                          'sheet_posts_checked': result['sheet_posts_checked']}, ensure_ascii=False))
    except Exception as exc:
        print('error: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
