import re
from urllib.parse import urlsplit, urlunsplit, urljoin, unquote

ASSETS = re.compile(r'\.(pdf|png|jpe?g|gif|webp|svg|zip|mp[34]|css|js|ico|woff2?|docx?|xlsx?)$', re.I)

def normalize(value):
    p = urlsplit(value.strip())
    if p.scheme.lower() not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise ValueError('http:// または https:// で始まるURLを入力してください。')
    host = p.hostname.lower().encode('idna').decode('ascii')
    if ':' in host:
        host = '[' + host + ']'
    port = p.port
    netloc = host if port is None or (p.scheme.lower(), port) in [('http', 80), ('https', 443)] else f'{host}:{port}'
    return urlunsplit((p.scheme.lower(), netloc, p.path or '/', '', ''))

def origin(value):
    p = urlsplit(normalize(value))
    return p.scheme, p.netloc

def candidate(base, href, allowed):
    try:
        u = normalize(urljoin(base, href))
        return u if origin(u) == allowed and not ASSETS.search(urlsplit(u).path) else None
    except (ValueError, UnicodeError):
        return None

def filename(url):
    text = unquote(urlsplit(url).path).strip('/') or 'top'
    text = re.sub(r'[\x00-\x1f<>:"/\\|?*]', '_', text).strip(' .')[:90] or 'page'
    if text.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:
        text = '_' + text
    return text
