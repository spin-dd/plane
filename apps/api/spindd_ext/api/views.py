# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# spin-dd fork addition (2026-08-10): this file does not exist upstream.

"""工事情報の API。

Plane 側の BaseViewSet / 権限クラスを再利用している。認証やページネーションを
自前で書き直すと upstream の変更に追従できなくなるため、既存の基底クラスに乗る。
"""

from rest_framework.response import Response

from plane.app.permissions import WorkspaceEntityPermission
from plane.app.views.base import BaseViewSet
from plane.db.models import Project, ProjectMember
from spindd_ext.api.serializers import ConstructionProjectSerializer
from spindd_ext.models import ConstructionProject


class ConstructionProjectViewSet(BaseViewSet):
    """ワークスペース配下の工事情報。

    可視範囲は「そのユーザーが参加している現場」に限る。Plane の Project 一覧と
    同じ見え方に揃えるため、ProjectMember を経由して絞り込む。
    """

    model = ConstructionProject
    serializer_class = ConstructionProjectSerializer
    permission_classes = [WorkspaceEntityPermission]

    def get_queryset(self):
        member_project_ids = ProjectMember.objects.filter(
            workspace__slug=self.kwargs["slug"],
            member=self.request.user,
            is_active=True,
        ).values_list("project_id", flat=True)

        return (
            ConstructionProject.objects.filter(
                project__workspace__slug=self.kwargs["slug"],
                project_id__in=member_project_ids,
            )
            .select_related("project")
            .order_by("contract_number")
        )

    def perform_create(self, serializer):
        # 他ワークスペースの現場に紐づけられないよう検証する。
        project = serializer.validated_data["project"]
        if project.workspace.slug != self.kwargs["slug"]:
            raise ValueError("project does not belong to this workspace")
        serializer.save()

    def ledger(self, request, slug):
        """工事台帳（一覧）。集計値を添えて返す。"""
        queryset = self.get_queryset()
        rows = ConstructionProjectSerializer(queryset, many=True).data
        total = sum(r["contract_amount"] or 0 for r in rows)
        return Response(
            {
                "count": len(rows),
                "total_contract_amount": total,
                "results": rows,
            }
        )


class UnregisteredProjectListEndpoint(BaseViewSet):
    """工事情報が未登録の現場を返す。台帳の登録漏れを見つけるために使う。"""

    model = Project
    permission_classes = [WorkspaceEntityPermission]

    def list(self, request, slug):
        member_project_ids = ProjectMember.objects.filter(
            workspace__slug=slug, member=request.user, is_active=True
        ).values_list("project_id", flat=True)

        projects = (
            Project.objects.filter(workspace__slug=slug, id__in=member_project_ids, spindd_construction__isnull=True)
            .values("id", "name", "identifier")
            .order_by("name")
        )
        return Response({"count": len(projects), "results": list(projects)})
