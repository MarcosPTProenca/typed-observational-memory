---
description: "Rust API development standards and architecture"
globs: "apps/api/**/*"
alwaysApply: false
---
---
description: Standards and best practices for the Rust API (Axum, sqlx, Lambda)
globs: apps/api/**/*
---
# Rust API Development Rules

あなたは高信頼なRust製APIサーバーを開発するエキスパートエンジニアです。以下のアーキテクチャ、設計指針、およびコーディング規約を厳守してください。

## 1. アーキテクチャと依存関係
以下のレイヤードアーキテクチャの方向性を遵守し、レイヤーを飛び越えた依存を禁止します。
- **handlers**: `axum`のルートハンドラー。リクエストのバリデーションとレスポンスへの変換のみを担当。ビジネスロジックは書かない。
- **services**: ビジネスロジックの核。`repository`を使用してデータ操作を行う。
- **repository**: `sqlx`を使用したDBアクセスに特化。
- **models**: データの構造体定義。`typeshare`属性を付与してTypeScript型生成を考慮する。

## 2. エラーハンドリング
- **内部エラー**: `anyhow` を使用してコンテキストを保持し、エラーを伝播させます。
- **APIレスポンスエラー**: `src/error.rs` で定義された `AppError`（または `IntoResponse` を実装した型）を使用し、適切なHTTPステータスコードを返却します。
- **unwrap/expectの禁止**: 本番コードでの `unwrap()` は禁止です。適切に `?` 演算子で処理するか、エラーハンドリングを行ってください。

## 3. データベース操作 (sqlx)
- **型安全なクエリ**: 可能な限り `sqlx::query!` などのマクロを使用し、コンパイル時のクエリチェックを有効にします。
- **コネクション管理**: `axum::extract::State` を通じて `PgPool` を注入します。
- **命名規則**: DBカラム名は `snake_case` とし、Rust側で `#[derive(sqlx::FromRow)]` を使用してマッピングします。

## 4. 非同期処理とパフォーマンス
- **Tokio**: 非同期処理は `tokio` ランタイムを前提とします。ブロッキングな処理を行う場合は `spawn_blocking` を使用してください。
- **AppState**: 共有状態は `Arc` を含む `AppState` 構造体を `State` エクストラクターで共有します。

## 5. フロントエンドとの連携 (typeshare)
- **型共有**: フロントエンド（`apps/web`）と共有する構造体やEnumには必ず `#[typeshare]` 属性を付与してください。
- **生成コマンド**: 構造体を変更した際は、`typeshare` コマンドで型定義を更新することを提案してください。

## 6. コーディング規約
- **コメント**: 複雑なロジックやドメイン知識（特にx402決済関連）には詳細なコメントを残してください。
- **テスト**: `tests/` ディレクトリに統合テスト、各モジュール内に `mod tests` でユニットテストを記述してください。
- **ロギング**: `println!` ではなく `tracing` クレート（`info!`, `error!`, `instrument` 等）を使用してください。

## 7. 実装時の思考プロセス
1. 修正が必要な場合、まずどのレイヤー（Handler/Service/Repo）に責任があるか特定する。
2. DB変更を伴う場合は、`packages/database/prisma`（またはsqlx migration）との整合性を確認する。
3. 実装後、`cargo check` や `cargo clippy` で静的解析を通すことを確認する。