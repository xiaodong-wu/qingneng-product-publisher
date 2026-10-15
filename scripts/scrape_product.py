#!/usr/bin/env python3
"""Read the official public catalog and prepare one campaign candidate; GET requests only."""
import argparse
import io
import json
import random
import re
import sys
import uuid
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urlsplit, urlunsplit, quote, parse_qs
from urllib.request import Request, build_opener, HTTPRedirectHandler
from PIL import Image
from common import SITE, API, SKILL, PAGE_ID, PAGE_URL, SHEET_ID, SHEET_URL, now, read, write, require, manifest, product_url

HOSTS = {'en.tsino-dynatron.com', 'enht.tsino-dynatron.com', 'www.tsino-dynatron.com', 'tsino-dynatron.com'}
MAX_ATTEMPTS = 10


class CandidateError(ValueError):
    pass


def safe_url(url):
    p = urlsplit(url)
    require(p.scheme in {'http', 'https'} and p.netloc in HOSTS, 'Unexpected source host or URL: ' + url)
    return urlunsplit(('https', p.netloc, quote(p.path, safe='/%:@-._~'), quote(p.query, safe='=&%+'), ''))


class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, safe_url(newurl))


def get(url):
    req = Request(safe_url(url), headers={'User-Agent': 'QingnengProductPublisher/1.0 (public product research)'})
    with build_opener(Redirects()).open(req, timeout=30) as response:
        data = response.read(25 * 1024 * 1024 + 1)
        require(len(data) <= 25 * 1024 * 1024, 'Source response exceeds 25 MiB')
        return data


def get_json(url):
    data = json.loads(get(url))
    require(data.get('code') == 0, 'Public API returned an unexpected status')
    return data


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.images, self.skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style'}:
            self.skip += 1
        if tag in {'p', 'div', 'li', 'br', 'tr', 'td', 'h3'}:
            self.parts.append(' ')
        if tag == 'img' and dict(attrs).get('src'):
            self.images.append(dict(attrs)['src'])

    def handle_endtag(self, tag):
        if tag in {'script', 'style'}:
            self.skip = max(0, self.skip - 1)
        self.parts.append(' ')

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def plain(value):
    parser = Text()
    parser.feed(str(value or ''))
    text = re.sub(r'[\u200b-\u200f\ufeff]', '', ''.join(parser.parts))
    return re.sub(r'\s+', ' ', text).strip(), parser.images


def discover(fetch=get_json):
    by_id, pages, expected = {}, [], None
    for number in range(1, 101):
        url = API + '/api/product/list' + ('' if number == 1 else f'?pageNum={number}&pageSize=100')
        # If the first response is paginated, restart with a stable explicit page size.
        if number == 1:
            data = fetch(url)
            if len(data.get('rows', [])) < int(data.get('total', 0)):
                url = API + '/api/product/list?pageNum=1&pageSize=100'
                data = fetch(url)
        else:
            data = fetch(url)
        rows = data.get('rows')
        require(isinstance(rows, list) and type(data.get('total')) is int, 'Catalog schema changed')
        if expected is None:
            expected = data['total']
        require(expected == data['total'], 'Catalog changed during pagination; restart later')
        before = len(by_id)
        for row in rows:
            require(isinstance(row, dict) and str(row.get('productId', '')).isdigit(), 'Invalid catalog product')
            pid = str(row['productId'])
            if pid in by_id:
                require(by_id[pid] == row, 'Conflicting duplicate catalog product')
            by_id[pid] = row
        pages.append({'url': url, 'rows': len(rows), 'new_ids': len(by_id) - before})
        require(len(by_id) <= expected, 'Catalog total smaller than unique product count')
        if len(by_id) == expected:
            break
        require(len(by_id) > before, 'Catalog pagination repeated or ended before total')
    require(len(by_id) == expected and expected > 0, 'Incomplete or empty catalog')
    for item in by_id.values():
        require(str(item.get('status')) in {'0', '1'}, 'Unrecognized product status')
    active = [row for row in by_id.values() if str(row['status']) == '0']
    return {'fetched_at': now(), 'complete': True, 'total': expected, 'unique_count': len(by_id),
            'active_count': len(active), 'pages': pages, 'products': active}


def extract(raw, categories):
    if not plain(raw.get('productName'))[0]:
        raise CandidateError('Missing product title')
    if str(raw.get('status')) != '0':
        raise CandidateError('Product is inactive')
    fields, images = {}, []
    for key in ['productName', 'subhead', 'description', 'featuresAndBenefits', 'specifications']:
        fields[key], found = plain(raw.get(key))
        images.extend(found)
    by_id = {row['categoryId']: row for row in categories}
    current, ancestry, seen = raw.get('categoryId'), [], set()
    while current and current in by_id and current not in seen:
        seen.add(current)
        ancestry.insert(0, by_id[current]['categoryName'])
        current = by_id[current].get('parentId')
    fields['category'] = ' > '.join(ancestry)
    if len((fields['description'] + ' ' + fields['featuresAndBenefits']).split()) < 35:
        raise CandidateError('Insufficient product-specific descriptive text')
    if not raw.get('coverImage'):
        raise CandidateError('Missing hero image')
    return {'product_id': str(raw['productId']), 'title': fields['productName'],
            'url': SITE + '/cp_xqy?pId=' + str(raw['productId']), 'source_fields': fields,
            'image_only_specifications': bool(images) and not fields['specifications'],
            'reference_images': images, 'hero_url': safe_url(raw['coverImage']),
            'source_api_url': API + '/api/product/info?productId=' + str(raw['productId']),
            'fetched_at': now(), 'review_required': True}


def ensure_reselectable(job):
    for path in job.glob('candidates/*/manifest.json'):
        data = manifest(path)
        require(not data.get('submission_history') and data['channels']['facebook']['status'] != 'published', 'Reselection forbidden after any submission marker')


def run(args):
    if args.retry_from:
        require(not args.product_url and bool(args.reason), 'Retry needs reason and cannot change target URL')
        old_path = args.retry_from.resolve()
        old = manifest(old_path)
        job = old_path.parent.parent.parent
        ledger = read(job / 'selection-ledger.json')
        require(not ledger['targeted'], 'Explicitly targeted product cannot be substituted')
        ensure_reselectable(job)
        require(ledger['attempts'][-1].get('manifest') == str(old_path.relative_to(job)), 'Only the current candidate can be rejected')
        require(ledger['attempts'][-1]['status'] == 'selected', 'Candidate already rejected')
        ledger['attempts'][-1].update(status='rejected', reason=args.reason)
        old['selection_status'] = 'rejected'
        write(old_path, old)
        write(job / 'selection-ledger.json', ledger)
        catalog, mode = read(job / 'catalog.json'), old['mode']
    else:
        common_js = get(SITE + '/js/common.js').decode()
        require(re.search(r'API_BASE_URL\s*=\s*[\"\']' + re.escape(API) + r'[\"\']', common_js), 'Official backend declaration changed')
        catalog = discover()
        job = (args.output_root / (now().replace(':', '').replace('+', '-') + '-' + uuid.uuid4().hex[:6])).resolve()
        job.mkdir(parents=True)
        write(job / 'catalog.json', catalog)
        (job / 'site-common.js').write_text(common_js)
        pool = [str(p['productId']) for p in catalog['products']]
        if args.product_url:
            selected = parse_qs(urlparse(product_url(args.product_url)).query)['pId'][0]
            require(selected in pool, 'Target product is absent from active public catalog')
            pool = [selected]
        else:
            random.SystemRandom().shuffle(pool)
        ledger = {'created_at': now(), 'targeted': bool(args.product_url), 'max_candidates': MAX_ATTEMPTS,
                  'pool': pool, 'attempts': []}
        write(job / 'selection-ledger.json', ledger)
        mode = args.mode
    categories = get_json(API + '/api/product/category/list')['data']
    require(isinstance(categories, list), 'Category schema changed')
    write(job / 'categories.json', categories)
    tried = {a['product_id'] for a in ledger['attempts']}
    remaining = [pid for pid in ledger['pool'] if pid not in tried]
    for pid in remaining:
        if len(ledger['attempts']) >= MAX_ATTEMPTS:
            break
        folder = job / 'candidates' / f'{len(ledger["attempts"]) + 1:02d}-{pid}'
        (folder / 'source').mkdir(parents=True)
        (folder / 'evidence').mkdir()
        attempt = {'product_id': pid, 'url': SITE + '/cp_xqy?pId=' + pid, 'status': 'reviewing', 'at': now()}
        ledger['attempts'].append(attempt)
        write(job / 'selection-ledger.json', ledger)
        try:
            raw = get_json(API + '/api/product/info?productId=' + pid)['data']
            require(isinstance(raw, dict) and str(raw.get('productId')) == pid, 'Detail identity/schema mismatch')
            write(folder / 'source/product-raw.json', raw)
            product = extract(raw, categories)
            hero = get(product['hero_url'])
            try:
                with Image.open(io.BytesIO(hero)) as img:
                    img.verify()
                with Image.open(io.BytesIO(hero)) as img:
                    size, fmt = img.size, img.format
            except (OSError, ValueError) as exc:
                raise CandidateError('Unusable hero image') from exc
            if min(size) < 300 or fmt not in {'PNG', 'JPEG', 'WEBP'}:
                raise CandidateError('Hero resolution/format unsuitable')
            hero_name = 'source/hero.' + {'PNG': 'png', 'JPEG': 'jpg', 'WEBP': 'webp'}[fmt]
            (folder / hero_name).write_bytes(hero)
            product['hero_path'], product['hero_dimensions'] = hero_name, list(size)
            write(folder / 'product.json', product)
            (folder / 'source/product.txt').write_text('\n\n'.join(k + '\n' + v for k, v in product['source_fields'].items()), encoding='utf-8')
            path = folder / 'manifest.json'
            data = {'schema_version': 1, 'skill': SKILL, 'created_at': now(), 'mode': mode,
                    'target': {'website': SITE, 'facebook_page_id': PAGE_ID, 'facebook_page_url': PAGE_URL},
                    'product': {'id': pid, 'title': product['title'], 'url': product['url']},
                    'selection_status': 'selected', 'selection_ledger': '../../selection-ledger.json',
                    'disabled_channels': ['website', 'linkedin'],
                    'channels': {'facebook': {'status': 'pending'}}, 'submission_history': [],
                    'reporting': {'google_sheet': {'status': 'pending', 'spreadsheet_id': SHEET_ID, 'url': SHEET_URL}},
                    'artifacts': {'product': 'product.json', 'keywords': 'keyword-plan.json', 'copy': 'facebook.txt',
                                  'review': 'review.json', 'social': 'social.webp', 'transport': 'social-upload.jpg'}}
            write(path, data)
            attempt.update(status='selected', manifest=str(path.relative_to(job)))
            write(job / 'selection-ledger.json', ledger)
            return {'status': 'source_ready', 'manifest': str(path), 'candidate_count': len(ledger['attempts']),
                    'catalog_count': catalog['unique_count'], 'title': product['title']}
        except CandidateError as exc:
            attempt.update(status='rejected', reason=str(exc))
            write(job / 'selection-ledger.json', ledger)
        except Exception as exc:
            attempt.update(status='blocked', reason=str(exc))
            write(job / 'selection-ledger.json', ledger)
            raise
    raise ValueError('Candidate budget or pool exhausted; inspect ' + str(job / 'selection-ledger.json'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['live', 'dry-run'], default='dry-run')
    parser.add_argument('--product-url')
    parser.add_argument('--output-root', type=Path, default=Path.cwd() / 'campaign-runs')
    parser.add_argument('--retry-from', type=Path)
    parser.add_argument('--reason')
    args = parser.parse_args()
    skill_dir = Path(__file__).resolve().parents[1]
    require(not args.output_root.resolve().is_relative_to(skill_dir), 'Campaign output must be outside the skill directory; pass --output-root')
    print(json.dumps(run(args), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('error: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
