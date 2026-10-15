"""Offline behavioral checks. All simulated publication evidence stays in temporary folders."""
import argparse
import copy
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from common import *
from scrape_product import discover, ensure_reselectable, safe_url
from update_manifest import update
from validate_campaign import validate
from validate_completion import complete


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.job = Path(self.tmp.name)
        self.root = self.job / 'candidates/01-16'
        self.root.mkdir(parents=True)
        (self.root / 'evidence').mkdir()
        self.path = self.root / 'manifest.json'
        self.url = SITE + '/cp_xqy?pId=16'
        self.post = 'https://www.facebook.com/permalink.php?story_fbid=TEST_ONLY&id=' + PAGE_ID
        self.data = {'schema_version': 1, 'skill': SKILL, 'mode': 'live',
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
              'claims': [{'text': c, 'source_field': 'description', 'quote': fields['description']} for c in claims],
              'image_review': {'identity_preserved': True, 'text_accurate': True,
                              'reviewed_files': ['social.webp', 'social-upload.jpg'], 'notes': 'Synthetic offline test fixture only'}})
        img = Image.new('RGB', (960, 960), '#d1dde2')
        img.save(self.root / 'social.webp', 'WEBP')
        img.save(self.root / 'social-upload.jpg', 'JPEG')
        img.resize((16,16)).save(self.root / 'evidence/test.png')
        write(self.root / 'evidence/facebook-preflight.json', {'page_id': PAGE_ID, 'page_url': PAGE_URL,
              'active_identity_verified': True, 'create_post_available': True, 'verified_at': now(),
              'visible_page_name': 'TEST FIXTURE', 'screenshot': 'evidence/test.png'})

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


if __name__ == '__main__':
    unittest.main(verbosity=2)
