# =========================
# Config
# =========================
PYTHON      := python
BUILD_DIR   := build
VENDOR_DIR  := $(BUILD_DIR)/vendor
SIMCORE_PKG := simcore

DEPS := simpy networkx nuitka

# =========================
# Phony targets
# =========================
.PHONY: all build simcore deps run clean

all: build

# =========================
# Build everything
# =========================
build: simcore deps
	@echo "Build finished."

# =========================
# Build simcore with Nuitka
# =========================
simcore:
	@echo ">>> Building simcore with Nuitka"
	$(PYTHON) -m nuitka \
		--module $(SIMCORE_PKG) \
		--follow-import-to=$(SIMCORE_PKG) \
		--output-dir=$(BUILD_DIR)

# =========================
# Vendor dependencies
# =========================
deps:
	@echo ">>> Vendoring dependencies: $(DEPS)"
	mkdir -p $(VENDOR_DIR)
	pip install --upgrade --target $(VENDOR_DIR) $(DEPS)

# =========================
# Run example with built core
# =========================
run:
	PYTHONPATH=$(BUILD_DIR):$(VENDOR_DIR) $(PYTHON) example_run.py

# =========================
# Clean
# =========================
clean:
	@echo ">>> Cleaning build artifacts"
	rm -rf $(BUILD_DIR)
	rm -rf $(SIMCORE_PKG)/*.so
	rm -rf $(SIMCORE_PKG)/__pycache__