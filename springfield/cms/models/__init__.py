# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .locale import *  # noqa
from .snippets import *  # noqa
from .pages import *  # noqa
from .images import *  # noqa

# Framework-owned routing schema (spec §5). Imported here so Django registers the
# models under the `cms` app and their schema ships in the app's migrations.
from springfield.cms.routing.models import (  # noqa: E402, F401
    RoutingCondition,
    RoutingConfig,
    RoutingRule,
)
