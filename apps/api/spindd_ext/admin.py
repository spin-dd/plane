# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# spin-dd fork addition (2026-08-10): this file does not exist upstream.

from django.contrib import admin

from spindd_ext.models import ConstructionProject


@admin.register(ConstructionProject)
class ConstructionProjectAdmin(admin.ModelAdmin):
    list_display = (
        "contract_number",
        "project",
        "client_name",
        "contract_amount",
        "construction_start",
        "construction_end",
    )
    search_fields = ("contract_number", "official_name", "client_name", "site_address")
    list_filter = ("contract_type",)
    raw_id_fields = ("project",)
    date_hierarchy = "construction_end"
