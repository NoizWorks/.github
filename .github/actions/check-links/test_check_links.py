from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from check_links import check_links


class LocalLinksTest(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def write(self, path, text):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding='utf-8')

    def test_markdown_inline_image_reference_and_encoded_path(self):
        self.write('docs/read me.md', '# Text')
        self.write('image.png', '')
        self.write('README.md', '[Guide](docs/read%20me.md#text)\n![Image](image.png)\n[More][ref]\n[ref]: <docs/read me.md>\n')
        self.assertEqual(check_links(self.root, ['README.md']), [])

    def test_missing_targets_fail(self):
        self.write('README.md', '[Missing](missing.md)\n![Missing](missing.png)')
        self.assertEqual(len(check_links(self.root, ['README.md'])), 2)

    def test_external_and_code_examples_are_ignored(self):
        self.write('README.md', '[External](https://example.invalid/)\n[Email](mailto:a@example.org)\n```md\n[Example](not-a-file.md)\n```\n')
        self.assertEqual(check_links(self.root, ['README.md']), [])

    def test_html_directories_and_anchors(self):
        self.write('index.html', '<h1 id="main">Home</h1><a href="#main">Home</a><a href="docs/#help">Help</a><img src="/image.png">')
        self.write('docs/index.html', '<h1 id="help">Help</h1><a href="../">Home</a>')
        self.write('image.png', '')
        self.assertEqual(check_links(self.root, ['index.html', 'docs/index.html']), [])

    def test_missing_html_anchor_fails(self):
        self.write('index.html', '<a href="#missing">Missing</a><a href="other.html#absent">Other</a>')
        self.write('other.html', '<h1>Other</h1>')
        self.assertEqual(len(check_links(self.root, ['index.html'])), 2)

    def test_links_cannot_escape_repository(self):
        self.write('README.md', '[Outside](../outside.md)')
        self.assertIn('escapes repository', check_links(self.root, ['README.md'])[0])

    def test_sources_cannot_escape_repository(self):
        self.write('outside.md', '# Outside')
        child = self.root / 'repo'
        child.mkdir()
        self.assertIn('source escapes repository', check_links(child, ['../outside.md'])[0])


if __name__ == '__main__':
    unittest.main()
