#!/usr/bin/env python3
"""Guard completion from verified local evidence; never contact Facebook or Google."""
import argparse
import json
import sys
from pathlib import Path
from common import *
from validate_campaign import validate


def complete(path):
    path = path.resolve()
    root, data = path.parent, manifest(path)
    require(data['mode'] == 'live', 'Dry run is not live completion')
    require(bool(data['submission_history']), 'Missing submission history')
    facebook, sheet = data['channels']['facebook'], data['reporting']['google_sheet']
    require(facebook['status'] == 'published' and sheet['status'] == 'reported', 'Facebook or Sheet incomplete')
    check_frozen(root, data, allow_missing_transport=True)
    validate(path, require_transport=False)
    fb_evidence = read(local(root, facebook['evidence']))
    published_evidence(root, fb_evidence, facebook['url'])
    expected = ['en.tsino-dynatron.com', timestamp(fb_evidence.get('published_at', fb_evidence['verified_at'])).astimezone(SHANGHAI).strftime('%Y-%m-%d %H:%M:%S'), '不适用', facebook['url'], '不适用']
    require(sheet.get('expected_values') == expected and sheet.get('spreadsheet_id') == SHEET_ID, 'Reporting expectation changed')
    sheet_evidence(read(local(root, sheet['evidence'])), expected)
    result = {'status': 'complete', 'verified_at': now(), 'facebook_url': facebook['url'],
              'sheet_url': SHEET_URL, 'sheet_row': sheet['row_number'], 'website': '不适用', 'linkedin': '不适用'}
    data['completion'] = result
    write(path, data)
    write(root / 'evidence/completion-validation.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(complete(args.manifest), ensure_ascii=False, indent=2))
    except Exception as exc:
        print('error: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
