# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Title of the page that lists all topics available in the blog.
blog-all-topics = All Topics

# Button leading to the page that lists every topic.
blog-view-all-topics = View all topics

# A button leading to the full list of articles, used next to a
# section that shows only a few (for example "Latest Articles").
blog-all-articles = All Articles

# The heading of the page that lists all articles
blog-all-articles-heading = All Articles


# Link text on an article preview card, leading to the full article.
blog-read-more = Read more

# Heading of the article page section that lists related articles
blog-related-articles = Related Articles

# Accessibility label for the page navigation controls (previous/next
# page, page numbers) at the bottom of the article listing. Only shown
# when there is more than one page. Read by screen readers; not shown
# visually.
blog-pagination-label = Pagination

# Button text that removes the currently selected topic filter and
# shows all articles again.
blog-clear-topic-filter = Clear topic filter

# Variables:
#   $date (Date) - the date the article was last modified. Formatted
#   automatically for the locale.
blog-last-updated = Last updated on { $date }

# Variables:
#   $authors (String) - one or more author names, already joined into
#   a localized list (for example "Ada Lovelace, Grace Hopper, and
#   Alan Turing"). Can be a single name.
blog-byline = By { $authors }
