# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
# Build the FRT card-entry wrapper. Inside the SDK environment:
#   make -C /opt/mun-devkit/engines/godot3/frt-boot OUT=/work/build/frt-boot

CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra
OUT ?= frt-boot

.PHONY: all clean

all: $(OUT)

$(OUT): frt_boot.c
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f $(OUT)
