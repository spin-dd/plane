# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# spin-dd fork addition (2026-08-11): this file does not exist upstream.

"""GUEST の可視範囲を「作成者 or 担当者」へ広げた変更の契約テスト。

建設業では元請が是正指示を起票し、協力会社の担当者に割り当てる。upstream の CE は
`guest_view_all_features=False` のとき `created_by` だけで絞るため、割り当てられた
本人に見えなかった（Issue #12）。

このテストは 2 方向を同時に守る。

1. **広がったこと**: 担当に割り当てられた課題は GUEST に見える
2. **広がりすぎていないこと**: 作成者でも担当者でもない課題は依然として見えない
   （GHSA-32c7-84jc-4w67 / WEB-8074 の回帰。upstream の
   `test_issue_list_guest_scope_app.py` と対になる）
"""

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import Issue, IssueAssignee, Project, ProjectMember, User, WorkspaceMember

LIST_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/list/"
DETAIL_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"


@pytest.fixture
def project(db, workspace, create_user):
    """guest_view_all_features は既定の False。"""
    project = Project.objects.create(
        name="Construction Site", identifier="CS", workspace=workspace, created_by=create_user
    )
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


@pytest.fixture
def subcontractor(db, workspace, project):
    """協力会社の担当者に見立てた GUEST（role=5）。"""
    unique_id = uuid4().hex[:8]
    user = User.objects.create(
        email=f"sub-{unique_id}@example.com",
        username=f"sub_{unique_id}",
        first_name="Sub",
        last_name="Contractor",
    )
    user.set_password("test-password")
    user.save()
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=5)
    ProjectMember.objects.create(project=project, member=user, workspace=workspace, role=5)
    return user


@pytest.fixture
def guest_client(subcontractor):
    client = APIClient()
    client.force_authenticate(user=subcontractor)
    return client


def _make_issue(name, project, workspace, author):
    # BaseModel.save は crum から created_by を決めるため、明示的に渡す。
    issue = Issue(name=name, project=project, workspace=workspace)
    issue.save(created_by_id=author.id)
    return issue


@pytest.fixture
def assigned_issue(db, workspace, project, create_user, subcontractor):
    """元請（create_user）が起票し、協力会社（subcontractor）に割り当てた是正指示。"""
    issue = _make_issue("鉄骨建方精度の是正", project, workspace, create_user)
    IssueAssignee.objects.create(
        issue=issue, assignee=subcontractor, project=project, workspace=workspace
    )
    return issue


@pytest.fixture
def other_company_issue(db, workspace, project, create_user):
    """他社に向けた是正指示。作成者でも担当者でもない。"""
    return _make_issue("他社向けの是正指示", project, workspace, create_user)


@pytest.mark.contract
class TestIssueGuestAssigneeScope:
    @pytest.mark.django_db
    def test_guest_can_read_issue_assigned_to_them(
        self, guest_client, workspace, project, assigned_issue
    ):
        """広がったこと: 割り当てられた課題は見える。"""
        url = LIST_URL.format(slug=workspace.slug, project_id=project.id)
        response = guest_client.get(url, {"issues": str(assigned_issue.id)})

        assert response.status_code == status.HTTP_200_OK, (
            f"Got {response.status_code}: {getattr(response, 'data', None)!r}"
        )
        returned_ids = {str(row["id"]) for row in response.data}
        assert str(assigned_issue.id) in returned_ids, (
            f"担当者に割り当てられた課題が見えていない: {response.data!r}"
        )

    @pytest.mark.django_db
    def test_guest_still_cannot_read_unrelated_issue(
        self, guest_client, workspace, project, assigned_issue, other_company_issue
    ):
        """広がりすぎていないこと: 無関係な課題は依然として見えない（CVE の回帰）。"""
        url = LIST_URL.format(slug=workspace.slug, project_id=project.id)
        response = guest_client.get(
            url, {"issues": f"{assigned_issue.id},{other_company_issue.id}"}
        )

        assert response.status_code == status.HTTP_200_OK
        returned_ids = {str(row["id"]) for row in response.data}
        assert str(assigned_issue.id) in returned_ids
        assert str(other_company_issue.id) not in returned_ids, (
            f"無関係な課題まで見えている: {response.data!r}"
        )

    @pytest.mark.django_db
    def test_guest_can_retrieve_assigned_issue_detail(
        self, guest_client, workspace, project, assigned_issue
    ):
        """詳細取得でも担当分は 200 で返る。"""
        url = DETAIL_URL.format(
            slug=workspace.slug, project_id=project.id, issue_id=assigned_issue.id
        )
        response = guest_client.get(url)
        assert response.status_code == status.HTTP_200_OK, (
            f"Got {response.status_code}: {getattr(response, 'data', None)!r}"
        )

    @pytest.mark.django_db
    def test_guest_cannot_retrieve_unrelated_issue_detail(
        self, guest_client, workspace, project, other_company_issue
    ):
        """詳細取得では無関係な課題を 403 で弾く。"""
        url = DETAIL_URL.format(
            slug=workspace.slug, project_id=project.id, issue_id=other_company_issue.id
        )
        response = guest_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN, (
            f"Got {response.status_code}: {getattr(response, 'data', None)!r}"
        )

    @pytest.mark.django_db
    def test_list_returns_no_duplicates_for_assignee(
        self, guest_client, workspace, project, assigned_issue
    ):
        """M2M の join で行が重複しないこと（サブクエリで表現している理由）。"""
        url = LIST_URL.format(slug=workspace.slug, project_id=project.id)
        response = guest_client.get(url, {"issues": str(assigned_issue.id)})

        assert response.status_code == status.HTTP_200_OK
        ids = [str(row["id"]) for row in response.data]
        assert len(ids) == len(set(ids)), f"重複行が返っている: {ids}"
