# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# spin-dd fork addition (2026-08-11): this file does not exist upstream.

"""fork のテスト設定。

`plane/settings/test.py`（upstream）は `INSTALLED_APPS` に `plane.spindd_ext` を
含まないため、そのままでは独自モデルが
`RuntimeError: Model class ... doesn't declare an explicit app_label` で読めない。

upstream の `test.py` と `pytest.ini` を改変せずに済ませるため、ここで足す。
アプリの追加は加算的なので、upstream のテストにも影響しない。

実行:
    docker compose -f docker-compose-test.yml run --rm api-tests \
        pytest --ds=plane.settings.spindd_test -q
"""

from .test import *  # noqa

INSTALLED_APPS = (*INSTALLED_APPS, "plane.spindd_ext")  # noqa: F405
# /api/spindd/ を生やすため。plane/urls.py の urlpatterns を取り込んで後ろに足す。
ROOT_URLCONF = "plane.spindd_ext.urls"
