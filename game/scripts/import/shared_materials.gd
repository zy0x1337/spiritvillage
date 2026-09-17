@tool
extends EditorScenePostImport
## Post-import pass for the environment assets (S4b).
##
## Leaf cards (materials whose name contains Leaves/Leaf/Flowers) must not cast
## shadows: dense double-sided cards shadow each other and the crowns go almost
## black under the game light. Small assets (crops, props, bushes) cast no
## shadow at all; trunks keep casting because the bark and leaf surfaces of a
## tree are split into two MeshInstance3D nodes here.
##
## "Disable Ambient Light" is deliberately NOT set on any material.

const LEAF_KEYWORDS := ["Leaves", "Leaf", "Flowers"]
const SMALL_MAX_EXTENT := 1.2


func _post_import(scene: Node) -> Object:
	var meshes := _collect_meshes(scene)
	var extent := _combined_aabb_size(meshes)
	var is_small := maxf(extent.x, maxf(extent.y, extent.z)) < SMALL_MAX_EXTENT
	for mesh_instance in meshes:
		if is_small:
			mesh_instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		else:
			_split_shadow_surfaces(mesh_instance)
	return scene


func _collect_meshes(node: Node) -> Array[MeshInstance3D]:
	var result: Array[MeshInstance3D] = []
	if node is MeshInstance3D:
		result.append(node)
	for child in node.get_children():
		result.append_array(_collect_meshes(child))
	return result


func _combined_aabb_size(meshes: Array[MeshInstance3D]) -> Vector3:
	var size := Vector3.ZERO
	for mesh_instance in meshes:
		if mesh_instance.mesh != null:
			size = size.max(mesh_instance.mesh.get_aabb().size)
	return size


func _is_leaf_material(material: Material) -> bool:
	if material == null:
		return false
	var name := material.resource_name
	for keyword in LEAF_KEYWORDS:
		if name.contains(keyword):
			return true
	return false


func _split_shadow_surfaces(mesh_instance: MeshInstance3D) -> void:
	var mesh := mesh_instance.mesh
	if mesh == null:
		return
	var leaf_surfaces: Array[int] = []
	var solid_surfaces: Array[int] = []
	for i in mesh.get_surface_count():
		if _is_leaf_material(mesh.surface_get_material(i)):
			leaf_surfaces.append(i)
		else:
			solid_surfaces.append(i)
	if leaf_surfaces.is_empty():
		return
	if solid_surfaces.is_empty():
		mesh_instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		return
	mesh_instance.mesh = _build_subset(mesh, solid_surfaces)
	var leaf_instance := MeshInstance3D.new()
	leaf_instance.name = "%s_Leaves" % mesh_instance.name
	leaf_instance.mesh = _build_subset(mesh, leaf_surfaces)
	leaf_instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mesh_instance.add_child(leaf_instance)
	# New nodes are only serialised into the imported scene when they have an owner.
	leaf_instance.owner = mesh_instance.owner


func _build_subset(mesh: Mesh, surfaces: Array[int]) -> ArrayMesh:
	var subset := ArrayMesh.new()
	for i in surfaces:
		var primitive: Mesh.PrimitiveType = mesh.surface_get_primitive_type(i)
		subset.add_surface_from_arrays(primitive, mesh.surface_get_arrays(i))
		var index := subset.get_surface_count() - 1
		subset.surface_set_material(index, mesh.surface_get_material(i))
		subset.surface_set_name(index, mesh.surface_get_name(i))
	return subset
