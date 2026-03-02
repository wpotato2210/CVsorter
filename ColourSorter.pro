TEMPLATE = aux
CONFIG += no_link

PROJECT_ROOT = $$PWD

INCLUDEPATH += \
    $$PROJECT_ROOT/src \
    $$PROJECT_ROOT/gui

DISTFILES += \
    $$files($$PROJECT_ROOT/src/*.py, true) \
    $$files($$PROJECT_ROOT/gui/*.py, true) \
    $$files($$PROJECT_ROOT/configs/*.yaml, true) \
    $$files($$PROJECT_ROOT/configs/*.json, true) \
    $$files($$PROJECT_ROOT/contracts/*.json, true) \
    $$files($$PROJECT_ROOT/protocol/*.json, true)

QMAKE_EXTRA_TARGETS += run_bench_gui run_webcam_poc

run_bench_gui.target = run_bench_gui
run_bench_gui.commands = \
    PYTHONPATH=$$PROJECT_ROOT/src:$$PROJECT_ROOT/gui \
    QT_QPA_PLATFORM=$$(QT_QPA_PLATFORM) \
    python $$PROJECT_ROOT/gui/bench_app/app.py --config $$PROJECT_ROOT/configs/bench_runtime.yaml

run_webcam_poc.target = run_webcam_poc
run_webcam_poc.commands = \
    PYTHONPATH=$$PROJECT_ROOT/src:$$PROJECT_ROOT/gui \
    QT_QPA_PLATFORM=$$(QT_QPA_PLATFORM) \
    python $$PROJECT_ROOT/gui/bench_app/controller_integration_stub.py
