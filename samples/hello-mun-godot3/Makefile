# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: MIT-0
# Prepare the Godot 3 probe for mdk: compile frt-boot and ensure content/.

MUN_DEVKIT ?= ../..
OUT_DIR ?= build
CONTENT ?= $(OUT_DIR)/content

.PHONY: all content-dir clean

all: $(OUT_DIR)/frt-boot content-dir
	@if [ ! -f "$(CONTENT)/game.pck" ]; then \
	  echo "NOTE: put your exported game.pck at $(CONTENT)/game.pck"; \
	fi
	@if [ ! -x "$(CONTENT)/frt" ]; then \
	  echo "NOTE: put an aarch64 FRT 3.5.x binary at $(CONTENT)/frt"; \
	fi

$(OUT_DIR)/frt-boot: $(MUN_DEVKIT)/engines/godot3/frt-boot/frt_boot.c
	mkdir -p $(OUT_DIR)
	$(MAKE) -C $(MUN_DEVKIT)/engines/godot3/frt-boot OUT=$(abspath $(OUT_DIR)/frt-boot)

content-dir:
	mkdir -p $(CONTENT)

clean:
	rm -rf $(OUT_DIR)
