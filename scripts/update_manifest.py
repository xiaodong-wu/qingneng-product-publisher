#!/usr/bin/env python3
"""Record verified Facebook/Sheet outcomes locally; no external mutations."""
import argparse
import json
import sys
import fcntl
from datetime import datetime
from pathlib import Path
from common import *
from validate_campaign import validate
from publication_history import eligible_pool, load_history, scan_local


def evidence_path(root, value):
    require(value is not None, 'Evidence JSON is required')
    path = value.resolve()
    require(path.is_relative_to(root), 'Evidence must be inside this candidate directory')
    return str(path.relative_to(root)), read(path)


def update(args):
    if args.submission_started:
        data = manifest(args.manifest)
        require(data['mode'] == 'live', 'Dry runs cannot record external submissions or reporting')
        require(data['channels']['facebook']['status'] != 'published', 'Successful outcome is immutable; skip it when resuming')
        # Preserve historic frozen batches on explicit resume, but guard every first submit.
        if not data['submission_history']:
            history_path = getattr(args, 'history', None) or args.manifest.parent / 'publication-history.json'
            history = load_history(history_path, max_age=1800)
            runs_root = Path(history['runs_root'])
            require(args.manifest.resolve().is_relative_to(runs_root), 'Submission is outside the history runs root')
            # Serialize the final local check + reservation; two fresh runs cannot submit one product.
            with (runs_root / '.submission.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                entries = history['entries'] + scan_local(runs_root, exclude=args.manifest)
                eligible_pool({'products': [{'productId': data['product']['id']}]}, entries, data['product']['id'])
                # Keep the drafting snapshot stable for its editorial review; freeze the fresh check separately.
                proof = args.manifest.parent / 'evidence/submission-history.json'
                write(proof, history)
                return _update(args)
    return _update(args)


def check_ai_disclosure(preflight):
    disclosure = preflight.get('ai_disclosure', {})
    requirement = disclosure.get('requirement')
    require(requirement in {'optional', 'required', 'not_offered'}, 'AI disclosure requirement must be checked, not assumed')
    require(type(disclosure.get('enabled')) is bool and bool(disclosure.get('notes')), 'Record actual AI disclosure setting and reason')
    if requirement == 'required':
        require(disclosure['enabled'] is True, 'Required AI disclosure must be enabled')
    else:
        require(disclosure['enabled'] is False, 'Optional AI label must remain off by default')


def _update(args):
    path = args.manifest.resolve()
    root, data = path.parent, manifest(path)
    require(data['mode'] == 'live', 'Dry runs cannot record external submissions or reporting')
    require(data.get('selection_status') == 'selected', 'Rejected candidate cannot publish')
    channel = data['channels']['facebook'] if args.channel == 'facebook' else data['reporting']['google_sheet']
    require(channel['status'] not in {'published', 'reported'}, 'Successful outcome is immutable; skip it when resuming')
    if args.submission_started:
        require(args.channel == 'facebook' and args.status == 'pending', 'Submission marker is Facebook pending only')
        validate(path)
        preflight = read(root / 'evidence/facebook-preflight.json')
        require(preflight.get('page_id') == PAGE_ID and preflight.get('page_url') == PAGE_URL, 'Preflight target mismatch')
        require(preflight.get('active_identity_verified') is True and preflight.get('create_post_available') is True and bool(preflight.get('visible_page_name')), 'Identity or permission not verified')
        age = (datetime.now(SHANGHAI) - timestamp(preflight['verified_at'])).total_seconds()
        require(0 <= age <= 1800, 'Refresh preflight within 30 minutes before submit')
        screenshot(root, preflight)
        check_ai_disclosure(preflight)
        history = data['submission_history']
        require(len(history) < 2, 'Maximum two submissions reached')
        if history:
            check_frozen(root, data)
            rel, rec = evidence_path(root, args.reconciliation)
            require(rec.get('page_id') == PAGE_ID, 'Wrong reconciliation page')
            for key in ['absence_confirmed', 'published_list_checked', 'drafts_and_scheduled_checked']:
                require(rec.get(key) is True, 'Absence not established: ' + key)
            require(timestamp(rec['checked_at']) >= timestamp(history[-1]['started_at']) and bool(rec.get('notes')), 'Reconciliation predates last attempt or lacks evidence notes')
            screenshot(root, rec)
            history.append({'started_at': now(), 'reconciliation': rel})
        else:
            data['frozen_artifacts'] = batch_hashes(root)
            history.append({'started_at': now()})
    elif args.channel == 'facebook' and args.status == 'pending':
        raise ValueError('Pending transition requires --submission-started')
    elif args.channel == 'facebook' and args.status == 'published':
        require(bool(data['submission_history']), 'Cannot record publication without submission marker')
        check_frozen(root, data)
        rel, evidence = evidence_path(root, args.evidence)
        published_evidence(root, evidence, args.url)
        channel.update(url=args.url, evidence=rel, verified_at=evidence['verified_at'])
        published_at = timestamp(evidence.get('published_at', evidence['verified_at']))
        values = ['en.tsino-dynatron.com', published_at.astimezone(SHANGHAI).strftime('%Y-%m-%d %H:%M:%S'), '不适用', args.url, '不适用']
        data['reporting']['google_sheet']['expected_values'] = values
    elif args.channel == 'google_sheet' and args.status == 'reported':
        require(data['channels']['facebook']['status'] == 'published', 'Facebook must be verified before reporting')
        rel, evidence = evidence_path(root, args.evidence)
        sheet_evidence(evidence, channel['expected_values'])
        channel.update(evidence=rel, row_number=evidence['row_number'], verified_at=evidence['verified_at'])
    else:
        allowed = {'blocked', 'failed', 'uncertain'} if args.channel == 'facebook' else {'blocked', 'failed'}
        require(args.status in allowed and bool(args.error), 'Invalid status or missing error')
    channel.update(status=args.status, updated_at=now())
    if args.error:
        channel['error'] = args.error
    else:
        channel.pop('error', None)
    data.setdefault('history', []).append({'at': now(), 'channel': args.channel, 'status': args.status})
    write(path, data)
    return {'status': args.status, 'channel': args.channel, 'manifest': str(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--channel', choices=['facebook', 'google_sheet'], required=True)
    parser.add_argument('--status', required=True)
    parser.add_argument('--url')
    parser.add_argument('--error')
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--submission-started', action='store_true')
    parser.add_argument('--reconciliation', type=Path)
    parser.add_argument('--history', type=Path, help='Refreshed history for the final duplicate check (within 30 minutes)')
    print(json.dumps(update(parser.parse_args()), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('error: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
