# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: MIT-0

extends Control
# MUN Hello for Godot 3.5: count, save, quit — same idea as hello-mun-godot
# (4.7), using yield instead of await.
#
# Controls: Up/Down change the count; Enter/Space/S save; Escape/Q quit.
# MUN_HELLO_SCRIPT="up up save wait quit" runs steps one per frame.

const SAVE_SCHEMA = 1
const COUNT_MAX = 9999

var count = 0
var saves = 0
var dirty = false
var saving = false
var _script_steps = []
var _script_idle = 0
var _count_label
var _save_label
var _facts_label


func _ready():
	_build_screen()
	var ver = Engine.get_version_info()
	print("hello-mun-godot3: ", "in a MUN session" if Mun.in_session else "not in a MUN session",
			"; card ", Mun.card_id, ", profile ", Mun.runtime_profile,
			"; engine ", ver.get("string", "?"),
			"; uds ", ClassDB.class_exists("StreamPeerUnix") or ClassDB.class_exists("StreamPeerUDS"))
	_restore()
	var raw = OS.get_environment("MUN_HELLO_SCRIPT").replace(",", " ").strip_edges()
	if raw != "":
		_script_steps = raw.split(" ", false)
	_show()


func _restore():
	var loaded = Mun.save_load()
	var status = loaded["status"]
	var text = "NEW GAME"
	if status == Mun.Status.OK:
		var data = loaded["data"]
		if loaded["schema"] == SAVE_SCHEMA and typeof(data.get("count")) == TYPE_REAL:
			count = clamp(int(data["count"]), 0, COUNT_MAX)
			saves = max(int(data.get("saves", 0)), 0)
			text = "RESTORED THE PREVIOUS SAVE" if loaded["recovered"] else "RESTORED FROM THE CARD"
		else:
			text = "SAVE NOT UNDERSTOOD"
	elif status == Mun.Status.UNAVAILABLE:
		text = "NOT IN A MUN SESSION"
	elif status != Mun.Status.NO_SAVE:
		text = "THE CARD'S SAVE IS DAMAGED"
	_save_label.text = text
	print("hello-mun-godot3: restore: ", Mun.status_name(status), " (count ", count, ")")


func _change(delta):
	var next = clamp(count + delta, 0, COUNT_MAX)
	if next == count:
		return
	count = next
	dirty = true
	_show()


func _save():
	if saving:
		return
	saving = true
	var saved_count = count
	var data = {"count": saved_count, "saves": saves + 1}
	_save_label.text = "SAVE: WRITING..."
	print("hello-mun-godot3: save requested: ", JSON.print(data))
	var result = yield(Mun.save_write(data, SAVE_SCHEMA), "completed")
	saving = false
	if result["status"] == Mun.Status.OK:
		saves += 1
		dirty = count != saved_count
		_save_label.text = "SAVED ON THE CARD (%d BYTES)" % result["bytes"]
		print("hello-mun-godot3: save confirmed: ", result["bytes"], " bytes")
	else:
		var why = result.get("code", Mun.status_name(result["status"]))
		_save_label.text = "NOT SAVED: " + why
		print("hello-mun-godot3: save not confirmed: ", Mun.status_name(result["status"]),
				" (", result.get("code", ""), ")")
	_show()


func _quit(code = 0):
	print("hello-mun-godot3: exit ", code, "; count ", count, ", saves ", saves)
	get_tree().quit(code)


func _unhandled_input(event):
	if event is InputEventKey and event.pressed and not event.echo:
		match event.scancode:
			KEY_UP:
				_change(1)
			KEY_DOWN:
				_change(-1)
			KEY_ENTER, KEY_KP_ENTER, KEY_SPACE, KEY_S:
				_save()
			KEY_ESCAPE, KEY_Q:
				_quit()


func _process(_delta):
	_play_script()


func _play_script():
	if _script_idle > 0:
		_script_idle -= 1
		return
	if _script_steps.empty():
		return
	var step = _script_steps[0]
	if step == "wait" and saving:
		return
	_script_steps.remove(0)
	if step == "up":
		_change(1)
	elif step == "down":
		_change(-1)
	elif step == "save":
		_save()
	elif step == "quit":
		_quit()
	elif step == "fail":
		_quit(3)
	elif step.begins_with("idle:"):
		_script_idle = int(step.substr(5))


func _label(text, size_px, y, colour):
	var label = Label.new()
	label.text = text
	label.add_color_override("font_color", colour)
	label.align = Label.ALIGN_CENTER
	label.set_anchors_and_margins_preset(Control.PRESET_TOP_WIDE)
	label.margin_top = y
	label.margin_bottom = y + size_px
	add_child(label)
	return label


func _build_screen():
	var ink = Color("EFE9DD")
	var accent = Color("E39A63")
	var background = ColorRect.new()
	background.color = Color("16202B")
	background.set_anchors_and_margins_preset(Control.PRESET_FULL_RECT)
	add_child(background)
	_label("MUN HELLO (GODOT 3)", 28, 40, ink)
	_count_label = _label("0", 96, 200, accent)
	_save_label = _label("", 22, 420, ink)
	_label("UP/DOWN  ENTER: SAVE  ESC: QUIT", 16, 520, ink)
	_facts_label = _label("", 14, 580, ink.darkened(0.35))
	var ver = Engine.get_version_info().get("string", "?")
	_facts_label.text = "CARD %s  PROFILE %s  GODOT %s" % [
			Mun.card_id if Mun.card_id != "" else "-",
			Mun.runtime_profile if Mun.runtime_profile != "" else "-",
			ver]


func _show():
	_count_label.text = "%d%s" % [count, " *" if dirty else ""]
