# Map Reconstruction packaging size audit

Date: 2026-09-12  
Scope: Windows PyInstaller on Python 3.12, standalone `MapReconstruction` portable build.

## Result

The issue was packaging over-collection, not an unavoidable Python GUI baseline.

| artifact | before | after | change |
|---|---:|---:|---:|
| extracted `dist/MapReconstruction` | 740,462,949 bytes / 706.16 MiB | 129,265,489 bytes / 123.28 MiB | -82.5% |
| portable ZIP | 277,356,207 bytes / 264.51 MiB | 52,679,225 bytes / 50.24 MiB | -81.0% |

The final extracted package is below the 300 MiB escalation threshold. No final file is above 20 MiB; the two largest are the retained OpenGL fallback (19.68 MiB) and numpy OpenBLAS (19.64 MiB). No WebEngine, QML/Quick, Qt translations, Qt image-format packs, or Qt optional module is present in the final package.

## Root cause and remediation

The old spec called `collect_all()` for PySide6, pyqtgraph, and numpy, then repeated the result in `binaries`, `datas`, and `hiddenimports`. This pulled in the complete PySide6 wheel, including QtWebEngine and its 72 MiB devtools resource, despite no source import of WebEngine. The pyqtgraph PyInstaller hook also collected all pyqtgraph submodules and the default Qt hooks collected every QtGui plugin and locale pack.

The spec now declares only the three application bindings (`QtCore`, `QtGui`, `QtWidgets`), excludes unused optional PySide6 modules, and uses narrow local hooks to:

- remove all Qt locale/translation data;
- keep only `qwindows.dll` from Qt platform and image/plugin families;
- remove optional style, network, virtual-keyboard, SVG, PDF, and QML/Quick plugin chains;
- retain QtOpenGL/QtOpenGLWidgets because pyqtgraph imports their compatibility path at package import time;
- retain the Windows OpenGL software fallback and numpy's OpenBLAS because they are runtime dependencies of the retained Qt/numpy stack;
- exclude host-resolved ICU DLLs: this Qt wheel uses the Windows ICU API, while an unrelated host ICU (for example Poppler ICU 78) causes `QtCore` to fail with `ERROR_PROC_NOT_FOUND` when frozen.

No source feature code was changed. CSV/project IO remains stdlib/numpy-based; no pandas, scipy, sklearn, Pillow, OpenCV, numba, or matplotlib runtime is imported or packaged.

## Baseline largest files

The following is the top 30 from the pre-change extracted package. Sizes are MiB.

| rank | file | size | classification | remediation |
|---:|---|---:|---|---|
| 1 | `PySide6/Qt6WebEngineCore.dll` | 194.02 | unused QtWebEngine | removed |
| 2 | `PySide6/resources/qtwebengine_devtools_resources.debug.pak` | 72.33 | unused WebEngine devtools | removed |
| 3 | `PySide6/opengl32sw.dll` | 19.68 | Qt Windows rendering fallback | retained |
| 4 | `numpy.libs/libscipy_openblas64_*.dll` | 19.64 | numpy numerical runtime | retained |
| 5 | `PySide6/avcodec-61.dll` | 13.41 | unused QtMultimedia chain | removed |
| 6 | `PySide6/resources/qtwebengine_devtools_resources.pak` | 11.07 | unused WebEngine devtools | removed |
| 7 | `PySide6/resources/icudtl.dat` | 9.98 | WebEngine ICU data | removed |
| 8 | `PySide6/Qt6Core.dll` | 9.88 | QtCore runtime | retained |
| 9 | `PySide6/Qt6Gui.dll` | 9.10 | QtGui runtime | retained |
| 10 | `MapReconstruction.exe` | 8.66 | application and frozen Python code | retained |
| 11 | `PySide6/QtOpenGL.pyd` | 8.28 | pyqtgraph import-time compatibility dependency | retained |
| 12 | `python312.dll` | 6.62 | standalone embedded Python runtime | retained |
| 13 | `PySide6/Qt6Quick.dll` | 6.26 | unused QtQuick/QML | removed |
| 14 | `PySide6/Qt6Widgets.dll` | 6.20 | QtWidgets runtime | retained |
| 15 | `PySide6/Qt6Qml.dll` | 5.09 | unused QtQuick/QML chain | removed |
| 16 | `PySide6/Qt6Designer.dll` | 4.99 | unused QtDesigner | removed |
| 17 | `libcrypto-3.dll` | 4.99 | unused QtNetwork/OpenSSL chain | removed from Qt chain; Python SSL support remains where frozen |
| 18 | `PySide6/QtWidgets.pyd` | 4.63 | QtWidgets binding | retained |
| 19 | `PySide6/Qt6Pdf.dll` | 4.41 | unused QtPdf/image plugin chain | removed |
| 20 | `PySide6/Qt6Quick3DRuntimeRender.dll` | 4.18 | unused QtQuick3D | removed |
| 21 | `PySide6/Qt6ShaderTools.dll` | 4.18 | unused QtQuick shader chain | removed |
| 22 | `PySide6/QtGui.pyd` | 3.72 | QtGui binding | retained |
| 23 | `numpy/_core/_multiarray_umath*.pyd` | 3.68 | numpy core | retained |
| 24 | `PySide6/qmlls.exe` | 3.56 | QML development tool | removed |
| 25 | `PySide6/QtCore.pyd` | 3.19 | QtCore binding | retained |
| 26 | `PySide6/qml/...FluentWinUI3...dll` | 3.19 | unused QML style | removed |
| 27 | `PySide6/Qt6QuickControls2Imagine.dll` | 2.96 | unused QtQuick Controls | removed |
| 28 | `PySide6/Qt6QuickDialogs2QuickImpl.dll` | 2.63 | unused QtQuick dialogs | removed |
| 29 | `PySide6/avformat-61.dll` | 2.53 | unused QtMultimedia chain | removed |
| 30 | `PySide6/Qt63DRender.dll` | 2.46 | unused Qt3D | removed |

## Final top 20 files

| rank | file | size | why it remains |
|---:|---|---:|---|
| 1 | `PySide6/opengl32sw.dll` | 19.68 MiB | Windows software OpenGL fallback used by Qt/pyqtgraph |
| 2 | `numpy.libs/libscipy_openblas64_*.dll` | 19.64 MiB | numpy numerical operations |
| 3 | `PySide6/Qt6Core.dll` | 9.88 MiB | QtCore |
| 4 | `PySide6/Qt6Gui.dll` | 9.10 MiB | QtGui/QImage/QPainter |
| 5 | `PySide6/QtOpenGL.pyd` | 8.28 MiB | pyqtgraph import-time compatibility path |
| 6 | `python312.dll` | 6.62 MiB | standalone runtime |
| 7 | `PySide6/Qt6Widgets.dll` | 6.20 MiB | Qt widgets |
| 8 | `MapReconstruction.exe` | 5.72 MiB | frozen application |
| 9 | `libcrypto-3.dll` | 4.99 MiB | Python SSL/runtime dependency collected by the frozen interpreter |
| 10 | `PySide6/QtWidgets.pyd` | 4.63 MiB | QtWidgets binding |
| 11 | `PySide6/QtGui.pyd` | 3.72 MiB | QtGui binding |
| 12 | `numpy/_core/_multiarray_umath*.pyd` | 3.68 MiB | numpy core |
| 13 | `PySide6/QtCore.pyd` | 3.19 MiB | QtCore binding |
| 14 | `PySide6/Qt6OpenGL.dll` | 1.90 MiB | QtOpenGL binding dependency |
| 15 | `ucrtbase.dll` | 1.30 MiB | Windows C runtime |
| 16 | `base_library.zip` | 1.27 MiB | frozen Python standard library |
| 17 | `unicodedata.pyd` | 1.09 MiB | Python Unicode support |
| 18 | `map_reconstruction/assets/map_reconstruction.png` | 0.99 MiB | application icon |
| 19 | `PySide6/plugins/platforms/qwindows.dll` | 0.95 MiB | required Windows desktop platform |
| 20 | `libssl-3.dll` | 0.76 MiB | Python SSL/runtime dependency |

## Dependency classification

| component | extracted size in final | required? | why included | remediation |
|---|---:|---|---|---|
| numpy + OpenBLAS | 26.25 MiB | yes | reconstruction, rolling quantile, map arrays, CSV conversion | retain; no scipy/numba/MKL |
| PySide6 Core/Gui/Widgets | ~41.5 MiB including Qt DLLs/bindings and qwindows | yes | desktop UI, QImage/QPainter PDF report, widgets | retain |
| QtOpenGL/QtOpenGLWidgets | 10.30 MiB | yes for current pyqtgraph import path | pyqtgraph 0.14 imports OpenGL compatibility classes at module import | retain; revisit only with a deliberate pyqtgraph import redesign |
| pyqtgraph | 1.28 MiB | yes | trace/map plotting | retain; no examples/assets beyond its icon data |
| scipy, pandas, sklearn, Pillow, OpenCV, numba | 0 | no | no source import and no final package files | remain build/dev optional only |
| matplotlib | 0 | no | no source import; only present in the developer build environment | excluded |
| QtWebEngine + PAK/resources | 0 after / ~280 MiB before | no | came from broad PySide6 collection | removed |
| QtQuick/QML/Qt3D/Designer/Multimedia/Pdf | 0 | no | optional module/plugin chains | excluded |
| Qt translations | 0 after / 58.83 MiB before | no | default QtCore hook locale collection | removed |
| Qt image-format/icon/style/touch/network plugins | only `qwindows.dll` remains | no except desktop platform | default QtGui/Widgets hooks collect families, but app has no runtime file-image or touch/network workflow | narrowed to `qwindows.dll` |
| pytest/test assets/examples/docs | 0 | no | development-only | not collected |
| Python/Qt duplication with HappyMeasure | no acquisition runtime present | standalone contract | the companion EXE must run without Python/HappyMeasure installed | A/B is future architecture work; current safe build is strict standalone C |

## Architecture assessment

1. **A — full integration into HappyMeasure:** best long-term ownership and would avoid a second embedded runtime, but requires a deliberate UI/runtime integration project and was not safe to introduce in this size-only change.
2. **B — two entry points sharing one deployed runtime:** possible with a redesigned common deployment root and launcher/versioning contract; the current two portable ZIPs do not share files, so this is not a one-line packaging option.
3. **C — standalone with strict pruning:** selected for this release-hardening pass. It preserves the existing offline companion contract and removes only verified unused dependency families.

## Validation

- clean PyInstaller build: passed with `--clean`, fresh `build`, fresh `dist/MapReconstruction`, and fresh ZIP;
- Map Qt suite: 175 passed;
- packaged EXE launch with a CSV argument: stayed alive and responsive for 8 seconds, then closed by the harness; the earlier `unhandled exception in script` was traced to an incompatible host Poppler ICU DLL being bundled for QtCore and is fixed by excluding those host-resolved ICU names;
- source/integration coverage includes CSV load, Signal Preparation, reconstruction, map display, project/export paths, and PDF report generation;
- final package contains no `QtWebEngine`, `QtQuick`, `QtQml`, `QtPdf`, translations, image-format plugins, host ICU DLLs, test assets, or matplotlib/scipy/pandas/sklearn/Pillow/OpenCV/numba files.
