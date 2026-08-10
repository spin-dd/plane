# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# spin-dd fork addition (2026-08-10): this file does not exist upstream.

from django.urls import path

from spindd_ext.api.views import ConstructionProjectViewSet, UnregisteredProjectListEndpoint

urlpatterns = [
    path(
        "workspaces/<str:slug>/construction-projects/",
        ConstructionProjectViewSet.as_view({"get": "list", "post": "create"}),
        name="spindd-construction-projects",
    ),
    path(
        "workspaces/<str:slug>/construction-projects/<int:pk>/",
        ConstructionProjectViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="spindd-construction-project-detail",
    ),
    path(
        "workspaces/<str:slug>/construction-ledger/",
        ConstructionProjectViewSet.as_view({"get": "ledger"}),
        name="spindd-construction-ledger",
    ),
    path(
        "workspaces/<str:slug>/construction-projects/unregistered/",
        UnregisteredProjectListEndpoint.as_view({"get": "list"}),
        name="spindd-construction-unregistered",
    ),
]
