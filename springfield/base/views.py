# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import logging
import os.path
from datetime import datetime
from os import getenv
from time import time

from django.conf import settings
from django.core.cache import caches
from django.http import HttpResponse
from django.shortcuts import render
from django.test import Client
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from django.views.generic import TemplateView

import timeago
from product_details import product_details
from waffle.models import Switch

from lib import l10n_utils
from lib.l10n_utils import RequireSafeMixin
from springfield.base.config_manager import config
from springfield.base.geo import get_country_from_request
from springfield.base.waffle import switch
from springfield.utils import git


class GeoTemplateView(l10n_utils.L10nTemplateView):
    """Use the template appropriate to the request country

    Set the `geo_template_names` variable to a mapping of country codes to template names.

    If the requesting country isn't in the list it falls back to the `template_name`
    setting like the normal TemplateView class.
    """

    # dict of country codes to template names
    geo_template_names = {}

    def get_template_names(self):
        country_code = get_country_from_request(self.request)
        template = self.geo_template_names.get(country_code)
        if template:
            return [template]

        return super().get_template_names()


SQLITE_DB_IN_USE = settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
LOCAL_DB_UPDATE = config("LOCAL_DB_UPDATE", default="False", parser=bool)

HEALTH_FILES = [
    # Format: (file name, max seconds since last run)
    ("update_locales", 600),
]

# Only check download_database health for SQLite deployments that download from S3
if SQLITE_DB_IN_USE and not LOCAL_DB_UPDATE:
    HEALTH_FILES.insert(
        0,
        ("download_database", 600),
    )

DB_INFO_FILE = getenv("AWS_DB_JSON_DATA_FILE", f"{settings.DATA_PATH}/springfield_db_info.json")
GIT_SHA = getenv("GIT_SHA")
BUCKET_NAME = getenv("AWS_DB_S3_BUCKET", "springfield-db-dev")
REGION_NAME = os.getenv("AWS_DB_REGION", "us-west-2")
S3_BASE_URL = f"https://s3-{REGION_NAME}.amazonaws.com/{BUCKET_NAME}"


def get_l10n_repo_info():
    fluent_repo = git.GitRepo(settings.FLUENT_REPO_PATH, settings.FLUENT_REPO_URL, settings.FLUENT_REPO_BRANCH)
    data = {
        "latest_ref": fluent_repo.current_hash,
        "last_updated": fluent_repo.last_updated,
        "repo_url": fluent_repo.clean_remote_url,
    }
    try:
        data["last_updated_timestamp"] = datetime.fromtimestamp(fluent_repo.current_commit_timestamp)
    except AttributeError:
        pass
    return data


def get_db_file_url(filename):
    return "/".join([S3_BASE_URL, filename])


def get_extra_server_info():
    server_name = [getattr(settings, x) for x in ["HOSTNAME", "CLUSTER_NAME"]]
    server_name = ".".join(x for x in server_name if x)
    server_info = {
        "name": server_name,
        "git_sha": GIT_SHA,
    }
    try:
        with open(DB_INFO_FILE) as fp:
            db_info = json.load(fp)
    except (OSError, ValueError):
        pass
    else:
        last_updated_timestamp = datetime.fromtimestamp(db_info["updated"])
        db_info["last_updated_timestamp"] = last_updated_timestamp
        db_info["last_update"] = timeago.format(last_updated_timestamp)
        db_info["file_url"] = get_db_file_url(db_info["file_name"])
        for key, value in db_info.items():
            server_info[f"db_{key}"] = value

    return server_info


logger = logging.getLogger(__name__)


# The page-check result is cached in the `healthz` Django cache, which in prod
# is a Redis backend shared across all pods (see settings.CACHES). This means
# the fleet runs ~one critical-page render per TTL instead of one per pod per
# TTL, decoupling healthcheck cost from pod count. When REDIS_URL is unset
# (local dev, CI), the `healthz` cache falls back to a per-process LocMemCache.
HEALTHZ_CDN_CACHE_KEY = "healthz-cdn:page-check"
HEALTHZ_CDN_LOCK_KEY = "healthz-cdn:page-check:lock"
HEALTHZ_CDN_CACHE_TIMEOUT = 30
# Lock TTL bounds how long a stuck check can hog the single-flight slot. Slightly
# longer than the longest expected render so a healthy check always releases the
# lock explicitly; the TTL is the backstop for a crashed/killed worker.
HEALTHZ_CDN_LOCK_TIMEOUT = 15

# A small set of representative pages we expect to always serve. Anything other
# than a sub-400 status from any of them flips the healthcheck to 500 and lets
# Fastly fall back to its static page. Together these cover the download page,
# a CMS-served whatsnew page (Wagtail page-lookup path), a version-specific
# whatsnew, and a non-en-US locale — most causes of a real user-facing outage
# (schema drift, template errors, broken context processors, DB outage) show
# up in at least one of them.
HEALTHZ_CDN_CRITICAL_PATHS = (
    f"/{settings.LANGUAGE_CODE}/",
    "/en-US/whatsnew/general/",
    "/de/whatsnew/150/",
)


def _check_critical_pages():
    """Return (status_code, body) by issuing internal GETs against critical pages.

    Symptom-based rather than cause-based: if old code can still render a page
    against a newer DB (benign migration), we pass; if it can't (destructive
    schema change), we fail. This sidesteps the false-positive problem of
    cause-based reverse-skew detection — where any rollout containing any
    migration would have flipped Fastly to fallback during the brief window
    before old pods were replaced.

    The earlier per-model `get_table_description` approach was both expensive
    (~200 DB queries per check, the cause of the original overload) and unable
    to distinguish benign from destructive schema change. This is cheaper per
    check (one page render against an in-process cache) and more accurate.
    """
    if settings.WATCHMAN_DISABLE_APM:
        try:
            from watchman.views import _disable_apm  # inline: _disable_apm is a private watchman API; guard defensively against upstream rename

            _disable_apm()
        except (ImportError, AttributeError):
            logger.warning("healthz_cdn: watchman _disable_apm unavailable; continuing without disabling APM")

    # raise_request_exception=False so a 500 from the view comes back as a normal
    # response with status_code=500 rather than propagating — we want to handle
    # both the same way (page broken → fail healthcheck).
    client = Client(raise_request_exception=False)
    for path in HEALTHZ_CDN_CRITICAL_PATHS:
        try:
            response = client.get(path, follow=False)
        except Exception:
            logger.exception("healthz_cdn: critical page %s raised", path)
            return 500, "critical page failed"
        if response.status_code >= 400:
            logger.warning("healthz_cdn: critical page %s returned %s", path, response.status_code)
            return 500, "critical page failed"
    return 200, "pong"


def _safe_cache_get(cache_obj, key):
    """Wrap cache.get() so a Redis hiccup doesn't take down the healthcheck."""
    try:
        return cache_obj.get(key)
    except Exception:
        logger.exception("healthz_cdn: cache get failed")
        return None


def _safe_cache_add(cache_obj, key, value, timeout):
    """Wrap cache.add() so a Redis hiccup doesn't take down the healthcheck.

    Returns True when we claimed the slot (or couldn't tell because of an error
    and chose to proceed anyway). False only when the slot is genuinely held by
    another caller.
    """
    try:
        return bool(cache_obj.add(key, value, timeout))
    except Exception:
        logger.exception("healthz_cdn: cache add failed; running check uncoordinated")
        return True


def _safe_cache_set(cache_obj, key, value, timeout):
    try:
        cache_obj.set(key, value, timeout)
    except Exception:
        logger.exception("healthz_cdn: cache set failed")


def _safe_cache_delete(cache_obj, key):
    try:
        cache_obj.delete(key)
    except Exception:
        logger.exception("healthz_cdn: cache delete failed")


@require_safe
@never_cache
def healthz_cdn(request):
    # Feature toggle: when the switch is off, behave like the simple ping. Lets us
    # dial back the page-rendering behaviour without a deploy if it ever proves
    # too costly again. Propagation is not instantaneous — each pod caches the
    # switch state in its own LocMemCache (django-waffle default MAX_AGE is 30
    # days), so if a flip needs to take effect on every pod immediately, restart
    # the rollout. The switch helper defaults to settings.DEV when undefined, so
    # local dev sees real page renders while a fresh prod deploy is safe by default.
    if not switch("healthz-cdn-db-checks-enabled"):
        return HttpResponse("pong", content_type="text/plain")

    healthz_cache = caches["healthz"]

    cached = _safe_cache_get(healthz_cache, HEALTHZ_CDN_CACHE_KEY)
    if cached is not None:
        status, body = cached
        return HttpResponse(body, content_type="text/plain", status=status)

    # Cache miss. Single-flight via cache.add(): only the caller that claims the
    # lock runs the render. Other concurrent cache-missers return 200 pong as a
    # best-effort; the next probe after the winner populates the cache will see
    # the real result. With a Redis-backed `healthz` cache this dedupes across
    # the whole fleet, so a cold cache or simultaneous TTL expiry doesn't fan
    # out into N renders against the DB.
    if not _safe_cache_add(healthz_cache, HEALTHZ_CDN_LOCK_KEY, 1, HEALTHZ_CDN_LOCK_TIMEOUT):
        return HttpResponse("pong", content_type="text/plain")

    try:
        try:
            status, body = _check_critical_pages()
        except Exception:
            logger.exception("healthz_cdn: check failed")
            status, body = 500, "check error"
        _safe_cache_set(healthz_cache, HEALTHZ_CDN_CACHE_KEY, (status, body), HEALTHZ_CDN_CACHE_TIMEOUT)
    finally:
        _safe_cache_delete(healthz_cache, HEALTHZ_CDN_LOCK_KEY)

    return HttpResponse(body, content_type="text/plain", status=status)


@require_safe
@never_cache
def cron_health_check(request):
    results = []
    check_pass = True
    for fname, max_time in HEALTH_FILES:
        fpath = f"{settings.DATA_PATH}/last-run-{fname}"
        try:
            last_check = os.path.getmtime(fpath)
        except OSError:
            check_pass = False
            results.append((fname, max_time, "None", False))
            continue

        time_since = int(time() - last_check)
        if time_since > max_time:
            task_pass = False
            check_pass = False
        else:
            task_pass = True

        results.append((fname, max_time, time_since, task_pass))

    git_repos = git.GitRepoState.objects.exclude(repo_name="").order_by("repo_name", "-latest_ref_timestamp")
    unique_repos = {}
    for repo in git_repos:
        if repo.repo_name in unique_repos:
            continue
        unique_repos[repo.repo_name] = repo
        setattr(
            unique_repos[repo.repo_name],
            "last_updated_timestamp",
            datetime.fromtimestamp(repo.latest_ref_timestamp),
        )

    try:
        most_recent_data_change_ts = sorted([x.last_updated_timestamp for x in unique_repos.values()])[-1]
    except IndexError:
        most_recent_data_change_ts = None

    return render(
        request,
        "cron-health-check.html",
        {
            "results": results,
            "server_info": get_extra_server_info(),
            "success": check_pass,
            "git_repos": unique_repos.values(),
            "fluent_repo": get_l10n_repo_info(),
            "SQLITE_DB_IN_USE": SQLITE_DB_IN_USE,
            "most_recent_data_change_ts": most_recent_data_change_ts,
            "switches": Switch.objects.order_by("name"),
        },
        status=200 if check_pass else 500,
    )


def server_error_view(request, template_name="500.html"):
    """500 error handler that runs context processors."""
    return l10n_utils.render(request, template_name, ftl_files=["500"], status=500)


def page_not_found_view(request, exception=None, template_name="404.html"):
    """404 error handler that runs context processors."""
    return l10n_utils.render(request, template_name, ftl_files=["404", "500"], status=404)


def csrf_failure(request, reason="CSRF failure", template_name="403_csrf.html"):
    return render(request, template_name, status=403)


class Robots(RequireSafeMixin, TemplateView):
    template_name = "base/robots.txt"
    content_type = "text/plain"

    def get_context_data(self, **kwargs):
        hostname = self.request.get_host()
        _disallow_all = switch("ROBOTS_FORCE_DISALLOW_ALL") or (not hostname == "www.firefox.com")
        return {"disallow_all": _disallow_all}


class SecurityDotTxt(RequireSafeMixin, TemplateView):
    # https://github.com/mozilla/bedrock/issues/14173
    # served under .well-known/security.txt
    template_name = "base/security.txt"
    content_type = "text/plain"


class GpcDotJson(RequireSafeMixin, TemplateView):
    # https://github.com/mozilla/bedrock/issues/14213
    # served under .well-known/gpc.json
    template_name = "base/gpc.json"
    content_type = "application/json"


@require_safe
def locales(request):
    context = {"languages": product_details.languages}
    return l10n_utils.render(request, "base/locales.html", context)
