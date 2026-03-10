# UI設計仕様書（MUI Only / Next.js App Router）
Version: 1.0  
Owner: (あなたの名前/チーム)  
Last Updated: 2025-12-23

---

## 0. 目的
本仕様書は、アプリ全体のUI/UXを **MUIのDesign System（Theme）で統一**し、画面ごとのブレを防ぎつつ、実装・保守・拡張を高速化するためのルールを定義する。

- UIのSingle Source of Truth（唯一の正）は **MUI Theme**
- “画面ごとの差分”は最小にし、再利用可能な形で集約する
- UI更新（デザイン変更・改善）時に **破壊的変更 / 回帰**を防ぐ

---

## 1. 前提・技術スタック
- Frontend: React / Next.js（App Router）
- UI: MUI（@mui/material + Emotion）
- ルーティング: Next.js Route Segment
- グローバルCSS: 原則使わない（必要最小限のみ）

---

## 2. UI設計の基本原則
### 2.1 Single Source of Truth
- **色 / 余白 / タイポ / 角丸 / 影 / ボーダー** は Theme のトークンから参照する
- hex直書きや px直書きの乱用は禁止（例外は後述）

### 2.2 “統一”は2種類ある
- **部品の統一（Button/TextField等の見た目）** → `theme.components` で決める
- **画面構造の統一（PageHeader/FormRow等の組み合わせ）** → `src/ui` に複合コンポーネントを作る

### 2.3 変更容易性
- 「1回だけの見た目」は `sx`
- 「繰り返す見た目」は `theme.components`（variants/overrides） or `src/ui`（複合UI）
- “同じパターンが2回出たら”再利用へ寄せる

---

---

## 4. Theme設計ルール（最重要）
### 4.1 トークン（Design Tokens）
以下をThemeに定義し、アプリ内の参照元を統一する。

- `palette`: primary/secondary/success/warning/error, background, text, divider
- `typography`: h1-h6/body1/body2/caption の用途を固定
- `shape`: borderRadius を固定
- `spacing`: `theme.spacing(n)` を基準にする（`sx={{ p: 2 }}` など）

### 4.2 `theme.components` の使い方
#### defaultProps（標準）
- TextFieldの `size / variant`
- Buttonの `disableElevation / variant`
- Dialogの `maxWidth / fullWidth`
など、アプリ全体の標準をここに寄せる

#### styleOverrides（“素の見た目”の統一）
- 角丸/罫線/ホバー等の微調整
- コンポーネントの基本トーン統一

#### variants（社内用の“型”）
- “同じ用途の見た目”をvariant化し、画面側の` sxコピペ`を禁止する
- 例：PrimaryCTA / Danger / Subtle / ToolbarButton など

> 方針：**部品をラップする（MyButton等）より、ThemeのdefaultProps/variantsで統一**する

---

## 5. `src/ui`（複合UI）設計ルール
### 5.1 何を `src/ui` に作るか
次の条件を満たすものだけ `src/ui` に追加する。

- 2画面以上で再利用される
- “構造（レイアウト）”が統一されると品質が上がる
- MUI単体コンポーネントでは表現しきれない（複数部品の組み合わせ）

例：
- `PageHeader`（タイトル＋右上アクション＋説明）
- `FormRow`（label + field + help + error）
- `EmptyState` / `ErrorState`
- `ConfirmDialog`

### 5.2 逆に作らないもの
- MUIコンポーネントの単純ラッパ（`MyButton`, `MyTextField` など）は原則禁止  
  ※例外：Next.js Link対応など “技術的都合で必須” な薄いラッパのみ許可

---

## 6. 画面実装ルール（MUST/SHOULD）
### 6.1 MUST（必須）
- 画面の余白・並びは `Stack / Box / Grid` + `theme.spacing` で統一
- `sx` は「その場限り」に限定する
- 同一UIパターンの `sxコピペ` を見つけたら variant化 or `src/ui` 化する
- フォームは **label/required/error** の表記位置を統一（FormRow使用推奨）
- 色は `theme.palette.*` 参照のみ

### 6.2 SHOULD（推奨）
- レスポンシブは MUIの breakpoints (`{ xs, sm, md... }`) を用いる
- 空/エラー/ローディング状態は専用コンポーネントで統一（EmptyState等）
- ダイアログ/ドロワーの “操作ボタン配置” を統一（右下：主要、左：キャンセル）

### 6.3 例外（許可）
- `border: 1px` などの “物理ピクセル” は許可
- 外部ライブラリとの衝突回避（限定的なGlobalStyles）は許可
- カレンダーの重い描画領域は例外的に最適化のための独自実装を許可

---

## 7. パフォーマンス方針
- カレンダー等の重いUIは `features/calendar` に隔離し、描画最適化を独立して行う
- 不要な再レンダリングを避ける（メモ化・分割はCalendar領域で優先）
- 画面を跨ぐ共通UI（PageHeader等）は軽量に保つ（状態を持ちすぎない）

---

## 8. アクセシビリティ（最低限のルール）
- Buttonは `aria-label` を必要に応じ付与（アイコンのみボタン等）
- Dialogは title を必ず付与し、閉じる導線を確保する
- キーボード操作（Tab移動）で主要操作が可能であること

---

## 9. UIをアップデートする際の注意点（回帰防止のためのルール）
### 9.1 変更の分類（まず分類する）
1) **トークン変更**（palette/typography/shape/spacing）  
   → 影響範囲が最大。最も慎重に扱う  
2) **コンポーネント標準変更**（theme.components defaultProps/overrides/variants）  
   → 多画面に影響。回帰が起きやすい  
3) **複合UI変更**（src/ui）  
   → 再利用先に影響。画面横断で確認が必要  
4) **画面個別変更**（ページ内sx等）  
   → 影響局所。最小の確認でOK

### 9.2 変更時のMUSTチェックリスト
- 変更の種類（9.1）をPR本文に明記する
- “影響する画面一覧” をPR本文に列挙する（最低3画面は確認する）
- トークン変更 or components変更の場合：
  - 主要画面（一覧/詳細/編集/カレンダー/設定）を目視確認する
  - 代表コンポーネント（Button/TextField/Dialog/Table）を確認する
- “例外的なsx” を増やしていないか確認する（増えていたらvariant化を検討）

### 9.3 禁止事項（UI更新でやりがちな事故）
- 画面ごとに色や余白を “個別調整” して統一感を壊す
- `sx` のコピペで同じ見た目を量産する（後で変更できなくなる）
- 「とりあえずGlobal CSS」で直す（後で衝突する）
- コンポーネント標準を変えたのに、影響画面を確認しない

### 9.4 変更の原則（迷った時の順番）
- 1回だけ → `sx`
- 2回以上同じ → `variants`（単体の見た目）
- 2回以上で構造も同じ → `src/ui`（複合UI）

---

## 10. 新規画面追加の手順（初心者向け）
1) 画面レイアウトは `PageLayout` / `PageHeader` を使う  
2) フォームは `FormRow` を使い、label/error位置を統一する  
3) 状態（Loading/Empty/Error）は既存のStateコンポーネントを使う  
4) `sx` で頑張りすぎない（同じパターンが出たらvariant/uiへ）

---


## 12. カレンダー（0から実装する場合の設計ルール）
- UIの統一（Dialog/フォーム/ボタン/メニュー）はMUIで行う
- 重い描画（Grid/EventLayer）は `features/calendar` で閉じる
- カレンダー領域だけは最適化優先（構造を分けて保守可能にする）

---

## 13. 用語集（初心者向け）
- **Theme**：アプリ全体のデザインの“設計図”（色/文字/余白の基準）
- **variants**：同じ部品（例：Button）の “用途別プリセット見た目”
- **複合UI**：複数の部品を組み合わせた “画面でよく出る塊”（PageHeader等）
- **回帰（Regression）**：変更した覚えがない画面が壊れること