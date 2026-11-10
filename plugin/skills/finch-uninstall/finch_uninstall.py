#!/usr/bin/env python3
"""The Finch-account side of /finch-uninstall.

  --delete-project <prototypeId>   delete that Finch site with its suggestions, notes and
                                   apply history (only if the signed-in account owns it)
  --disconnect                     revoke this computer's Finch API key and remove
                                   ~/.finch/credentials and ~/.finch-session.json

Signs in the same way /finch-install does (reuses or refreshes ~/.finch-session.json,
opens the browser only when neither works). The raw API key is never printed.
Prints one line of JSON: {"email", "project": ..., "computer": ...}.

Standard library only; borrows the sign-in helpers from ../finch-install/finch_auth.py.
"""
import argparse, hashlib, json, os, sys, time, urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'finch-install'))
import finch_auth as fa  # noqa: E402


def sign_in():
    session = fa.load_json(fa.SESSION_FILE)
    if not (session and session.get('access_token') and session.get('expires_at', 0) > time.time() + 120):
        session = fa.refresh(session) or fa.browser_sign_in()
    fa.write_private(fa.SESSION_FILE, session)
    status, user = fa.request('GET', '/auth/v1/user', token=session['access_token'])
    if status != 200 or not isinstance(user, dict):
        session = fa.refresh(session) or fa.browser_sign_in()
        fa.write_private(fa.SESSION_FILE, session)
        status, user = fa.request('GET', '/auth/v1/user', token=session['access_token'])
        if status != 200 or not isinstance(user, dict):
            sys.exit('Could not read your Finch account after signing in.')
    return session['access_token'], user


def delete_project(token, prototype_id):
    q = urllib.parse.quote(prototype_id, safe='')
    status, rows = fa.request('GET', f'/rest/v1/projects?prototype_id=eq.{q}&select=id,name', token=token)
    if status != 200:
        return {'status': 'failed', 'error': f'Could not look up the site ({status})'}
    if not rows:
        # Reads are owner-only, so "not found" also covers "someone else's site".
        return {'status': 'not_found'}
    project = rows[0]
    pid = urllib.parse.quote(project['id'], safe='')
    # threads.project_id is ON DELETE SET NULL, so remove the threads first
    # (replies cascade with them; apply_requests cascade with the project).
    status, data = fa.request('DELETE', f'/rest/v1/threads?project_id=eq.{pid}', token=token)
    if status not in (200, 204):
        return {'status': 'failed', 'name': project['name'], 'error': f'Could not delete its suggestions ({status}): {data}'}
    status, data = fa.request('DELETE', f'/rest/v1/projects?id=eq.{pid}', token=token,
                              extra={'Prefer': 'return=representation'})
    if status not in (200, 204) or not data:
        return {'status': 'failed', 'name': project['name'], 'error': f'Could not delete the site ({status}): {data}'}
    return {'status': 'deleted', 'name': project['name']}


def disconnect(token):
    creds = fa.load_json(fa.CRED_FILE) or {}
    raw = creds.get('apiKey')
    result = {'status': 'no_key'}
    if raw:
        h = hashlib.sha256(raw.encode()).hexdigest()
        status, data = fa.request('DELETE', f'/rest/v1/api_keys?key_hash=eq.{h}', token=token,
                                  extra={'Prefer': 'return=representation'})
        if status not in (200, 204):
            return {'status': 'failed', 'error': f'Could not revoke the API key ({status})'}
        # Empty means it was already revoked from the dashboard; still clean up locally.
        result = {'status': 'disconnected' if data else 'already_revoked'}
    for path in (fa.CRED_FILE, fa.SESSION_FILE):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    try:
        os.rmdir(fa.CRED_DIR)  # only if empty
    except OSError:
        pass
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--delete-project', metavar='PROTOTYPE_ID')
    p.add_argument('--disconnect', action='store_true')
    args = p.parse_args()
    if not args.delete_project and not args.disconnect:
        sys.exit('Nothing to do: pass --delete-project <prototypeId> and/or --disconnect')

    token, user = sign_in()
    out = {'email': user.get('email', '')}
    if args.delete_project:
        out['project'] = delete_project(token, args.delete_project)
    if args.disconnect:
        out['computer'] = disconnect(token)  # last: it removes the session file
    print(json.dumps(out))


if __name__ == '__main__':
    main()
