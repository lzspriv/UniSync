import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrapers.html_cards import fetch_html_announcements


class HtmlCardFormatTests(unittest.TestCase):
    def setUp(self):
        self.recent = datetime.now() - timedelta(days=1)
        self.date_text = self.recent.strftime("%Y-%m-%d")
        self.year = self.recent.year
        self.month = self.recent.month
        self.day = self.recent.day

    def scrape(self, html, config):
        response = Mock(status_code=200, text=html)
        session = Mock()
        session.get.return_value = response
        with patch("scrapers.html_cards.create_request_session", return_value=session):
            return fetch_html_announcements(
                "https://example.edu.tw/news/",
                "測試單位-公告",
                config,
            )

    def test_text_based_link_formats(self):
        cases = [
            (
                "spaced_date_link",
                f'<a class="item" href="/spaced">{self.year} {self.month} {self.day} 空白日期公告</a>',
                "空白日期公告",
                "",
            ),
            (
                "row_date_link",
                f'<div class="item">{self.date_text} <a href="/row">列日期公告</a></div>',
                "列日期公告",
                "列日期公告",
            ),
            (
                "link_date_text",
                f'<a class="item" href="/link">{self.date_text} 2020-01-01 連結日期公告</a>',
                "連結日期公告",
                "連結日期公告",
            ),
        ]

        for parser_name, html, expected_title, expected_summary in cases:
            with self.subTest(parser=parser_name):
                result = self.scrape(
                    html,
                    {
                        "parser": parser_name,
                        "article": ".item",
                        "title_link": "a[href]",
                    },
                )

                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]["date"], self.date_text)
                self.assertEqual(result[0]["title"], expected_title)
                self.assertEqual(result[0]["summary"], expected_summary)

    def test_management_alumni_and_split_date_cards(self):
        management_html = f"""
        <div class="item">
          <div class="news-list-date">
            <span class="year">{self.year}</span>
            <span class="month">{self.month}</span>
            <span class="date">{self.day}</span>
          </div>
          <div class="news-list-text"><a href="/mgt">管理活動</a></div>
        </div>
        """
        alumni_html = f"""
        <div class="item">
          <div class="title"><a href="/alumni">校友活動</a></div>
          <div class="font_con">校友活動摘要</div>
          <div class="square_date">{self.day} {self.year}.{self.month}</div>
        </div>
        """
        split_html = f"""
        <div class="item">
          <a href="/split">通識活動</a>
          <span class="yearmonth">{self.year}-{self.month}</span>
          <span class="day">{self.day}</span>
        </div>
        """
        cases = [
            (
                management_html,
                {
                    "parser": "mgt_card",
                    "article": ".item",
                    "title_link": ".news-list-text a",
                },
                "管理活動",
                "",
            ),
            (
                alumni_html,
                {
                    "parser": "alumni_card",
                    "article": ".item",
                    "title": ".title",
                    "title_link": ".title a",
                    "summary": ".font_con",
                    "date": ".square_date",
                },
                "校友活動",
                "校友活動摘要",
            ),
            (
                split_html,
                {
                    "parser": "split_date_card",
                    "article": ".item",
                    "title_link": "a",
                    "date_yearmonth": ".yearmonth",
                    "date_day": ".day",
                },
                "通識活動",
                "",
            ),
        ]

        for html, config, expected_title, expected_summary in cases:
            with self.subTest(parser=config["parser"]):
                result = self.scrape(html, config)

                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]["date"], self.date_text)
                self.assertEqual(result[0]["title"], expected_title)
                self.assertEqual(result[0]["summary"], expected_summary)

    def test_ctld_cal_and_rcemi_cards(self):
        ctld_html = f"""
        <div class="item">
          <a href="/ctld"><h4 class="media-heading">教學活動</h4></a>
          <span class="date">{self.date_text}</span>
        </div>
        """
        cal_html = f"""
        <div class="item">
          <a href="/cal">英語活動</a>
          <div class="date-box">{self.year}年{self.month}月{self.day}日</div>
          <div class="article">英語活動摘要</div>
        </div>
        """
        rcemi_html = f"""
        <a href="/rcemi"><div class="item">
          <div class="date-row">{self.date_text}</div>
          <div class="article"><h3>EMI 活動</h3><p>EMI 活動摘要</p></div>
        </div></a>
        """
        cases = [
            (
                ctld_html,
                {
                    "parser": "ctld_media",
                    "article": ".item",
                    "title": "h4.media-heading",
                    "title_link": "a",
                    "date": ".date",
                },
                "教學活動",
                "",
            ),
            (
                cal_html,
                {
                    "parser": "cal_news_card",
                    "article": ".item",
                    "title_link": "a",
                    "date": ".date-box",
                    "summary": ".article",
                },
                "英語活動",
                "英語活動摘要",
            ),
            (
                rcemi_html,
                {
                    "parser": "rcemi_article_box",
                    "article": ".item",
                    "title": ".article h3",
                    "title_link": ".missing-link",
                },
                "EMI 活動",
                "EMI 活動摘要",
            ),
        ]

        for html, config, expected_title, expected_summary in cases:
            with self.subTest(parser=config["parser"]):
                result = self.scrape(html, config)

                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]["date"], self.date_text)
                self.assertEqual(result[0]["title"], expected_title)
                self.assertEqual(result[0]["summary"], expected_summary)

    def test_sdgs_and_wix_cards(self):
        sdgs_html = f"""
        <article class="item">
          <h2 class="entry-title"><a href="/sdgs">永續活動</a></h2>
          <div class="elementskit-meta-lists">{self.day} {self.month}月</div>
          <div class="elementskit-post-body"><p>永續活動摘要</p></div>
        </article>
        """
        wix_html = f"""
        <article class="item">
          <a href="/wix"><span data-hook="post-title">心理文章</span></a>
          <span data-hook="post-date">{self.month}月{self.day}日</span>
          <p data-hook="post-description">心理文章摘要</p>
        </article>
        """
        cases = [
            (
                sdgs_html,
                {
                    "parser": "sdgs_elementskit_card",
                    "article": ".item",
                    "title_link": ".entry-title a",
                },
                "永續活動",
                "永續活動摘要",
            ),
            (
                wix_html,
                {
                    "parser": "wix_blog_card",
                    "article": ".item",
                    "title": "[data-hook='post-title']",
                    "title_link": "a",
                    "date": "[data-hook='post-date']",
                    "summary": "[data-hook='post-description']",
                },
                "心理文章",
                "心理文章摘要",
            ),
        ]

        for html, config, expected_title, expected_summary in cases:
            with self.subTest(parser=config["parser"]):
                result = self.scrape(html, config)

                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]["date"], self.date_text)
                self.assertEqual(result[0]["title"], expected_title)
                self.assertEqual(result[0]["summary"], expected_summary)


if __name__ == "__main__":
    unittest.main()
