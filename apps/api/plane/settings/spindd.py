# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# spin-dd fork addition (2026-08-10): this file does not exist upstream.
# It layers fork-specific settings on top of the upstream production settings so
# that plane/settings/common.py stays untouched (CONTRIBUTING.spindd.md §3).
#
# Activated by setting the environment variable:
#     DJANGO_SETTINGS_MODULE=plane.settings.spindd
#
# manage.py / wsgi.py / asgi.py / celery.py all use os.environ.setdefault(), so an
# environment variable that is already present wins over "plane.settings.production".

"""spin-dd fork settings for the Japanese construction use case."""

import os

from .production import *  # noqa

# ---------------------------------------------------------------------------
# 独自 Django アプリの登録
# ---------------------------------------------------------------------------
# INSTALLED_APPS と ROOT_URLCONF はどちらも設定値なので、ここで差し替えれば
# plane/settings/common.py も plane/urls.py も改変せずに機能を追加できる。
# spindd_ext は自前の migrations を持つため、plane.db の連番衝突も起きない。
# アプリを plane パッケージの内側に置いているのは、apps/api/Dockerfile.api が
# `COPY plane plane/` しかしないため。plane の外に置くとイメージに入らず、
# この設定を有効にした本番イメージが ModuleNotFoundError で起動不能になる。
INSTALLED_APPS = (*INSTALLED_APPS, "plane.spindd_ext")  # noqa: F405
ROOT_URLCONF = "plane.spindd_ext.urls"

# ---------------------------------------------------------------------------
# 添付ファイル: 現場写真と図面を通せる MIME を追加する
# ---------------------------------------------------------------------------
# upstream の ATTACHMENT_MIME_TYPES は許可リスト方式（common.py:457）。
# 建設現場で日常的に発生する以下の形式が漏れているため足す。
CONSTRUCTION_MIME_TYPES = [
    # iPhone のカメラは既定で HEIC で保存する。これが無いと現場担当者が
    # 撮った写真をそのまま添付できず、全端末を「互換性優先」に変える運用が要る。
    "image/heic",
    "image/heif",
    "image/heic-sequence",
    "image/heif-sequence",
    # CAD 図面。ブラウザは application/octet-stream を送ることが多いが、
    # 明示的な MIME で来た場合にも通るようにしておく。
    "image/vnd.dwg",
    "application/acad",
    "application/x-acad",
    "application/dxf",
    "image/vnd.dxf",
    # 電子納品・官公庁提出で使われる形式
    "application/vnd.ms-xpsdocument",
    "application/xps",
]

ATTACHMENT_MIME_TYPES = [*ATTACHMENT_MIME_TYPES, *CONSTRUCTION_MIME_TYPES]  # noqa: F405

# ---------------------------------------------------------------------------
# POST body の許容メモリを FILE_SIZE_LIMIT から切り離す
# ---------------------------------------------------------------------------
# upstream は DATA_UPLOAD_MAX_MEMORY_SIZE を FILE_SIZE_LIMIT から導出している
# （common.py:371）。しかし添付ファイルは presigned POST で S3/MinIO へ直接
# 送られ Django を経由しない（app/views/issue/attachment.py:132-136）ため、
# 添付上限を 50MB に上げるためだけに Django が 50MB の POST body を
# メモリに載せられるようにする必要はない。
#
# ここを分離しておかないと、添付上限を上げるほど通常の POST の
# メモリ消費上限も一緒に上がる。
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get("DATA_UPLOAD_MAX_MEMORY_SIZE", 5242880))
