# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# spin-dd fork addition (2026-08-11): this file does not exist upstream.

"""工事台帳の書き込み権限の契約テスト。

工事情報には**請負金額**が含まれる。upstream の `WorkspaceEntityPermission` は
書き込みを「ワークスペースの ADMIN または MEMBER」まで許すため、これでは緩い。

`ConstructionProjectPermission` は書き込みを
「ワークスペース ADMIN」または「対象現場の ADMIN（= 現場代理人）」に絞る。
このテストはその境界を固定する。
"""

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import Project, ProjectMember, User, WorkspaceMember
from plane.spindd_ext.models import ConstructionProject

LIST_URL = "/api/spindd/workspaces/{slug}/construction-projects/"
DETAIL_URL = "/api/spindd/workspaces/{slug}/construction-projects/{pk}/"
LEDGER_URL = "/api/spindd/workspaces/{slug}/construction-ledger/"


def _user(prefix):
    unique_id = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{prefix}-{unique_id}@example.com", username=f"{prefix}_{unique_id}"
    )
    user.set_password("test-password")
    user.save()
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def site(db, workspace, create_user):
    """現場。create_user は現場 ADMIN。"""
    project = Project.objects.create(
        name="Site A", identifier="SA", workspace=workspace, created_by=create_user
    )
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


@pytest.fixture
def plain_member(db, workspace, site):
    """ワークスペース MEMBER かつ現場 MEMBER（ADMIN ではない）。"""
    user = _user("member")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    ProjectMember.objects.create(project=site, member=user, workspace=workspace, role=15)
    return user


@pytest.fixture
def site_admin(db, workspace, site):
    """現場 ADMIN だが、ワークスペースでは MEMBER。"""
    user = _user("agent")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    ProjectMember.objects.create(project=site, member=user, workspace=workspace, role=20)
    return user


@pytest.fixture
def existing(db, site, workspace):
    return ConstructionProject.objects.create(
        project=site, contract_number="26-A-0001", client_name="発注者A", contract_amount=1000
    )


@pytest.mark.contract
class TestConstructionLedgerPermissions:
    @pytest.mark.django_db
    def test_plain_member_can_read(self, plain_member, workspace, site, existing):
        """読み取りはワークスペースメンバーなら通る。"""
        response = _client(plain_member).get(LEDGER_URL.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    @pytest.mark.django_db
    def test_plain_member_cannot_create(self, plain_member, workspace, site):
        """現場 ADMIN でない一般メンバーは登録できない。"""
        other = Project.objects.create(name="Site B", identifier="SB", workspace=workspace)
        ProjectMember.objects.create(
            project=other, member=plain_member, workspace=workspace, role=15
        )
        response = _client(plain_member).post(
            LIST_URL.format(slug=workspace.slug),
            {"project": str(other.id), "contract_number": "26-B-0001"},
            format="json",
        )
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_400_BAD_REQUEST,
        ), f"Got {response.status_code}: {getattr(response, 'data', None)!r}"

    @pytest.mark.django_db
    def test_plain_member_cannot_update(self, plain_member, workspace, existing):
        """一般メンバーは請負金額を書き換えられない。"""
        response = _client(plain_member).patch(
            DETAIL_URL.format(slug=workspace.slug, pk=existing.pk),
            {"contract_amount": 999_999_999},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, (
            f"Got {response.status_code}: {getattr(response, 'data', None)!r}"
        )
        existing.refresh_from_db()
        assert existing.contract_amount == 1000, "一般メンバーの更新が通ってしまった"

    @pytest.mark.django_db
    def test_site_admin_can_create_and_update(self, site_admin, workspace, site):
        """現場 ADMIN は登録・更新できる。"""
        client = _client(site_admin)

        created = client.post(
            LIST_URL.format(slug=workspace.slug),
            {"project": str(site.id), "contract_number": "26-A-0100", "contract_amount": 500},
            format="json",
        )
        assert created.status_code == status.HTTP_201_CREATED, (
            f"Got {created.status_code}: {getattr(created, 'data', None)!r}"
        )

        updated = client.patch(
            DETAIL_URL.format(slug=workspace.slug, pk=created.data["id"]),
            {"contract_amount": 750},
            format="json",
        )
        assert updated.status_code == status.HTTP_200_OK
        assert updated.data["contract_amount"] == 750

    @pytest.mark.django_db
    def test_project_cannot_be_reassigned_on_update(self, site_admin, workspace, site, existing):
        """作成後に現場を付け替えられない（#11 のレビュー指摘の回帰）。"""
        other = Project.objects.create(name="Site C", identifier="SC", workspace=workspace)
        ProjectMember.objects.create(project=other, member=site_admin, workspace=workspace, role=20)

        response = _client(site_admin).patch(
            DETAIL_URL.format(slug=workspace.slug, pk=existing.pk),
            {"project": str(other.id)},
            format="json",
        )
        # read_only なので無視される（200 だが project は変わらない）
        assert response.status_code == status.HTTP_200_OK
        existing.refresh_from_db()
        assert existing.project_id == site.id, "現場が付け替えられてしまった"

    @pytest.mark.django_db
    def test_ledger_reports_editable_projects(self, site_admin, plain_member, workspace, existing):
        """editable_project_ids が UI の出し分けに使える形で返る。"""
        admin_response = _client(site_admin).get(LEDGER_URL.format(slug=workspace.slug))
        assert admin_response.status_code == status.HTTP_200_OK
        assert str(existing.project_id) in admin_response.data["editable_project_ids"]

        member_response = _client(plain_member).get(LEDGER_URL.format(slug=workspace.slug))
        assert member_response.status_code == status.HTTP_200_OK
        assert member_response.data["editable_project_ids"] == []
