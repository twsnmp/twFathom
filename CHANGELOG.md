# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-07-01

### Added
- **窓開閉センサー（contact）対応**: Zigbee等の窓開閉センサーデータ（contact/battery/device_temperature/linkquality等）の収集・グラフ描画・KPIカード表示・異常検知に対応。`contact=true`（閉）を1、`contact=false`（開）を0として可視化。

### Fixed
- **ダッシュボードのスレッドセーフ修正**: `auto_arrange_dashboards`においてウィンドウサイズをDBステートから取得するよう変更し、スレッド競合問題を解消。
- **タイマーのスレッドリーク・ハング修正**: `setInterval`を再帰的`setTimeout`＋排他フラグに置き換え、スレッドリークおよびハングアップを防止。

## [0.2.0] - 2026-06-22

### Added
- **バージョンおよびGitコミットハッシュの表示**: 起動時のメインUI上にバージョン番号とGitコミットハッシュを表示する機能を追加。
- **SQLiteデータベースのロック競合防止**: WAL（Write-Ahead Logging）モードを有効化し、データベース接続時のタイムアウト設定を延長することで、ロック競合エラー（database is locked）を防止。
- **Linuxダッシュボードのドラッグ・レイアウトのネイティブ化および描画バグ修正**: Linux環境でJSによるダッシュボードドラッグ移動機能のネイティブGTK化（easy_drag）を適用し、x11バックエンドでの黒画面バグ修正、Waylandでのx11バックエンド設定（GDK_BACKEND=x11）、スレッドセーフなウィンドウ自動整列（Auto-Arrange）を実装。

### Fixed
- **JavaScriptにおけるエスケープ処理の修正**: `main.js`における文字列エスケープ処理の不備（CodeQL警告）を修正。
- **macOSパッケージ起動エラーの解決**: macOS向けのbuild/release-macタスク実行時に発生するファイル権限問題を修正し、起動時のPermissionErrorを解消。
- **Linuxダッシュボード起動競合の解消**: pywebviewreadyイベントの競合回避、およびローカルストレージのフォールバック処理追加によるダッシュボード読み込みエラーの解決。

## [0.1.0] - 2026-06-12

### Added
- **時系列異常検知機能 (Hotelling's T^2法)**: 標準ライブラリのみで動作するホテリングのT^2法を実装。各種データの異常度を自動算出し、ダッシュボード上にステータス（正常/注意/異常）および異常要因となる主要カラムを日本語で表示。
- **システムメトリクス対応**: CPU/メモリ/ディスク使用率、システム負荷/プロセス数、およびネットワーク送受信速度の3パターンのシステムメトリクスデータの収集・グラフ描画に対応。
- **ダッシュボード画面の自動整列 (Auto-Arrange)**: 起動した複数のダッシュボードサブウィンドウを画面上に格子状（タイル状）に自動で整列するレイアウト機能を追加。
- **ダッシュボードの状態保存と復元**: ウィンドウ位置・サイズ（枠なしウィンドウ状態含む）、チャートの表示範囲、およびグラフの右軸に割り当てるメトリクス選択状態を永続化し、次回起動時に自動復元する機能を追加。
- **表示・グラフの改善**: チャートの表示範囲セレクターの最適化、EChartsの描画バグ修正、およびレンダリングパフォーマンスの向上。

## [0.0.2] - 2026-05-25

### Added
- **Linux (AppImage) Support**: Transitioned the Linux package format to portable AppImage to completely resolve python shared library missing errors (`libpython3.10.so.1.0`).
- **Bundled GTK Dependencies**: Bundled `pygobject` and `pycairo` in the Linux package to fix `pywebview` runtime crashes.
- **CI/CD Stabilization**: Rewrote GitHub Actions pipelines, separating Windows and Linux builds into independent jobs, fixing Windows output path resolution (`dist/`), and incorporating `pwsh` for case-insensitive renaming.

### Fixed
- **Windows DevTools Suppression**: Disabled debug mode on `pywebview` to prevent Chromium Developer Tools from opening automatically on sub-windows.

## [0.0.1] - 2026-05-23

### Added
- Initial release of twFathom.
- AI-driven data exploration interfaces.
- Custom graphing priority order for environment metrics.
- Signed installer packaging configuration for macOS, Windows, and Linux.

