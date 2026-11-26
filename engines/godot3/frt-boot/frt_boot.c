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
 * On a real console, content/ is mounted noexec: FRT cannot be exec'd from
 * there. This wrapper copies it into $HOME (session work/) or /tmp, then
 * execs the copy. The pack stays on the content mount (read-only data).
 *
 * Override the FRT file with MUN_FRT_PATH (absolute) when testing.
 * Override the pack name with MUN_FRT_PACK (default game.pck).
 * Extra video driver: MUN_FRT_VIDEO_DRIVER (default GLES2).
 */
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int readable_file(const char *path)
{
	struct stat st;

	return path && path[0] && access(path, R_OK) == 0
		&& stat(path, &st) == 0 && S_ISREG(st.st_mode);
}

static void join2(char *out, size_t n, const char *a, const char *b)
{
	snprintf(out, n, "%s/%s", a, b);
}

/* Copy src → dst and make dst executable. content/ may be noexec. */
static int copy_exec(const char *src, const char *dst)
{
	char buf[1 << 16];
	ssize_t n;
	int in = -1, out = -1;
	int err = 0;

	in = open(src, O_RDONLY | O_CLOEXEC);
	if (in < 0)
		return -1;
	out = open(dst, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0755);
	if (out < 0) {
		err = errno;
		close(in);
		errno = err;
		return -1;
	}
	while ((n = read(in, buf, sizeof buf)) > 0) {
		char *p = buf;
		ssize_t left = n;
		while (left > 0) {
			ssize_t w = write(out, p, (size_t)left);
			if (w < 0) {
				err = errno;
				close(in);
				close(out);
				unlink(dst);
				errno = err;
				return -1;
			}
			p += w;
			left -= w;
		}
	}
	if (n < 0) {
		err = errno;
		close(in);
		close(out);
		unlink(dst);
		errno = err;
		return -1;
	}
	if (fchmod(out, 0755) != 0) {
		err = errno;
		close(in);
		close(out);
		unlink(dst);
		errno = err;
		return -1;
	}
	close(in);
	if (close(out) != 0) {
		unlink(dst);
		return -1;
	}
	return 0;
}

static const char *stage_frt(const char *src, char *dst, size_t dst_n)
{
	const char *home = getenv("HOME");
	const char *dir;

	if (home && home[0] && access(home, W_OK) == 0)
		dir = home;
	else
		dir = "/tmp";

	/* Already executable where it sits (sim / override outside the card). */
	if (access(src, X_OK) == 0) {
		snprintf(dst, dst_n, "%s", src);
		return dst;
	}

	join2(dst, dst_n, dir, "mun-frt");
	if (copy_exec(src, dst) != 0) {
		fprintf(stderr, "frt-boot: cannot stage FRT to %s: %s\n",
			dst, strerror(errno));
		return NULL;
	}
	fprintf(stderr, "frt-boot: staged FRT %s -> %s\n", src, dst);
	return dst;
}

int main(void)
{
	const char *content = getenv("MUN_CONTENT_DIR");
	const char *override_frt = getenv("MUN_FRT_PATH");
	const char *pack_name = getenv("MUN_FRT_PACK");
	const char *video = getenv("MUN_FRT_VIDEO_DRIVER");
	char pack[4096];
	char candidate[4096];
	char staged[4096];
	const char *frt_src = NULL;
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

	if (readable_file(override_frt))
		frt_src = override_frt;
	for (i = 0; !frt_src && rel[i]; i++) {
		join2(candidate, sizeof candidate, content, rel[i]);
		if (readable_file(candidate)) {
			frt_src = strdup(candidate);
			if (!frt_src) {
				fprintf(stderr, "frt-boot: out of memory\n");
				return 127;
			}
		}
	}
	if (!frt_src) {
		fprintf(stderr,
			"frt-boot: no FRT binary under %s (tried frt, bin/frt, frt_aarch64).\n"
			"Place an aarch64 FRT 3.5.x next to game.pck, or set MUN_FRT_PATH.\n",
			content);
		return 127;
	}

	frt = stage_frt(frt_src, staged, sizeof staged);
	if (!frt)
		return 127;

	fprintf(stderr, "frt-boot: exec %s --main-pack %s --video-driver %s\n", frt, pack, video);
	/* FRT argv: program name, then flags Godot/FRT understand. */
	execl(frt, frt, "--main-pack", pack, "--video-driver", video, (char *)NULL);
	fprintf(stderr, "frt-boot: exec failed: %s\n", strerror(errno));
	return 127;
}
