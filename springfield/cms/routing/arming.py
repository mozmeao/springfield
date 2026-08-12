# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The consumer trigger — the condition under which routing fires for a surface.

An abstraction rather than a hardcoded query param, so a future referrer, cookie or
path trigger is a new subclass rather than a change to the serve path.
"""

from springfield.cms.routing.params import TRIGGER_PARAM


class ArmingCondition:
    """Abstract arming condition. Callers depend only on ``is_satisfied(request)``."""

    def is_satisfied(self, request) -> bool:
        raise NotImplementedError


class QueryParamArmingCondition(ArmingCondition):
    """Armed iff a query param is present, whatever its value.

    ``?routing`` and ``?routing=1`` both arm; an empty value still counts.
    """

    def __init__(self, param_name: str = TRIGGER_PARAM):
        self.param_name = param_name

    def is_satisfied(self, request) -> bool:
        return self.param_name in request.GET


class QueryParamValueArmingCondition(ArmingCondition):
    """Armed iff a query param holds one of ``values``.

    For a surface arming on a shared param — one ``utm_source`` value among many — which
    must stay dark for every other value of it. An empty value is a mismatch.
    """

    def __init__(self, param_name: str, values):
        self.param_name = param_name
        self.values = frozenset(values)

    def is_satisfied(self, request) -> bool:
        return request.GET.get(self.param_name) in self.values
