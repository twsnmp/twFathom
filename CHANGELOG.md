# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-05-25

### Added
- **Linux (AppImage) Support**: Transitioned the Linux package format to portable AppImage to completely resolve python shared library missing errors (`libpython3.10.so.1.0`).
- **Bundled GTK Dependencies**: Bundled `pygobject` and `pycairo` in the Linux package to fix `pywebview` runtime crashes.
- **CI/CD Stabilization**: Rewrote GitHub Actions pipelines, separating Windows and Linux builds into independent jobs, fixing Windows output path resolution (`dist/`), and incorporating `pwsh` for case-insensitive renaming.

### Fixed
- **Windows DevTools Suppression**: Disabled debug mode on `pywebview` to prevent Chromium Developer Tools from opening automatically on sub-windows.

## [0.1.0] - 2026-05-23

### Added
- Initial release of twFathom.
- AI-driven data exploration interfaces.
- Custom graphing priority order for environment metrics.
- Signed installer packaging configuration for macOS, Windows, and Linux.
