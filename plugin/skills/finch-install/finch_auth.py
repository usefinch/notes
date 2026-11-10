#!/usr/bin/env python3
"""Sign in to Finch for /finch-install.

- Reuses ~/.finch-session.json while it's valid, refreshes it when it has expired,
  and only opens the browser (Google sign-in on finchnotes.co) when neither works.
- Creates a Finch API key when ~/.finch/credentials has none, and saves it there
  (mode 600) for the Finch plugin's MCP connection. The raw key is never printed.
- Prints one line of JSON: {"email", "user_id", "name", "apiKey": "existing"|"created"}.
  The access token for creating the project stays in ~/.finch-session.json.

Standard library only.
"""
import hashlib, json, os, secrets, socket, sys, time, urllib.parse, urllib.request, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

SUPABASE_URL = 'https://djrzptnmlkvafrtxismf.supabase.co'
ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRqcnpwdG5tbGt2YWZydHhpc21mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3MzMyMzksImV4cCI6MjA5MTMwOTIzOX0.7vAL8UYx_CjSC8eFAo8mfs0YrFF5GCRR40TQhxYhVFY'
DASHBOARD_URL = 'https://finchnotes.co'
SESSION_FILE = os.path.expanduser('~/.finch-session.json')
CRED_DIR = os.path.expanduser('~/.finch')
CRED_FILE = os.path.join(CRED_DIR, 'credentials')


def log(msg):
    print(msg, file=sys.stderr)


def request(method, path, token=None, body=None, extra=None):
    headers = {'apikey': ANON_KEY, 'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    headers.update(extra or {})
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(SUPABASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            text = res.read().decode()
            return res.status, (json.loads(text) if text else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def write_private(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(obj, f, indent=2)
    os.chmod(path, 0o600)


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def refresh(session):
    if not session or not session.get('refresh_token'):
        return None
    status, data = request('POST', '/auth/v1/token?grant_type=refresh_token',
                           body={'refresh_token': session['refresh_token']})
    if status != 200 or not isinstance(data, dict) or not data.get('access_token'):
        return None
    user = data.get('user') or {}
    return {
        'access_token': data['access_token'],
        'refresh_token': data.get('refresh_token', session['refresh_token']),
        'expires_at': int(data.get('expires_at') or time.time() + int(data.get('expires_in', 3600))),
        'user_id': user.get('id') or session.get('user_id', ''),
        'email': user.get('email') or session.get('email', ''),
    }


def browser_sign_in():
    s = socket.socket(); s.bind(('localhost', 0)); port = s.getsockname()[1]; s.close()
    state = secrets.token_urlsafe(16)
    url = f'{DASHBOARD_URL}/auth/cli?port={port}&state={urllib.parse.quote(state)}'
    holder = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if not parsed.path.endswith('/callback'):
                self.send_response(404); self.end_headers(); return
            p = urllib.parse.parse_qs(parsed.query)
            if p.get('state', [None])[0] != state:
                holder['error'] = 'state mismatch'
            elif 'access_token' not in p:
                holder['error'] = 'no access token received'
            else:
                holder['session'] = {
                    'access_token': p['access_token'][0],
                    'refresh_token': p.get('refresh_token', [''])[0],
                    'expires_at': int(p.get('expires_at', [str(int(time.time()) + 3600)])[0]),
                    'user_id': p.get('user_id', [''])[0],
                    'email': p.get('email', [''])[0],
                }
            ok = 'session' in holder
            body = ('<html><body style="font-family:sans-serif;text-align:center;padding:60px">'
                    + ('<h2>Signed in to Finch</h2><p>You can close this tab and go back to Claude.</p>'
                       if ok else '<h2>Sign-in failed</h2><p>Go back to Claude and try again.</p>')
                    + '</body></html>').encode()
            self.send_response(200 if ok else 400)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    server = HTTPServer(('localhost', port), Handler)
    server.timeout = 300
    log('Opening your browser to sign in to Finch with Google...')
    log('If it does not open, visit:\n  ' + url)
    webbrowser.open(url)
    deadline = time.time() + 300
    while 'session' not in holder and 'error' not in holder and time.time() < deadline:
        server.handle_request()
    server.server_close()
    if 'error' in holder:
        sys.exit('Sign-in failed: ' + holder['error'])
    if 'session' not in holder:
        sys.exit('Sign-in timed out after 5 minutes. Run /finch-install again to retry.')
    return holder['session']


def main():
    session = load_json(SESSION_FILE)
    if not (session and session.get('access_token') and session.get('expires_at', 0) > time.time() + 120):
        session = refresh(session) or browser_sign_in()
    write_private(SESSION_FILE, session)

    status, user = request('GET', '/auth/v1/user', token=session['access_token'])
    if status != 200 or not isinstance(user, dict):
        # Stale token that still looked valid: sign in again once.
        session = refresh(session) or browser_sign_in()
        write_private(SESSION_FILE, session)
        status, user = request('GET', '/auth/v1/user', token=session['access_token'])
        if status != 200 or not isinstance(user, dict):
            sys.exit('Could not read your Finch account after signing in.')
    meta = user.get('user_metadata') or {}
    name = meta.get('full_name') or meta.get('name') or ''

    creds = load_json(CRED_FILE) or {}
    api_key_state = 'existing'
    if not creds.get('apiKey'):
        raw = 'fnk_' + secrets.token_hex(32)
        status, data = request('POST', '/rest/v1/api_keys', token=session['access_token'],
                               body={'owner_id': user['id'],
                                     'key_hash': hashlib.sha256(raw.encode()).hexdigest(),
                                     'label': 'Claude Code (finch-install)'},
                               extra={'Prefer': 'return=minimal'})
        if status not in (200, 201, 204):
            sys.exit(f'Could not create a Finch API key ({status}): {data}')
        creds['apiKey'] = raw
        write_private(CRED_FILE, creds)
        api_key_state = 'created'

    print(json.dumps({'email': user.get('email', ''), 'user_id': user['id'],
                      'name': name, 'apiKey': api_key_state}))


if __name__ == '__main__':
    main()
