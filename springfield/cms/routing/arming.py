# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The consumer trigger, framed as an arming condition.

A consumer's trigger is *the condition under which routing fires for its surface*.
Framing it as an abstraction — rather than hardcoding "a query param" — keeps a future
non-param trigger (referrer, cookie, path, always-on) a new realization of the same
interface, not a framework change (deferred). v1 ships exactly one
realization: query-param presence.
"""

from springfield.cms.routing.params import TRIGGER_PARAM


class ArmingCondition:
    """Abstract arming condition: does this request arm routing for the surface?

    Callers (the dispatcher) depend only on ``is_satisfied(request)``; the concrete
    realization is swappable without touching them.
    """

    def is_satisfied(self, request) -> bool:
        raise NotImplementedError


class QueryParamArmingCondition(ArmingCondition):
    """v1 realization: armed iff a query param is present on the request.

    Presence-based: any value — including an empty one — counts, so
    ``?routing`` and ``?routing=1`` both arm routing.
    """

    def __init__(self, param_name: str = TRIGGER_PARAM):
        self.param_name = param_name

    def is_satisfied(self, request) -> bool:
        return self.param_name in request.GET


class QueryParamValueArmingCondition(ArmingCondition):
    """Armed iff a query param is present *and* its value is one of ``values``.

    Value-matching, not presence-based: when a surface arms on a shared query param
    (e.g. one ``utm_source`` value among many), it must fire only for that value and
    stay dark for every other value of the same param (an empty value counts as a
    mismatch). Single-purpose alongside the presence-only condition — each arming
    strategy stays its own class.
    """

    def __init__(self, param_name: str, values):
        self.param_name = param_name
        self.values = frozenset(values)

    def is_satisfied(self, request) -> bool:
        return request.GET.get(self.param_name) in self.values
