# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: MIT-0

extends Node
# What a MUN console gives a game session, for Godot 3.5: the session's
# facts, the save the console restored, and acknowledged saves on the Game
# Card (MUN OS docs/runtime.md and docs/saves.md).
#
# Add it as an autoload named `Mun`:
#
#     [autoload]
#     Mun="*res://addons/mun/mun.gd"
#
# Save writes need a Unix stream peer (StreamPeerUnix module/GDNative, or
# StreamPeerUDS if present). See engines/godot3/uds/README.md. Without one,
# save_write reports UNAVAILABLE so the editor and desktop runs stay safe.
#
# Call save_write with yield:
#     var result = yield(Mun.save_write(data, schema), "completed")

enum Status {
	OK,
	UNAVAILABLE, # Not in a MUN session, or no save feature / no UDS peer.
	NO_SAVE,     # The card holds no save for this game: a new game.
	DAMAGED,     # A save file exists and is not a save this game can read.
	REFUSED,     # The console answered with an error; see `code`.
	TIMEOUT,     # No answer in time; the save may or may not be on the card.
	IO,          # The socket failed, or the console closed it without answering.
	PROTOCOL,    # An answer that cannot be read.
	ARGUMENT,    # A schema below 1, or data that cannot be written as JSON.
	TOO_LARGE,   # The payload exceeds SAVE_MAX_BYTES.
}

const SAVE_MAX_BYTES = 65536
const SAVE_FORMAT = "mun-save/1"
const _SAVE_FILE_MAX_BYTES = 112 * 1024
const _REPLY_MAX_BYTES = 4096

var in_session = false
var card_id = ""
var content_version = ""
var session = ""
var runtime_profile = ""
var content_dir = ""
var display_mode = ""

var _save_file = ""
var _save_socket = ""


func _init():
	session = OS.get_environment("MUN_SESSION")
	in_session = session != ""
	card_id = OS.get_environment("MUN_CARD_ID")
	content_version = OS.get_environment("MUN_CONTENT_VERSION")
	runtime_profile = OS.get_environment("MUN_RUNTIME_PROFILE")
	content_dir = OS.get_environment("MUN_CONTENT_DIR")
	display_mode = OS.get_environment("MUN_DISPLAY_MODE")
	_save_file = OS.get_environment("MUN_SAVE_FILE")
	_save_socket = OS.get_environment("MUN_SAVE_SOCKET")


func content_path(relative):
	if content_dir == "" or relative == "" or relative.begins_with("/") or relative.ends_with("/"):
		return ""
	var path = content_dir
	for segment in relative.split("/"):
		if segment == "" or segment == "." or segment == "..":
			return ""
		path = path.plus_file(segment)
	return path


func save_load():
	if _save_file == "":
		return {"status": Status.UNAVAILABLE}
	var file = File.new()
	if not file.file_exists(_save_file):
		return {"status": Status.NO_SAVE}
	if file.open(_save_file, File.READ) != OK:
		return {"status": Status.IO}
	if file.get_len() > _SAVE_FILE_MAX_BYTES:
		file.close()
		return {"status": Status.DAMAGED}
	var text = file.get_as_text()
	file.close()
	var parsed = JSON.parse(text)
	if parsed.error != OK or typeof(parsed.result) != TYPE_DICTIONARY:
		return {"status": Status.DAMAGED}
	var envelope = parsed.result
	var schema = envelope.get("schema")
	if envelope.get("format") != SAVE_FORMAT or typeof(envelope.get("payload")) != TYPE_DICTIONARY \
			or typeof(schema) != TYPE_REAL or schema < 1 or schema != floor(schema):
		return {"status": Status.DAMAGED}
	return {
		"status": Status.OK,
		"schema": int(schema),
		"recovered": envelope.has("recovered_from"),
		"data": envelope["payload"],
	}


# Asks the console to save `data` under `schema` and waits without blocking
# frames. Use: yield(Mun.save_write(data, schema), "completed")
func save_write(data, schema, timeout_ms = 25000):
	if schema < 1:
		return {"status": Status.ARGUMENT}
	if _save_socket == "":
		return {"status": Status.UNAVAILABLE}
	var peer = _make_unix_peer()
	if peer == null:
		return {"status": Status.UNAVAILABLE}
	var payload = JSON.print(data)
	if payload == "" or not payload.begins_with("{"):
		return {"status": Status.ARGUMENT}
	if payload.to_utf8().size() > SAVE_MAX_BYTES:
		return {"status": Status.TOO_LARGE}
	var request = ('{"type":"save","schema":%d,"data":%s}\n' % [schema, payload]).to_utf8()
	var deadline = OS.get_ticks_msec() + max(timeout_ms, 1)
	if not _peer_connect(peer, _save_socket):
		return {"status": Status.IO}
	while true:
		_peer_poll(peer)
		var state = _peer_status(peer)
		if state == _STATUS_CONNECTED:
			break
		if state != _STATUS_CONNECTING:
			_peer_close(peer)
			return {"status": Status.IO}
		if OS.get_ticks_msec() >= deadline:
			_peer_close(peer)
			return {"status": Status.TIMEOUT}
		yield(get_tree(), "idle_frame")
	if _peer_put(peer, request) != OK:
		_peer_close(peer)
		return {"status": Status.IO}
	var reply = PoolByteArray()
	while true:
		_peer_poll(peer)
		var available = _peer_available(peer)
		if available > 0:
			var chunk = _peer_get(peer, available)
			if chunk[0] != OK:
				_peer_close(peer)
				return {"status": Status.IO}
			reply.append_array(chunk[1])
			if _pool_find_byte(reply, 10) >= 0:
				break
			if reply.size() > _REPLY_MAX_BYTES:
				_peer_close(peer)
				return {"status": Status.PROTOCOL}
		elif _peer_status(peer) != _STATUS_CONNECTED:
			_peer_close(peer)
			return {"status": Status.IO}
		elif OS.get_ticks_msec() >= deadline:
			_peer_close(peer)
			return {"status": Status.TIMEOUT}
		else:
			yield(get_tree(), "idle_frame")
	_peer_close(peer)
	var line_end = _pool_find_byte(reply, 10)
	var line = reply.subarray(0, line_end - 1).get_string_from_utf8()
	var parsed = JSON.parse(line)
	if parsed.error != OK or typeof(parsed.result) != TYPE_DICTIONARY:
		return {"status": Status.PROTOCOL}
	var answer = parsed.result
	if answer.get("type") != "saved" or typeof(answer.get("ok")) != TYPE_BOOL:
		return {"status": Status.PROTOCOL}
	if answer["ok"]:
		return {"status": Status.OK, "bytes": int(answer.get("bytes", 0))}
	var error = answer.get("error")
	if typeof(error) != TYPE_DICTIONARY or typeof(error.get("code")) != TYPE_STRING or error["code"] == "":
		return {"status": Status.PROTOCOL}
	return {"status": Status.REFUSED, "code": error["code"], "message": str(error.get("message", ""))}


func status_name(status):
	var keys = Status.keys()
	if status >= 0 and status < keys.size():
		return keys[status].to_lower()
	return "unknown"


# --- Unix peer helpers (StreamPeerUnix module or StreamPeerUDS) ----------------

const _STATUS_CONNECTING = 1
const _STATUS_CONNECTED = 2

func _make_unix_peer():
	if ClassDB.class_exists("StreamPeerUnix"):
		return ClassDB.instance("StreamPeerUnix")
	if ClassDB.class_exists("StreamPeerUDS"):
		return ClassDB.instance("StreamPeerUDS")
	return null


func _peer_connect(peer, path):
	if peer.has_method("open"):
		return peer.open(path) == OK
	if peer.has_method("connect_to_host"):
		return peer.connect_to_host(path) == OK
	return false


func _peer_poll(peer):
	if peer.has_method("poll"):
		peer.poll()


func _peer_status(peer):
	if peer.has_method("get_status"):
		return peer.get_status()
	# StreamPeerUnix (lihop) has no connecting state once open() succeeded.
	return _STATUS_CONNECTED


func _peer_available(peer):
	if peer.has_method("get_available_bytes"):
		return peer.get_available_bytes()
	return 0


func _peer_put(peer, data):
	if peer.has_method("put_data"):
		var err = peer.put_data(data)
		if typeof(err) == TYPE_ARRAY:
			return err[0]
		return err
	return FAILED


func _peer_get(peer, n):
	if peer.has_method("get_data"):
		return peer.get_data(n)
	return [FAILED, PoolByteArray()]


func _peer_close(peer):
	if peer.has_method("close"):
		peer.close()
	elif peer.has_method("disconnect_from_host"):
		peer.disconnect_from_host()


func _pool_find_byte(pool, value):
	for i in range(pool.size()):
		if pool[i] == value:
			return i
	return -1
