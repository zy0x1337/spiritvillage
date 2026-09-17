extends SceneTree
## Renders the garden scene, waits ~60 frames, saves a 360x800 PNG and reports
## the average frame rate of the last 30 frames plus the primitives (triangles)
## drawn per frame.
##
## Run WITHOUT --headless (a headless viewport is empty):
##   <godot> --path game --resolution 360x800 --script res://tools/capture.gd

const SCENE_PATH := "res://scenes/garden.tscn"
const WARMUP_FRAMES := 60
const FPS_WINDOW := 30

var _frames := 0
var _deltas: Array[float] = []
var _primitives: Array[int] = []


func _initialize() -> void:
	var packed: PackedScene = load(SCENE_PATH)
	root.add_child(packed.instantiate())


func _process(delta: float) -> bool:
	_frames += 1
	if _frames > WARMUP_FRAMES - FPS_WINDOW:
		_deltas.append(delta)
		_primitives.append(_primitives_in_frame())
	if _frames < WARMUP_FRAMES:
		return false
	_save()
	return true


func _primitives_in_frame() -> int:
	return int(RenderingServer.get_rendering_info(
			RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME))


func _save() -> void:
	var image := root.get_texture().get_image()
	var path := ProjectSettings.globalize_path("res://") + "../docs/previews/garden_scene.png"
	var err := image.save_png(path)
	var avg_delta := 0.0
	for delta in _deltas:
		avg_delta += delta
	if not _deltas.is_empty():
		avg_delta /= float(_deltas.size())
	var avg_primitives := 0.0
	var max_primitives := 0
	for count in _primitives:
		avg_primitives += float(count)
		max_primitives = maxi(max_primitives, count)
	if not _primitives.is_empty():
		avg_primitives /= float(_primitives.size())
	var fps := (1.0 / avg_delta) if avg_delta > 0.0 else 0.0
	print("[capture] frames=%d avg_fps=%.1f triangles_per_frame=%.0f max=%d size=%dx%d saved=%s err=%d" % [
		_frames, fps, avg_primitives, max_primitives, image.get_width(), image.get_height(), path, err])
