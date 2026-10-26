#!/usr/bin/env python3
"""UniSender Go Web API client. Python 3.9+, standard library only."""
import argparse
from http.client import HTTPException
import json
import math
import os
from pathlib import Path
import re
import shlex
import socket
import stat
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

DEFAULT_BASE = 'https://goapi.unisender.ru/ru/transactional/api/v1'
API_PATH = '/ru/transactional/api/v1'
HOSTS = {'goapi.unisender.ru', 'go1.unisender.ru', 'go2.unisender.ru'}
MAX_BYTES = 10_000_000  # Conservative interpretation of the documented 10 MB limit.
DOCS = 'https://godocs.unisender.ru/web-api-ref#'
# Explicit effects: the names of several domain/get-* methods hide writes.
METHODS = {
    'email/send': ('send', ('message',)),
    'email/subscribe': ('send', ('from_email', 'from_name', 'to_email')),
    'email-validation/single': ('check', ('email',)),
    'confirmed-email/create': ('send', ('email',)),
    'confirmed-email/list': ('read', ()),
    'confirmed-email/delete': ('write', ('email',)),
    'template/set': ('write', ('template',)),
    'template/get': ('read', ('id',)),
    'template/list': ('read', ()),
    'template/delete': ('write', ('id',)),
    'webhook/set': ('write', ('url',)),
    'webhook/get': ('read', ('url',)),
    'webhook/list': ('read', ()),
    'webhook/delete': ('write', ('url',)),
    'suppression/set': ('write', ('email', 'cause')),
    'suppression/get': ('read', ('email',)),
    'suppression/list': ('read', ()),
    'suppression/delete': ('write', ('email',)),
    'domain/get-dns-records': ('write', ('domain',)),
    'domain/validate-verification-record': ('write', ('domain',)),
    'domain/validate-dkim': ('write', ('domain',)),
    'domain/list': ('read', ()),
    'domain/get-sandbox-domain': ('write', ()),
    'domain/delete': ('write', ('domain',)),
    'event-dump/create': ('write', ('start_time',)),
    'event-dump/get': ('read', ('dump_id',)),
    'event-dump/list': ('read', ()),
    'event-dump/delete': ('write', ('dump_id',)),
    'tag/list': ('read', ()),
    'tag/delete': ('write', ('tag_id',)),
    'project/create': ('write', ('project',)),
    'project/update': ('write', ('project',)),
    'project/list': ('read', ()),
    'project/delete': ('write', ()),
    'system/ping': ('read', ()),
    'system/info': ('read', ()),
}
SECRET_FIELDS = {'apikey', 'projectapikey', 'xapikey', 'authorization', 'password',
                 'secret', 'webhooksecret', 'token', 'auth'}


class ClientError(Exception):
    def __init__(self, message, **details):
        super().__init__(message)
        self.details = details


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the API key to a redirect destination, even for 307/308.
        raise HTTPError(newurl, code, 'API redirect refused', headers, fp)


def secret_field(name):
    return ''.join(c for c in name.lower() if c.isalnum()) in SECRET_FIELDS


def redact(value, key=''):
    if isinstance(value, dict):
        return {k: '[REDACTED]' if secret_field(k) else redact(v, key) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, key) for v in value]
    if isinstance(value, str) and key:
        return value.replace(key, '[REDACTED]')
    return value


def load_api_key(key_file=None):
    """Explicit file > process environment > configured file > standard file."""
    if key_file is None:
        key = os.environ.get('UNISENDER_GO_API_KEY', '').strip()
        if key:
            return key
        config_dir = Path.home() / '.config/unisender-go'
        config_path = config_dir / 'config.json'
        try:
            config = json.loads(config_path.read_text(encoding='utf-8'))
        except FileNotFoundError:
            config = {}
        except (OSError, ValueError):
            raise ClientError('Cannot read valid JSON from ~/.config/unisender-go/config.json.') from None
        if not isinstance(config, dict) or ('key_file' in config and (
                not isinstance(config['key_file'], str) or not config['key_file'].strip())):
            raise ClientError('config.json must contain a nonempty key_file path when configured.')
        key_file = config.get('key_file', str(config_dir / 'api-key'))
    path = Path(key_file).expanduser()
    try:
        # Nonblocking open avoids hanging on a mistakenly selected named pipe.
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0))
        with os.fdopen(fd, 'rb') as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise ClientError('The key file must be a regular file.')
            if os.name == 'posix' and (metadata.st_uid != os.getuid() or metadata.st_mode & 0o077):
                raise ClientError('The key file must belong to you with owner-only access (chmod 600).')
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ClientError('The key file exceeds 64 KiB.')
        text = raw.decode('utf-8-sig')
        named = re.findall(r'^[ \t]*api_key[ \t]*:[ \t]*([^\r\n]*)', text, flags=re.MULTILINE)
        if len(named) > 1:
            raise ClientError('Multiple api_key entries found; choose a file with one key.')
        if named:
            values = shlex.split(named[0], comments=True)
            key = values[0] if len(values) == 1 else ''
        else:
            key = text.strip()
        if not key or len(key) > 4096 or any(not 33 <= ord(c) <= 126 for c in key):
            raise ClientError('The key file must contain one key or a single api_key: value entry.')
        return key
    except FileNotFoundError:
        raise ClientError('Key file not found. Set UNISENDER_GO_API_KEY, --key-file, '
                          'or ~/.config/unisender-go/config.json.') from None
    except (OSError, UnicodeError, ValueError):
        raise ClientError('Cannot read the key file; check its path, encoding, and format.') from None


def validate(method, payload):
    if not isinstance(payload, dict):
        raise ClientError('Request JSON must be an object.')
    # project_api_key is a documented project selector, not request authentication.
    def reject_auth(value):
        if isinstance(value, dict):
            for k, v in value.items():
                if ''.join(c for c in k.lower() if c.isalnum()) in {'apikey', 'xapikey'}:
                    raise ClientError('Use a key file or UNISENDER_GO_API_KEY, not an API key in request JSON.')
                reject_auth(v)
        elif isinstance(value, list):
            for v in value:
                reject_auth(v)
    reject_auth(payload)
    for field in METHODS[method][1]:
        if field not in payload or payload[field] is None or payload[field] == '':
            raise ClientError('Missing required field: ' + field)
    if method in {'project/update', 'project/delete'} and not (
            payload.get('project_id') or payload.get('project_api_key')):
        raise ClientError('Provide project_id or project_api_key to identify the project.')
    if method == 'email/send':
        message = payload['message']
        if not isinstance(message, dict):
            raise ClientError('message must be an object.')
        recipients = message.get('recipients')
        if not isinstance(recipients, list) or not 1 <= len(recipients) <= 500:
            raise ClientError('message.recipients must contain 1 to 500 recipients.')
        if any(not isinstance(r, dict) or not isinstance(r.get('email'), str)
               or not r['email'].strip() for r in recipients):
            raise ClientError('Each recipient must contain an email string.')
        if not message.get('template_id'):
            body = message.get('body')
            if not message.get('subject') or not message.get('from_email'):
                raise ClientError('Without template_id, subject and from_email are required.')
            if not isinstance(body, dict) or not (body.get('html') or body.get('plaintext')):
                raise ClientError('Without template_id, body.html or body.plaintext is required.')
        identity = message.get('idempotence_key')
        if identity is not None and (not isinstance(identity, str) or not 1 <= len(identity) <= 64):
            raise ClientError('message.idempotence_key must be a string of 1 to 64 characters.')
    if method == 'event-dump/create' and payload.get('aggregate') == 'day_status' and payload.get('filter'):
        raise ClientError('aggregate=day_status cannot be combined with a nonempty filter.')


def resolve_base(base_url):
    base = (base_url or os.environ.get('UNISENDER_GO_BASE_URL') or DEFAULT_BASE).rstrip('/')
    parts = urlsplit(base)
    if (parts.scheme != 'https' or parts.netloc not in HOSTS or parts.path != API_PATH
            or parts.query or parts.fragment):
        raise ClientError('Use the documented HTTPS UniSender Go base URL (goapi, go1, or go2).')
    return base


def call_api(method, payload=None, *, execute=False, dry_run=False, base_url=None, timeout=30,
             key_file=None):
    method = method[:-5] if method.endswith('.json') else method
    if method not in METHODS:
        raise ClientError('Unknown or unsupported method. Run the methods command.')
    if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ClientError('timeout must be a positive finite number.')
    payload = {} if payload is None else payload
    validate(method, payload)
    url = resolve_base(base_url) + '/' + method + '.json'
    try:
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    except (TypeError, ValueError) as exc:
        raise ClientError('Request must contain valid JSON values.') from exc
    if len(encoded) > MAX_BYTES:
        raise ClientError('Request exceeds the 10 MB UTF-8 JSON limit.')
    key = os.environ.get('UNISENDER_GO_API_KEY', '').strip()
    effect = METHODS[method][0]
    if dry_run or (effect != 'read' and not execute):
        return {'dry_run': True, 'method': method, 'url': url, 'effect': effect,
                'body': redact(payload, key), 'request_bytes': len(encoded)}
    key = load_api_key(key_file)
    if any(c in key for c in '\r\n'):
        raise ClientError('UNISENDER_GO_API_KEY contains an invalid newline.')
    request = Request(url, data=encoded, method='POST', headers={
        'X-API-KEY': key, 'Content-Type': 'application/json', 'Accept': 'application/json',
        'User-Agent': 'unisender-go-skill/1.0',
    })
    try:
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as exc:
        try:
            error_body = redact(json.loads(exc.read()), key)
        except (ValueError, OSError, HTTPException):
            error_body = {'message': 'Non-JSON HTTP error body omitted.'}
        raise ClientError('UniSender Go HTTP error.', http_status=exc.code, response=error_body,
                          outcome_unknown=effect != 'read' and exc.code >= 500) from None
    except (URLError, OSError, socket.timeout, HTTPException):
        raise ClientError('Network failure; request was not retried.',
                          outcome_unknown=effect != 'read') from None
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        raise ClientError('Non-JSON API response; request was not retried.',
                          outcome_unknown=effect != 'read') from None
    data = redact(data, key)
    if not isinstance(data, dict) or data.get('status') != 'success':
        raise ClientError('UniSender Go returned an unsuccessful response.', response=data,
                          outcome_unknown=effect != 'read' and not (
                              isinstance(data, dict) and data.get('status') == 'error'))
    return {'dry_run': False, 'method': method, 'response': data}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('methods', help='List supported methods, effects and required top-level fields.')
    call = sub.add_parser('call', help='Read methods run live; other methods preview unless --execute.')
    call.add_argument('method', help='Example: system/info or email/send (optional .json suffix).')
    call.add_argument('--data-file', metavar='PATH', help='JSON object file; - reads stdin. Default: {}.')
    call.add_argument('--execute', action='store_true', help='Perform a send, write, or validation check.')
    call.add_argument('--dry-run', action='store_true', help='Preview without network, including reads.')
    call.add_argument('--base-url', help='Override with a documented UniSender Go datacenter URL.')
    call.add_argument('--key-file', help='Read a key or api_key: value from this file; overrides environment.')
    call.add_argument('--timeout', type=float, default=30, help='Request timeout in seconds (default 30).')
    args = parser.parse_args(argv)
    try:
        if args.command == 'methods':
            result = {'methods': [{'method': m, 'effect': e, 'required': list(r),
                                   'docs': DOCS + m.replace('/', '-')}
                                  for m, (e, r) in METHODS.items()]}
        else:
            payload = {}
            if args.data_file:
                if args.data_file == '-':
                    payload = json.load(sys.stdin)
                else:
                    payload = json.loads(Path(args.data_file).read_text(encoding='utf-8'))
            result = call_api(args.method, payload, execute=args.execute, dry_run=args.dry_run,
                              base_url=args.base_url, timeout=args.timeout, key_file=args.key_file)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3 if result.get('response', {}).get('failed_emails') else 0
    except (ClientError, OSError, ValueError) as exc:
        # Do not echo JSON decoder snippets, filesystem content, or transport exceptions.
        message = str(exc) if isinstance(exc, ClientError) else 'Cannot read valid JSON from the input file.'
        error = {'error': message, **(exc.details if isinstance(exc, ClientError) else {})}
        print(json.dumps(redact(error, os.environ.get('UNISENDER_GO_API_KEY', '').strip()),
                         ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
