# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""User Routing framework.

A generic, consumer-agnostic routing layer for Wagtail reading surfaces. Authors
declare typed rules in the admin; the rules are evaluated on the client and resolve
a triggered request to a target page.

This package owns *how* routing is evaluated and presented. It carries no knowledge
of any specific consumer, update-delivery mechanism, or campaign.
"""
