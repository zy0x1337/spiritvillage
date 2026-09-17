extends SceneTree
## Headless logic tests for crop_growth.gd.
## Usage: <godot> --headless --path game --script res://tests/test_crop_growth.gd
## Prints PASS/FAIL per case and exits with 1 on any failure.

const Growth := preload("res://scripts/crop_growth.gd")

var _failures := 0


func _init() -> void:
	_test_no_change_before_time()
	_test_change_after_time()
	_test_multiple_stages_in_one_step()
	_test_no_overrun()
	_test_ripe_does_not_advance()
	_test_harvest_resets()
	if _failures > 0:
		print("FAIL: %d case(s) failed" % _failures)
		quit(1)
	else:
		print("PASS: all cases")
		quit(0)


func _check(name: String, condition: bool) -> void:
	if condition:
		print("PASS ", name)
	else:
		_failures += 1
		print("FAIL ", name)


func _test_no_change_before_time() -> void:
	var growth := Growth.new(3.0, 0)
	var changed := growth.advance(1.0)
	_check("no change before time", changed == false and growth.stage == 0)


func _test_change_after_time() -> void:
	var growth := Growth.new(3.0, 0)
	growth.advance(2.9)
	var changed := growth.advance(0.2)
	_check("change after time", changed == true and growth.stage == 1)


func _test_multiple_stages_in_one_step() -> void:
	var growth := Growth.new(1.0, 0)
	var changed := growth.advance(2.5)
	_check("multiple stages in one step", changed == true and growth.stage == 2)


func _test_no_overrun() -> void:
	var growth := Growth.new(0.001, 0)
	growth.advance(100.0)
	_check("no stage above 4", growth.stage == 4 and growth.is_ripe())


func _test_ripe_does_not_advance() -> void:
	var growth := Growth.new(1.0, 4)
	var changed := growth.advance(50.0)
	_check("ripe does not advance", changed == false and growth.stage == 4)


func _test_harvest_resets() -> void:
	var growth := Growth.new(1.0, 0)
	growth.advance(1.0)
	growth.harvest()
	_check("harvest resets to stage 0", growth.stage == 0 and growth.is_ripe() == false)
