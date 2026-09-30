# PySamurai - Project Guide

## Overview

ruby-warrior (ryanb) ベースのPython対応Web版プログラミング学習ゲーム。
サムライ猫キャラがタワーを登る。ユーザーはPythonでプレイヤーコードを記述し、
Skulptで内部的にJSに変換してブラウザ上で動作。サーバーサイド不要。

## Current Phase

**Phase 2**: Python→JS変換層 (Skulpt統合) (次)

## Tech Stack

- **Language**: TypeScript
- **Build**: Vite
- **UI**: React
- **Python実行**: Skulpt (Python→JS変換)
- **Code Editor**: CodeMirror 6 (<REDACTED_USER>/react-codemirror)
- **Game Rendering**: HTML Canvas + Sprite
- **Styling**: Tailwind CSS
- **i18n**: react-i18next
- **Testing**: Vitest

## Architecture

```
src/
├── engine/          # ゲームエンジン (pure TS, フレームワーク非依存)
│   ├── abilities/   # walk, attack, feel, look, shoot, rescue, bind, etc. (18種)
│   ├── units/       # samurai, sludge, thick-sludge, archer, wizard, captive, golem
│   ├── tower.ts     # Tower - レベル群の管理
│   ├── profile.ts   # Profile - プレイヤー進行状態 (保存/読込対応)
│   ├── game.ts      # Game - ゲームフロー (Normal/Epic Mode)
│   └── level.ts     # Level - 1レベルの実行管理
├── levels/          # レベルデータ
│   ├── beginner/    # Beginner タワー (9レベル)
│   ├── intermediate/ # Intermediate タワー (9レベル)
│   └── index.ts     # Tower インスタンスの export
├── python/          # Skulpt統合 & Python↔JS API bridge
├── renderer/        # Canvas描画 & スプライトアニメーション
├── ui/              # React UI (screens/ components/)
└── utils/           # 共通ユーティリティ
```

## Code Conventions

- ゲームエンジン (`src/engine/`) はReactに依存しない純粋TSで実装
- ファイル名: kebab-case (`thick-sludge.ts`)
- Rubyの `!` メソッド → アクション (1ターン1回), `?` メソッド → `is_` prefix
- Python API: snake_case (`samurai.walk()`, `space.is_empty()`)
- レベルデータ: TypeScriptオブジェクトで定義

## Phase Roadmap

1. ~~**Phase 1-1**: プロジェクトセットアップ & コアデータ構造~~ (完了 - 104テスト Pass)
2. ~~**Phase 1-2**: ターンシステム & 最小プレイセット~~ (完了 - 161テスト Pass)
3. ~~**Phase 1-3**: Beginnerタワー完成 (全9レベル)~~ (完了 - 211テスト Pass)
4. ~~**Phase 1-4**: Intermediateタワー & ゲーム管理 (Epic Mode含む)~~ (完了 - 301テスト Pass)
5. **Phase 2**: Python→JS変換層 (Skulpt統合)
6. **Phase 3**: 基本Web UI & コードエディタ (React + CodeMirror)
7. **Phase 4**: ゲームレンダラー & アニメーション (Canvas + Sprite)
8. **Phase 5**: UI洗練 & i18n & ゲーム体験完成

詳細は `PLAN.md` を参照。

## Agent Rules

エージェント共通ルールは `AGENTS.md` を参照すること。

## Reference Files (Original)

- ゲームエンジン: `original/ryanb-ruby-warrior/lib/ruby_warrior/`
- レベルデータ: `original/ryanb-ruby-warrior/towers/`
- Web実装参考: `original/palkan-ruby-warrior/web/src/`