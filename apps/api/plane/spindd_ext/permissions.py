# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# spin-dd fork addition (2026-08-11): this file does not exist upstream.

"""工事情報の権限。

upstream の `WorkspaceEntityPermission` は書き込みを「ワークスペースの ADMIN または
MEMBER」まで許す。工事情報には**請負金額**が含まれるため、これでは緩い。

読み取りと書き込みを分け、書き込みは「ワークスペース ADMIN」または
「対象現場の ADMIN（= 現場代理人）」に限る。
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from plane.db.models import ProjectMember, WorkspaceMember
from plane.db.models.project import ROLE


class ConstructionProjectPermission(BasePermission):
    """読み取りはワークスペースメンバー、書き込みは現場 ADMIN かワークスペース ADMIN。

    可視範囲そのものは ViewSet の `get_queryset` が `ProjectMember` 経由で
    「参加している現場」に絞っている。ここは操作の可否だけを見る。
    """

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False

        slug = view.workspace_slug
        if not slug:
            return False

        if request.method in SAFE_METHODS:
            return WorkspaceMember.objects.filter(
                workspace__slug=slug, member=request.user, is_active=True
            ).exists()

        # ワークスペース ADMIN は全現場の工事情報を扱える
        if WorkspaceMember.objects.filter(
            workspace__slug=slug,
            member=request.user,
            role=ROLE.ADMIN.value,
            is_active=True,
        ).exists():
            return True

        # そうでなければ、どこか 1 つの現場で ADMIN であることを要求する。
        # どの現場かはオブジェクト単位（has_object_permission）と
        # シリアライザの validate_project で絞る。
        return ProjectMember.objects.filter(
            workspace__slug=slug,
            member=request.user,
            role=ROLE.ADMIN.value,
            is_active=True,
        ).exists()

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        slug = view.workspace_slug
        if WorkspaceMember.objects.filter(
            workspace__slug=slug,
            member=request.user,
            role=ROLE.ADMIN.value,
            is_active=True,
        ).exists():
            return True

        # その工事情報が紐づく現場の ADMIN でなければ書き換えさせない。
        return ProjectMember.objects.filter(
            project_id=obj.project_id,
            member=request.user,
            role=ROLE.ADMIN.value,
            is_active=True,
        ).exists()
