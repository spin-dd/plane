# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# spin-dd fork addition (2026-08-10): this file does not exist upstream.

from rest_framework import serializers

from plane.db.models import ProjectMember, WorkspaceMember
from plane.db.models.project import ROLE
from plane.spindd_ext.models import ConstructionProject


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
        # workspace は project から導出するため受け付けない。
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 作成後に現場を付け替えられないようにする。
        # これが無いと PATCH で project を他ワークスペースの UUID に差し替えられ、
        # 工事番号・請負金額・発注者を他テナントの現場へ移送できてしまう。
        if self.instance is not None:
            self.fields["project"].read_only = True

    def validate_project(self, value):
        """URL のワークスペース配下かつ、リクエスト者が参加している現場に限る。

        ModelSerializer が既定で付ける queryset は Project.objects.all()、
        つまりインスタンス上の全プロジェクトなので、ここで必ず絞る。
        """
        workspace_slug = self.context.get("workspace_slug")
        if not workspace_slug or value.workspace.slug != workspace_slug:
            raise serializers.ValidationError("この現場は対象のワークスペースに属していません。")

        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None:
            raise serializers.ValidationError("参加していない現場には工事情報を登録できません。")

        # 請負金額を含むため、登録できるのは現場 ADMIN かワークスペース ADMIN のみ。
        # 非公開プロジェクトの名称が 201 応答から漏れるのも同時に防ぐ。
        is_workspace_admin = WorkspaceMember.objects.filter(
            workspace=value.workspace, member=user, role=ROLE.ADMIN.value, is_active=True
        ).exists()
        is_project_admin = ProjectMember.objects.filter(
            project=value, member=user, role=ROLE.ADMIN.value, is_active=True
        ).exists()
        if not (is_workspace_admin or is_project_admin):
            raise serializers.ValidationError(
                "この現場に工事情報を登録する権限がありません。現場の管理者に依頼してください。"
            )

        return value
