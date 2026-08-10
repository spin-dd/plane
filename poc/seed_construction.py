"""
PoC 用シードスクリプト（fork 側で追加した新規ファイル / upstream には存在しない）。

架空の建設案件「（仮称）新川崎テクノロジーセンター新築工事」を Plane に投入し、
素の Plane が日本の建設現場の実務に耐えるかを確認する。

実行:
    docker compose --project-name plane-poc --env-file poc/.env \
        -f deployments/cli/community/docker-compose.yml \
        exec -T api python - < poc/seed_construction.py

冪等: 同じ内容で再実行しても重複を作らない（get_or_create ベース）。

※ 登場する会社名・人名・工事名はすべて架空である。
"""

import os
from datetime import date

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plane.settings.production")
django.setup()

from plane.db.models import (  # noqa: E402
    Cycle,
    CycleIssue,
    Issue,
    Profile,
    IssueAssignee,
    IssueComment,
    IssueLabel,
    Label,
    Module,
    ModuleIssue,
    Project,
    ProjectIdentifier,
    ProjectMember,
    State,
    User,
    Workspace,
    WorkspaceMember,
)

# --------------------------------------------------------------------------
# 1. 体制（ユーザー）
# --------------------------------------------------------------------------
# 役割は建設業法・労働安全衛生法上の呼称に合わせる。
PEOPLE = [
    ("yamada@spin-kensetsu.example", "山田", "太郎", "山田 太郎（現場代理人・監理技術者）"),
    ("sato@spin-kensetsu.example", "佐藤", "花子", "佐藤 花子（工事主任）"),
    ("suzuki@spin-kensetsu.example", "鈴木", "一郎", "鈴木 一郎（安全衛生責任者）"),
    ("tanaka@spin-kensetsu.example", "田中", "健二", "田中 健二（設備担当）"),
    ("takahashi@spin-kensetsu.example", "高橋", "みどり", "高橋 みどり（工事事務）"),
]

users = {}
for email, last, first, display in PEOPLE:
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
    # UI 言語は User ではなく Profile が持つ（既定 "en"）。ここを "ja" にしないと
    # データだけ日本語でメニューが英語のままになる。
    # 反映は apps/web/core/store/user/profile.store.ts:115 の setLanguage 経由。
    profile, _ = Profile.objects.get_or_create(user=user, defaults={"language": "ja"})
    if profile.language != "ja":
        profile.language = "ja"
        profile.save(update_fields=["language"])
    users[email.split("@")[0]] = user

yamada = users["yamada"]
sato = users["sato"]
suzuki = users["suzuki"]
tanaka = users["tanaka"]
takahashi = users["takahashi"]

# --------------------------------------------------------------------------
# 2. ワークスペース（＝会社）
# --------------------------------------------------------------------------
workspace, _ = Workspace.objects.get_or_create(
    slug="spin-kensetsu",
    defaults={"name": "株式会社スピン建設", "owner": yamada},
)

for user in users.values():
    WorkspaceMember.objects.get_or_create(
        workspace=workspace,
        member=user,
        defaults={"role": 20 if user == yamada else 15},
    )

# --------------------------------------------------------------------------
# 3. プロジェクト（＝現場）
# --------------------------------------------------------------------------
# 工事番号・発注者・請負金額は Plane に置き場所が無いため、やむなく description に流し込む。
# → これ自体が PoC の観測対象（カスタム項目の不在）。
PROJECT_DESCRIPTION = (
    "工事番号: 26-A-0147 / 発注者: 株式会社みなと開発 / "
    "工事場所: 神奈川県川崎市幸区新川崎 / 用途: 事務所・研究施設 / "
    "構造規模: S造（一部SRC造） 地下1階 地上8階 / 延床面積: 18,450 m2 / "
    "工期: 2026-04-01 〜 2027-09-30 / 請負金額: 4,820,000,000 円"
)

project, _ = Project.objects.get_or_create(
    workspace=workspace,
    identifier="SKTC",
    defaults={
        "name": "26-A-0147 新川崎テクノロジーセンター新築工事",
        "description": PROJECT_DESCRIPTION,
        "description_html": f"<p>{PROJECT_DESCRIPTION}</p>",
        "network": 2,
        "project_lead": yamada,
        "default_assignee": yamada,
        "created_by": yamada,
        "timezone": "Asia/Tokyo",
    },
)
ProjectIdentifier.objects.get_or_create(
    workspace=workspace, project=project, defaults={"name": "SKTC"}
)

for user in users.values():
    ProjectMember.objects.get_or_create(
        project=project,
        member=user,
        workspace=workspace,
        defaults={"role": 20 if user in (yamada, sato) else 15},
    )

# --------------------------------------------------------------------------
# 4. ステータス（State）
# --------------------------------------------------------------------------
# Plane の group は 6 種類固定。建設のステータスを既存 group に寄せる。
STATES = [
    ("未着手", "unstarted", "#E0E0E0", True),
    ("施工中", "started", "#3F76FF", False),
    ("検査待ち", "started", "#F59E0B", False),
    ("是正中", "started", "#EF4444", False),
    ("完了", "completed", "#16A34A", False),
    ("保留", "backlog", "#9CA3AF", False),
]
states = {}
for seq, (name, group, color, is_default) in enumerate(STATES, start=1):
    state, _ = State.objects.get_or_create(
        name=name,
        project=project,
        workspace=workspace,
        defaults={
            "group": group,
            "color": color,
            "sequence": seq * 15000,
            "default": is_default,
            "created_by": yamada,
        },
    )
    states[name] = state

# Plane が初期作成する既定 State（Backlog/Todo/...）は PoC の観測を濁すので落とす。
State.objects.filter(project=project).exclude(name__in=states.keys()).exclude(
    is_triage=True
).delete()

# --------------------------------------------------------------------------
# 5. ラベル
# --------------------------------------------------------------------------
# 分類ラベルと、本来エンティティであるべき「協力会社」をラベルで代用する。
# → 代用の限界そのものが PoC の観測対象。
CATEGORY_LABELS = [
    ("安全", "#DC2626"),
    ("品質", "#7C3AED"),
    ("工程", "#2563EB"),
    ("原価", "#CA8A04"),
    ("近隣対応", "#DB2777"),
    ("設計変更", "#0891B2"),
    ("法令対応", "#4B5563"),
]
SUBCONTRACTOR_LABELS = [
    ("協力会社/大和基礎工業", "#059669"),
    ("協力会社/三崎鉄骨建設", "#059669"),
    ("協力会社/東洋電設工業", "#059669"),
    ("協力会社/中央空調サービス", "#059669"),
    ("協力会社/光和内装", "#059669"),
    ("協力会社/新和外構", "#059669"),
]
labels = {}
for name, color in CATEGORY_LABELS + SUBCONTRACTOR_LABELS:
    label, _ = Label.objects.get_or_create(
        name=name,
        project=project,
        workspace=workspace,
        defaults={"color": color, "created_by": yamada},
    )
    labels[name] = label

# --------------------------------------------------------------------------
# 6. 工種（Module）
# --------------------------------------------------------------------------
MODULES = [
    ("仮設工事", date(2026, 4, 1), date(2027, 9, 30), "in-progress", yamada),
    ("土工事・山留工事", date(2026, 4, 15), date(2026, 8, 31), "in-progress", sato),
    ("杭・地業工事", date(2026, 5, 1), date(2026, 9, 30), "in-progress", sato),
    ("躯体工事", date(2026, 8, 1), date(2027, 3, 31), "planned", sato),
    ("外装工事", date(2027, 1, 15), date(2027, 6, 30), "planned", sato),
    ("内装工事", date(2027, 3, 1), date(2027, 8, 31), "backlog", sato),
    ("電気設備工事", date(2026, 10, 1), date(2027, 8, 31), "planned", tanaka),
    ("空調・衛生設備工事", date(2026, 10, 1), date(2027, 8, 31), "planned", tanaka),
    ("外構工事", date(2027, 6, 1), date(2027, 9, 15), "backlog", sato),
]
modules = {}
for name, start, target, status, lead in MODULES:
    module, _ = Module.objects.get_or_create(
        name=name,
        project=project,
        workspace=workspace,
        defaults={
            "start_date": start,
            "target_date": target,
            "status": status,
            "lead": lead,
            "created_by": yamada,
        },
    )
    modules[name] = module

# --------------------------------------------------------------------------
# 7. 月次工程（Cycle）
# --------------------------------------------------------------------------
CYCLES = [
    ("2026年4月度", date(2026, 4, 1), date(2026, 4, 30)),
    ("2026年5月度", date(2026, 5, 1), date(2026, 5, 31)),
    ("2026年6月度", date(2026, 6, 1), date(2026, 6, 30)),
    ("2026年7月度", date(2026, 7, 1), date(2026, 7, 31)),
    ("2026年8月度", date(2026, 8, 1), date(2026, 8, 31)),
    ("2026年9月度", date(2026, 9, 1), date(2026, 9, 30)),
]
cycles = {}
for name, start, end in CYCLES:
    cycle, _ = Cycle.objects.get_or_create(
        name=name,
        project=project,
        workspace=workspace,
        defaults={
            "start_date": start,
            "end_date": end,
            "owned_by": yamada,
            "created_by": yamada,
            "timezone": "Asia/Tokyo",
        },
    )
    cycles[name] = cycle

# --------------------------------------------------------------------------
# 8. 課題（Work Item）
# --------------------------------------------------------------------------
# (件名, 本文, State, 優先度, 工種, 月次, ラベル, 担当, 開始日, 期限, コメント)
ISSUES = [
    (
        "山留壁の変位が管理値を超過（A-3 測点）",
        "8/5 の計測で A-3 測点の水平変位が 32mm となり、二次管理値 30mm を超過。"
        "切梁のプレロード再導入と、計測頻度を 1 日 2 回へ変更する。設計事務所への報告済み。",
        "是正中", "urgent", "土工事・山留工事", "2026年8月度",
        ["安全", "品質"], sato, date(2026, 8, 5), date(2026, 8, 12),
        [
            (sato, "切梁 2 段目のプレロードを 8/6 午前に再導入。導入後の変位は 30mm で横ばい。"),
            (yamada, "設計事務所と協議のうえ、三次管理値 40mm までは計測強化で対応。超えたら即時作業中止とする。"),
        ],
    ),
    (
        "4F 床コンクリート 呼び強度 33N/mm2 の 28 日強度試験が不合格",
        "7/10 打設分の供試体で 28 日強度 30.2N/mm2（規格値 33N/mm2）を下回った。"
        "調合報告書とプラント出荷記録を照合のうえ、コア採取による実強度確認を行う。",
        "是正中", "urgent", "躯体工事", "2026年8月度",
        ["品質"], sato, date(2026, 8, 8), date(2026, 8, 25),
        [
            (sato, "コア採取は 8/18 に実施予定。試験機関は日本建材試験センターへ手配済み。"),
            (yamada, "監理者へ第一報を報告。是正方針はコア強度の結果を待って決定する。"),
        ],
    ),
    (
        "足場からの工具落下（ヒヤリハット / 3F 東側）",
        "7/28 15:20 頃、3F 東側外部足場からラチェットレンチが落下。下部は立入禁止措置済みで負傷者なし。"
        "工具落下防止コードの装着徹底と、朝礼での水平展開を実施する。",
        "完了", "high", "仮設工事", "2026年7月度",
        ["安全", "協力会社/三崎鉄骨建設"], suzuki, date(2026, 7, 28), date(2026, 8, 4),
        [
            (suzuki, "8/1 の安全衛生協議会で全社に水平展開。落下防止コード未装着者は入場停止とする旨を周知。"),
        ],
    ),
    (
        "近隣住民から騒音苦情（土曜 7:30 の重機稼働）",
        "7/25（土）7:30 の杭打機稼働について、北側マンション住民より苦情。"
        "特定建設作業実施届出の作業時間は 8:00〜17:00 で届出済み。始業前の暖機運転が原因。",
        "完了", "high", "杭・地業工事", "2026年7月度",
        ["近隣対応", "法令対応", "協力会社/大和基礎工業"], yamada, date(2026, 7, 25), date(2026, 8, 1),
        [
            (yamada, "7/26 に戸別訪問して謝罪。暖機運転は 8:00 以降とし、防音パネルを北面へ追加設置。"),
        ],
    ),
    (
        "既存建屋解体分の石綿事前調査報告（法令期限あり）",
        "既存倉庫の解体に先立つ石綿事前調査を実施。分析の結果、屋根材に石綿含有を確認。"
        "石綿障害予防規則に基づく届出と、レベル 3 相当の除去計画書の提出が必要。",
        "施工中", "urgent", "仮設工事", "2026年5月度",
        ["法令対応", "安全"], suzuki, date(2026, 5, 7), date(2026, 5, 29),
        [
            (suzuki, "労基署への届出は 5/20 提出済み。除去は 6/2 週で計画。"),
        ],
    ),
    (
        "杭施工記録（オールケーシング）の未提出",
        "5 月施工分の杭 24 本について、施工記録および支持層確認記録が未提出。"
        "出来形管理資料として監理者提出が必要。",
        "検査待ち", "high", "杭・地業工事", "2026年6月度",
        ["品質", "協力会社/大和基礎工業"], sato, date(2026, 6, 1), date(2026, 6, 15),
        [
            (sato, "6/10 に 18 本分を受領。残 6 本（P-19〜P-24）は 6/14 提出予定との回答。"),
        ],
    ),
    (
        "杭頭処理後の鉄筋かぶり不足（P-12）",
        "P-12 の杭頭補強筋のかぶりが設計 60mm に対し 42mm。斫り直しとスペーサー再設置で是正する。",
        "完了", "high", "杭・地業工事", "2026年7月度",
        ["品質", "協力会社/大和基礎工業"], sato, date(2026, 7, 6), date(2026, 7, 13),
        [],
    ),
    (
        "鉄骨建方精度の是正（通り芯 X6-Y3 / 2FR 階梁）",
        "2FR 階梁の建方精度計測で、X6-Y3 の柱倒れが 1/700（管理値 1/1000）を超過。"
        "ワイヤ調整による建入れ直しを実施する。",
        "是正中", "high", "躯体工事", "2026年9月度",
        ["品質", "協力会社/三崎鉄骨建設"], sato, date(2026, 9, 2), date(2026, 9, 9),
        [],
    ),
    (
        "電気配管と空調ダクトの干渉（3F 天井内 X4 通り）",
        "BIM 干渉チェックで、3F 天井内 X4 通りにおいて幹線ラックと空調主ダクトが 120mm 干渉。"
        "設備間で納まり協議を行い、ラックのレベルを FL+3,250 へ変更する方向で調整。",
        "施工中", "medium", "電気設備工事", "2026年9月度",
        ["設計変更", "協力会社/東洋電設工業", "協力会社/中央空調サービス"], tanaka,
        date(2026, 9, 1), date(2026, 9, 18),
        [
            (tanaka, "9/8 の設備調整会議で決着。ラック側を下げる方針で両社合意。施工図を改訂して監理者承認へ回す。"),
        ],
    ),
    (
        "消防同意に伴う防火区画の設計変更（B1 機械室）",
        "消防同意の過程で B1 機械室の防火区画貫通処理の仕様変更を指示された。"
        "工事変更契約の要否を含めて発注者と協議が必要。",
        "施工中", "high", "躯体工事", "2026年8月度",
        ["設計変更", "法令対応", "原価"], yamada, date(2026, 8, 3), date(2026, 9, 30),
        [
            (yamada, "8/20 の定例で発注者へ変更概算 1,240 万円を提示。変更契約は次回定例で協議。"),
        ],
    ),
    (
        "外装 ALC パネルの納期遅延（メーカー生産調整）",
        "外装 ALC パネルについて、メーカーの生産調整により納期が 3 週間遅延する旨の連絡。"
        "外装工事の着手が 2027-02-05 へずれるため、後続の内装工事への波及を確認する。",
        "保留", "high", "外装工事", None,
        ["工程", "原価"], sato, date(2026, 9, 5), date(2026, 10, 15),
        [
            (sato, "代替メーカーの見積を 2 社取得中。工程優先なら単価 +8% を許容するか要判断。"),
        ],
    ),
    (
        "型枠支保工の組立て等作業計画書の再提出",
        "提出された作業計画書に、支保工の設置高さ 4.5m 以上に対する構造計算書の添付が無い。"
        "労働安全衛生規則第 240 条に基づき再提出を指示。",
        "検査待ち", "high", "躯体工事", "2026年8月度",
        ["安全", "法令対応"], suzuki, date(2026, 8, 10), date(2026, 8, 20),
        [],
    ),
    (
        "揚重計画の変更（タワークレーン → 移動式クレーン）",
        "北側敷地の借地交渉が不調となり、タワークレーンの設置位置が確保できない。"
        "500t 吊 移動式クレーンによる建方へ計画変更し、揚重回数と工程を再計算する。",
        "施工中", "urgent", "躯体工事", "2026年8月度",
        ["工程", "原価", "安全"], yamada, date(2026, 8, 1), date(2026, 8, 29),
        [
            (yamada, "揚重回数が 1.4 倍。工程は 12 日延伸、費用は 3,800 万円増の試算。発注者協議へ。"),
        ],
    ),
    (
        "新規入場者教育の未受講者が入場（協力会社 3 次下請）",
        "8/6 の入場者チェックで、新規入場者教育未受講の作業員 2 名を確認。当日は入場を差し止め。"
        "一次下請へ再発防止報告書の提出を求める。",
        "完了", "high", "仮設工事", "2026年8月度",
        ["安全", "協力会社/三崎鉄骨建設"], suzuki, date(2026, 8, 6), date(2026, 8, 13),
        [],
    ),
    (
        "地下 1 階 コンクリート打継処理の確認",
        "B1 耐圧盤と立上りの打継部について、レイタンス除去と打継面の湿潤養生の実施状況を確認する。"
        "写真台帳への記録も併せて指示。",
        "完了", "medium", "躯体工事", "2026年6月度",
        ["品質"], sato, date(2026, 6, 15), date(2026, 6, 22),
        [],
    ),
    (
        "山留支保工の切梁架設完了検査",
        "1 段目切梁の架設完了に伴う社内検査。ジャッキの設置状況、火打ちの取合い、腹起しの隙間を確認する。",
        "完了", "medium", "土工事・山留工事", "2026年6月度",
        ["品質", "安全"], sato, date(2026, 6, 8), date(2026, 6, 12),
        [],
    ),
    (
        "根切り底の地耐力確認（平板載荷試験）",
        "設計 GL-9.5m の根切り底について、平板載荷試験により支持地盤の地耐力を確認する。"
        "設計値 300kN/m2 に対する確認が必要。",
        "完了", "high", "土工事・山留工事", "2026年7月度",
        ["品質"], sato, date(2026, 7, 13), date(2026, 7, 21),
        [],
    ),
    (
        "残土処分先の変更に伴う建設リサイクル法の届出変更",
        "当初予定の残土処分場が受入停止となり、処分先を変更。搬出計画と届出内容の変更手続きを行う。",
        "施工中", "medium", "土工事・山留工事", "2026年7月度",
        ["法令対応", "原価"], takahashi, date(2026, 7, 1), date(2026, 7, 31),
        [],
    ),
    (
        "週間工程会議 議事録の展開（第 18 回）",
        "8/10 開催の週間工程会議の議事録を協力各社へ展開する。次週の重点は躯体 2F 立上り配筋検査。",
        "完了", "low", "仮設工事", "2026年8月度",
        ["工程"], takahashi, date(2026, 8, 10), date(2026, 8, 12),
        [],
    ),
    (
        "月次出来高査定資料の作成（2026 年 7 月分）",
        "7 月末時点の出来高を集計し、発注者への出来高請求資料を作成する。累計出来高率 22.4% の見込み。",
        "完了", "medium", "仮設工事", "2026年8月度",
        ["原価"], takahashi, date(2026, 8, 1), date(2026, 8, 7),
        [],
    ),
    (
        "月次出来高査定資料の作成（2026 年 8 月分）",
        "8 月末時点の出来高を集計し、発注者への出来高請求資料を作成する。",
        "未着手", "medium", "仮設工事", "2026年9月度",
        ["原価"], takahashi, date(2026, 9, 1), date(2026, 9, 7),
        [],
    ),
    (
        "北側マンションへの工程説明会の開催",
        "躯体工事の本格化に先立ち、北側マンション管理組合向けに工程説明会を開催する。"
        "騒音・振動の想定値と作業時間帯を説明する。",
        "未着手", "medium", "仮設工事", "2026年9月度",
        ["近隣対応"], yamada, date(2026, 9, 10), date(2026, 9, 25),
        [],
    ),
    (
        "仮囲い破損の補修（南側 W3 パネル）",
        "台風接近時の強風により南側仮囲い W3 パネルが変形。歩行者への影響があるため早急に補修する。",
        "完了", "high", "仮設工事", "2026年9月度",
        ["安全", "近隣対応"], suzuki, date(2026, 9, 3), date(2026, 9, 5),
        [],
    ),
    (
        "受電計画の確認（本設受電時期の前倒し）",
        "内装工事の空調試運転を前倒しするため、本設受電時期を 2027-05 から 2027-04 へ変更できるか確認する。"
        "電力会社との協議が必要。",
        "未着手", "medium", "電気設備工事", None,
        ["工程", "協力会社/東洋電設工業"], tanaka, date(2026, 10, 1), date(2026, 11, 30),
        [],
    ),
    (
        "スリーブ位置図の承認遅れ（2F〜4F 設備）",
        "2F〜4F の設備スリーブ位置図が監理者未承認のまま。躯体配筋に着手できないため工程クリティカル。",
        "施工中", "urgent", "空調・衛生設備工事", "2026年9月度",
        ["工程", "設計変更", "協力会社/中央空調サービス"], tanaka, date(2026, 9, 1), date(2026, 9, 12),
        [
            (tanaka, "9/9 に監理者から朱書き返却。9/11 再提出予定。配筋着手は 9/16 で調整。"),
        ],
    ),
    (
        "内装什器の仕様確定待ち（研究室ゾーン）",
        "研究室ゾーンの実験台・ドラフトチャンバーの仕様が発注者側で未確定。"
        "内装施工図の作成に着手できない。",
        "保留", "medium", "内装工事", None,
        ["設計変更", "工程", "協力会社/光和内装"], sato, date(2026, 9, 1), date(2026, 12, 25),
        [],
    ),
    (
        "外構植栽の樹種変更（自治体の緑化基準）",
        "川崎市の緑化基準に対し、当初計画の樹種構成では緑化面積が不足。中高木の本数を見直す。",
        "未着手", "low", "外構工事", None,
        ["設計変更", "法令対応", "協力会社/新和外構"], sato, date(2027, 1, 15), date(2027, 3, 31),
        [],
    ),
    (
        "熱中症予防対策の実施（WBGT 計の設置）",
        "7〜9 月の作業に向け、各作業階に WBGT 計を設置し、基準値超過時の作業中断ルールを周知する。",
        "完了", "high", "仮設工事", "2026年6月度",
        ["安全"], suzuki, date(2026, 6, 20), date(2026, 6, 30),
        [],
    ),
    (
        "KY 活動記録の様式統一（協力会社間で不統一）",
        "協力会社ごとに KY 活動記録の様式が異なり、安全書類の一元管理ができていない。"
        "共通様式を定めて 9 月から運用する。",
        "施工中", "medium", "仮設工事", "2026年8月度",
        ["安全"], suzuki, date(2026, 8, 18), date(2026, 8, 31),
        [],
    ),
    (
        "施工計画書の改訂（第 3 回 / 揚重計画変更反映）",
        "揚重計画の変更を受け、総合施工計画書を改訂して監理者へ再提出する。",
        "検査待ち", "high", "仮設工事", "2026年9月度",
        ["工程", "法令対応"], yamada, date(2026, 9, 1), date(2026, 9, 20),
        [],
    ),
    (
        "アンカーボルトの位置ずれ（X3-Y5 柱脚）",
        "X3-Y5 の柱脚アンカーボルトが設計位置から 18mm ずれ。ベースプレートの孔径内で吸収可能か構造設計者へ確認する。",
        "是正中", "high", "躯体工事", "2026年9月度",
        ["品質", "協力会社/三崎鉄骨建設"], sato, date(2026, 9, 4), date(2026, 9, 16),
        [],
    ),
    (
        "現場事務所の増設（協力会社詰所の不足）",
        "躯体工事の本格化で入場者数が 120 名/日に増加する見込み。協力会社詰所と休憩所が不足する。",
        "未着手", "low", "仮設工事", "2026年9月度",
        ["原価", "安全"], takahashi, date(2026, 9, 15), date(2026, 10, 31),
        [],
    ),
]

created_count = 0
for (
    name,
    body,
    state_name,
    priority,
    module_name,
    cycle_name,
    label_names,
    assignee,
    start_date,
    target_date,
    comments,
) in ISSUES:
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
            "created_by": assignee,
        },
    )
    if not created:
        continue
    created_count += 1

    IssueAssignee.objects.get_or_create(
        issue=issue, assignee=assignee, project=project, workspace=workspace
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
    for actor, text in comments:
        IssueComment.objects.get_or_create(
            issue=issue,
            comment_html=f"<p>{text}</p>",
            project=project,
            workspace=workspace,
            defaults={"actor": actor, "created_by": actor},
        )

print("=" * 60)
print(f"workspace   : {workspace.name} (/{workspace.slug})")
print(f"project     : {project.name} [{project.identifier}]")
print(f"members     : {ProjectMember.objects.filter(project=project).count()}")
print(f"states      : {State.objects.filter(project=project).count()}")
print(f"labels      : {Label.objects.filter(project=project).count()}")
print(f"modules     : {Module.objects.filter(project=project).count()}")
print(f"cycles      : {Cycle.objects.filter(project=project).count()}")
print(f"work items  : {Issue.objects.filter(project=project).count()} (今回作成 {created_count})")
print(f"comments    : {IssueComment.objects.filter(project=project).count()}")
print("=" * 60)
