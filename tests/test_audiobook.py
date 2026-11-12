import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_audiobook as abb  # noqa: E402


SAMPLE_SEARCH_HTML = """
<h1 class="archiveTitle"><strong>the great gatsby</strong> Audiobooks Free Download</h1>
<div class="post"><div class="postTitle"><h2><a href="/abss/dthe-great-gatsby-f-scott-fitzgerald-3/" rel="bookmark">The Great Gatsby - F. Scott Fitzgerald</a></h2></div><div class="postInfo">Category: Classic&nbsp; Literature&nbsp; <br />Language: English<span style="margin-left:100px;">Keywords: 1920's&nbsp;</span><br /></div><div class="postContent"><div class="center">
<p class="center"><a href="https://audiobookbay.lu/abss/dthe-great-gatsby-f-scott-fitzgerald-3/"><img src="https://m.media-amazon.com/images/I/717IjGLkebL._SL1500_.jpg" alt="Cover" width="250" /></a></p>
</div>
<p style='text-align:center;'>Posted: 24 Mar 2026<br />Format: <span style='color:#a00;'>MP3</span> / Bitrate: <span style='color:#a00;'>128 Kbps</span><br />File Size: <span style='color:#00f;'>260.76</span> MBs</p>
</div></div>
"""

SAMPLE_DETAIL_HTML = """
<div class="post">
    <div class="postTitle"><h1 itemprop="name">The Great Gatsby - F. Scott Fitzgerald</h1></div>
    <div class="postContent"><p class="center"><img src="https://m.media-amazon.com/images/I/717IjGLkebL._SL1500_.jpg" itemprop="image" /></p></div>
    <div class="desc" itemprop="">
        <p style="left;">Written by <a href="/?s=f.+scott+fitzgerald"><span class="author" itemprop="author">F. Scott Fitzgerald</span></a> <br />Read by <a href="/?s=alexander+scourby"><span class="narrator" itemprop="author">Alexander Scourby</span></a> <br />Format: <span class="format" itemprop="encodingFormat">MP3</span> <br />Bitrate: <span class="bitrate" itemprop="bitrate">128 Kbps</span> <br /><span class="is_abridged">Unabridged</span> </p>
        <p>A true classic of American literature.</p>
    </div>
    <table>
        <tr><td>Tracker:</td><td>udp://tracker.opentrackr.org:1337/announce</td></tr>
        <tr><td>Combined File Size:</td><td><span style='color:#00f;'>260.76</span> MBs</td></tr>
        <tr><td>Info Hash:</td><td>4e845c5874a5371462efc59b6b009c7d210a90cd</td></tr>
    </table>
</div>
"""


class AudiobookBayTests(unittest.TestCase):
    def test_parse_search_html(self):
        results = abb.parse_search_html(SAMPLE_SEARCH_HTML, base_domain="audiobookbay.lu")
        self.assertEqual(len(results), 1)
        item = results[0]
        self.assertEqual(item["title"], "The Great Gatsby - F. Scott Fitzgerald")
        self.assertEqual(item["format"], "MP3")
        self.assertEqual(item["bitrate"], "128 Kbps")
        self.assertEqual(item["size"], "260.76 MBs")
        self.assertEqual(item["cover_url"], "https://m.media-amazon.com/images/I/717IjGLkebL._SL1500_.jpg")
        self.assertEqual(
            abb.thumbnail_url(item["cover_url"], width=100),
            "https://m.media-amazon.com/images/I/717IjGLkebL._SX100_.jpg",
        )
        self.assertEqual(
            item["url"],
            "https://audiobookbay.lu/abss/dthe-great-gatsby-f-scott-fitzgerald-3/",
        )

    def test_parse_detail_html_and_magnet(self):
        detail = abb.parse_detail_html(
            SAMPLE_DETAIL_HTML,
            url="https://audiobookbay.lu/abss/dthe-great-gatsby-f-scott-fitzgerald-3/",
        )
        self.assertEqual(detail["title"], "The Great Gatsby - F. Scott Fitzgerald")
        self.assertEqual(detail["author"], "F. Scott Fitzgerald")
        self.assertEqual(detail["narrator"], "Alexander Scourby")
        self.assertEqual(detail["format"], "MP3")
        self.assertEqual(detail["bitrate"], "128 Kbps")
        self.assertEqual(detail["abridged"], "Unabridged")
        self.assertEqual(detail["size"], "260.76 MBs")
        self.assertEqual(detail["cover_url"], "https://m.media-amazon.com/images/I/717IjGLkebL._SL1500_.jpg")
        self.assertEqual(detail["info_hash"], "4e845c5874a5371462efc59b6b009c7d210a90cd")
        self.assertTrue(
            detail["magnet"].startswith(
                "magnet:?xt=urn:btih:4e845c5874a5371462efc59b6b009c7d210a90cd&dn=The%20Great%20Gatsby"
            )
        )
        self.assertEqual(detail["description"], "A true classic of American literature.")

    def test_invalid_info_hash_rejected(self):
        with self.assertRaises(ValueError):
            abb.build_magnet_uri("not-a-valid-40-char-hex-hash", "Book Title")


if __name__ == "__main__":
    unittest.main()
