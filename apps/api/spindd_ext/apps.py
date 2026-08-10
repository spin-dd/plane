# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# spin-dd fork addition (2026-08-10): this file does not exist upstream.

from django.apps import AppConfig


class SpinddExtConfig(AppConfig):
    """建設業向けの独自機能をまとめた Django アプリ。

    plane.db には一切マイグレーションを追加しないための隔離先である
    （CONTRIBUTING.spindd.md §4）。plane 側のモデルへは FK で繋ぐだけにする。
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "spindd_ext"
    verbose_name = "spindd 拡張"
