"""PoC 用: 残り 3 現場の課題データと、協力会社の GUEST アカウントを投入する。

`poc/seed_construction.py` は SKTC（新築）に 32 件の課題を入れる。
`poc/seed_construction_ledger.py` は 4 現場ぶんの工事情報を入れるが、
SKTC 以外は課題が 0 件で、現場ごとの性格の違いが見えなかった。

このスクリプトは 3 つの性格の異なる現場を埋める。

- TKMS 改修（居ながら工事・竣工済み）
- YKHS 増築（既存稼働中・夜間作業）
- OMYA 新築（着工直後・駅前狭小敷地）

あわせて **協力会社の GUEST アカウント**を作り、担当課題を割り当てる。
これは #14（GUEST の可視範囲を「作成者 or 担当者」に広げた変更）を
実際に画面で確認するためのデータでもある。

実行:
    docker compose --project-name plane-poc --env-file poc/.env --project-directory . \
        -f deployments/cli/community/docker-compose.yml \
        -f poc/docker-compose.override.yml \
        exec -T api python - < poc/seed_more_sites.py

冪等。会社名・人名・工事名・金額はすべて架空である。
"""

import os
from datetime import date

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plane.settings.spindd")
django.setup()

from plane.db.models import (  # noqa: E402
    Cycle,
    CycleIssue,
    Issue,
    IssueAssignee,
    IssueComment,
    IssueLabel,
    Label,
    Module,
    ModuleIssue,
    Profile,
    Project,
    ProjectMember,
    State,
    User,
    Workspace,
)

workspace = Workspace.objects.get(slug="spin-kensetsu")
staff = {
    u.email.split("@")[0]: u
    for u in User.objects.filter(email__endswith="@spin-kensetsu.example")
}
lead = staff["yamada"]

# --------------------------------------------------------------------------
# 協力会社の GUEST アカウント
# --------------------------------------------------------------------------
# GUEST は「自分が作成した、または自分が担当している課題」だけが見える（#14）。
# 元請が起票して割り当てた是正指示が担当者に見えることを、この 3 名で確認できる。
SUBCONTRACTORS = [
    ("misaki@misaki-steel.example", "三崎", "健", "三崎 健（三崎鉄骨建設）"),
    ("daiwa@daiwa-kiso.example", "大和", "茂", "大和 茂（大和基礎工業）"),
    ("toyo@toyo-densetsu.example", "東洋", "実", "東洋 実（東洋電設工業）"),
]

partners = {}
for email, last, first, display in SUBCONTRACTORS:
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "username": email,
            "first_name": first,
            "last_name": last,
            "display_name": display,
            "is_password_autoset": False,
            "is_email_verified": True,
        },
    )
    if created:
        user.set_password("PlanePoC!2026")
        user.save()
    profile, _ = Profile.objects.get_or_create(user=user, defaults={"language": "ja"})
    if profile.language != "ja":
        profile.language = "ja"
        profile.save(update_fields=["language"])
    partners[email.split("@")[0]] = user

# --------------------------------------------------------------------------
# 現場ごとのデータ
# --------------------------------------------------------------------------
# (工種, 開始, 完了)
# (月次工程, 開始, 終了)
# 課題: (件名, 本文, 状態, 優先度, 工種, 月次, ラベル, 担当, 開始, 期限, コメント)

SITES = {
    "TKMS": {
        "note": "居ながら改修・竣工済み",
        "modules": [
            ("仮設工事", date(2025, 10, 1), date(2026, 8, 31)),
            ("耐震補強工事", date(2025, 11, 1), date(2026, 4, 30)),
            ("内装改修工事", date(2026, 3, 1), date(2026, 7, 31)),
            ("電気設備工事", date(2026, 1, 15), date(2026, 7, 31)),
            ("空調・衛生設備工事", date(2026, 1, 15), date(2026, 7, 31)),
        ],
        "cycles": [
            ("2026年5月度", date(2026, 5, 1), date(2026, 5, 31)),
            ("2026年6月度", date(2026, 6, 1), date(2026, 6, 30)),
            ("2026年7月度", date(2026, 7, 1), date(2026, 7, 31)),
            ("2026年8月度", date(2026, 8, 1), date(2026, 8, 31)),
        ],
        "labels": [
            ("安全", "#DC2626"),
            ("品質", "#7C3AED"),
            ("工程", "#2563EB"),
            ("原価", "#CA8A04"),
            ("近隣対応", "#DB2777"),
            ("設計変更", "#0891B2"),
            ("法令対応", "#4B5563"),
            ("協力会社/光和内装", "#059669"),
            ("協力会社/東洋電設工業", "#059669"),
        ],
        "issues": [
            (
                "営業中テナントの夜間作業時間の再調整（B1 飲食フロア）",
                "B1 飲食テナントの営業終了が 23:30 まで延びたため、はつり作業の開始を 24:00 へ後ろ倒しする。"
                "作業時間が 4 時間に圧縮されるため、工程への影響を再算定する。",
                "完了", "high", "耐震補強工事", "2026年5月度",
                ["工程", "近隣対応"], "sato", date(2026, 5, 7), date(2026, 5, 15),
                [("sato", "テナント会と合意。5/18 週から 24:00〜4:00 で運用する。")],
            ),
            (
                "既存吹付材の石綿含有調査（機械室・レベル2）",
                "3F 機械室の吹付ロックウールから石綿を検出。レベル2 の除去計画書を作成し、"
                "労基署・自治体への届出を行う。除去期間中は当該系統を停止する。",
                "完了", "urgent", "耐震補強工事", "2026年5月度",
                ["法令対応", "安全"], "suzuki", date(2026, 5, 11), date(2026, 6, 12),
                [("suzuki", "6/1 に届出受理。6/8〜6/11 で除去、完了後の空気環境測定も基準値内。")],
            ),
            (
                "耐震ブレース取付部のアンカー引張試験",
                "2F〜5F の耐震ブレース基部あと施工アンカーについて、抜取り引張試験を実施する。"
                "設計引張力 42kN に対する確認。",
                "完了", "high", "耐震補強工事", "2026年6月度",
                ["品質"], "sato", date(2026, 6, 1), date(2026, 6, 12),
                [],
            ),
            (
                "既存図と現況の相違（4F 梁貫通スリーブ位置）",
                "竣工図に無いスリーブが 4F 大梁に 3 箇所存在。構造設計者に補強要否を確認する。"
                "設備ルートの再検討が必要になる可能性がある。",
                "完了", "high", "空調・衛生設備工事", "2026年6月度",
                ["設計変更", "品質", "協力会社/東洋電設工業"], "tanaka", date(2026, 6, 8), date(2026, 6, 26),
                [("tanaka", "構造設計者より補強不要の回答。設備ルートは天井内で 150mm 下げて回避する。")],
            ),
            (
                "消防設備切替時の停電・断水計画（全館 4 時間）",
                "自火報の受信機更新にあたり全館停電 4 時間が必要。テナント各社への事前通知と、"
                "冷蔵ショーケースの代替電源手配を調整する。",
                "完了", "urgent", "電気設備工事", "2026年7月度",
                ["工程", "近隣対応", "協力会社/東洋電設工業"], "tanaka", date(2026, 7, 6), date(2026, 7, 26),
                [("tanaka", "7/21（火）2:00〜6:00 で実施。飲食 4 社へ発電機を手配済み。")],
            ),
            (
                "内装仕上材の変更（共用部床タイル 廃番）",
                "指定の床タイルがメーカー廃番。同等品 2 案を提示して発注者承認を得る。",
                "完了", "medium", "内装改修工事", "2026年7月度",
                ["設計変更", "原価", "協力会社/光和内装"], "sato", date(2026, 7, 1), date(2026, 7, 17),
                [],
            ),
            (
                "完了検査の指摘事項対応（防火区画貫通処理 6 箇所）",
                "特定行政庁の完了検査で、防火区画貫通部の処理不良を 6 箇所指摘。是正して再検査を受ける。",
                "完了", "urgent", "耐震補強工事", "2026年8月度",
                ["法令対応", "品質"], "yamada", date(2026, 8, 3), date(2026, 8, 14),
                [("yamada", "8/12 に是正完了、8/17 の再検査で適合。検査済証を受領した。")],
            ),
            (
                "竣工図書の提出（電子納品）",
                "竣工図・施工記録・保全マニュアルを電子納品形式で提出する。写真台帳は工種別に整理する。",
                "完了", "medium", "仮設工事", "2026年8月度",
                ["品質"], "takahashi", date(2026, 8, 10), date(2026, 8, 20),
                [],
            ),
        ],
    },
    "YKHS": {
        "note": "既存稼働中・夜間作業",
        "modules": [
            ("仮設工事", date(2026, 7, 1), date(2027, 2, 28)),
            ("地盤改良・基礎工事", date(2026, 7, 15), date(2026, 10, 31)),
            ("鉄骨工事", date(2026, 10, 1), date(2026, 12, 27)),
            ("屋根・外装工事", date(2026, 12, 1), date(2027, 1, 31)),
            ("舗装・外構工事", date(2027, 1, 15), date(2027, 2, 28)),
        ],
        "cycles": [
            ("2026年7月度", date(2026, 7, 1), date(2026, 7, 31)),
            ("2026年8月度", date(2026, 8, 1), date(2026, 8, 31)),
            ("2026年9月度", date(2026, 9, 1), date(2026, 9, 30)),
            ("2026年10月度", date(2026, 10, 1), date(2026, 10, 31)),
        ],
        "labels": [
            ("安全", "#DC2626"),
            ("品質", "#7C3AED"),
            ("工程", "#2563EB"),
            ("原価", "#CA8A04"),
            ("近隣対応", "#DB2777"),
            ("設計変更", "#0891B2"),
            ("法令対応", "#4B5563"),
            ("協力会社/大和基礎工業", "#059669"),
            ("協力会社/三崎鉄骨建設", "#059669"),
        ],
        "issues": [
            (
                "既存倉庫のフォークリフト動線と工事車両の交錯（南ゲート）",
                "既存棟の入出庫が日中 80 台/日あり、南ゲートで工事車両と交錯する。"
                "工事車両の入場を 9:30〜11:30 と 14:00〜16:00 に限定し、誘導員を 2 名配置する。",
                "施工中", "urgent", "仮設工事", "2026年8月度",
                ["安全", "工程"], "suzuki", date(2026, 8, 3), date(2026, 8, 21),
                [("suzuki", "荷主側の出荷ピークが月末に寄るため、月末週は工事車両を朝のみに絞る。")],
            ),
            (
                "地盤改良の出来形確認（柱状改良 φ800 × 142 本）",
                "液状化対策の柱状改良について、施工記録と一軸圧縮強度試験の結果を照合する。"
                "設計基準強度 600kN/m2。",
                "検査待ち", "high", "地盤改良・基礎工事", "2026年9月度",
                ["品質", "協力会社/大和基礎工業"], "sato", date(2026, 9, 7), date(2026, 9, 25),
                [("sato", "142 本中 138 本の記録を受領。残 4 本（No.71-74）は 9/24 提出予定。")],
            ),
            (
                "夜間作業の照度確保と投光器の向き（既存棟事務所へ漏光）",
                "夜間作業の投光器が既存棟 2F 事務所へ直接入射している。"
                "遮光板を設置し、照度は作業面 150lx を確保したうえで向きを調整する。",
                "完了", "medium", "仮設工事", "2026年8月度",
                ["安全", "近隣対応"], "suzuki", date(2026, 8, 18), date(2026, 8, 26),
                [],
            ),
            (
                "鉄骨建方時の強風中止基準の明確化（臨海部）",
                "臨海部で日中の平均風速が 10m/s を超える日が多い。建方の中止基準と、"
                "中止判断のタイミング（当日 6:00 の予報）を施工計画書に明記する。",
                "施工中", "high", "鉄骨工事", "2026年9月度",
                ["安全", "工程", "協力会社/三崎鉄骨建設"], "sato", date(2026, 9, 1), date(2026, 9, 18),
                [("sato", "平均 10m/s または瞬間 15m/s で中止。判断は当日 6:00、順延は翌営業日とする。")],
            ),
            (
                "既存棟との取合い部の止水詳細（EXP.J 部）",
                "増築部と既存棟の間の EXP.J について、止水ディテールが設計図で未確定。"
                "メーカー納まり図をもとに承認図を作成する。",
                "施工中", "medium", "屋根・外装工事", None,
                ["設計変更", "品質"], "sato", date(2026, 9, 14), date(2026, 10, 30),
                [],
            ),
            (
                "特定建設作業の届出（杭打・地盤改良）",
                "騒音規制法・振動規制法に基づく特定建設作業実施届出を提出する。"
                "作業時間は 8:00〜17:00、日曜・祝日は作業しない。",
                "完了", "high", "地盤改良・基礎工事", "2026年7月度",
                ["法令対応"], "takahashi", date(2026, 7, 6), date(2026, 7, 17),
                [],
            ),
            (
                "増築部への消防用設備の連動試験計画",
                "既存棟の自火報と増築部の連動試験を、既存棟の稼働を止めずに実施する計画を立てる。",
                "未着手", "medium", "仮設工事", None,
                ["法令対応", "工程"], "tanaka", date(2026, 12, 1), date(2027, 1, 30),
                [],
            ),
        ],
    },
    "OMYA": {
        "note": "着工直後・駅前狭小敷地",
        "modules": [
            ("仮設工事", date(2026, 9, 1), date(2028, 3, 31)),
            ("山留・土工事", date(2026, 9, 15), date(2027, 1, 31)),
            ("杭・地業工事", date(2026, 11, 1), date(2027, 3, 31)),
            ("躯体工事", date(2027, 2, 1), date(2027, 11, 30)),
        ],
        "cycles": [
            ("2026年9月度", date(2026, 9, 1), date(2026, 9, 30)),
            ("2026年10月度", date(2026, 10, 1), date(2026, 10, 31)),
            ("2026年11月度", date(2026, 11, 1), date(2026, 11, 30)),
        ],
        "labels": [
            ("安全", "#DC2626"),
            ("品質", "#7C3AED"),
            ("工程", "#2563EB"),
            ("原価", "#CA8A04"),
            ("近隣対応", "#DB2777"),
            ("設計変更", "#0891B2"),
            ("法令対応", "#4B5563"),
            ("協力会社/大和基礎工業", "#059669"),
        ],
        "issues": [
            (
                "狭小敷地の資材搬入計画と道路使用許可",
                "敷地間口が 18m しかなく、十分な荷捌きスペースが取れない。"
                "県道の一部を使用する道路使用許可を申請し、搬入は 9:00〜16:00 に限定する。",
                "施工中", "urgent", "仮設工事", "2026年9月度",
                ["法令対応", "工程", "近隣対応"], "yamada", date(2026, 9, 1), date(2026, 9, 30),
                [("yamada", "所轄署と協議済み。歩行者の安全通路 1.5m 確保が条件。")],
            ),
            (
                "駅前歩行者動線の切り回しと仮設安全通路",
                "1 日 2.4 万人が通行する駅前歩道を仮囲いで狭める。有効幅員 2.0m を確保し、"
                "夜間も照度を保った仮設安全通路を設置する。",
                "施工中", "urgent", "仮設工事", "2026年9月度",
                ["安全", "近隣対応"], "suzuki", date(2026, 9, 5), date(2026, 9, 25),
                [("suzuki", "視覚障害者誘導用ブロックの仮設敷設について市のバリアフリー担当と協議中。")],
            ),
            (
                "近隣商業テナントへの工事説明会（1 階路面店 12 店舗）",
                "隣接する路面店 12 店舗に対し、工期・作業時間・粉塵騒音対策を説明する。"
                "営業への影響が大きい解体時期を重点的に説明する。",
                "完了", "high", "仮設工事", "2026年9月度",
                ["近隣対応"], "yamada", date(2026, 9, 8), date(2026, 9, 19),
                [],
            ),
            (
                "地中障害物の撤去（旧建物基礎・想定外）",
                "山留工事の掘削で旧建物の独立基礎を GL-3.2m に確認。設計図書に記載が無い。"
                "撤去範囲と費用について発注者と協議する。",
                "是正中", "urgent", "山留・土工事", "2026年10月度",
                ["原価", "工程", "設計変更"], "sato", date(2026, 10, 5), date(2026, 10, 31),
                [("sato", "撤去概算 2,180 万円・工程 9 日延伸。10/20 の定例で変更協議に上げる。")],
            ),
            (
                "タワークレーンの設置協議（航空法の高さ制限）",
                "計画高さが 62m となり航空法の制限表面に抵触する可能性がある。"
                "国土交通省への確認と、必要なら航空障害灯の設置を計画する。",
                "施工中", "high", "仮設工事", "2026年10月度",
                ["法令対応", "安全"], "yamada", date(2026, 10, 1), date(2026, 11, 14),
                [],
            ),
            (
                "杭施工計画の確認（アースドリル工法・支持層 GL-28m）",
                "支持層が GL-28m と深く、孔壁保護の安定液管理が要点になる。"
                "施工計画書と管理基準値を確認する。",
                "未着手", "medium", "杭・地業工事", "2026年11月度",
                ["品質", "協力会社/大和基礎工業"], "sato", date(2026, 11, 2), date(2026, 11, 27),
                [],
            ),
        ],
    },
}

# 協力会社の担当割り当て。
# 元請（yamada / sato）が起票した課題を協力会社の担当者に割り当てる形にして、
# 「作成者ではないが担当者なので見える」ことを確認できるようにする。
PARTNER_ASSIGNMENTS = {
    "misaki": [("YKHS", "鉄骨建方時の強風中止基準の明確化（臨海部）")],
    "daiwa": [
        ("YKHS", "地盤改良の出来形確認（柱状改良 φ800 × 142 本）"),
        ("OMYA", "杭施工計画の確認（アースドリル工法・支持層 GL-28m）"),
    ],
    "toyo": [
        ("TKMS", "消防設備切替時の停電・断水計画（全館 4 時間）"),
        ("TKMS", "既存図と現況の相違（4F 梁貫通スリーブ位置）"),
    ],
}

# 協力会社をどの現場に GUEST として入れるか
PARTNER_PROJECTS = {
    "misaki": ["YKHS"],
    "daiwa": ["YKHS", "OMYA"],
    "toyo": ["TKMS"],
}

created_issues = 0
for identifier, spec in SITES.items():
    project = Project.objects.get(workspace=workspace, identifier=identifier)
    states = {s.name: s for s in State.objects.filter(project=project)}

    modules = {}
    for name, start, target in spec["modules"]:
        modules[name], _ = Module.objects.get_or_create(
            name=name,
            project=project,
            workspace=workspace,
            defaults={
                "start_date": start,
                "target_date": target,
                "status": "in-progress",
                "lead": lead,
                "created_by": lead,
            },
        )

    cycles = {}
    for name, start, end in spec["cycles"]:
        cycles[name], _ = Cycle.objects.get_or_create(
            name=name,
            project=project,
            workspace=workspace,
            defaults={
                "start_date": start,
                "end_date": end,
                "owned_by": lead,
                "created_by": lead,
                "timezone": "Asia/Tokyo",
            },
        )

    labels = {}
    for name, color in spec["labels"]:
        labels[name], _ = Label.objects.get_or_create(
            name=name,
            project=project,
            workspace=workspace,
            defaults={"color": color, "created_by": lead},
        )

    for (
        name,
        body,
        state_name,
        priority,
        module_name,
        cycle_name,
        label_names,
        author_key,
        start_date,
        target_date,
        comments,
    ) in spec["issues"]:
        author = staff[author_key]
        issue, created = Issue.objects.get_or_create(
            name=name,
            project=project,
            workspace=workspace,
            defaults={
                "description_html": f"<p>{body}</p>",
                "state": states[state_name],
                "priority": priority,
                "start_date": start_date,
                "target_date": target_date,
            },
        )
        if not created:
            continue
        created_issues += 1
        # BaseModel.save は crum 由来で created_by を決めるため、明示的に入れる。
        Issue.objects.filter(pk=issue.pk).update(created_by=author)

        IssueAssignee.objects.get_or_create(
            issue=issue, assignee=author, project=project, workspace=workspace
        )
        for label_name in label_names:
            IssueLabel.objects.get_or_create(
                issue=issue, label=labels[label_name], project=project, workspace=workspace
            )
        ModuleIssue.objects.get_or_create(
            issue=issue, module=modules[module_name], project=project, workspace=workspace
        )
        if cycle_name:
            CycleIssue.objects.get_or_create(
                issue=issue, cycle=cycles[cycle_name], project=project, workspace=workspace
            )
        for actor_key, text in comments:
            IssueComment.objects.get_or_create(
                issue=issue,
                comment_html=f"<p>{text}</p>",
                project=project,
                workspace=workspace,
                defaults={"actor": staff[actor_key], "created_by": staff[actor_key]},
            )

# --------------------------------------------------------------------------
# 協力会社を GUEST として参加させ、担当を割り当てる
# --------------------------------------------------------------------------
for key, identifiers in PARTNER_PROJECTS.items():
    for identifier in identifiers:
        project = Project.objects.get(workspace=workspace, identifier=identifier)
        ProjectMember.objects.get_or_create(
            project=project,
            member=partners[key],
            workspace=workspace,
            defaults={"role": 5},  # GUEST
        )

assigned = 0
for key, targets in PARTNER_ASSIGNMENTS.items():
    for identifier, issue_name in targets:
        project = Project.objects.get(workspace=workspace, identifier=identifier)
        issue = Issue.objects.filter(project=project, name=issue_name).first()
        if issue is None:
            continue
        _, was_created = IssueAssignee.objects.get_or_create(
            issue=issue, assignee=partners[key], project=project, workspace=workspace
        )
        assigned += int(was_created)

print("=" * 70)
print(f"課題を作成: {created_issues} 件 / 協力会社への割り当て: {assigned} 件")
print()
for p in Project.objects.filter(workspace=workspace).order_by("identifier"):
    print(
        f"  {p.identifier}: 課題 {Issue.objects.filter(project=p).count():3} / "
        f"工種 {Module.objects.filter(project=p).count()} / "
        f"工程 {Cycle.objects.filter(project=p).count()} / "
        f"ラベル {Label.objects.filter(project=p).count()}"
    )
print()
print("  協力会社（GUEST / パスワードは PlanePoC!2026）")
for key, user in partners.items():
    sites = ", ".join(PARTNER_PROJECTS[key])
    n = IssueAssignee.objects.filter(assignee=user).count()
    print(f"    {user.email:34} {user.display_name:26} 参加: {sites:12} 担当 {n} 件")
print("=" * 70)
