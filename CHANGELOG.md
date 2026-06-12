# Changelog

All notable changes to this project will be documented in this file.

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

