"""Offline behavioral checks. All simulated publication evidence stays in temporary folders."""
import argparse
import copy
import io
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from PIL import Image
from common import *
from scrape_product import discover, ensure_reselectable, safe_url
from update_manifest import update
from validate_campaign import validate
from validate_completion import complete
from publication_history import build, copy_overlap, eligible_pool, load_history, post_key, scan_local


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runs = Path(self.tmp.name) / 'runs'
        self.job = self.runs / 'batch'
        self.root = self.job / 'candidates/01-16'
        self.root.mkdir(parents=True)
        (self.root / 'evidence').mkdir()
        self.path = self.root / 'manifest.json'
        self.url = SITE + '/cp_xqy?pId=16'
        self.post = 'https://www.facebook.com/permalink.php?story_fbid=TEST_ONLY&id=' + PAGE_ID
        self.data = {'schema_version': 1, 'skill': SKILL, 'mode': 'live', 'history_policy': 1,
                     'target': {'website': SITE, 'facebook_page_id': PAGE_ID, 'facebook_page_url': PAGE_URL},
                     'product': {'id': '16', 'url': self.url, 'title': 'CDMA universal servo drive'},
                     'selection_status': 'selected', 'disabled_channels': ['website', 'linkedin'],
                     'channels': {'facebook': {'status': 'pending'}}, 'submission_history': [],
                     'reporting': {'google_sheet': {'status': 'pending', 'spreadsheet_id': SHEET_ID, 'url': SHEET_URL}}}
        write(self.path, self.data)
        fields = {'productName': 'CDMA universal servo drive',
                  'description': 'Compact multi-axis integrated structure. Model-based vibration suppression. Adaptive notch filters. Single interface for multi-axis debugging.'}
        write(self.root / 'product.json', {'product_id': '16', 'url': self.url, 'source_fields': fields})
        def keyword(phrase, field='description'):
            return {'phrase': phrase, 'source_field': field, 'quote': fields[field]}
        write(self.root / 'keyword-plan.json', {'core_keyword': keyword('universal servo drive', 'productName'),
              'related_keywords': [keyword('vibration suppression'), keyword('adaptive notch filters')],
              'intent': 'product-selection', 'buyer_stage': 'evaluation'})
        claims = ['Compact multi-axis integrated structure', 'Model-based vibration suppression', 'Adaptive notch filters', 'Single interface for multi-axis debugging']
        text = '\n'.join(['🔧 ' + claims[0] + ' for reviewing the drive arrangement in your equipment.',
                          '⚙️ ' + claims[1] + ' as part of the available application functions.',
                          '📐 ' + claims[2] + ' for your engineering team to evaluate.',
                          '🖥️ ' + claims[3] + ' when planning your commissioning workflow.', '',
                          'Review the CDMA universal servo drive with your integration team. Compare the documented features against the requirements of your own machine, and confirm the selected configuration before making a procurement decision.', '',
                          'Contact TSINO DYNATRON to discuss your project and request product information.', '', self.url, '',
                          '#ServoDrive #Automation #MotionControl #Engineering #Machinery #Integration #Commissioning #Procurement'])
        (self.root / 'facebook.txt').write_text(text)
        write(self.root / 'review.json', {'product_url': self.url, 'source_reviewed': True,
              'product_link_verified': True, 'conflicts': [], 'copy_reviewed': True, 'all_claims_supported': True,
              'editorial_review': {'product_angle': 'Multi-axis commissioning', 'specific_buyer_need': 'Evaluate interface and filtering',
                                   'variation_notes': 'First fixture, no recent copy', 'history_compared': True, 'compared_post_urls': []},
              'claims': [{'text': c, 'source_field': 'description', 'quote': fields['description']} for c in claims],
              'image_review': {'identity_preserved': True, 'text_accurate': True,
                              'reviewed_files': ['social.webp', 'social-upload.jpg'], 'notes': 'Synthetic offline test fixture only'}})
        img = Image.new('RGB', (960, 960), '#d1dde2')
        img.save(self.root / 'social.webp', 'WEBP')
        img.save(self.root / 'social-upload.jpg', 'JPEG')
        img.resize((16,16)).save(self.root / 'evidence/test.png')
        write(self.root / 'evidence/facebook-preflight.json', {'page_id': PAGE_ID, 'page_url': PAGE_URL,
              'active_identity_verified': True, 'create_post_available': True, 'verified_at': now(),
              'ai_disclosure': {'requirement': 'optional', 'enabled': False, 'notes': 'Observed optional toggle is off; synthetic fixture'},
              'visible_page_name': 'TEST FIXTURE', 'screenshot': 'evidence/test.png'})
        self.sheet_file = Path(self.tmp.name) / 'history/sheet.json'
        write(self.sheet_file.parent / 'readback.json', {'synthetic_fixture': True, 'values': []})
        self.sheet = {'spreadsheet_id': SHEET_ID, 'sheet_title': '工作表1', 'headers': HEADERS,
                      'checked_at': now(), 'complete': True, 'checked_ranges': ['工作表1!A1:E1'],
                      'raw_readback_file': 'readback.json', 'last_row': 1, 'rows': [], 'resolved_posts': []}
        write(self.sheet_file, self.sheet)
        write(self.root / 'publication-history.json', build(self.runs, self.sheet_file))

    def tearDown(self):
        self.tmp.cleanup()

    def record(self, status, channel='facebook', **kwargs):
        args = dict(manifest=self.path, channel=channel, status=status, url=None, error=None,
                    evidence=None, submission_started=False, reconciliation=None)
        args.update(kwargs)
        return update(argparse.Namespace(**args))

    def publish(self):
        self.record('pending', submission_started=True)
        p = self.root / 'evidence/published.json'
        write(p, {'page_id': PAGE_ID, 'post_url': self.post, 'author_verified': True,
                  'text_verified': True, 'image_verified': True, 'published_state_verified': True,
                  'verified_at': now(), 'public_access': 'login_required', 'screenshot': 'evidence/test.png'})
        self.record('published', url=self.post, evidence=p)

    def test_full_completion_and_transport_cleanup(self):
        self.assertEqual(validate(self.path)['status'], 'validated')
        self.publish()
        data = read(self.path)
        expected = data['reporting']['google_sheet']['expected_values']
        self.assertEqual([expected[2], expected[4]], ['不适用', '不适用'])
        p = self.root / 'evidence/sheet.json'
        write(p, {'spreadsheet_id': SHEET_ID, 'sheet_url': SHEET_URL, 'sheet_title': '工作表1', 'sheet_id': 0,
                  'row_number': 2, 'headers': HEADERS, 'values': expected, 'readback_values': expected,
                  'matched_rows': 1, 'checked_ranges': ['A2:E2'], 'verified_at': now()})
        self.record('reported', channel='google_sheet', evidence=p)
        self.assertEqual(complete(self.path)['status'], 'complete')
        (self.root / 'social-upload.jpg').unlink()
        self.assertEqual(complete(self.path)['status'], 'complete')

    def test_dry_run_blocks_submission(self):
        self.data['mode'] = 'dry-run'
        write(self.path, self.data)
        with self.assertRaisesRegex(ValueError, 'Dry runs'):
            self.record('pending', submission_started=True)

    def test_wrong_author_blocks_preflight(self):
        p = self.root / 'evidence/facebook-preflight.json'
        d = read(p); d['page_id'] = '123'; write(p,d)
        with self.assertRaisesRegex(ValueError, 'target mismatch'):
            self.record('pending', submission_started=True)

    def test_submission_closes_reselection(self):
        self.record('pending', submission_started=True)
        with self.assertRaisesRegex(ValueError, 'Reselection forbidden'):
            ensure_reselectable(self.job)

    def test_retry_requires_reconciliation_and_stops_at_two(self):
        self.record('pending', submission_started=True)
        with self.assertRaisesRegex(ValueError, 'Evidence JSON'):
            self.record('pending', submission_started=True)
        p = self.root / 'evidence/reconcile.json'
        write(p, {'page_id': PAGE_ID, 'absence_confirmed': True, 'published_list_checked': True,
                  'drafts_and_scheduled_checked': True, 'checked_at': now(), 'notes': 'Offline fixture only', 'screenshot': 'evidence/test.png'})
        self.record('pending', submission_started=True, reconciliation=p)
        with self.assertRaisesRegex(ValueError, 'Maximum two'):
            self.record('pending', submission_started=True, reconciliation=p)

    def test_submitted_copy_cannot_change(self):
        self.record('pending', submission_started=True)
        with (self.root / 'facebook.txt').open('a') as f:
            f.write('\nChanged')
        with self.assertRaisesRegex(ValueError, 'changed'):
            check_frozen(self.root, read(self.path))

    def test_sheet_failure_never_reopens_published_facebook(self):
        self.publish()
        self.record('failed', channel='google_sheet', error='Offline simulated reporting failure')
        with self.assertRaisesRegex(ValueError, 'immutable'):
            self.record('pending', submission_started=True)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            complete(self.path)

    def test_no_premature_reporting_or_completion(self):
        with self.assertRaisesRegex(ValueError, 'Facebook must'):
            self.record('reported', channel='google_sheet')
        with self.assertRaisesRegex(ValueError, 'history'):
            complete(self.path)

    def test_sheet_duplicates_and_disabled_channel_values_rejected(self):
        expected = ['en.tsino-dynatron.com', '2026-10-15 10:00:00', '不适用', self.post, '不适用']
        evidence = {'spreadsheet_id': SHEET_ID, 'sheet_url': SHEET_URL, 'sheet_title': '工作表1', 'sheet_id': 0,
                    'row_number': 2, 'headers': HEADERS, 'values': expected, 'readback_values': expected,
                    'matched_rows': 2, 'checked_ranges': ['A2:E3'], 'verified_at': now()}
        with self.assertRaisesRegex(ValueError, 'uniqueness'):
            sheet_evidence(evidence, expected)
        evidence['matched_rows'] = 1
        evidence['readback_values'] = list(expected)
        evidence['readback_values'][2] = SITE
        with self.assertRaisesRegex(ValueError, 'readback differs'):
            sheet_evidence(evidence, expected)

    def test_targeted_product_cannot_be_substituted(self):
        from scrape_product import run
        write(self.job / 'selection-ledger.json', {'targeted': True, 'attempts': []})
        args = argparse.Namespace(retry_from=self.path, product_url=None, reason='offline test')
        with self.assertRaisesRegex(ValueError, 'targeted product cannot'):
            run(args)

    def test_unsupported_quote_and_tiny_image_rejected(self):
        p = self.root / 'keyword-plan.json'; data = read(p)
        data['core_keyword']['quote'] = 'Claim from another product'; write(p,data)
        with self.assertRaisesRegex(ValueError, 'Quote absent'):
            validate(self.path)
        img = self.root / 'tiny.png'; Image.new('RGB',(50,50)).save(img)
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('optimize_image.py')), str(img), str(self.root/'out.webp'), '--kind','social'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('too small', result.stderr)

    def test_optimizer_strips_metadata(self):
        source = self.root / 'input.jpg'
        exif = Image.Exif(); exif[315] = 'TEST AUTHOR'
        Image.new('RGB',(1000,1000),'#aabbcc').save(source, exif=exif)
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('optimize_image.py')), str(source), str(self.root/'optimized.webp'), '--kind','social', '--transport-jpeg',str(self.root/'upload.jpg')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        with Image.open(self.root/'upload.jpg') as im:
            self.assertFalse(im.getexif())
        self.assertTrue(json.loads(result.stdout)['metadata_removed'])

    def test_catalog_complete_and_repeated_page_detection(self):
        def row(pid):
            return {'productId':pid,'status':'0'}
        responses = iter([{'code':0,'total':3,'rows':[row(1)]}, {'code':0,'total':3,'rows':[row(1),row(2)]}, {'code':0,'total':3,'rows':[row(3)]}])
        result = discover(lambda url: next(responses))
        self.assertEqual(result['unique_count'],3)
        responses = iter([{'code':0,'total':3,'rows':[row(1)]}, {'code':0,'total':3,'rows':[row(1)]}, {'code':0,'total':3,'rows':[row(1)]}])
        with self.assertRaisesRegex(ValueError, 'repeated'):
            discover(lambda url: next(responses))

    def test_wrong_domains_and_page_links_rejected(self):
        for url in ['https://evil.test/a.png','https://en.tsino-dynatron.com.evil.test/a.png']:
            with self.assertRaises(ValueError): safe_url(url)
        for url in [PAGE_URL, 'https://www.facebook.com/123/posts/test', 'https://www.facebook.com.evil.test/page/posts/test']:
            with self.assertRaises(ValueError): post_url(url)

    def historical(self, state='published', pid='16', mode='live', submitted=True):
        other = self.runs / 'previous/candidates/01-16/manifest.json'
        data = copy.deepcopy(self.data)
        data.update(mode=mode)
        data['product'].update(id=pid, url=SITE + '/cp_xqy?pId=' + pid)
        data['channels']['facebook'] = {'status': state, 'url': self.post, 'verified_at': now()}
        data['submission_history'] = [{'started_at': now()}] if submitted else []
        write(other, data)
        return other

    def test_history_excludes_published_even_without_sheet_success(self):
        self.historical()
        entries = scan_local(self.runs)
        pool, skipped = eligible_pool({'products': [{'productId': 16}, {'productId': 20}]}, entries)
        self.assertEqual(pool, ['20'])
        self.assertEqual(skipped[0]['reason'], 'published')

    def test_history_reserves_uncertain_submission_but_ignores_dry_runs_and_drafts(self):
        self.historical('uncertain')
        self.assertEqual(scan_local(self.runs)[0]['state'], 'submitted_unresolved')
        self.historical(mode='dry-run')
        self.assertEqual(scan_local(self.runs), [])
        self.historical('pending', submitted=False)
        self.assertEqual(scan_local(self.runs), [])

    def test_history_blocks_exhausted_pool_and_targeted_repeat(self):
        self.historical()
        entries = scan_local(self.runs)
        with self.assertRaisesRegex(ValueError, 'No unpublished'):
            eligible_pool({'products': [{'productId': 16}]}, entries)
        with self.assertRaisesRegex(ValueError, 'already published'):
            eligible_pool({'products': [{'productId': 16}, {'productId': 20}]}, entries, '16')

    def test_sheet_only_post_must_be_resolved_before_selection(self):
        self.sheet['last_row'] = 2
        self.sheet['rows'] = [{'row_number': 2, 'values': ['en.tsino-dynatron.com', '2026-01-01', '不适用', self.post, '不适用']}]
        write(self.sheet_file, self.sheet)
        with self.assertRaisesRegex(ValueError, 'Unresolved historical posts'):
            build(self.runs, self.sheet_file)
        (self.sheet_file.parent / 'post.txt').write_text('Synthetic Facebook readback: ' + self.url)
        self.sheet['resolved_posts'] = [{'post_url': self.post, 'author_verified': True,
                                        'product_urls': [self.url], 'copy': 'Synthetic product post', 'evidence_file': 'post.txt'}]
        write(self.sheet_file, self.sheet)
        result = build(self.runs, self.sheet_file)
        self.assertEqual(result['entries'][0]['product_id'], '16')

    def test_local_and_sheet_post_aliases_match_and_deduplicate(self):
        self.historical()
        alias = 'https://www.facebook.com/' + PAGE_ID + '/posts/TEST_ONLY?tracking=unused'
        self.assertEqual(post_key(alias), post_key(self.post))
        self.sheet['rows'] = [{'row_number': n, 'values': ['en.tsino-dynatron.com', '', '不适用', url, '不适用']}
                              for n, url in [(2, self.post), (3, alias)]]
        self.sheet['last_row'] = 3
        write(self.sheet_file, self.sheet)
        result = build(self.runs, self.sheet_file)
        self.assertEqual(result['sheet_posts_checked'], 1)
        self.assertEqual(len(result['entries']), 1)

    def test_missing_stale_or_incomplete_history_blocks_live_selection(self):
        from scrape_product import run
        args = argparse.Namespace(retry_from=None, output_root=self.runs, history=None, mode='live')
        with self.assertRaisesRegex(ValueError, 'requires --history'):
            run(args)
        self.sheet['complete'] = False
        write(self.sheet_file, self.sheet)
        with self.assertRaisesRegex(ValueError, 'all populated'):
            build(self.runs, self.sheet_file)
        self.sheet.update(complete=True, checked_at='2020-01-01T00:00:00+08:00')
        write(self.sheet_file, self.sheet)
        with self.assertRaisesRegex(ValueError, 'stale'):
            build(self.runs, self.sheet_file)

    def test_history_evidence_mutation_blocks_submission(self):
        write(self.sheet_file.parent / 'readback.json', {'changed': True})
        with self.assertRaisesRegex(ValueError, 'evidence missing or changed'):
            self.record('pending', submission_started=True)

    def test_final_guard_catches_another_run_submitted_after_selection(self):
        self.historical('pending')
        with self.assertRaisesRegex(ValueError, 'already published or submission unresolved'):
            self.record('pending', submission_started=True)
        self.assertEqual(read(self.path)['submission_history'], [])

    def test_optional_ai_label_off_and_required_disclosure_on(self):
        path = self.root / 'evidence/facebook-preflight.json'
        data = read(path)
        data['ai_disclosure']['enabled'] = True
        write(path, data)
        with self.assertRaisesRegex(ValueError, 'Optional AI label'):
            self.record('pending', submission_started=True)
        data['ai_disclosure'].update(requirement='required', enabled=False)
        write(path, data)
        with self.assertRaisesRegex(ValueError, 'Required AI disclosure'):
            self.record('pending', submission_started=True)
        data['ai_disclosure']['enabled'] = True
        write(path, data)
        self.record('pending', submission_started=True)

    def test_reused_copy_fails_but_original_format_remains_required(self):
        history_path = self.root / 'publication-history.json'
        history = read(history_path)
        text = (self.root / 'facebook.txt').read_text()
        history['entries'] = [{'state': 'published', 'post_url': self.post, 'at': now(), 'copy': text.replace(self.url, SITE + '/cp_xqy?pId=20')}]
        write(history_path, history)
        review_path = self.root / 'review.json'
        review = read(review_path)
        review['editorial_review']['compared_post_urls'] = [self.post]
        write(review_path, review)
        with self.assertRaisesRegex(ValueError, 'too similar'):
            validate(self.path)
        self.assertEqual(copy_overlap(text, text.replace(self.url, SITE + '/cp_xqy?pId=20')), 1.0)
        (self.root / 'facebook.txt').write_text(text.replace('🔧', 'Feature:'))
        with self.assertRaisesRegex(ValueError, 'four lines must begin with emojis'):
            validate(self.path)

    def test_completed_legacy_batches_remain_readable(self):
        self.publish()
        data = read(self.path)
        data.pop('history_policy')
        data['frozen_artifacts'].pop('publication-history.json')
        data['frozen_artifacts'].pop('evidence/submission-history.json')
        write(self.path, data)
        (self.root / 'publication-history.json').unlink()
        self.assertEqual(validate(self.path)['status'], 'validated')

    def test_missing_sheet_chunk_blocks_selection(self):
        self.sheet['last_row'] = 3
        self.sheet['rows'] = [{'row_number': 3, 'values': ['', '', '', '', '']}]
        write(self.sheet_file, self.sheet)
        with self.assertRaisesRegex(ValueError, 'row coverage is incomplete'):
            build(self.runs, self.sheet_file)

    def test_unreported_platform_post_is_also_excluded(self):
        (self.sheet_file.parent / 'post.txt').write_text('Synthetic post evidence')
        self.sheet['resolved_posts'] = [{'post_url': self.post, 'author_verified': True,
                                        'product_urls': [self.url], 'copy': 'Synthetic product post', 'evidence_file': 'post.txt'}]
        write(self.sheet_file, self.sheet)
        history = build(self.runs, self.sheet_file)
        self.assertEqual(history['entries'][0]['product_id'], '16')
        self.assertEqual(history['sheet_posts_checked'], 0)

    def test_scraper_selects_only_unused_products_from_full_catalog(self):
        from scrape_product import run
        self.historical()
        output = io.BytesIO()
        Image.new('RGB', (400, 400)).save(output, 'PNG')
        catalog = {'products': [{'productId': 16}, {'productId': 20}], 'unique_count': 2}
        raw = {'productId': 20, 'productName': 'Fixture drive', 'status': '0',
               'description': ' '.join(['Supported fixture text'] * 20),
               'coverImage': SITE + '/test.png'}
        args = argparse.Namespace(retry_from=None, product_url=None, mode='live', output_root=self.runs,
                                  history=self.root / 'publication-history.json')
        with patch('scrape_product.discover', return_value=catalog), \
             patch('scrape_product.get', side_effect=[('API_BASE_URL = "' + API + '"').encode(), output.getvalue()]), \
             patch('scrape_product.get_json', side_effect=[{'data': []}, {'data': raw}]):
            result = run(args)
        selected = read(result['manifest'])
        self.assertEqual(selected['product']['id'], '20')
        self.assertEqual(result['eligible_count'], 1)
        self.assertEqual(result['history_skipped'], [{'product_id': '16', 'reason': 'published'}])


if __name__ == '__main__':
    unittest.main(verbosity=2)
