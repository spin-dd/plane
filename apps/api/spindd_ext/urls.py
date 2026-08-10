# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# spin-dd fork addition (2026-08-10): this file does not exist upstream.

"""fork の ROOT_URLCONF。

plane/urls.py を改変せずに URL を追加するための入れ物である。
plane 側の urlpatterns をそのまま取り込み、後ろに独自のものを足す。

有効化は plane/settings/spindd.py の ROOT_URLCONF = "spindd_ext.urls" で行う。
plane/urls.py の handler404 もそのまま引き継ぐ。
"""

from django.urls import include, path

from plane.urls import handler404 as handler404  # noqa: F401  (Django が名前で参照する)
from plane.urls import urlpatterns as plane_urlpatterns

urlpatterns = [
    *plane_urlpatterns,
    path("api/spindd/", include("spindd_ext.api.urls")),
]
