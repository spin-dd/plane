# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# spin-dd fork addition (2026-08-10): this file does not exist upstream.

"""工事情報のモデル。

Plane の Project（= 1 現場）に 1 対 1 で紐づく工事台帳。
Plane 側のテーブルに列を足すのではなく、独立したテーブルを FK で繋いでいる。
これは plane.db のマイグレーション連番衝突を避けるための設計上の制約である
（CONTRIBUTING.spindd.md §4）。
"""

from django.db import models
from django.db.models import Q

from plane.db.mixins import SoftDeleteModel


class ConstructionProject(SoftDeleteModel):
    """現場（Plane の Project）に対応する工事情報。

    SoftDeleteModel を継承しているのは、Plane の削除が soft delete だからである。
    `plane/bgtasks/deletion_task.py` は 1 対 1 の関連先に `deleted_at` がある場合だけ
    連鎖させる。この属性が無いと、現場を削除しても工事情報が残り続け、
    OneToOne の枠と工事番号を占有したまま復活できなくなる。
    """

    class ContractType(models.TextChoices):
        LUMP_SUM = "lump_sum", "総価請負"
        UNIT_PRICE = "unit_price", "単価契約"
        COST_PLUS_FEE = "cost_plus_fee", "実費精算"

    project = models.OneToOneField(
        "db.Project",
        on_delete=models.CASCADE,
        related_name="spindd_construction",
        verbose_name="現場",
    )
    # project.workspace から辿れるが、工事番号の一意制約をワークスペース単位に
    # 掛けるために非正規化して持つ。制約式でリレーションを辿れないため。
    workspace = models.ForeignKey(
        "db.Workspace",
        on_delete=models.CASCADE,
        related_name="spindd_construction_projects",
        verbose_name="ワークスペース",
    )

    # 識別
    contract_number = models.CharField("工事番号", max_length=64)
    official_name = models.CharField("工事名称", max_length=255, blank=True)

    # 発注者・場所
    client_name = models.CharField("発注者", max_length=255, blank=True)
    site_address = models.CharField("工事場所", max_length=255, blank=True)

    # 建物概要
    building_use = models.CharField("用途", max_length=255, blank=True)
    structure = models.CharField("構造・規模", max_length=255, blank=True)
    total_floor_area = models.DecimalField(
        "延床面積（m2）", max_digits=12, decimal_places=2, null=True, blank=True
    )

    # 契約
    contract_type = models.CharField(
        "契約形態", max_length=32, choices=ContractType.choices, default=ContractType.LUMP_SUM
    )
    # 円単位の整数で持つ。float は端数が出るため使わない。
    contract_amount = models.BigIntegerField("請負金額（円）", null=True, blank=True)
    contract_date = models.DateField("契約日", null=True, blank=True)

    # 工期
    construction_start = models.DateField("着工日", null=True, blank=True)
    construction_end = models.DateField("竣工予定日", null=True, blank=True)
    actual_completion = models.DateField("実竣工日", null=True, blank=True)

    # 体制（建設業法上の呼称。Plane のメンバーとは別に氏名で持つ）
    site_agent = models.CharField("現場代理人", max_length=255, blank=True)
    chief_engineer = models.CharField("監理技術者・主任技術者", max_length=255, blank=True)

    remarks = models.TextField("備考", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "spindd_construction_projects"
        verbose_name = "工事情報"
        verbose_name_plural = "工事情報"
        ordering = ("contract_number",)
        constraints = [
            # 工事番号はワークスペース単位で一意。グローバル一意にすると、
            # 他社（他ワークスペース）が同じ番号を使えなくなるうえ、
            # IntegrityError の有無から他テナントの工事番号を推測できてしまう。
            # soft delete された行は除外する（Plane の既存モデルと同じ書き方）。
            models.UniqueConstraint(
                fields=["workspace", "contract_number"],
                condition=Q(deleted_at__isnull=True),
                name="spindd_construction_unique_contract_number_per_workspace",
            )
        ]

    def __str__(self):
        return f"{self.contract_number} {self.official_name or self.project_id}"

    def save(self, *args, **kwargs):
        # workspace は project から導出する。呼び出し側に指定させると
        # project と食い違った値を入れられる余地が残るため。
        if self.project_id:
            self.workspace_id = self.project.workspace_id
        super().save(*args, **kwargs)

    @property
    def is_completed(self):
        return self.actual_completion is not None
