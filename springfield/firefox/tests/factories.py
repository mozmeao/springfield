# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import factory
import wagtail_factories

from springfield.firefox.blocks import features
from springfield.firefox.models import FeaturesCallToActionSnippet, FeaturesDetailPage, FeaturesIndexPage


class FeaturesVideoBlockFactory(wagtail_factories.StructBlockFactory):
    image = factory.SubFactory(wagtail_factories.ImageChooserBlockFactory)
    title = wagtail_factories.CharBlockFactory
    youtube_video_id = wagtail_factories.CharBlockFactory

    class Meta:
        model = features.FeaturesVideoBlock


class FeaturesCallToActionSnippetFactory(factory.BaseDictFactory):
    heading = wagtail_factories.CharBlockFactory
    image = factory.SubFactory(wagtail_factories.ImageChooserBlockFactory)

    class Meta:
        model = FeaturesCallToActionSnippet


class FeaturesIndexPageFactory(wagtail_factories.PageFactory):
    title = "Test Index Page Title"
    live = True
    slug = "test"

    sub_title = wagtail_factories.CharBlockFactory

    class Meta:
        model = FeaturesIndexPage


class FeaturesDetailPageFactory(wagtail_factories.PageFactory):
    title = "Test Detail Page Title"
    live = True

    image = factory.SubFactory(wagtail_factories.ImageChooserBlockFactory)
    desc = wagtail_factories.CharBlockFactory
    content = wagtail_factories.CharBlockFactory
    article_media = wagtail_factories.StreamFieldFactory({"video": factory.SubFactory(FeaturesVideoBlockFactory)})
    featured_article = factory.LazyFunction(lambda: False)

    class Meta:
        model = FeaturesDetailPage
