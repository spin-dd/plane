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
from plane.spindd_ext.api.serializers import ConstructionProjectSerializer
from plane.spindd_ext.models import ConstructionProject

# 台帳は 1 レスポンスで返す前提の画面だが、無制限だと現場数に比例して
# レスポンスが膨らむ。既定で上限を設け、超えた分は truncated で明示する。
LEDGER_DEFAULT_LIMIT = 200
LEDGER_MAX_LIMIT = 1000


class ConstructionProjectViewSet(BaseViewSet):
    """ワークスペース配下の工事情報。

    可視範囲は「そのユーザーが参加している現場」に限る。Plane の Project 一覧と
    同じ見え方に揃えるため、ProjectMember を経由して絞り込む。
    """

    model = ConstructionProject
    serializer_class = ConstructionProjectSerializer
    permission_classes = [WorkspaceEntityPermission]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # シリアライザ側で「URL のワークスペース配下か」を検証するために渡す。
        context["workspace_slug"] = self.kwargs.get("slug")
        return context

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

    def _limit(self):
        try:
            limit = int(self.request.query_params.get("limit", LEDGER_DEFAULT_LIMIT))
        except (TypeError, ValueError):
            limit = LEDGER_DEFAULT_LIMIT
        return max(1, min(limit, LEDGER_MAX_LIMIT))

    def list(self, request, slug):
        queryset = self.get_queryset()
        total = queryset.count()
        limit = self._limit()
        rows = ConstructionProjectSerializer(queryset[:limit], many=True).data
        return Response({"count": total, "truncated": total > limit, "results": rows})

    def ledger(self, request, slug):
        """工事台帳（一覧）。集計値を添えて返す。

        合計はページングの影響を受けないよう DB 側で集計する。
        """
        from django.db.models import Sum

        queryset = self.get_queryset()
        total = queryset.count()
        total_amount = queryset.aggregate(total=Sum("contract_amount"))["total"] or 0
        limit = self._limit()
        rows = ConstructionProjectSerializer(queryset[:limit], many=True).data
        return Response(
            {
                "count": total,
                "truncated": total > limit,
                "total_contract_amount": total_amount,
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

        # soft delete された工事情報は「未登録」として扱う（default manager が除外する）。
        registered_project_ids = ConstructionProject.objects.filter(
            project__workspace__slug=slug
        ).values_list("project_id", flat=True)

        projects = (
            Project.objects.filter(workspace__slug=slug, id__in=member_project_ids)
            .exclude(id__in=registered_project_ids)
            .values("id", "name", "identifier")
            .order_by("name")
        )
        return Response({"count": len(projects), "results": list(projects)})
