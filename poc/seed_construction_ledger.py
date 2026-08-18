"""PoC 用: 工事台帳（spindd_ext）へのデータ投入。

poc/seed_construction.py で作った現場に工事情報を紐づける。
spindd_ext が有効なとき（DJANGO_SETTINGS_MODULE=plane.settings.spindd）のみ動く。

実行:
    docker compose --project-name plane-poc --env-file poc/.env --project-directory . \
        -f deployments/cli/community/docker-compose.yml \
        -f poc/docker-compose.override.yml \
        exec -T api python - < poc/seed_construction_ledger.py

冪等。会社名・人名・工事名・金額はすべて架空である。
"""

import os
from datetime import date
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plane.settings.spindd")
django.setup()

from plane.db.models import (  # noqa: E402
    Project,
    ProjectIdentifier,
    ProjectMember,
    State,
    User,
    Workspace,
)
from plane.spindd_ext.models import ConstructionProject  # noqa: E402

workspace = Workspace.objects.get(slug="spin-kensetsu")
members = list(User.objects.filter(email__endswith="@spin-kensetsu.example"))
lead = User.objects.get(email="yamada@spin-kensetsu.example")

# poc/seed_construction.py と同じステータス体系を全現場に用意する。
# Plane の本来の作成経路（app/views/project/base.py）は ProjectIdentifier と
# 既定 State を作る。get_or_create だけだと State が 0 件の現場ができてしまい、
# 課題を作れずボードもグループ無しで描画される。
STATES = [
    ("未着手", "unstarted", "#E0E0E0", True),
    ("施工中", "started", "#3F76FF", False),
    ("検査待ち", "started", "#F59E0B", False),
    ("是正中", "started", "#EF4444", False),
    ("完了", "completed", "#16A34A", False),
    ("保留", "backlog", "#9CA3AF", False),
]


def ensure_project_scaffolding(project):
    """Plane が本来作るものを補う（識別子の予約と既定ステータス）。"""
    ProjectIdentifier.objects.get_or_create(
        workspace=workspace, project=project, defaults={"name": project.identifier}
    )
    for seq, (name, group, color, is_default) in enumerate(STATES, start=1):
        State.objects.get_or_create(
            name=name,
            project=project,
            workspace=workspace,
            defaults={
                "group": group,
                "color": color,
                "sequence": seq * 15000,
                "default": is_default,
                "created_by": lead,
            },
        )

# 台帳としての体裁を見るため、既存の 1 現場に加えて架空の 2 現場を足す。
# いずれも架空。
LEDGER = [
    {
        "identifier": "SKTC",
        "name": "26-A-0147 新川崎テクノロジーセンター新築工事",
        "info": {
            "contract_number": "26-A-0147",
            "official_name": "（仮称）新川崎テクノロジーセンター新築工事",
            "client_name": "株式会社みなと開発",
            "site_address": "神奈川県川崎市幸区新川崎",
            "building_use": "事務所・研究施設",
            "structure": "S造（一部SRC造） 地下1階 地上8階",
            "total_floor_area": Decimal("18450.00"),
            "contract_type": ConstructionProject.ContractType.LUMP_SUM,
            "contract_amount": 4_820_000_000,
            "contract_date": date(2026, 3, 18),
            "construction_start": date(2026, 4, 1),
            "construction_end": date(2027, 9, 30),
            "site_agent": "山田 太郎",
            "chief_engineer": "山田 太郎",
            "remarks": "山留変位が二次管理値超過のため計測強化中。揚重計画を移動式クレーンへ変更。",
        },
    },
    {
        "identifier": "TKMS",
        "name": "25-B-0208 多摩センター駅前商業ビル改修工事",
        "info": {
            "contract_number": "25-B-0208",
            "official_name": "多摩センター駅前商業ビル 耐震改修および内装改修工事",
            "client_name": "多摩都市開発株式会社",
            "site_address": "東京都多摩市落合",
            "building_use": "店舗・事務所",
            "structure": "SRC造 地上7階",
            "total_floor_area": Decimal("9820.50"),
            "contract_type": ConstructionProject.ContractType.LUMP_SUM,
            "contract_amount": 1_240_000_000,
            "contract_date": date(2025, 9, 5),
            "construction_start": date(2025, 10, 1),
            "construction_end": date(2026, 8, 31),
            "actual_completion": date(2026, 8, 20),
            "site_agent": "佐藤 花子",
            "chief_engineer": "鈴木 一郎",
            "remarks": "営業中テナントありの居ながら改修。竣工済み。",
        },
    },
    {
        "identifier": "YKHS",
        "name": "26-C-0031 横浜港湾倉庫 増築工事",
        "info": {
            "contract_number": "26-C-0031",
            "official_name": "横浜港湾倉庫 第3期増築工事",
            "client_name": "港北ロジスティクス株式会社",
            "site_address": "神奈川県横浜市鶴見区大黒町",
            "building_use": "倉庫",
            "structure": "S造 地上2階",
            "total_floor_area": Decimal("6300.00"),
            "contract_type": ConstructionProject.ContractType.UNIT_PRICE,
            "contract_amount": 680_000_000,
            "contract_date": date(2026, 6, 12),
            "construction_start": date(2026, 7, 1),
            "construction_end": date(2027, 2, 28),
            "site_agent": "田中 健二",
            "chief_engineer": "田中 健二",
            "remarks": "既存倉庫の稼働を止めずに施工。夜間作業あり。",
        },
    },
    {
        "identifier": "OMYA",
        "name": "26-D-0055 大宮駅東口ホテル新築工事",
        "info": {
            "contract_number": "26-D-0055",
            "official_name": "（仮称）大宮駅東口ホテル新築工事",
            "client_name": "埼玉ホテルマネジメント株式会社",
            "site_address": "埼玉県さいたま市大宮区",
            "building_use": "ホテル",
            "structure": "RC造 地上14階",
            "total_floor_area": Decimal("11200.00"),
            "contract_type": ConstructionProject.ContractType.LUMP_SUM,
            "contract_amount": 3_150_000_000,
            "contract_date": date(2026, 7, 30),
            "construction_start": date(2026, 9, 1),
            "construction_end": date(2028, 3, 31),
            "site_agent": "山田 太郎",
            "chief_engineer": "佐藤 花子",
            "remarks": "駅前狭小敷地。夜間搬入。",
        },
    },
]

created = updated = 0
for row in LEDGER:
    project, project_created = Project.objects.get_or_create(
        workspace=workspace,
        identifier=row["identifier"],
        defaults={"name": row["name"], "network": 2, "timezone": "Asia/Tokyo", "project_lead": lead},
    )
    if project_created:
        # BaseModel.save() は crum.get_current_user() を見て created_by を上書きするため、
        # スクリプト実行時は defaults に渡しても None になる。save() を経由せず入れる。
        Project.objects.filter(pk=project.pk).update(created_by=lead)
    ensure_project_scaffolding(project)
    # API の可視範囲は ProjectMember 経由で絞るため、台帳に出すには参加が必要。
    for member in members:
        ProjectMember.objects.get_or_create(
            project=project,
            member=member,
            workspace=workspace,
            defaults={"role": 20 if member == lead else 15},
        )
    obj, was_created = ConstructionProject.objects.update_or_create(
        project=project, defaults=row["info"]
    )
    created += int(was_created)
    updated += int(not was_created)

print("=" * 64)
print(f"工事情報: 作成 {created} 件 / 更新 {updated} 件")
total = sum(c.contract_amount or 0 for c in ConstructionProject.objects.all())
for c in ConstructionProject.objects.select_related("project"):
    amount = f"{c.contract_amount:,}" if c.contract_amount else "-"
    print(f"  {c.contract_number}  {c.client_name:22} {amount:>16} 円  {c.project.identifier}")
print(f"  請負金額 合計: {total:,} 円")
print("=" * 64)
