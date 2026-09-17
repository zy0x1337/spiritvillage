class_name CropPlot
extends Node3D
## One 1x1 m field. Owns the growth logic and swaps the visible carrot model
## (crop_carrot_1..4); stage 0 shows only the soil block.

const CROP_SCENES: Array[PackedScene] = [
	preload("res://assets/crops/crop_carrot_1.glb"),
	preload("res://assets/crops/crop_carrot_2.glb"),
	preload("res://assets/crops/crop_carrot_3.glb"),
	preload("res://assets/crops/crop_carrot_4.glb"),
]
const SOIL_TOP := 0.08

@export var seconds_per_stage: float = 3.0
@export var start_stage: int = 0
@export var growth_enabled: bool = true

var growth: CropGrowth
var _model: Node3D


func _ready() -> void:
	growth = CropGrowth.new(seconds_per_stage, start_stage)
	_show_stage()


func _process(delta: float) -> void:
	if growth_enabled and growth.advance(delta):
		_show_stage()


func harvest() -> void:
	growth.harvest()
	_show_stage()


func _show_stage() -> void:
	if _model != null:
		_model.queue_free()
		_model = null
	if growth.stage == 0:
		return
	var packed: PackedScene = CROP_SCENES[growth.stage - 1]
	_model = packed.instantiate()
	_model.position = Vector3(0.0, SOIL_TOP, 0.0)
	add_child(_model)
