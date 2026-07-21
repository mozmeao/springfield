# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class FirefoxReferralDataManager(models.Manager):
    def refresh(self, new_data):
        raise NotImplementedError


class FirefoxReferralData(models.Model):
    referral_id = models.CharField(max_length=10, unique=True)
    install_count = models.PositiveIntegerField(default=0)
    last_refreshed_at = models.DateTimeField(auto_now=True)

    objects = FirefoxReferralDataManager()

    class Meta:
        app_label = "firefox"

    def __str__(self):
        return f"{self.referral_id}: {self.install_count} installs"
