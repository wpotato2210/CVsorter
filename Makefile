.PHONY: ci-smoke test

# CI smoke test to catch missing native shared libraries (e.g. libGL.so.1)
# in minimal container environments before runtime startup.
ci-smoke:
	python -m pip install -r requirements.txt
	python scripts/smoke_imports.py

test:
	gcc -std=c11 -Wall -Wextra -Werror \
		-Ifirmware/mcu/include -Ifirmware/mcu/config \
		firmware/mcu/src/encoder.c \
		firmware/mcu/src/queue.c \
		firmware/mcu/src/safety.c \
		firmware/mcu/src/scheduler.c \
		tests/test_firmware_core_modules.c \
		-o /tmp/test_firmware_core_modules
	/tmp/test_firmware_core_modules
