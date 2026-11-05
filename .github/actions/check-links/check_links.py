"""Check tracked Markdown links and HTML href/src/poster attributes locally."""

from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []
        self.anchors = set()
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if value and key in ('href', 'src', 'poster'):
                self.links.append(value)
            if value and (key == 'id' or (tag == 'a' and key == 'name')):
                self.anchors.add(value)


def markdown_links(text):
    text = re.sub(r'(?ms)^ {0,3}(`{3,}|~{3,})[^\n]*\n.*?^ {0,3}\1[ \t]*$', '', text)
    inline = re.findall(r'!?\[[^\]\n]*\]\(\s*(<[^>\n]+>|[^\s)]+)(?:\s+["\'][^)]*["\'])?\s*\)', text)
    references = re.findall(r'(?m)^ {0,3}\[[^\]]+\]:\s*(<[^>\n]+>|\S+)', text)
    return [link.strip('<>') for link in inline + references]


def check_links(root, paths):
    root = Path(root).resolve()
    errors = []
    for relative in paths:
        source = (root / relative).resolve()
        if not source.is_relative_to(root):
            errors.append(f'{relative}: source escapes repository')
            continue
        if source.suffix.lower() not in ('.md', '.html'):
            continue
        text = source.read_text(encoding='utf-8')
        html = source.suffix.lower() == '.html'
        page = Page(text)
        links = page.links + ([] if html else markdown_links(text))
        for link in links:
            uri = urlsplit(link)
            if uri.scheme or uri.netloc:
                continue
            if not uri.path:
                if html and uri.fragment and unquote(uri.fragment) not in page.anchors:
                    errors.append(f'{relative}: missing anchor {link}')
                continue
            base = root if uri.path.startswith('/') else source.parent
            target = (base / unquote(uri.path).lstrip('/')).resolve()
            if not target.is_relative_to(root):
                errors.append(f'{relative}: link escapes repository {link}')
                continue
            if html and target.is_dir():
                target /= 'index.html'
            if not target.exists():
                errors.append(f'{relative}: missing target {link}')
            elif html and uri.fragment and target.suffix.lower() == '.html':
                anchors = Page(target.read_text(encoding='utf-8')).anchors
                if unquote(uri.fragment) not in anchors:
                    errors.append(f'{relative}: missing anchor {link}')
    return errors


if __name__ == '__main__':
    root = Path(sys.argv[1]).resolve()
    tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode('utf-8').split('\0')
    errors = check_links(root, [path for path in tracked if path])
    print('\n'.join(errors) if errors else 'PASS repository-local Markdown and HTML links')
    sys.exit(bool(errors))
