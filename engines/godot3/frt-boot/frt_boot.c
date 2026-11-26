/* Copyright 2026 Iván Moreno Mendoza
 * SPDX-License-Identifier: Apache-2.0
 *
 * Card entry for Godot 3.5 / FRT games: MUN starts the entry with no
 * arguments. This program finds FRT and game.pck under MUN_CONTENT_DIR and
 * execs FRT with a fixed argv (main pack + GLES2).
 *
 * Layout expected on the card / in sim:
 *
 *   entry ELF  = this program (build/frt-boot)
 *   content/   = MUN_CONTENT_DIR, containing:
 *     game.pck           required
 *     frt                optional name for the FRT binary
 *     bin/frt            alternate path
 *     frt_aarch64        alternate path
 *
 * Override the FRT file with MUN_FRT_PATH (absolute) when testing.
 * Override the pack name with MUN_FRT_PACK (default game.pck).
 * Extra video driver: MUN_FRT_VIDEO_DRIVER (default GLES2).
 */
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int usable_exec(const char *path)
{
	return path && path[0] && access(path, X_OK) == 0;
}

static void join2(char *out, size_t n, const char *a, const char *b)
{
	snprintf(out, n, "%s/%s", a, b);
}

int main(void)
{
	const char *content = getenv("MUN_CONTENT_DIR");
	const char *override_frt = getenv("MUN_FRT_PATH");
	const char *pack_name = getenv("MUN_FRT_PACK");
	const char *video = getenv("MUN_FRT_VIDEO_DRIVER");
	char pack[4096];
	char candidate[4096];
	const char *frt = NULL;
	const char *rel[] = {"frt", "bin/frt", "frt_aarch64", "bin/frt_aarch64", NULL};
	int i;

	if (!pack_name || !pack_name[0])
		pack_name = "game.pck";
	if (!video || !video[0])
		video = "GLES2";

	if (!content || !content[0]) {
		fprintf(stderr, "frt-boot: MUN_CONTENT_DIR is not set\n");
		return 127;
	}
	join2(pack, sizeof pack, content, pack_name);
	if (access(pack, R_OK) != 0) {
		fprintf(stderr, "frt-boot: cannot read pack %s: %s\n", pack, strerror(errno));
		return 127;
	}

	if (usable_exec(override_frt))
		frt = override_frt;
	for (i = 0; !frt && rel[i]; i++) {
		join2(candidate, sizeof candidate, content, rel[i]);
		if (usable_exec(candidate)) {
			/* candidate is overwritten next loop; copy into pack buffer spare — use strdup */
			frt = strdup(candidate);
			if (!frt) {
				fprintf(stderr, "frt-boot: out of memory\n");
				return 127;
			}
		}
	}
	if (!frt) {
		fprintf(stderr,
			"frt-boot: no FRT binary under %s (tried frt, bin/frt, frt_aarch64).\n"
			"Place an aarch64 FRT 3.5.x next to game.pck, or set MUN_FRT_PATH.\n",
			content);
		return 127;
	}

	fprintf(stderr, "frt-boot: exec %s --main-pack %s --video-driver %s\n", frt, pack, video);
	/* FRT argv: program name, then flags Godot/FRT understand. */
	execl(frt, frt, "--main-pack", pack, "--video-driver", video, (char *)NULL);
	fprintf(stderr, "frt-boot: exec failed: %s\n", strerror(errno));
	return 127;
}
