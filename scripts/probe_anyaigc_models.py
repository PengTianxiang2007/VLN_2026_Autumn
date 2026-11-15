"""Read the model list through a secure stdin-provided bearer key."""
import getpass
import json
import os
import sys
from urllib.request import ProxyHandler, Request, build_opener


def main():
    key = os.environ.get('JEV_API_KEY', '')
    if not key:
        key = getpass.getpass('JEV API key: ') if sys.stdin.isatty() else sys.stdin.readline()
    key = key.strip()
    if not key:
        raise RuntimeError('A bearer key is required')
    request = Request(
        'https://anyaigc.ai/v1/models',
        headers={'Authorization': 'Bearer ' + key, 'Accept': 'application/json'},
    )
    opener = build_opener(ProxyHandler({}))
    with opener.open(request, timeout=30) as response:
        value = json.load(response)
    rows = value.get('data', value)
    print(json.dumps([
        {
            'id': row.get('id'),
            'owned_by': row.get('owned_by'),
            'created': row.get('created'),
        }
        for row in rows
    ], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
