class_name CropGrowth
extends RefCounted
## Pure growth logic for one field, independent of rendering.
## Stages 0..4: 0 = empty soil, 4 = ripe. One stage takes seconds_per_stage.

const MAX_STAGE := 4

var stage: int = 0
var seconds_per_stage: float = 3.0

var _elapsed: float = 0.0


func _init(p_seconds_per_stage: float = 3.0, p_start_stage: int = 0) -> void:
	seconds_per_stage = maxf(0.001, p_seconds_per_stage)
	stage = clampi(p_start_stage, 0, MAX_STAGE)


## Advances by delta seconds. Returns true when the stage changed at least once.
func advance(delta: float) -> bool:
	if delta <= 0.0 or is_ripe():
		return false
	_elapsed += delta
	var changed := false
	while _elapsed >= seconds_per_stage and stage < MAX_STAGE:
		_elapsed -= seconds_per_stage
		stage += 1
		changed = true
	if stage >= MAX_STAGE:
		_elapsed = 0.0
	return changed


func is_ripe() -> bool:
	return stage >= MAX_STAGE


## Harvests the field: back to empty soil.
func harvest() -> void:
	stage = 0
	_elapsed = 0.0
