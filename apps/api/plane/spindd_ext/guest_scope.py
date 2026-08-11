# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# spin-dd fork addition (2026-08-11): this file does not exist upstream.

"""GUEST に見せる課題の範囲。

## なぜ必要か

upstream の CE は、GUEST の可視範囲を `Project.guest_view_all_features` の真偽で
二択にしている。

- `False` → **自分が作成した**課題のみ（`created_by`）
- `True`  → プロジェクト内の全課題

建設業では元請が是正指示を起票し、協力会社の担当者に割り当てる。上の二択だと
「割り当てられた本人に見えない」か「他社の指示まで全部見える」かのどちらかに
なってしまい、協力会社にアカウントを配れない。

そこで **`False` 側の意味を「自分が作成した」から「自分が作成した、または
自分が担当している」へ広げる**。これは Plane の Commercial Edition が
Project Guest を "view-only access to assigned work items" と定義しているのと
同じ意味であり、独自解釈ではない（#12 の調査）。

## セキュリティ上の注意

ここは GHSA-32c7-84jc-4w67 (WEB-8074) の修正が入っている箇所である。
`IssueListEndpoint` が `?issues=` で渡された id を無条件に返してしまい、
GUEST が他人の課題を読めた脆弱性だった。

**この関数は「作成者 or 担当者」までしか広げない。** 追従時にここを触るときは、
`apps/api/plane/tests/contract/app/test_issue_list_guest_scope_app.py` と
`test_issue_guest_assignee_scope_spindd.py` の両方が通ることを必ず確認する。
"""

from django.db.models import Q

from plane.db.models import IssueAssignee


def guest_visible_issue_filter(user) -> Q:
    """GUEST に見せる課題を絞る Q。

    `Q(assignees=user)` と書くと M2M の join で行が重複し、呼び出し側に
    `.distinct()` を強いる。既存のクエリセットに影響を出さないよう、
    中間テーブルのサブクエリで表現している。
    """
    return Q(created_by=user) | Q(
        pk__in=IssueAssignee.objects.filter(assignee=user).values("issue_id")
    )


def is_issue_visible_to_guest(issue, user) -> bool:
    """単一の課題を GUEST に見せてよいか。

    オブジェクト単位のチェック（retrieve やコメント取得）で使う。
    """
    if issue.created_by_id == user.id:
        return True
    return IssueAssignee.objects.filter(issue=issue, assignee=user).exists()
