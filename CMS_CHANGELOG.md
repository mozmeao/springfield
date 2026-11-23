## 2026-11-27

- The Video and Animation blocks have an "Uploaded Video" / "Uploaded Animation" field. Choose a WebM video from Documents or upload a new one, instead of asking a developer to add the file to assets.mozilla.net.
    - Fill in either this field or the URL field, not both.
    - The video must be a real WebM file of 5 MB or less. Other document types are unchanged.
    - A WebM document can only be replaced with another WebM video.
    - In the Video block, an uploaded video needs a Poster image, the same as an assets.mozilla.net video.

## 2026-11-23

- The video block's Poster image is optional for YouTube videos. Leave it empty and, when you save, the video's YouTube thumbnail is added to the "YouTube Thumbnails" image collection and filled in as the poster. If you change the video URL, the thumbnail changes with it. Choose your own image to use that instead. assets.mozilla.net videos still need a poster image.
- Drafts save with an incomplete video block. The poster is checked when you publish.
- The Code block has a Language field. Pick a programming language to colour the code and show its name above it; leave it on Plain text for no colours. Every Code block has a Copy button and an optional Caption.
- Set Language to Prompt or Model output to show an AI prompt or reply. These wrap long lines, and their text is sent for translation; code isn't.

## 2026-11-19

- Every field that sets where a QR code points is now called "QR Code URL", with the same help text: the QR Code block, Mobile Store Button / QR Code, Home Kit Banner, QR Code Modal Button, the Banner, QR Code and Floating QR Code snippets, and the page-level "Override QR Code URL". If you leave off `https://` it is added when you save, `http://` is changed to `https://`, and `tel:`, `mailto:` and `sms:` links are kept as they are. Anything else, like plain text, shows an error.

## 2026-11-17

- UI Tour buttons have an "Open Preferences - About (Firefox Updates)" action, which opens `about:preferences#about`.

## 2026-11-09

- Generated QR codes now use rounded dots and corners with the Firefox logo in the middle, matching the designed QR images.
- Fixed the QR Code block, which encoded the wrong value instead of its QR Code Data.

## 2026-11-05
- When a page's English text is edited after it has been translated, the translation editor's "Previous translations" panel shows the previous translation for that text, so it can be read and reused instead of retyped.

## 2026-11-04
- Wagtail upgraded from 7.4 to 8.1. The page editor's Checks panel now shows the page's meta title and description, with their lengths measured against search engine limits. Moving or renaming a draft page no longer creates a redirect; live pages still do.

## 2026-11-02
- Comparison Result label now uses Fluent-translated Yes/No/Limited text

## 2026-10-29

- Share Firefox pages have "Show Navigation CTA" and "Show Pre-Footer" checkboxes on the Settings tab. Both are off by default.
- The Sharing Links block has a "Show URL" checkbox in its settings. It's on by default, so existing blocks keep showing the URL above the buttons; turn it off to show only the buttons.

## 2026-10-26

- The Sharing Links block can be added to a Banner's content.

## 2026-10-21

- Blog articles have an "Exclude from RSS" checkbox on the Settings tab. It keeps the article out of the blog's RSS feeds; the article still shows on the blog. Translations follow after Sync translated pages and publish.
- Blog article slugs can't be `all`, `topics` or `feed`, which are reserved for blog pages.

## 2026-10-20

- Blog index: when it has no featured articles and no article sections, the page lists every article in its language instead, 10 per page. Used for the German and French blog homes.
- Added the Sharing Links block: copy link, email and QR code buttons for one URL. It is available in Section, Featured Image Section, Media + Content and Two-Column Card blocks.
- Added Partner downloads (Snippets → Partner downloads): set up a partner's Firefox builds for firefox.com/get/?p=<link name>, with a Test links panel to check each download before publishing.
- Added Buttons below to the Kit Intro: an optional second row of buttons under the first row and its privacy notice.
- Added the Video Modal Button, which opens a YouTube video in a modal and starts playing it. It's offered wherever UI Tour buttons are, and in the HomePage intro.

## 2026-10-07

- Added this changelog, available from the Flare Docs page.
