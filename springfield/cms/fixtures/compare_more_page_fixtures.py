# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# ruff: noqa: E501

"""
Fixtures for Firefox /compare/ and /more/ pages.

These fixtures create ArticleIndexPage + ArticleDetailPage instances for each
compare/more page, allowing them to be served via the CMS instead of Django views.

IMPORTANT: The content in COMPARE_PAGES and MORE_PAGES must match the FTL source
strings exactly (after brand term expansion) for translation import to work correctly.

FTL brand terms are expanded as follows (see ftl_parser.BRAND_TERMS for the full list):
    { -brand-name-firefox }         -> Firefox
    { -brand-name-firefox-browser } -> Firefox Browser
    { -brand-name-mozilla }         -> Mozilla
    etc.

Links use standard HTML <a href="..."> format. Wagtail-Localize extracts the href
as an OverridableSegment, allowing translators to modify the URL if needed.
The FTL import script normalizes both <a href="..."> and <a { $url }> to <a>
for matching purposes, so exact URLs do not need to match the template.
"""

from pathlib import Path

from django.conf import settings
from django.core.files.images import ImageFile

from wagtail.models import Locale, Site

from springfield.cms.models import ArticleDetailPage, ArticleIndexPage, SpringfieldImage

# =============================================================================
# Images
# =============================================================================

MORE_IMAGES = {
    "faq": {
        "file": "img/firefox/more/faq.jpg",
        "title": "Firefox FAQ illustration",
    },
}

MORE_PAGE_IMAGES = {
    "best-browser": {
        "file": "img/firefox/more/best-browser/hero-pattern.png",
        "title": "Firefox best browser hero pattern",
    },
    "browser-history": {
        "file": "img/firefox/more/browser-history.jpg",
        "title": "Firefox browser history illustration",
    },
    "faq": {
        "file": "img/firefox/more/faq.jpg",
        "title": "Firefox FAQ illustration",
    },
    "incognito-browser": {
        "file": "img/firefox/more/incognito-browser.jpg",
        "title": "Firefox incognito browser illustration",
    },
    "update-your-browser": {
        "file": "img/firefox/more/update-browser.jpg",
        "title": "Firefox update browser illustration",
    },
    "what-is-a-browser": {
        "file": "img/firefox/more/what-is-a-browser.jpg",
        "title": "Firefox what is a browser illustration",
    },
    "windows-64-bit": {
        "file": "img/firefox/more/firefox-64-bit.jpg",
        "title": "Firefox 64-bit illustration",
    },
}


def _get_or_import_image(info: dict) -> SpringfieldImage:
    """Get or import a SpringfieldImage by title, creating it from the media file if needed."""
    existing = SpringfieldImage.objects.filter(title=info["title"]).first()
    if existing:
        return existing
    static_path = Path(settings.ROOT) / "media" / info["file"]
    with open(static_path, "rb") as f:
        image = SpringfieldImage(title=info["title"])
        image.file.save(static_path.name, ImageFile(f, name=static_path.name))
    return image


def get_or_import_more_image(slug: str) -> SpringfieldImage:
    """Get or import the article image for a more page."""
    return _get_or_import_image(MORE_IMAGES[slug])


def get_or_import_more_page_image(slug: str) -> SpringfieldImage:
    """Get or import the featured image for a more page."""
    return _get_or_import_image(MORE_PAGE_IMAGES[slug])


# =============================================================================
# FTL file constants
#
# The management command (create_compare_more_pages) and the repair command
# (repair_compare_more_translations) use these to look up translations for
# both index page fields (other_articles_heading, etc.) and detail page content.
# =============================================================================

COMPARE_INDEX_FTL_FILES = [
    "firefox/browsers/compare/index.ftl",
    "firefox/browsers/compare/shared.ftl",
]

MORE_INDEX_FTL_FILES = [
    "firefox/more/more.ftl",
    "firefox/more/shared.ftl",
]

# =============================================================================
# Compare page content
#
# IMPORTANT: content strings must match FTL source strings after brand expansion.
# FTL files: firefox/browsers/compare/<slug>.ftl + firefox/browsers/compare/shared.ftl
# =============================================================================

COMPARE_PAGES = {
    "brave": {
        "ftl_files": [
            "firefox/browsers/compare/brave.ftl",
            "firefox/browsers/compare/shared.ftl",
        ],
        # compare-brave-firefox-vs-brave
        "title": "Firefox vs Brave",
        # compare-brave-read-our-comparison
        "description": "<p>Read our comparison of Firefox and Brave browsers on features, privacy, and ease-of-use.</p>",
        "featured": False,
        "content": """
<p>Firefox's privacy settings are strong and easy to use. Brave's default ad blocking may break the websites you visit, so you have to keep fiddling with it. We want privacy to be convenient enough that you'll actually <em>use</em> it.</p>

<p>Firefox makes it easy for you to choose which search engine you want to use every time you search. Brave defaults to their own search engine, and you have to go through the browser settings to pick something different.</p>

<p>Firefox gives you the option to encrypt your saved passwords, and you can <a href="https://support.mozilla.org/kb/use-primary-password-protect-stored-logins">use a primary password to access them</a>; your passwords are protected even if you have to share a computer. Brave does not password-protect your passwords.</p>

<p>We also offer easy-to-use features such as:</p>
<ul>
<li><a href="https://www.firefox.com/features/pdf-editor/">Edit PDFs</a> on the go within your Firefox browser window - no extra software needed.</li>
<li><a href="https://www.firefox.com/features/translate/">Translate a web page</a> locally and privately.</li>
</ul>

<h2>It's easy to switch</h2>

<p>Switching to Firefox is easy and fast - import your Brave bookmarks, your passwords, history and preferences with one click and immediately be ready to use Firefox. Here's <a href="https://support.mozilla.org/kb/import-data-another-browser">how to import your Brave data</a>.</p>
""",
    },
    "chrome": {
        "ftl_files": [
            "firefox/browsers/compare/chrome.ftl",
            "firefox/browsers/compare/shared.ftl",
        ],
        # compare-chrome-firefox-vs-google-chrome
        "title": "Firefox vs Google Chrome",
        # compare-chome-read-our-comparison
        "description": "<p>Read our comparison of Firefox and Chrome browsers on features, privacy, and ease-of-use.</p>",
        "featured": False,
        "content": """
<p>Firefox's default privacy settings are much stronger than Chrome's – and we have additional features to prevent websites from tracking you, such as <a href="https://www.firefox.com/features/block-fingerprinting/">fingerprint blocking</a>, as well as your choice of add-ons for <a href="https://www.firefox.com/features/adblocker/">ad blocking</a>.</p>

<h2>We block trackers by default. Chrome doesn't.</h2>

<p>In fact, by default Chrome monitors which websites you visit and what you do so that it can identify "ad topics" to send you more-targeted ads. You can block three topics but you can't make them stop identifying other ad topics for you.</p>

<p>Chrome allows other websites to collect information about you so that they can suggest ads. You can block specific sites from suggesting ads, but you can't stop the data collection or suggestions from other sites.</p>

<h2>Google runs the world's largest advertising network, and Chrome is part of that.</h2>

<p>Since we don't have to make shareholders happy, we can focus on making <strong>you</strong> happy and always put your privacy and convenience first.</p>

<h2>It's easy to switch</h2>

<p>Switching to Firefox is easy and fast — import your Chrome bookmarks, your passwords, history and preferences with one click and immediately be ready to use Firefox. Find out <a href="https://support.mozilla.org/kb/switching-chrome-firefox">how to switch from Chrome to Firefox</a>.</p>
""",
    },
    "edge": {
        "ftl_files": [
            "firefox/browsers/compare/edge.ftl",
            "firefox/browsers/compare/shared.ftl",
        ],
        # compare-edge-firefox-vs-microsoft-edge
        "title": "Firefox vs Microsoft Edge",
        # compare-edge-read-our-comparison
        "description": "<p>Read our comparison of Firefox and Edge browsers on features, privacy, and ease-of-use.</p>",
        "featured": False,
        "content": """
<p>Firefox makes privacy protection easy and convenient, so that you don't have to worry about it.</p>

<p>We block trackers by default. Edge doesn't.</p>

<p>We also offer easy-to-use features such as:</p>
<ul>
<li><a href="https://www.firefox.com/features/pdf-editor/">Edit PDFs</a> on the go within your Firefox browser window - no extra software needed.</li>
<li><a href="https://www.firefox.com/features/translate/">Translate a web page</a> locally and privately.</li>
</ul>

<p>And we make it easy for you to choose which search engine you use whenever you search. Edge makes you dig through your settings to use a search engine other than Bing.</p>

<p>Microsoft has to make their shareholders happy, but we can focus on making <strong>you</strong> happy and put your privacy first.</p>

<h2>It's easy to switch</h2>

<p>Switching to Firefox is easy and fast — import your Edge bookmarks, your passwords, history and preferences with one click and immediately be ready to use Firefox. Here's <a href="https://support.mozilla.org/kb/import-bookmarks-and-other-data-microsoft-edge">how to use the Import button to switch</a>.</p>
""",
    },
    "opera": {
        "ftl_files": [
            "firefox/browsers/compare/opera.ftl",
            "firefox/browsers/compare/shared.ftl",
        ],
        # compare-opera-firefox-vs-opera
        "title": "Firefox vs Opera",
        # compare-opera-read-our-comparison
        "description": "<p>Read our comparison of Firefox and Opera browsers on features, privacy, and ease-of-use.</p>",
        "featured": False,
        "content": """
<p>Firefox's default privacy settings are stronger than Opera's – and we have more features to prevent websites from tracking you, such as <a href="https://www.firefox.com/features/block-fingerprinting/">fingerprint blocking</a>.</p>

<p>Firefox also has built-in tools such as:</p>
<ul>
<li><a href="https://www.firefox.com/features/pdf-editor/">Edit PDFs</a> on the go within your Firefox browser window - no extra software needed.</li>
<li><a href="https://www.firefox.com/features/translate/">Translate a web page</a> locally and privately.</li>
</ul>

<p>Firefox offers a wide range of customization options, including the ability to move menus and toolbars to different locations on the browser window. Opera's interface is less customizable.</p>

<p>Since we don't have to make shareholders happy, we can focus on making <strong>you</strong> happy and always put your privacy and convenience first.</p>

<h2>It's easy to switch</h2>

<p>Switching to Firefox is easy and fast — import your Opera bookmarks, your passwords, history, and preferences with one click and immediately be ready to use Firefox. Here's <a href="https://support.mozilla.org/kb/import-data-another-browser">how to use the Import button to switch</a>.</p>
""",
    },
    "safari": {
        "ftl_files": [
            "firefox/browsers/compare/safari.ftl",
            "firefox/browsers/compare/shared.ftl",
        ],
        # compare-safari-firefox-vs-apple-safari
        "title": "Firefox vs Apple Safari",
        # compare-safari-read-our-comparison
        "description": "<p>Read our comparison of Firefox and Safari browsers on features, privacy, and ease-of-use.</p>",
        "featured": False,
        "content": """
<p>Safari and Firefox both have good privacy and security features.</p>

<p>But Firefox also has built-in tools such as:</p>
<ul>
<li><a href="https://www.firefox.com/features/pdf-editor/">Edit PDFs</a> on the go within your Firefox browser window - no extra software needed.</li>
<li><a href="https://www.firefox.com/features/translate/">Translate a web page</a> locally and privately.</li>
</ul>

<p>Firefox offers a wide range of customization options, including the ability to move menus and toolbars to different locations on the browser window. Safari's interface is less customizable.</p>

<p>Since we don't have to make shareholders happy, we can focus on making <strong>you</strong> happy and always put your privacy and convenience first.</p>

<h2>It's easy to switch</h2>

<p>Switching to Firefox is easy and fast - import your Safari bookmarks, your passwords, history and preferences with one click and immediately be ready to use Firefox. Here's <a href="https://support.mozilla.org/kb/importing-safari-data-firefox">how to import your Safari data</a>.</p>
""",
    },
}

# =============================================================================
# More page content
#
# IMPORTANT: content strings must match FTL source strings after brand expansion.
# FTL files vary per page — see each entry's ftl_files list.
# incognito-browser and update-your-browser have no FTL (ftl_files=[]).
# =============================================================================

MORE_PAGES = {
    "best-browser": {
        "ftl_files": [
            "firefox/more/best-browser.ftl",
            "firefox/more/shared.ftl",
        ],
        # best-browser-find-your-best-browser
        "title": "Find your best browser for speed, privacy and security.",
        # best-browser-so-many-browser-options
        "description": "<p>So many browser options, but there's only one that works best for your needs. The best browser for you should offer both speed and privacy protection.</p>",
        "featured": False,
        "content": """
<p>The internet has become as essential as electricity and running water, so choosing the best browser for you is more important than ever. The internet is a second office, a teacher and sometimes a medical advisor, even if your actual doctor would prefer you didn't look up your symptoms online.</p>

<p>In the mid-nineties, Netscape, Internet Explorer and AOL dominated the landscape. It was a simpler time when the sweet melody of dial-up internet rang across the land. You learned the meaning of patience waiting for web pages to load. Back then, all that mattered was browser speed.</p>

<p>Today is a different story. Ads, privacy hacks, security breaches, and fake news might have you looking at other qualities in a browser. How does the browser protect your privacy? Does it allow trackers to follow you across the web? Is it built to multitask and handle many computer and internet operations at once?</p>

<p>When you use a browser for everything, it needs to be fast. But for the same reason, it needs to be private. A browser has access to everything you do online, so it can put you at real risk if it doesn't have strong privacy features.</p>

<p>If you're wondering what it means to have a private or fast browser, here's a breakdown of three things a browser should have.</p>

<h2>A browser built for speed.</h2>

<p>A browser is still a tool, so it makes sense that you'll want to pick the best one for the job. If you're a human who needs to work to survive, you'll need a fast internet browser. One thing to keep in mind is a browser that runs third-party trackers is more likely to be slower than a browser that doesn't. Third-party trackers are cookies, and while you can't see them, they are running in the background of the site, taking up precious time. The more third-party trackers a browser blocks, the faster it can run.</p>

<p>This is one of the many reasons to choose the Firefox browser: Firefox blocks third-party trackers by default. We have other reasons and we'll get into those later.</p>

<h2>A browser that puts safety first.</h2>

<p>Remember the last massive data breach? If not, it's probably because it happens so often. Companies hold on to customer data, like their personal or financial information, and hackers steal it. If you're making safety a priority, then a secure internet browser is the best browser for you.</p>

<p>There are a few ways a browser can help its users stay secure. A browser that is up to date with the latest security tech can help protect your computer and websites from unwanted visitors, such as malware or computer viruses.</p>

<p>The second is not storing too much user data. Hackers can't steal what's not there, which is why Firefox keeps a minimum amount of information about its users. <a href="https://www.mozilla.org/privacy/firefox/">Firefox knows</a> if you use the browser and your general location <a href="https://www.mozilla.org/privacy/firefox/">but not the name of your childhood pet or your favorite color.</a></p>

<p>Last but not least, a safe browser should offer tools to help you keep an eye on your accounts. Think of alerts that go straight to your email if any of your accounts get breached or icons that tell you whether a website is encrypted, (i.e., if it's a good idea to enter your credit number on a shopping site).</p>

<p>Firefox is offering something new to keep you safe: <a href="https://monitor.mozilla.org/">Mozilla Monitor</a>. It's a free service that will alert you if there are any public hacks on your accounts and let you know if your accounts got hacked in the past. Another neat feature is the Green Lock. It looks like a small green icon at the top left side of the browser window. If you're on Firefox and see the green lock, it means the website is encrypted and secure. If the lock is grey, you might want to think twice about entering any sensitive information.</p>

<p>We visit hundreds or even thousands of websites each day, and you can't expect users to make security and privacy decisions for each of these sites. That is why a browser that gives you more control is so important - because it offers real, meaningful protection.</p>

<h2>A browser that minds its business.</h2>

<p>Privacy on the web is a hot button issue. If privacy is number one on your list of priorities, you want to look for a browser that takes that seriously. When choosing the best private browser for you, look at the tracking policy and how a browser handles your data. These seem like technical questions, but they're the reason some browsers are more private than others.</p>

<p>Trackers are all those annoying "cookies" messages you get on airline sites. These third-party trackers know where you click and can be used to analyze your behavior. A private browser should give users the option to turn off third-party trackers, but ideally, turn them off by default.</p>

<p>Another way to stop trackers from tracking is using private mode to browse. Any browser that claims to be private should offer browsing in private mode.</p>

<p>One easy way to check is to visit a browser's content setting page and privacy policy. The privacy webpage should outline if your data is shared and why. It's why the <a href="https://www.mozilla.org/privacy/firefox/">Firefox privacy notice</a> is easy to read and easy to find.</p>

<p>Choosing the best browser for you is a lot like choosing a home. You want to explore your options, do some research and make a decision based on what's important to you.</p>

<p>At <a href="https://www.firefox.com/">Firefox</a>, we've worked hard to build a browser that is twice as fast as before and gives users more control over their online life.</p>
""",
    },
    "browser-history": {
        "ftl_files": [
            "firefox/more/browser-history.ftl",
            "firefox/more/shared.ftl",
        ],
        # browser-history-browser-history
        "title": "Browser History: Epic power struggles that brought us modern browsers",
        # browser-history-the-browser-wars-underdogs-giants
        "description": "<p>The browser wars, underdogs vs giants, and moments that changed the world. Read about the history of the web browser.</p>",
        "featured": False,
        "content": """
<h2>The History of Web Browsers</h2>

<p>World history is rife with epic power struggles, world-conquering tyrants, and heroic underdogs. The history of web browsers isn't very different. University pioneers wrote simple software that sparked an information revolution, and battle for browser superiority and internet users.</p>

<h2>Before Web Era</h2>

<p>In 1950, computers took up whole rooms and were dumber than today's pocket calculators. But progress was swift, and by 1960 they were able to run complex programs. Governments and universities across the globe thought it would be great if the machines could talk, nurturing collaboration and scientific breakthroughs.</p>

<p><a href="https://en.wikipedia.org/wiki/ARPANET">ARPANET</a> was the first successful networking project and in 1969 the first message was sent from the computer science lab at University of California, Los Angeles (UCLA) to Stanford Research Institute (SRI), also in California.</p>

<p>That sparked a revolution in computer networking. New networks formed, connecting universities and research centers across the globe. But for the next 20 years, the internet wasn't accessible to the public. It was restricted to university and government researchers, students, and private corporations. There were dozens of programs that could trade information over telephone lines, but none of them were easy to use. The real open internet, and the first web browser, wasn't created until 1990.</p>

<h2>Web Era</h2>

<p>British computer scientist Tim Berners-Lee created the first web server and graphical web browser in 1990 while <a href="https://home.cern/topics/birth-web">working at CERN</a>, the European Organization for Nuclear Research, in Switzerland. He called his new window into the internet "WorldWideWeb." It was an easy-to-use graphical interface created for the NeXT computer. For the first time, text documents were linked together over a public network—the web as we know it.</p>

<p>A year later, Berners-Lee asked CERN math student Nicola Pellow to write the Line Mode Browser, a program for basic computer terminals.</p>

<p>By 1993, the web exploded. Universities, governments, and private corporations all saw opportunity in the open internet. Everyone needed new computer programs to access it. That year, Mosaic was created at the National Center for Supercomputing Applications (NCSA) at the University of Illinois Urbana-Champaign by computer scientist Marc Andreessen. It was the very first popular web browser and the early ancestor of <a href="https://en.wikipedia.org/wiki/Firefox">Mozilla Firefox</a>.</p>

<p>NCSA Mosaic ran on Windows computers, was easy to use, and gave anyone with a PC access to early web pages, chat rooms, and image libraries. The next year (1994), Andreessen founded <a href="https://en.wikipedia.org/wiki/Netscape_(web_browser)">Netscape</a> and released Netscape Navigator to the public. It was wildly successful, and the first browser for the people. It was also the first move in a new kind of war for internet users.</p>

<h2>The Browser Wars</h2>

<p>By 1995, Netscape Navigator wasn't the only way to get online. Computer software giant Microsoft licensed the old Mosaic code and built its own window to the web, <a href="https://en.wikipedia.org/wiki/Internet_Explorer">Internet Explorer</a>. The release sparked a war. Netscape and Microsoft worked feverishly to make new versions of their programs, each attempting to outdo the other with faster, better products.</p>

<p>Netscape created and released JavaScript, which gave websites powerful computing capabilities they never had before. (They also made the infamous <a href="https://developer.mozilla.org/en-US/docs/Glossary/blink_element">&lt;blink&gt; tag</a>.) Microsoft countered with Cascading Style Sheets (CSS), which became the standard for web page design.</p>

<p>Things got a little out of hand in 1997 when Microsoft released Internet Explorer 4.0. The team built a giant letter "e" and snuck it on the lawn of Netscape headquarters. The Netscape team promptly knocked the giant "e" over and <a href="https://medium.com/@ddprrt/tales-from-the-browser-wars-mozilla-stomps-internet-explorer-799035887cb1">put their own Mozilla dinosaur mascot on top of it</a>.</p>

<p>Then Microsoft began shipping Internet Explorer with their Windows operating system. Within 4 years, it had 75% of the market and by 1999 it had 99% of the market. The company faced antitrust litigation over the move, and Netscape decided to open source its codebase and created the not-for-profit <a href="https://en.wikipedia.org/wiki/Mozilla">Mozilla</a>, which went on to create and release Firefox in 2002. Realizing that having a browser monopoly wasn't in the best interests of users and the open web, Firefox was created to provide choice for web users. By 2010, Mozilla Firefox and others had <a href="https://en.wikipedia.org/wiki/Internet_Explorer#Market_adoption_and_usage_share">reduced Internet Explorer's market share to 50%</a>.</p>

<p>Other competitors emerged during the late '90s and early 2000s, including Opera, Safari, and Google Chrome. Microsoft Edge replaced Internet Explorer with the release of Windows 10 in 2015.</p>

<h2>Browsing the Web Today</h2>

<p>Today there are just a handful of ways to access the internet. Firefox, Google Chrome, Microsoft Edge, Safari and Opera are the main competitors. Mobile devices have emerged during the past decade as the preferred way to access the internet. Today, most internet users only use mobile browsers and <a href="https://blog.mozilla.org/firefox/no-judgment-digital-definitions-app-vs-web-app/">applications</a> to get online. Mobile versions of the major browsers are available for iOS and Android devices. While these apps are very useful for specific purposes, they only provide limited access to the web.</p>

<p>In the future, the web will likely stray further from its hypertext roots to become a vast sea of interactive experiences. Virtual reality has been on the horizon for decades (at least since the release of Lawnmower Man in 1992 and the Nintendo Virtual Boy in 1995), but the web may finally bring it to the masses. Firefox now has support for WebVR and A-Frame, which let developers quickly and easily build virtual reality websites. Most modern mobile devices support WebVR, and can easily be used as headsets with simple cardboard cases. A 3D virtual reality web like the one imagined by science fiction author Neal Stephenson may be just around the corner. If that's the case, the web browser itself may completely disappear and become a true window into another world.</p>

<p>Whatever the future of the web holds, Mozilla and Firefox will be there for users, ensuring that they have powerful tools to experience the web and all it has to offer. The web is for everyone, and everyone should have control of their online experience. That's why we give Firefox tools to protect user privacy and we never sell user data to advertisers.</p>

<h3>Resources</h3>

<ul>
<li><a href="https://en.wikipedia.org/wiki/Mosaic_(web_browser)">https://en.wikipedia.org/wiki/Mosaic_(web_browser)</a></li>
<li><a href="https://en.wikipedia.org/wiki/History_of_the_web_browser">https://en.wikipedia.org/wiki/History_of_the_web_browser</a></li>
<li><a href="https://en.wikipedia.org/wiki/History_of_the_Internet">https://en.wikipedia.org/wiki/History_of_the_Internet</a></li>
<li><a href="https://en.wikipedia.org/wiki/Browser_wars">https://en.wikipedia.org/wiki/Browser_wars</a></li>
<li><a href="https://home.cern/topics/birth-web">https://home.cern/topics/birth-web</a></li>
<li><a href="https://www.zdnet.com/article/before-the-web-the-internet-in-1991/">https://www.zdnet.com/article/before-the-web-the-internet-in-1991/</a></li>
</ul>
""",
    },
    "faq": {
        "ftl_files": [
            "firefox/more/faq.ftl",
        ],
        # firefox-faq
        "title": "Firefox FAQ",
        # whether-you-searched-privacy
        "description": "<p>Whether you searched for a fast browser that protects your privacy, this FAQ is here to answer the most pressing Firefox-related questions.</p>",
        "featured": False,
        "content": """
<p>Whether you searched for a fast browser, or you're looking for independent tech that protects your privacy, this FAQ is here to answer the most pressing Firefox-related questions.</p>

<h2>What is Firefox?</h2>
<p>The Firefox Browser, the only major browser backed by a not-for-profit, helps you protect your personal information. Learn more about the <a href="/">Firefox Browsers</a> and <a href="https://www.mozilla.org/products/">other products.</a></p>

<h2>How do I get the Firefox Browser?</h2>
<p>You can easily download the Firefox desktop browser <a href="/">here.</a> Firefox works on <a href="https://www.firefox.com/download/windows/">Windows,</a> <a href="https://www.firefox.com/download/mac/">Mac</a> and <a href="https://www.firefox.com/download/linux/">Linux</a> devices, and is also available for <a href="https://www.firefox.com/browsers/mobile/">Android and iOS.</a> Make sure you're downloading our browser from one of our trusted Mozilla/Firefox pages.</p>

<h2>Is Firefox free?</h2>
<p>Yep! The Firefox Browser is free. Super free, actually. No hidden costs or anything. You don't pay anything to use it.</p>

<h2>Is Chrome better than Firefox?</h2>
<p>No, we don't think Chrome is better than Firefox, and here is why: when people ask which browser is better, they're really asking which browser is faster and safer. Firefox is updated monthly to make sure you have the speediest browser that respects your privacy automatically.</p>
<p><a href="https://www.firefox.com/browsers/compare/chrome/">See how Firefox compares Chrome.</a></p>

<h2>Is Firefox safe to download?</h2>
<p>Protecting your privacy is our number one priority, and we ensure that installing Firefox on your devices is completely safe — but always make sure you are downloading from a trusted Mozilla/Firefox site, like <a href="/">our download page.</a></p>

<h2>Is Firefox safe?</h2>
<p>Not only is Firefox safe to use, it also helps keep your data and private information safe. The Firefox Browser automatically blocks known third party trackers, social media trackers, cryptominers and fingerprinters from collecting your data. <a href="https://www.firefox.com/features/private/">Learn more about the privacy in our products.</a></p>

<h2>Why is Firefox so slow?</h2>
<p>Firefox isn't slow… now. In 2017, we completely rebuilt our browser engine (called Quantum), to ensure Firefox could compete with other major browsers. And, our tracker blockers help pages load even faster. So Firefox is lightning fast without sacrificing any of your privacy.</p>

<h2>Is Firefox Chromium based?</h2>
<p>Firefox is not based on Chromium (the open source browser project at the core of Google Chrome). In fact, we're one of the last major browsers that isn't. Firefox runs on our Quantum browser engine built specifically for Firefox, so we can ensure your data is handled respectfully and kept private.</p>

<h2>Does Firefox use Google?</h2>
<p>Google is the default search engine in Firefox, which means you can search the web directly from the address bar. <a href="https://support.mozilla.org/kb/change-your-default-search-settings-firefox/">Learn more about search engine preferences and changing defaults.</a></p>

<h2>Does Firefox have a built-in VPN?</h2>
<p>Firefox does not have a built-in VPN (virtual private network), but Mozilla creates a product called <a href="https://www.mozilla.org/products/vpn/">Mozilla VPN</a> that you can use in addition to the private Firefox Browser that can protect your connection on Wi-Fi, as well as your IP address.</p>

<h2>Who owns Firefox?</h2>
<p>Firefox is made by Mozilla Corporation, a wholly owned subsidiary of the not-for-profit <a href="https://foundation.mozilla.org/">Mozilla Foundation,</a> and is guided by the principles of the Mozilla Manifesto. Learn more about the maker of Firefox <a href="https://www.mozilla.org/foundation/moco/">here.</a></p>
""",
    },
    "incognito-browser": {
        "ftl_files": [],  # no FTL — content is hardcoded in the template
        # more.ftl: incognito-browser-what
        "title": "Incognito browser: What it really means",
        # more.ftl: firefox-calls-it (after brand expansion)
        "description": "<p>Firefox calls it private browsing, Chrome calls it incognito mode. Both let you browse the web without saving your browsing history.</p>",
        "featured": False,
        "content": """
<p>Firefox calls it private browsing, Chrome calls it incognito mode. Both let you browse the web without saving your browsing history.</p>

<h2>What Incognito/Private Mode Does</h2>

<p>Incognito or private mode keeps your browsing history private. That's it.</p>

<h2>What Incognito/Private Mode Doesn't Do</h2>

<p>A 2018 survey of 460 internet users by the University of Chicago found that <a href="https://www.cnbc.com/2018/07/12/private-web-browsing-not-as-private-as-you-think-research.html">there are a lot of misconceptions</a> out there about private browsing or incognito mode. It won't protect you from viruses or malware. It won't keep your internet service provider (ISP) from seeing where you've been online. It won't stop websites from seeing your physical location. And any bookmarks you save while in private browsing or incognito mode won't disappear when you switch it off.</p>

<h2>Why go private/incognito?</h2>

<p>Just because you're using private browsing mode doesn't mean you're up to something nefarious. Perhaps you want to keep your work and personal life separate. You might share a computer or device and you don't want your siblings snooping. You could be shopping for a gift and you don't want anything to spoil the surprise. Or maybe you just want to limit the amount of data companies collect about you and you value privacy. Incognito or private browsing mode is made for any of these scenarios.</p>

<h3>Web Tracking</h3>

<p>A lot of sites keep track of your browsing activity. Most do it to understand if you're interested in purchasing a product or clicking on an article. They can also do it to help make their sites easier to use. But almost all tracking is done to serve you ads.</p>

<p>Online ads are customized based on your browsing. Been searching for a new pair of sandals? "Shoe Store X" has a great deal for you. The company knows where you've been because they dropped a bit of code into your browser called a cookie. The cookie tracks you, and so do Shoe Store X ads.</p>

<h3>Cookies</h3>

<p>Cookies were first used to customize websites, keep track of shopping carts, and maintain online account security, but today most are used to help companies serve targeted ads.</p>

<p>Here's how it works: You visit a site, an advertiser leaves a cookie on your browser. The cookie is your unique ID. Your information is stored in the cloud along with that ID. That can include which sites you visited, how long you visited them, what you clicked on, your language preferences and more.</p>

<p>Cookies also help advertisers deliver ads in your social media feeds. Social sites have their own tracking schemes and they're far more robust. They can track every click, post, and comment. In addition, cookies can report what you've been doing online to a social site, which is how some ads follow you into social media.</p>

<h2>Going Incognito</h2>

<p>So you've decided to keep to yourself online, to go incognito or enter private browsing mode. What does that mean? In Firefox, Private Browsing deletes cookie data when you close the browser window and doesn't track your browsing data. It also blocks tracking cookies by default. Finally, it won't remember any files you download, but those files will still be on your computer.</p>

<p>In Chrome, incognito mode does the same thing. In either case, your actions could be visible to the websites you visit, your employer or school, or your internet service provider (ISP). Also, if you sign into any accounts, your browsing activity may be saved to that account. And chances are if you're using Chrome, you'll be logged into your Google account.</p>

<h3>Firefox Tracking Protection</h3>

<p>Firefox goes beyond private browsing with <a href="https://support.mozilla.org/kb/tracking-protection">Tracking Protection</a>. It stops companies from following you around the web. It uses a list of tracking sites compiled by <a href="http://disconnect.me/">Disconnect.me</a>. Whenever a cookie tries to reach a site on the list, Tracking Protection blocks it.</p>

<h3>Firefox Multi-Account Containers</h3>

<p>The Firefox <a href="https://addons.mozilla.org/firefox/addon/multi-account-containers/">Multi-Account Containers</a> add-on isn't technically a form of private browsing or tracking protection, but it can help keep companies from knowing everything you do online. It lets you open fresh, cookie-free tabs that can be used for different accounts—personal, work, shopping, etc. That means you can use Multi-Account Containers to open several Google accounts at once without any overlap. Most trackers won't associate the different accounts, keeping your work life separate from your personal life online. Some more advanced trackers, however, can and will track you across different accounts, so beware.</p>

<h3>Is Incognito/Private Mode Really Private?</h3>

<p>Incognito or private mode will keep your local browsing private, but it won't stop your ISP, school, or employer from seeing where you've been online. In fact, your ISP has access to all your browsing activity pretty much no matter what you do.</p>

<p>You can, however, use a <a href="https://blog.mozilla.org/internetcitizen/2017/08/29/do-you-need-a-vpn/">Virtual Private Network (VPN) service</a>. VPN services route traffic through remote servers, so it looks like you're browsing from another location or multiple locations. VPN providers can track where you've been online, though, so it's good to find a company you can trust to either delete or lock up your browsing activity. VPNs won't block third-party cookies from advertisers, but those cookies won't be able to identify your location accurately, making it difficult or impossible for ad trackers to be effective.</p>

<p><a href="https://www.torproject.org/">Tor Browser</a> can truly mask your online activity. It bounces traffic through multiple servers around the globe, making it difficult to track that traffic. The website you visit really has no idea where you are, only the approximate location of the last server your request was routed through. But again, even Tor proxy won't stop third-party advertisers from installing cookies in your browser. Tor Browser deletes all cookies when closed. People can also start a new session in Tor Browser to clear them as well.</p>

<h3>Incognito: TL:DR</h3>

<p>Incognito mode keeps your browser history private, and that's pretty much it. If you want more privacy, you'll need to add <a href="https://support.mozilla.org/kb/tracking-protection">Tracking Protection</a> and maybe even browse through a <a href="https://blog.mozilla.org/internetcitizen/2017/08/29/do-you-need-a-vpn/">Virtual Private Network (VPN) service</a>. Incognito mode can't.</p>
""",
    },
    "update-your-browser": {
        "ftl_files": [],  # no FTL — content is hardcoded in the template
        # more.ftl: update-your-browser (after brand expansion)
        "title": "Update your browser to fast, safe and secure Firefox.",
        # more.ftl: the-firefox-browser (after brand expansion)
        "description": "<p>The Firefox browser is built to protect your privacy at every turn — because that's the fastest way to free you from slow loads, bad ads, and trackers.</p>",
        "featured": False,
        "content": """
<p>One of the most important things you can do to have a safe, fast and secure online browsing experience is to make sure your browser is up to date. Update your browser like you would update your apps. No matter which browser you use, make sure you're using the latest version.</p>

<h2>Stay safe, browse safe</h2>

<p>Up-to-date browsers protect you from viruses, security breaches and hacks. Older versions of browsers may be vulnerable to attacks and security holes. Firefox engineers have been known to ship a security update <a href="https://hacks.mozilla.org/2018/03/shipping-a-security-update-of-firefox-in-less-than-a-day/">within a day</a> of learning of a vulnerability.</p>

<h2>The fastest Firefox yet</h2>

<p>We work tirelessly to make sure Firefox is the fastest it can be, while making sure it doesn't hog your memory or system resources. With each version we make improvements to the code that makes Firefox quick and nimble as you browse.</p>

<h2>Always protected</h2>

<p>We are passionate about user privacy. With each new release we give you more ways to control who sees and accesses your personal browsing data. Tracking protection, private browsing and <a href="https://blog.mozilla.org/firefox/make-your-firefox-browser-a-privacy-superpower-with-these-extensions/">powerful privacy extensions</a> all work together to make sure your private browsing information stays yours.</p>

<h2>New features</h2>

<p>Whether it's enabling powerful new Mixed Reality features, improving <a href="https://support.mozilla.org/kb/accessibility-features-firefox-make-firefox-and-we">accessibility</a> or testing <a href="https://blog.mozilla.org/firefox/its-a-new-firefox-multi-tasking-extension-side-view/">extensions that enrich your life</a>, new browser releases always have something new and innovative for you to enjoy. Don't miss out by lagging behind on an older version.</p>

<h2>Why Firefox?</h2>

<p>Firefox is independent and a part of the not-for-profit Mozilla, which fights for your online rights, keeps corporate powers in check and makes the internet accessible to everyone, everywhere. We believe the internet is for people, not profit. You're in control over who sees your search and browsing history. All that and exceptional performance too.</p>

<h2>How do I update?</h2>

<p>Most major browsers update automatically, which means that when a new version is available, your system will download and install it for you. So that's one less thing you have to worry about keeping on top of. First find out <a href="https://blog.mozilla.org/firefox/info-worth-knowing-firefox-version-using/">which version of your browser you're on</a>. Then, if auto update is switched off, here's how to manually update <a href="https://support.mozilla.org/kb/update-firefox-latest-version">Firefox</a>, <a href="https://www.microsoft.com/en-ca/windows/microsoft-edge">Edge</a>, <a href="https://support.google.com/chrome/answer/95414">Chrome</a>, <a href="https://help.opera.com/opera-tutorials/how-do-i-update-my-opera-browser/">Opera</a> or <a href="https://support.apple.com/HT204416">Safari</a>.</p>
""",
    },
    "what-is-a-browser": {
        "ftl_files": [
            "firefox/more/what-is-a-browser.ftl",
            "firefox/more/shared.ftl",
        ],
        # what-is-a-browser-what-is-a-web
        "title": "What is a web browser?",
        # what-is-a-browser-a-web-browser
        "description": "<p>A web browser takes you anywhere on the internet, letting you see text, images and video from anywhere in the world.</p>",
        "featured": False,
        "content": """
<p>A web browser takes you anywhere on the internet, letting you see text, images and video from anywhere in the world.</p>

<p>The web is a vast and powerful tool. Over the course of a few decades, the internet has changed the way we work, the way we play and the way we interact with one another. Depending on how it's used, it bridges nations, drives commerce, nurtures relationships, drives the innovation engine of the future and is responsible for more memes than we know what to do with.</p>

<p>It's important that everyone has access to the web, but it's also vital that we all <a href="https://blog.mozilla.org/firefox/internet-search-engine-browser/">understand the tools</a> we use to access it. We use web browsers like Mozilla Firefox, Google Chrome, Microsoft Edge and Apple Safari every day, but do we understand what they are and how they work?</p>

<p>In a short period of time we've gone from being amazed by the ability to send an email to someone around the world, to a change in how we think of information. It's not a question of how much you know anymore, but simply a question of what browser or app can get you to that information fastest.</p>

<p>In a short period of time, we've gone from being amazed by the ability to send an email to someone around the world, to a change in how we think about information.</p>

<h2>How does a web browser work?</h2>

<p>A web browser takes you anywhere on the internet. It retrieves information from other parts of the web and displays it on your desktop or mobile device. The information is transferred using the Hypertext Transfer Protocol, which defines how text, images and video are transmitted on the web. This information needs to be shared and displayed in a consistent format so that people using any browser, anywhere in the world can see the information.</p>

<p>Sadly, not all browser makers choose to interpret the format in the same way. For users, this means that a website can look and function differently. Creating consistency between browsers, so that any user can enjoy the internet, regardless of the browser they choose, is called <a href="https://developer.mozilla.org/docs/Archive/Web_Standards">web standards</a>.</p>

<p>When the web browser fetches data from an internet connected server, it uses a piece of software called a rendering engine to translate that data into text and images. This data is written in <a href="https://developer.mozilla.org/docs/Glossary/HTML">Hypertext Markup Language</a> (HTML) and web browsers read this code to create what we see, hear and experience on the internet.</p>

<p><a href="https://developer.mozilla.org/docs/Glossary/Hyperlink">Hyperlinks</a> allow users to follow a path to other pages or sites on the web. Every webpage, image and video has its own unique <a href="https://wikipedia.org/wiki/URL">Uniform Resource Locator</a> (URL), which is also known as a web address. When a browser visits a server for data, the web address tells the browser where to look for each item that is described in the html, which then tells the browser where it goes on the web page.</p>

<h2>Cookies (not the yummy kind)</h2>

<p>Websites save information about you in files called <a href="https://wikipedia.org/wiki/HTTP_cookie">cookies</a>. They are saved on your computer for the next time you visit that site. Upon your return, the website code will read that file to see that it's you. For example, when you go to a website, the page remembers your username and password – that's made possible by a cookie.</p>

<p>There are also cookies that remember more detailed information about you. Perhaps your interests, your web browsing patterns, etc. This means that a site can provide you more targeted content – often in the form of ads. There are types of cookies, called <em>third-party</em> cookies, that come from sites you're not even visiting at the time and can track you from site to site to gather information about you, which is sometimes sold to other companies. Sometimes you can block these kinds of cookies, though not all browsers allow you to.</p>

<p>When you go to a website and the page remembers your username and password – that's made possible by a cookie.</p>

<h2>Understanding privacy</h2>

<p>Nearly all major browsers have a private browsing setting. These exist to hide the browsing history from other users on the same computer. Many people think that private browsing or incognito mode will hide both their identity and browsing history from internet service providers, governments and advertisers. They don't. These settings just clear the history on your system, which is helpful if you're dealing with sensitive personal information on a shared or public computer. Firefox goes beyond that.</p>

<p>Firefox helps you be more private online by letting you block trackers from following you around the web.</p>

<h2>Making your web browser work for you</h2>

<p>Most major web browsers let users modify their experience through extensions or add-ons. Extensions are bits of software that you can add to your browser to customize it or add functionality. Extensions can do all kinds of fun and practical things like enabling new features, foreign language dictionaries, or visual appearances and themes.</p>

<p>All browser makers develop their products to display images and video as quickly and smoothly as possible, making it easy for you to make the most of the web. They all work hard to make sure users have a browser that is fast, powerful and easy to use. Where they differ is why. It's important to choose the right browser for you. Mozilla builds Firefox to ensure that users have control over their online lives and to ensure that the internet is a global, public resource, accessible to all.</p>
""",
    },
    "windows-64-bit": {
        "ftl_files": [
            "firefox/more/windows-64-bit.ftl",
            "firefox/more/shared.ftl",
        ],
        # windows-64-bit-firefox-for-windows
        "title": "Firefox for Windows 64-bit",
        # windows-64-bit-users-on-64-bit-windows
        "description": "<p>Users on 64-bit Windows who download Firefox can get our 64-bit version by default. That means you get a more secure version of Firefox.</p>",
        "featured": False,
        "content": """
<p>Users on 64-bit Windows who download Firefox can get our 64-bit version by default. That means you get a more secure version of Firefox, one that also <a href="https://blog.mozilla.org/firefox/defeat-browser-crashes/">crashes a whole lot less</a>. How much less? In our tests so far, 64-bit Firefox reduced crashes by 39% on machines with 4GB of RAM or more.</p>

<h2>What's the difference between 32-bit and 64-bit?</h2>

<p>Here's the key thing to know: 64-bit applications can access more memory and are less likely to crash than 32-bit applications. Also, with the jump from 32 to 64 bits, a security feature called <a href="https://en.wikipedia.org/wiki/Address_space_layout_randomization">Address Space Layout Randomization (ASLR)</a> works better to protect you from attackers. Linux and macOS users, fret not, you already enjoy a Firefox that's optimized for 64-bit.</p>

<h2>How do you get 64-bit Firefox?</h2>

<p>If you're running 64-bit Windows (<a href="https://support.microsoft.com/help/13443/windows-which-operating-system">here's how to check</a>), your Firefox may already be 64-bit. <a href="https://support.mozilla.org/kb/update-firefox-latest-version">Check your Firefox version</a> (in the "About Firefox" window) and look for "(32-bit)" or "(64-bit)" after the version number:</p>

<ul>
<li>If you see "(32-bit)" and you are running Firefox 56.0 or older, updating to the latest Firefox version should automatically upgrade you to 64-bit.</li>
<li>If you see "(32-bit)" and are running Firefox 56.0.1 or newer, then your computer may not meet the minimum memory requirement for 64-bit (3 GB RAM or more). You can still manually install 64-bit Firefox, if you choose.</li>
</ul>

<p>If you need to run 32-bit Firefox or manually install 64-bit Firefox, you can simply download and re-run the Windows (32-bit or 64-bit) Firefox installer from the <a href="https://www.firefox.com/download/all/">Firefox platforms and languages download page.</a></p>
""",
    },
}


# =============================================================================
# Index page fixtures
# =============================================================================


def get_compare_index_page(publish: bool = False) -> ArticleIndexPage:
    """Get or create the ArticleIndexPage at /compare/."""
    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    source_locale = Locale.objects.get(language_code="en-US")

    index_page = ArticleIndexPage.objects.filter(
        slug="compare",
        locale=source_locale,
        depth=root_page.depth + 1,
    ).first()
    if index_page:
        index_page.index_card_type = ArticleIndexPage.INDEX_CARD_OUTLINE
        index_page.save(update_fields=["index_card_type"])
        return index_page

    index_page = ArticleIndexPage(
        slug="compare",
        locale=source_locale,
        # compare-index-compare-firefox-with-other
        title="Compare Firefox with other browsers",
        # compare-index-see-how-firefox-stacks-up
        sub_title="See how Firefox stacks up to other leading desktop web browsers on features, privacy, and ease-of-use.",
        # compare-shared-compare-firefox (from shared.ftl)
        other_articles_heading="Compare Firefox",
        other_articles_subheading="",
        # detail pages are children, not siblings
        show_sibling_detail_pages=False,
        index_card_type=ArticleIndexPage.INDEX_CARD_OUTLINE,
    )
    root_page.add_child(instance=index_page)

    if publish:
        index_page.save_revision().publish()
    else:
        index_page.live = False
        index_page.has_unpublished_changes = True
        index_page.save_revision()
        index_page.save()
    return index_page


def get_more_index_page(publish: bool = False) -> ArticleIndexPage:
    """Get or create the ArticleIndexPage at /more/."""
    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    source_locale = Locale.objects.get(language_code="en-US")

    index_page = ArticleIndexPage.objects.filter(
        slug="more",
        locale=source_locale,
        depth=root_page.depth + 1,
    ).first()
    if index_page:
        index_page.index_card_type = ArticleIndexPage.INDEX_CARD_ILLUSTRATION
        index_page.save(update_fields=["index_card_type"])
        return index_page

    index_page = ArticleIndexPage(
        slug="more",
        locale=source_locale,
        # firefox-products-are (from more.ftl)
        title="Firefox products are designed to protect your privacy",
        # learn-more-about (from more.ftl)
        sub_title="Learn more about Firefox browsers and products that handle your data with respect and are built for privacy anywhere you go online.",
        # learn-more-about-firefox (from more.ftl, after -brand-name-firefox expansion)
        other_articles_heading="Learn more about Firefox, its history, features and mission",
        other_articles_subheading="",
        # detail pages are children, not siblings
        show_sibling_detail_pages=False,
        index_card_type=ArticleIndexPage.INDEX_CARD_ILLUSTRATION,
    )
    root_page.add_child(instance=index_page)

    if publish:
        index_page.save_revision().publish()
    else:
        index_page.live = False
        index_page.has_unpublished_changes = True
        index_page.save_revision()
        index_page.save()
    return index_page


# =============================================================================
# Detail page fixtures
# =============================================================================


def get_compare_page(slug: str, index_page: ArticleIndexPage, publish: bool = False) -> ArticleDetailPage:
    """Get or create an ArticleDetailPage for a compare page, as a child of index_page."""
    if slug not in COMPARE_PAGES:
        raise ValueError(f"Unknown compare page slug: {slug}")

    page_data = COMPARE_PAGES[slug]

    page = ArticleDetailPage.objects.child_of(index_page).filter(slug=slug).first()
    if not page:
        page = ArticleDetailPage(slug=slug, title=page_data["title"])
        index_page.add_child(instance=page)

    page.title = page_data["title"]
    page.description = ""
    page.featured = page_data.get("featured", False)
    page.link_text = "Learn more"

    existing_uuids = [block.get("id") for block in page.content.raw_data] if page.content else []
    new_blocks = [{"type": "text", "value": page_data["content"].strip()}]
    for i, block in enumerate(new_blocks):
        if i < len(existing_uuids) and existing_uuids[i]:
            block["id"] = existing_uuids[i]
    page.content = new_blocks

    if publish:
        page.save_revision().publish()
    else:
        page.live = False
        page.has_unpublished_changes = True
        page.save_revision()
        page.save()
    return page


def get_more_page(slug: str, index_page: ArticleIndexPage, publish: bool = False) -> ArticleDetailPage:
    """Get or create an ArticleDetailPage for a more page, as a child of index_page."""
    if slug not in MORE_PAGES:
        raise ValueError(f"Unknown more page slug: {slug}")

    page_data = MORE_PAGES[slug]

    page = ArticleDetailPage.objects.child_of(index_page).filter(slug=slug).first()
    if not page:
        page = ArticleDetailPage(slug=slug, title=page_data["title"])
        index_page.add_child(instance=page)

    page.title = page_data["title"]
    page.description = page_data["description"]
    page.featured = page_data.get("featured", False)
    page.link_text = "Learn more"

    if slug in MORE_IMAGES:
        page.image = get_or_import_more_image(slug)
    if slug in MORE_PAGE_IMAGES:
        page.featured_image = get_or_import_more_page_image(slug)

    existing_uuids = [block.get("id") for block in page.content.raw_data] if page.content else []
    new_blocks = [{"type": "text", "value": page_data["content"].strip()}]
    for i, block in enumerate(new_blocks):
        if i < len(existing_uuids) and existing_uuids[i]:
            block["id"] = existing_uuids[i]
    page.content = new_blocks

    if publish:
        page.save_revision().publish()
    else:
        page.live = False
        page.has_unpublished_changes = True
        page.save_revision()
        page.save()
    return page


# =============================================================================
# Main entry point
# =============================================================================


def load_compare_more_page_fixtures(publish: bool = False):
    """
    Load all compare and more page fixtures.

    Returns:
        Tuple of (compare_index, more_index, compare_pages, more_pages)
    """
    compare_index = get_compare_index_page(publish=publish)
    compare_pages = [get_compare_page(slug, compare_index, publish=publish) for slug in COMPARE_PAGES]

    more_index = get_more_index_page(publish=publish)
    more_pages = [get_more_page(slug, more_index, publish=publish) for slug in MORE_PAGES]

    return compare_index, more_index, compare_pages, more_pages
