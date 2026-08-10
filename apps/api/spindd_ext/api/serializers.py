# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# spin-dd fork addition (2026-08-10): this file does not exist upstream.

from rest_framework import serializers

from spindd_ext.models import ConstructionProject


class ConstructionProjectSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    project_identifier = serializers.CharField(source="project.identifier", read_only=True)
    contract_type_label = serializers.CharField(source="get_contract_type_display", read_only=True)

    class Meta:
        model = ConstructionProject
        fields = [
            "id",
            "project",
            "project_name",
            "project_identifier",
            "contract_number",
            "official_name",
            "client_name",
            "site_address",
            "building_use",
            "structure",
            "total_floor_area",
            "contract_type",
            "contract_type_label",
            "contract_amount",
            "contract_date",
            "construction_start",
            "construction_end",
            "actual_completion",
            "site_agent",
            "chief_engineer",
            "remarks",
            "is_completed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
