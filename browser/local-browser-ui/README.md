# MVD Console

Minimum Viable Dataspace の管理用 PoC Console です。

## 起動

```bash
docker compose up --build
```

- Console: http://localhost:7651
- Console DB: container internal only (host port is not published)

## 前提

`CONNECTOR_URL` はデフォルトで `http://host.docker.internal:7550` です。
Connector API がホスト側で起動している前提です。

## 注意

PoC用です。秘密鍵は `mvd-console-db` の PostgreSQL に平文保存しています。本番用途では暗号化やKMS利用が必要です。

## PKRユーザ削除順

PKRユーザ削除時は、関連項目を以下の順番で削除します。

1. Federated Catalog
2. AuthZ
3. Public Key Registry
4. Local Key

`Local Keys` 画面では PoC 検証のため秘密鍵も表示します。本番用途では秘密鍵を画面表示せず、暗号化保存やKMS利用を検討してください。

AuthZ Operation では、ローカル鍵登録済みユーザを Current User として選択し、その秘密鍵で AuthZ 操作要求に署名します。


Federated Catalog の Update は、既存の Owner を維持したまま、Description / Endpoint / Resource Path のカタログ情報のみを更新します。Console は Connector 経由で `/fc/upd` を呼び出し、既存 Owner のローカル秘密鍵で `signature_old` と `signature_new` を生成します。

UIでは Operation と Result の高さを揃え、AuthZ では Operation / Result の下に Entries を表示します。PKR では Local Keys と Public Key Registry を同じ幅で表示し、Local Keys では PoC 検証用に秘密鍵を表示します。

## ポート設定

Console は `http://localhost:7651` で公開します。
コンテナ内部の FastAPI もホスト側公開ポートも `7651` に統一します。docker compose では `7651:7651` として公開します。
秘密鍵保存用 DB はホスト側に公開せず、コンテナ内部通信のみで利用します。
