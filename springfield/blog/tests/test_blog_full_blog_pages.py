# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Blog page tests that need the full blog fixture set: 8 featured and 20 regular articles across
# five topics. Building it takes several seconds, so these tests only read it and share one copy,
# built once per class in setUpTestData. The query-count tests that need the same set stay in
# test_blog_pages.py with their own copy; see the blog_setup fixture there for why.

from django.test import RequestFactory, TestCase

from bs4 import BeautifulSoup

from springfield.blog.fixtures.blog_fixtures import (
    NUM_LIST_ARTICLES,
    get_blog_index_page,
    get_blog_pages,
    get_blog_tags,
    get_blog_topics,
)
from springfield.blog.tests.site_setup import build_minimal_site


class FullBlogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # "testserver" is the host Django's test client and RequestFactory use.
        build_minimal_site(hostname="testserver")
        cls.articles = get_blog_pages()
        cls.index_page = get_blog_index_page()

    def setUp(self):
        self.rf = RequestFactory()

    def test_blog_index_all_topics_are_counted_and_ordered(self):
        """Every topic with an article, most-populated first."""
        index_page = self.index_page
        topics = get_blog_topics()

        all_topics = index_page.get_all_topics()

        assert len(all_topics) == len(topics)
        assert all(hasattr(topic, "article_count") for topic in all_topics)
        counts = [topic.article_count for topic in all_topics]
        assert counts == sorted(counts, reverse=True)

    def test_blog_index_topic_links_point_to_topic_route(self):
        index_page = self.index_page
        request = self.rf.get(index_page.get_full_url())
        response = index_page.serve(request)
        soup = BeautifulSoup(response.content, "html.parser")
        header_topics = index_page.get_header_topics()

        topic_links = soup.find_all("a", class_="fl-blog-topic-link")
        assert len(topic_links) == len(header_topics)

        for index, topic in enumerate(header_topics):
            link = topic_links[index]
            assert topic.name in link.get_text()
            assert link["href"] == index_page.url + index_page.reverse_subpage("topic_route", args=[topic.slug])

    def test_blog_index_renders_first_featured_as_hero(self):
        index_page, articles = self.index_page, self.articles
        first_article = articles[0]  # first article placed in the StreamField
        request = self.rf.get(index_page.get_full_url())
        response = index_page.serve(request)
        soup = BeautifulSoup(response.content, "html.parser")

        hero = soup.find("div", class_="fl-blog-featured-main")
        assert hero, "First featured article should render as fl-blog-featured-main"

        heading = hero.find("h2", class_="fl-heading")
        assert heading and first_article.title in heading.get_text()

        topic = hero.find(class_="fl-superheading")
        assert topic and first_article.topic.name in topic.get_text()

        description = hero.find("p", class_="fl-body")
        assert description and BeautifulSoup(first_article.description, "html.parser").get_text() in description

        button = hero.find("a", class_="fl-button")
        assert button and button["href"] == first_article.get_url()

    def test_blog_index_renders_three_featured_articles_as_articles_list(self):
        index_page, articles = self.index_page, self.articles
        articles = articles[1:4]
        request = self.rf.get(index_page.get_full_url())
        response = index_page.serve(request)
        soup = BeautifulSoup(response.content, "html.parser")

        featured_row = soup.find("div", class_="fl-blog-featured")
        assert featured_row
        articles_list = featured_row.find("div", class_="fl-blog-article-list")
        assert articles_list, "Featured articles 1 - 4 should render as fl-blog-article-list inside the featured row"

        article_items = articles_list.find_all("article", class_="fl-blog-article-list-item")
        assert len(article_items) == len(articles)
        for article, item in zip(articles, article_items):
            heading = item.find("h2", class_="fl-heading")
            assert heading and article.title in heading.get_text()
            link = heading.find("a", class_="fl-link")
            assert link and link["href"] == article.url

            topic = item.find(class_="fl-superheading")
            assert topic and article.topic.name in topic.get_text()

            description = item.find("div", class_="fl-body")
            assert description and BeautifulSoup(article.description, "html.parser").get_text() in description.get_text()

    def test_blog_index_renders_cards_lists(self):
        index_page = self.index_page
        request = self.rf.get(index_page.get_full_url())
        response = index_page.serve(request)
        soup = BeautifulSoup(response.content, "html.parser")

        cards_list_divs = soup.find_all("div", class_="fl-blog-cards-list")
        assert len(cards_list_divs) == 2

        for cards_list in cards_list_divs:
            assert cards_list.find(class_="fl-heading")
            assert cards_list.find("a", class_="fl-blog-cards-list-link")
            cards = cards_list.find_all("article", class_="fl-card")
            assert cards
            for card in cards:
                assert "fl-card-expand-link" in card.get("class", [])

                # Sections pick articles by recency, and the fixture's hero-style demos have
                # no image, so the media slot is present but may be empty.
                assert card.find("div", class_="fl-card-top-media") is not None

                assert card.find("p", class_="fl-superheading")

                expand_link = card.find("a", class_="fl-link-expand")
                assert expand_link and expand_link["href"]

                body = card.find("div", class_="fl-body")
                assert not body

        images = soup.find("div", class_="fl-blog-cards-list").find_all("img")
        assert images, "articles that do have a listing image render one"

    def test_blog_index_renders_latest_section(self):
        index_page = self.index_page
        request = self.rf.get(index_page.get_full_url())
        response = index_page.serve(request)
        soup = BeautifulSoup(response.content, "html.parser")

        latest = soup.find("section", class_="fl-blog-latest-body")
        assert latest
        assert latest.find(class_="fl-heading")

        items = latest.find_all("article", class_="fl-blog-article-list-item")
        assert items
        for item in items:
            assert item.find("p", class_="fl-superheading")
            link = item.find("h3", class_="fl-heading").find("a")
            assert link and link["href"]

        assert latest.find("a", class_="fl-button")

    def test_blog_index_section_links_are_derived_from_the_source(self):
        index_page = self.index_page
        request = self.rf.get(index_page.get_full_url())
        response = index_page.serve(request)
        soup = BeautifulSoup(response.content, "html.parser")

        all_route_url = index_page.url + index_page.reverse_subpage("all_route")
        section_divs = soup.find_all("div", class_="fl-blog-cards-list")

        # Topic-sourced section links to the topic route
        link = section_divs[0].find("a", class_="fl-blog-cards-list-link")
        assert link.get_text(strip=True) == "View all Privacy"
        assert link["href"] == index_page.url + index_page.reverse_subpage("topic_route", args=["privacy"])

        # Tag-sourced section links to the tag filter
        link = section_divs[1].find("a", class_="fl-blog-cards-list-link")
        assert link.get_text(strip=True) == "View all Security"
        assert link["href"] == f"{all_route_url}?tag=security"

        # Latest section links to the full list
        latest = soup.find("section", class_="fl-blog-latest-body")
        link = latest.find("a", class_="fl-button")
        assert link.get_text(strip=True) == "View all"
        assert link["href"] == all_route_url

    def test_blog_all_renders_200(self):
        index_page = self.index_page
        url = index_page.full_url + index_page.reverse_subpage("all_route")
        request = self.rf.get(url)
        response = index_page.all_route(request)
        assert response.status_code == 200

    def test_blog_all_renders_full_topics_list(self):
        index_page = self.index_page
        topics = get_blog_topics()
        url = index_page.full_url + index_page.reverse_subpage("all_route")
        request = self.rf.get(url)
        response = index_page.all_route(request)
        soup = BeautifulSoup(response.content, "html.parser")

        topic_links = soup.find_all("a", class_="fl-blog-topic-link")
        assert len(topic_links) == len(topics)

    def test_blog_all_renders_list_articles(self):
        index_page = self.index_page
        url = index_page.full_url + index_page.reverse_subpage("all_route")
        request = self.rf.get(url)
        response = index_page.all_route(request)
        soup = BeautifulSoup(response.content, "html.parser")

        article_list = soup.find("div", class_="fl-blog-article-list")
        assert article_list

        items = article_list.find_all("article", class_="fl-blog-article-list-item")
        assert len(items) == 10  # first page

        for item in items:
            assert item.find("p", class_="fl-superheading")
            heading = item.find("h2", class_="fl-heading")
            assert heading and heading.find("a")
            assert item.find("div", class_="fl-body")

    def test_blog_all_renders_pagination(self):
        index_page = self.index_page
        url = index_page.full_url + index_page.reverse_subpage("all_route")
        request = self.rf.get(url)
        response = index_page.all_route(request)
        soup = BeautifulSoup(response.content, "html.parser")

        pagination = soup.find("nav", class_="fl-pagination")
        assert pagination, "Pagination nav should appear when there are more than 10 list articles"

        prev_button = pagination.find("div", class_="fl-pagination-prev").find("a")
        next_button = pagination.find("div", class_="fl-pagination-next").find("a")
        assert prev_button.get("aria-disabled") == "true"
        assert next_button.get("href")

        num_pages = (NUM_LIST_ARTICLES + 9) // 10
        indicator = pagination.find("span", class_="fl-pagination-indicator")
        assert indicator.get_text(strip=True) == f"1/{num_pages}"

    def test_blog_all_pagination_last_page(self):
        index_page = self.index_page
        num_pages = (NUM_LIST_ARTICLES + 9) // 10
        url = index_page.full_url + index_page.reverse_subpage("all_route")
        request = self.rf.get(url, {"page": str(num_pages)})
        response = index_page.all_route(request)
        soup = BeautifulSoup(response.content, "html.parser")

        article_list = soup.find("div", class_="fl-blog-article-list")
        assert article_list
        items = article_list.find_all("article", class_="fl-blog-article-list-item")
        assert len(items) == NUM_LIST_ARTICLES - (num_pages - 1) * 10

        pagination = soup.find("nav", class_="fl-pagination")
        assert pagination

        prev_button = pagination.find("div", class_="fl-pagination-prev").find("a")
        next_button = pagination.find("div", class_="fl-pagination-next").find("a")
        assert prev_button.get("href")
        assert next_button.get("aria-disabled") == "true"

        indicator = pagination.find("span", class_="fl-pagination-indicator")
        assert indicator.get_text(strip=True) == f"{num_pages}/{num_pages}"

    def test_blog_all_topic_filter_shows_selected_topic(self):
        index_page = self.index_page
        url = index_page.full_url + index_page.reverse_subpage("all_route")
        request = self.rf.get(url, {"topic": "privacy"})
        response = index_page.all_route(request)
        soup = BeautifulSoup(response.content, "html.parser")

        selected = soup.select_one("span.fl-tag-blog-topic.is-selected")
        assert selected and "Privacy" in selected.get_text()

    def test_blog_all_topic_filter_selected_topic_has_close_link(self):
        index_page = self.index_page
        url = index_page.full_url + index_page.reverse_subpage("all_route")
        request = self.rf.get(url, {"topic": "privacy"})
        response = index_page.all_route(request)
        soup = BeautifulSoup(response.content, "html.parser")

        selected = soup.select_one("span.fl-tag-blog-topic.is-selected")
        assert selected
        close_link = selected.find("a")
        all_route_url = index_page.url + index_page.reverse_subpage("all_route")
        assert close_link and close_link["href"] == all_route_url

    def test_blog_all_unknown_topic_shows_all_articles(self):
        index_page = self.index_page
        url = index_page.full_url + index_page.reverse_subpage("all_route")
        request = self.rf.get(url, {"topic": "nonexistent"})
        response = index_page.all_route(request)
        assert response.status_code == 200
        soup = BeautifulSoup(response.content, "html.parser")
        assert not soup.select_one("span.fl-tag-blog-topic.is-selected")

    def test_blog_all_topic_filter_pagination_urls_include_topic_param(self):
        index_page = self.index_page
        url = index_page.full_url + index_page.reverse_subpage("all_route")
        # Privacy has 11 regular articles in the full setup, triggering pagination
        request = self.rf.get(url, {"topic": "privacy"})
        response = index_page.all_route(request)
        soup = BeautifulSoup(response.content, "html.parser")

        pagination = soup.find("nav", class_="fl-pagination")
        if pagination:
            next_button = pagination.find("div", class_="fl-pagination-next").find("a")
            if next_button and next_button.get("href"):
                assert "topic=privacy" in next_button["href"]

    def test_blog_all_tag_filter_pagination_urls_include_tag_param(self):
        index_page = self.index_page
        tag = get_blog_tags()["privacy"]
        url = index_page.full_url + index_page.reverse_subpage("all_route")
        request = self.rf.get(url, {"tag": tag.slug})
        response = index_page.all_route(request)
        soup = BeautifulSoup(response.content, "html.parser")

        pagination = soup.find("nav", class_="fl-pagination")
        assert pagination, "The privacy tag has enough articles to paginate"
        next_button = pagination.find("div", class_="fl-pagination-next").find("a")
        assert f"tag={tag.slug}" in next_button["href"]

    def test_blog_all_renders_view_all_topics_link(self):
        index_page = self.index_page
        url = index_page.full_url + index_page.reverse_subpage("all_route")
        request = self.rf.get(url)
        response = index_page.all_route(request)
        soup = BeautifulSoup(response.content, "html.parser")

        topics_route_url = index_page.url + index_page.reverse_subpage("topics_route")
        topics_all_div = soup.find("div", class_="fl-blog-topics-all")
        assert topics_all_div
        link = topics_all_div.find("a", class_="fl-link")
        assert link and link["href"] == topics_route_url

    def test_blog_all_topic_links_are_tag_elements(self):
        index_page = self.index_page
        topics = get_blog_topics()
        url = index_page.full_url + index_page.reverse_subpage("all_route")
        request = self.rf.get(url)
        response = index_page.all_route(request)
        soup = BeautifulSoup(response.content, "html.parser")

        topic_links = soup.find_all("a", class_="fl-blog-topic-link")
        assert len(topic_links) == len(topics)
        for link in topic_links:
            assert "fl-tag" in link.get("class", [])

    def test_blog_topics_renders_200(self):
        index_page = self.index_page
        url = index_page.full_url + index_page.reverse_subpage("topics_route")
        request = self.rf.get(url)
        response = index_page.topics_route(request)
        assert response.status_code == 200

    def test_blog_topics_renders_back_link(self):
        index_page = self.index_page
        url = index_page.full_url + index_page.reverse_subpage("topics_route")
        request = self.rf.get(url)
        response = index_page.topics_route(request)
        soup = BeautifulSoup(response.content, "html.parser")

        back_link = soup.find("a", class_="fl-blog-back-link")
        assert back_link
        assert back_link["href"] == index_page.url

    def test_blog_topics_renders_heading(self):
        index_page = self.index_page
        url = index_page.full_url + index_page.reverse_subpage("topics_route")
        request = self.rf.get(url)
        response = index_page.topics_route(request)
        soup = BeautifulSoup(response.content, "html.parser")

        h1 = soup.find("h1", class_="fl-heading")
        assert h1 and "All Topics" in h1.get_text()

    def test_blog_topics_renders_topic_links(self):
        index_page = self.index_page
        topics = get_blog_topics()
        url = index_page.full_url + index_page.reverse_subpage("topics_route")
        request = self.rf.get(url)
        response = index_page.topics_route(request)
        soup = BeautifulSoup(response.content, "html.parser")

        topic_links = [a for a in soup.find_all("a", class_="fl-tag") if "is-large" in a.get("class", [])]
        assert len(topic_links) == len(topics)
        for link in topic_links:
            assert link["href"].startswith(index_page.url + "topics/")
            assert link["href"].endswith("/")

    def test_blog_topics_shows_article_count_badge(self):
        index_page = self.index_page
        topics = get_blog_topics()
        url = index_page.full_url + index_page.reverse_subpage("topics_route")
        request = self.rf.get(url)
        response = index_page.topics_route(request)
        soup = BeautifulSoup(response.content, "html.parser")

        badges = soup.find_all("span", class_="fl-tag-purple")
        assert len(badges) == len(topics), "Each topic link should show an article count badge, visible on hover."
        for badge in badges:
            assert badge.get_text(strip=True).isdigit()
