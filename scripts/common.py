"""Shared local contracts; this module never publishes or writes to external services."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from zoneinfo import ZoneInfo

SKILL = 'qingneng-product-publisher'
SITE = 'https://en.tsino-dynatron.com'
API = 'https://enht.tsino-dynatron.com'
PAGE_ID = '61587766500345'
PAGE_URL = 'https://www.facebook.com/profile.php?id=' + PAGE_ID
SHEET_ID = '18iLpJ7bpDbJzxYtg0vsSOQxOR2e0KBuMI9C7LK0MhAw'
SHEET_URL = 'https://docs.google.com/spreadsheets/d/' + SHEET_ID + '/edit'
HEADERS = ['域名', '发布时间', '发布的站内链接', 'Facebook链接', 'LinkedIn链接']
SHANGHAI = ZoneInfo('Asia/Shanghai')


def now():
    return datetime.now(SHANGHAI).isoformat(timespec='seconds')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'Timestamp requires timezone offset')
    return result


def local(root, relative):
    path = (Path(root) / relative).resolve()
    require(path.is_relative_to(Path(root).resolve()), 'Evidence/artifact must stay in candidate directory')
    return path


def manifest(path):
    data = read(path)
    require(data.get('skill') == SKILL and data.get('schema_version') == 1, 'Wrong manifest contract')
    require(data.get('mode') in {'live', 'dry-run'}, 'Unknown run mode')
    require(data.get('target') == {'website': SITE, 'facebook_page_id': PAGE_ID, 'facebook_page_url': PAGE_URL}, 'Wrong publisher target')
    require(set(data['channels']) == {'facebook'}, 'Only Facebook is a publishing channel')
    require(data.get('disabled_channels') == ['website', 'linkedin'], 'Disabled channels changed')
    return data


def product_url(value):
    p = urlparse(value)
    query = parse_qs(p.query)
    require(p.scheme == 'https' and p.netloc == 'en.tsino-dynatron.com', 'Product URL must be official English HTTPS host')
    require(p.path in {'/cp_xqy', '/cp_xqy.html'} and set(query) == {'pId'}, 'Expected product detail URL with pId')
    require(len(query['pId']) == 1 and query['pId'][0].isdigit(), 'Invalid product ID')
    return SITE + '/cp_xqy?pId=' + query['pId'][0]


def post_url(value):
    p = urlparse(value)
    q = parse_qs(p.query)
    require(p.scheme == 'https' and p.netloc in {'www.facebook.com', 'facebook.com'}, 'Invalid Facebook host')
    if p.path in {'/permalink.php', '/story.php'}:
        require(bool(q.get('story_fbid')) and q.get('id') == [PAGE_ID], 'Permalink belongs to wrong page or lacks story ID')
    else:
        parts = p.path.strip('/').split('/')
        require(len(parts) >= 3 and parts[1] == 'posts' and bool(parts[2]), 'Expected Facebook post permalink, not page/feed/admin URL')
        if parts[0].isdigit():
            require(parts[0] == PAGE_ID, 'Post belongs to another numeric page ID')
    return value


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


FROZEN_FILES = ['product.json', 'keyword-plan.json', 'facebook.txt', 'review.json', 'social.webp', 'social-upload.jpg']


def batch_hashes(root):
    return {name: digest(Path(root) / name) for name in FROZEN_FILES}


def check_frozen(root, data, allow_missing_transport=False):
    require(bool(data.get('frozen_artifacts')), 'Missing submitted batch hashes')
    for name, expected in data['frozen_artifacts'].items():
        path = local(root, name)
        if name == 'social-upload.jpg' and allow_missing_transport and not path.exists():
            continue
        require(path.is_file() and digest(path) == expected, 'Submitted artifact changed: ' + name)


def screenshot(root, evidence):
    require(bool(evidence.get('screenshot')), 'Missing screenshot path')
    require(local(root, evidence['screenshot']).is_file(), 'Screenshot file is missing')


def published_evidence(root, evidence, url):
    post_url(url)
    require(evidence.get('page_id') == PAGE_ID and evidence.get('post_url') == url, 'Published evidence target mismatch')
    for field in ['author_verified', 'text_verified', 'image_verified', 'published_state_verified']:
        require(evidence.get(field) is True, 'Unverified publication: ' + field)
    require(evidence.get('public_access') in {'anonymous_verified', 'login_required'}, 'Missing public access result')
    timestamp(evidence['verified_at'])
    screenshot(root, evidence)


def sheet_evidence(evidence, expected):
    require(evidence.get('spreadsheet_id') == SHEET_ID and evidence.get('sheet_url') == SHEET_URL, 'Wrong spreadsheet')
    require(evidence.get('sheet_title') == '工作表1', 'Wrong worksheet')
    require(type(evidence.get('sheet_id')) is int and evidence['sheet_id'] >= 0, 'Missing numeric worksheet ID')
    require(evidence.get('headers') == HEADERS, 'Sheet headers changed')
    require(type(evidence.get('row_number')) is int and evidence['row_number'] >= 2, 'Invalid report row')
    require(evidence.get('values') == expected and evidence.get('readback_values') == expected, 'Sheet readback differs from expected values')
    require(evidence.get('matched_rows') == 1 and bool(evidence.get('checked_ranges')), 'Reporting uniqueness not verified')
    timestamp(evidence['verified_at'])
