#!/usr/bin/env python3
"""Validate local Facebook assets and traceable review records; never publish."""
import argparse
import json
import re
import sys
from pathlib import Path
from PIL import Image
from common import manifest, read, require, product_url, local, now, write
from optimize_image import validate as validate_webp


def words(text):
    return re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?", text)


def normalized(text):
    return ' '.join(words(text)).lower()


def quoted(item, fields):
    require(item.get('source_field') in fields, 'Unknown product evidence field')
    quote = item.get('quote', '')
    require(bool(quote) and quote in fields[item['source_field']], 'Quote absent from selected product evidence')


def validate(path, require_transport=True):
    data = manifest(path)
    root = Path(path).resolve().parent
    require(data.get('selection_status') == 'selected', 'Rejected candidate cannot be validated')
    product = read(root / 'product.json')
    require(product_url(data['product']['url']) == product['url'] and data['product']['id'] == product['product_id'], 'Product/manifest mismatch')
    fields = product['source_fields']
    plan = read(root / 'keyword-plan.json')
    related = plan.get('related_keywords', [])
    require(2 <= len(related) <= 4, 'Need 2–4 related keywords')
    require(plan.get('intent') == 'product-selection' and plan.get('buyer_stage') == 'evaluation', 'Unsupported social keyword intent/stage')
    phrases = []
    for keyword in [plan['core_keyword']] + related:
        quoted(keyword, fields)
        phrase = normalized(keyword.get('phrase', ''))
        require(2 <= len(words(phrase)) <= 8, 'Keyword must contain 2–8 words')
        require(phrase in normalized(keyword['quote']), 'Keyword is not supported by quoted phrase')
        require(not re.search(r'\d', keyword['phrase']) and not re.search(r'\b(?:CDA|CDMA|CDRA|CDRD|CDLD|CDS|CDM-ANT|CDMD|CDD|TDA|RJM|JMDH?|CDRC|QE|QR)\b', keyword['phrase'], re.I), 'Remove whole model codes from keywords')
        require(all(phrase not in p and p not in phrase for p in phrases), 'Overlapping keywords')
        phrases.append(phrase)
    text = (root / 'facebook.txt').read_text(encoding='utf-8').strip()
    require(not re.search(r'[\u3400-\u9fff]', text), 'Facebook copy must be English')
    urls = re.findall(r'https?://\S+', text)
    require(urls == [product['url']] and product['url'] in text.splitlines(), 'Need exactly one canonical product URL on its own line')
    tags = re.findall(r'(?<!\w)#[A-Za-z][A-Za-z0-9_]*', text)
    require(8 <= len(tags) <= 12 and len(set(t.lower() for t in tags)) == len(tags), 'Need 8–12 unique hashtags')
    require(all(t in text.splitlines()[-1] for t in tags), 'Hashtags must be on the last line')
    body = re.sub(r'https?://\S+|#[A-Za-z][A-Za-z0-9_]*', '', text)
    count = len(words(body))
    require(80 <= count <= 150, f'Facebook body must be 80–150 words; got {count}')
    lines = [s.strip() for s in text.splitlines() if s.strip()]
    require(len(lines) >= 8, 'Missing feature lines, benefit, CTA, URL or hashtag line')
    emoji = r'^[\U0001F000-\U0001FAFF\u2300-\u27BF]'
    require(all(re.match(emoji, line) for line in lines[:4]), 'First four lines must begin with emojis')
    review = read(root / 'review.json')
    require(review.get('product_url') == product['url'], 'Review refers to another product')
    for key in ['source_reviewed', 'product_link_verified', 'copy_reviewed', 'all_claims_supported']:
        require(review.get(key) is True, 'Missing actual review: ' + key)
    require(review.get('conflicts') == [], 'Unresolved product conflicts')
    claims = review.get('claims', [])
    require(len(claims) >= 4, 'Review needs at least four supported claims')
    for claim in claims:
        quoted(claim, fields)
        require(bool(claim.get('text')) and claim['text'] in text, 'Reviewed claim absent from copy')
    for line in lines[:4]:
        require(any(c['text'] in line for c in claims), 'Feature line lacks a review evidence mapping')
    image_review = review.get('image_review', {})
    require(image_review.get('identity_preserved') is True and image_review.get('text_accurate') is True, 'Image visual review incomplete')
    require(set(image_review.get('reviewed_files', [])) == {'social.webp', 'social-upload.jpg'} and bool(image_review.get('notes')), 'Review optimized images with notes')
    image_info = validate_webp(root / 'social.webp', 'social', 750 * 1024)
    jpg = root / 'social-upload.jpg'
    if require_transport or jpg.exists():
        require(jpg.is_file() and jpg.stat().st_size <= 750 * 1024, 'Missing/oversized transport JPEG')
        with Image.open(jpg) as image:
            image.verify()
        with Image.open(jpg) as image:
            require(image.format == 'JPEG' and image.width == image.height and 960 <= image.width <= 1600, 'Transport format/dimensions invalid')
            require(not image.getexif() and not any(k in image.info for k in ['exif', 'icc_profile', 'xmp', 'comment']), 'Transport metadata remains')
    result = {'status': 'validated', 'validated_at': now(), 'mode': data['mode'], 'word_count': count,
              'hashtags': len(tags), 'image': image_info,
              'prospective_report': ['en.tsino-dynatron.com', '<Shanghai publish time>', '不适用', '<verified Facebook permalink>', '不适用']}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    result = validate(args.manifest)
    write(args.manifest.parent / 'evidence/campaign-validation.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('error: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
