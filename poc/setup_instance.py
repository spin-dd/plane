"""
PoC 用インスタンス初期設定（fork 側で追加した新規ファイル）。

素の状態では Instance.is_setup_done が False のままで、ログインが
`INSTANCE_NOT_CONFIGURED` で弾かれる。通常は admin アプリ（god-mode）から
設定するが、PoC では現場代理人アカウントをインスタンス管理者にして省略する。

実行:
    docker compose --project-name plane-poc --env-file poc/.env \
        -f deployments/cli/community/docker-compose.yml \
        exec -T api python - < poc/setup_instance.py
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plane.settings.production")
django.setup()

from plane.db.models import User  # noqa: E402
from plane.license.models import Instance, InstanceAdmin  # noqa: E402

ADMIN_EMAIL = "yamada@spin-kensetsu.example"

instance = Instance.objects.first()
if instance is None:
    raise SystemExit("Instance が未登録。api コンテナの起動を待ってから再実行すること。")

user = User.objects.get(email=ADMIN_EMAIL)
InstanceAdmin.objects.get_or_create(
    instance=instance, user=user, defaults={"role": 20, "is_verified": True}
)
instance.is_setup_done = True
instance.save()

print(f"instance admin : {user.email}")
print(f"is_setup_done  : {Instance.objects.first().is_setup_done}")
