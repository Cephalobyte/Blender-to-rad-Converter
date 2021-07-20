import bpy
from math import *


def difSign(a,b=0):
	return 1 if a < b else -1 if a > b else 0


def sRGBToLinear(l):
	if 0 <= l and l <= 0.0031308:
		return l * 12.92
	elif 0.0031308 < l and l <= 1:
		return 1.055 * (l ** (1 / 2.4)) - 0.055
	return l


def colPicker(col, paint, convert):
	max = 255
	rgb = []
	
	for i in range(3):
		if convert:
			col[i] = sRGBToLinear(col[i])
		
		rgb.append(round(col[i] * 255))
		
		if rgb[i] > max:
			max = rgb[i]
	
	if max > 255:
		paint[2] = -10
	
	max = ceil(max / 255)
	
	for i in range(3):
		rgb[i] = int(rgb[i] / max)
	
	return rgb


def colFromMats(mats, paints, surfs, convert):
	for i in range(len(mats)):
		paints.append(['', [], 0, 0])
		
		rgb = colPicker([mats[i].diffuse_color[ch] for ch in range(3)], paints[i], convert)
		nm = mats[i].name.casefold()
		
		paints[i][0] = f'c({rgb[0]},{rgb[1]},{rgb[2]})'
		
		if nm.find('glass') != -1:
			surfs.pop(surfs.index(i))
			paints[i][0] = None
			paints[i][1].append('glass')
		
		if nm.find('light') != -1:
			if nm.find('b') != -1 or nm.find('rear') != -1: # find back/rear lights
				surfs.pop(surfs.index(i))
				paints[i][1].append('lightB')
			else: # find front lights
				surfs.pop(surfs.index(i))   			
				paints[i][1].append('lightF')


def generatePoly(poly, verts, paint, preciFac):
	col = paint[0]
	efx = paint[1].copy()
	gr = paint[2]
	fs = paint[3]
	
	if poly.use_smooth:
		efx.append('noOutline()') # remove face's outlines if marked smooth
	if poly.use_freestyle_mark: # electrify face if marked freestyle
		gr = -18
	if poly.hide: # hide face if hidden
		gr = -13
	
	rtrn = 2
	if col != None:
		rtrn -= 1
	rtrn -= len(efx)
	if gr != 0:
		rtrn -= 1
	if fs != 0:
		rtrn -= 1
	
	txt = '<p>\n' # open the polygon
	
	if col != None: # generate c(r,g,b) line
		txt += f'{col}\n'
	
	if len(efx) > 0: # generate the first effect
		txt += f'{efx[0]}\n'
	
	for i in range(rtrn): # generate the return lines
		txt += '\n'
	del rtrn
	
	if len(efx) > 1: # generate the rest of the effects
		for i in range(1, len(efx)):
			txt += f'{efx[i]}\n'
	
	if gr != 0: # generate the gr() line
		txt += f'gr({gr})\n'
	
	if fs != 0: # generate the fs() line
		txt += f'fs({fs})\n'
	
	for iVtx in poly.vertices: # generate all the p() lines
		vtx = verts[iVtx]
		txt += 'p('
		for j in [0, 2, 1]:
			txt += str(round(vtx.co[j] * -preciFac))
			if j == 1:
				break
			txt += ','
		txt += ')\n'

	return txt + '</p>' # close and return the polygon


def detectPosPair(posList):
	for i in range(len(posList)):
		for j in range(i + 1, len(posList)):
			pos1 = posList[i]
			pos2 = posList[j]
			
			if pos1[1] == pos2[1] and pos1[2] == pos2[2] and pos1[0] == -pos2[0]:
				posList.remove(pos1)
				posList.remove(pos2)
				return [pos1, pos2]
	
	return [[], []]


def generateWheels(mesh, preciFac):
	iMeshVerts = [e.vertices[0] for e in mesh.edges] + [e.vertices[1] for e in mesh.edges]
	lonePoss = [[round(ax * preciFac) for ax in v.co] for v in mesh.vertices if v.index not in iMeshVerts] # if a vertex index doesn't appear in any edge, consider it lonely, then take all its position axies and round them once multiplied by the precision factor to store them in a list of loose vertex positions
	
	posPairs = [detectPosPair(lonePoss), detectPosPair(lonePoss)]
	
	for pair in posPairs:
		if pair == [[], []] and len(lonePoss) > 0: # as long as there is an empty pairs in posPairs and a loose vertex left,
			lonePos = lonePoss[0] # pick the first lone vertex
			pair[0] = lonePos # and make a pair out of it
			pair[1] = [-lonePos[0], lonePos[1], lonePos[2]] # (mirror)
			
			lonePoss.pop(0) # then remove it from the lone positions list
				
	posPairs = [pair for pair in posPairs if pair != [[], []]] # remove all remaining empty pairs
	txt = ''
	
	for i in range(len(posPairs)):
		txt += 'gwgr(0)\n'
		txt += 'rims(140,140,140,18,10)\n'
		for j in range(2):
			steer = 1-i
			left = j*2-1
			pos = posPairs[i][j]
			
			txt += 'w('
			txt += f'{left * abs(pos[0])},'
			txt += f'{-pos[2]},'
			txt += f'{-pos[1]},'
			txt += f'{steer*11},{left*-26},20)\n'
		txt += '\n'
	return txt


def main(op, ctx):
	obj = ctx.active_object
	mesh = obj.data

	paints = []
	surfs = []

	surfs = [i for i in range(len(mesh.materials))]
	colFromMats(mesh.materials, paints, surfs, op.srgb_linear_convert)
	
	scaleFac = op.model_scale
	preciFac = 10 ** op.model_precision
	
	
	op.gen(f'// converted car: {op.car_name}')
	op.gen('---------------------',2)
	
	op.gen(f'1stColor{paints[surfs[0]][0].strip("c")}')
	op.gen(f'2ndColor{paints[surfs[1]][0].strip("c")}',3)
	
	
	if op.apply_object_scale:
		op.gen(f'ScaleZ({round(obj.scale[1] * scaleFac)})')
		op.gen(f'ScaleY({round(obj.scale[2] * scaleFac)})')
		op.gen(f'ScaleX({round(obj.scale[0] * scaleFac)})',3)
	else:
		op.gen(f'ScaleZ({round(scaleFac)})')
		op.gen(f'ScaleY({round(scaleFac)})')
		op.gen(f'ScaleX({round(scaleFac)})',3)
	
	
	polySort = op.polySort(op.sort_by)
	polyGroup = op.polyGroup(op.group_by)
	
	polys = polySort(mesh)
	
	polyGroup(polys, obj, paints)
	
	if op.generate_wheels:
		op.gen(generateWheels(mesh, preciFac),0)
	
	if op.quick_stats_toggle:
		op.gen(f'stat({op.quick_stats_speed},{op.quick_stats_acceleration},{op.quick_stats_stunts},{op.quick_stats_strength},{op.quick_stats_endurance})',2)
		
		op.gen(f'handling({op.quick_stats_handling})',2)
	
	if op.quick_phys_toggle:
		txt = 'physics('
		txt += f'{op.quick_phys_handbrake},{op.quick_phys_turning_sensitivity},{op.quick_phys_tire_grip},{op.quick_phys_bouncing},'
		txt += f'{op.quick_phys_lifts_others},{op.quick_phys_gets_lifted},{op.quick_phys_pushes_others},{op.quick_phys_gets_pushed},'
		txt += f'{op.quick_phys_aerial_rotation_speed},{op.quick_phys_aerial_control_gliding},'
		txt += f'{op.quick_phys_crash_radius},{op.quick_phys_crash_magnitude},{op.quick_phys_crash_roof},{op.quick_phys_engine_sound},21717)'
		op.gen(txt,0)


class OBJECT_OT_model_to_rad(bpy.types.Operator):
	"""Creates a '.rad' text file from the selected object, compatible with _Need for Madness? Car Maker_."""
	bl_idname = "object.model_to_rad"
	bl_label = "Create NfM Car Maker file."
	bl_options = {'REGISTER', 'UNDO'}
	
	car_name: bpy.props.StringProperty(
		name="Car Name",
		description="What name do you want your car to display?",
		default="",
	)
	model_precision: bpy.props.IntProperty(
		name="Model Precision",
		description="Amount of decimals you want to keep.\nThe model also appear bigger, 10^n.",
		min=0, soft_max=8,
		default=1,
	)
	model_scale: bpy.props.IntProperty(
		name="Model Scale",
		description="Scale factor applied to the model.",
		min=1, max=1000,
		default=10,
		subtype="PERCENTAGE",
	)
	apply_object_scale: bpy.props.BoolProperty(
		name="Apply Object Scale",
		description="Should I apply the object's Scale property on top of the model scale?\nUseful when you want to scale each axies independently.",
	)
	srgb_linear_convert: bpy.props.BoolProperty(
		name="Color Space Conversion",
		description="Should I convert the 0-1 sRGB color into Linear RGB 255 value?\nIf not, colors may appear darker than expected.",
		default=True,
	)
	sort_by: bpy.props. EnumProperty(
		name="Sort By",
		description="In which order should I sort the polygons?",
		items=[
			("index","Polygon Index","Sort by the index of the face.\nThe last face is usually the last generated polygon.", "MESH_DATA", 0),
			("material","Material","Sort by the index of face's material.\nThe order is the same as your material list." , "MATERIAL", 1),
		],
		default=1,
	)
	group_by: bpy.props. EnumProperty(
		name="Group By",
		description="Which attribute should group the polygons together?",
		items=[
			("none","None","Do not group any polygon\nsorting only", "X", 0),
			("material","Material","Group the polygons of the same Material\n(create a separator named after the Material)" , "MATERIAL", 1),
			("face_map","Face Map","Group the polygons of the same Face Map\n(create a separator named after the Face Map)" , "FACE_MAPS", 2),
		],
		default=2,
	)
	generate_wheels: bpy.props.BoolProperty(
		name="Generate Wheels",
		description="I can automatically place the wheels based on loose vertices.\nI will generate 2 wheels (and maximum 4 wheels) per loose vertex:\n    one at its exact position,\n    one mirrored on the X axis.\nIf the vertex is already mirrored, then I generate one wheel per vertex",
		default=True,
	)
	#- Stats -----------------------------------------
	quick_stats_toggle: bpy.props.BoolProperty(
		name="Quick Stats",
		description="If you want to, I can set up your stats so you can immediately start playing once import is complete!",
		default=False,
	)
	quick_stats_speed: bpy.props.IntProperty(
		name="Speed",
		min=16, soft_min=0, max=200,
		default=120,
	)
	quick_stats_acceleration: bpy.props.IntProperty(
		name="Acceleration",
		min=16, max=200,
		default=100,
	)
	quick_stats_stunts: bpy.props.IntProperty(
		name="Stunts",
		min=16, max=200,
		default=100,
	)
	quick_stats_strength: bpy.props.IntProperty(
		name="Strength",
		min=16, max=200,
		default=100,
	)
	quick_stats_endurance: bpy.props.IntProperty(
		name="Endurance",
		min=16, max=200,
		default=100,
	)
	quick_stats_handling: bpy.props.IntProperty(
		name="Handling",
		min=16, max=200,
		default=100,
	)
	#- Physics ---------------------------------------
	quick_phys_toggle: bpy.props.BoolProperty(
		name="Quick Physics",
		description="If you want to, I can set up your physics so you can immediately start playing once import is complete!",
		default=False,
	)
	quick_phys_handbrake: bpy.props.IntProperty(
		name="Handbrake",
		min=0, max=100,
		default=50,
	)
	quick_phys_turning_sensitivity: bpy.props.IntProperty(
		name="Turning Sensitivity",
		min=0, max=100,
		default=50,
	)
	quick_phys_tire_grip: bpy.props.IntProperty(
		name="Tire Grip",
		min=0, max=100,
		default=50,
	)
	quick_phys_bouncing: bpy.props.IntProperty(
		name="Bouncing",
		min=0, max=100,
		default=50,
	)
	quick_phys_lifts_others: bpy.props.IntProperty(
		name="Lifts Others",
		min=0, max=100,
		default=50,
	)
	quick_phys_gets_lifted: bpy.props.IntProperty(
		name="Gets Lifted",
		min=0, max=100,
		default=50,
	)
	quick_phys_pushes_others: bpy.props.IntProperty(
		name="Pushes Others",
		min=0, max=100,
		default=50,
	)
	quick_phys_gets_pushed: bpy.props.IntProperty(
		name="Gets Pushed",
		min=0, max=100,
		default=50,
	)
	quick_phys_aerial_rotation_speed: bpy.props.IntProperty(
		name="Rotation Speed",
		min=0, max=100,
		default=50,
	)
	quick_phys_aerial_control_gliding: bpy.props.IntProperty(
		name="Control/Gliding",
		min=0, max=100,
		default=50,
	)
	quick_phys_crash_radius: bpy.props.IntProperty(
		name="Radius",
		min=0, max=100,
		default=50,
	)
	quick_phys_crash_magnitude: bpy.props.IntProperty(
		name="Magnitude",
		min=0, max=100,
		default=50,
	)
	quick_phys_crash_roof: bpy.props.IntProperty(
		name="Roof Destruction",
		min=0, max=100,
		default=50,
	)
	quick_phys_engine_sound: bpy.props.EnumProperty(
		name="Engine Sound",
		description="Select the most suitable engine for your car",
		items=[
			("0","Normal Engine","Like Tornado Shark, Sword of Justice or Radical One's engine."),
			("1","V8 Engine","High speed engine like Formula 7, Drifter X or Mighty Eight's engine."),
			("2","Retro Engine","Like Wow Caninaro, Lead Oxide or Kool Kat's engine."),
			("3","Power Engine","Turbo/super charged engine like MAX Revenge, High Rider or DR Monstaa's engine."),
			("4","Diesel Engine","Big diesel powered engine for big cars like EL King or M A S H E E N."),
		],
	)
	
	rad_file = None
	
	@classmethod
	def poll(cls, context):
		return context.active_object is not None and context.area.type == "VIEW_3D"
	
	def gen(self, txt="", n=1):
		self.rad_file.write(txt)
		
		for i in range(n):
			self.rad_file.write('\n')
	
	def execute(self, context):
		if self.car_name == "":
			self.car_name = context.active_object.name
		
		self.rad_file = bpy.data.texts.get(f'{self.car_name}.rad')
		if self.rad_file == None:
			self.rad_file = bpy.data.texts.new(f'{self.car_name}.rad')
		else:
			self.rad_file.clear()
		
		main(self, context)
		return {'FINISHED'}
	
	def draw(self, context):
		layout = self.layout
		
		layout.label(text="Basic Settings")
		col = layout.column_flow(columns=0, align=True)
		col.prop(self, "car_name")
		
		col = layout.column_flow(columns=2)
		col.label(text="Model Precision")
		col.prop(self, "model_precision", text="")
		col.label(text="Model Scale")
		col.prop(self, "model_scale", text="")
		
		col = layout.column_flow(columns=2, align=False)
		col.prop(self, "apply_object_scale")
		col.prop(self, "srgb_linear_convert")
		col.separator()
		
		
		col = layout.column(align=True)
		col.label(text="Advanced Settings")
		col.row().prop(self, "sort_by")
		col.row().prop(self, "group_by")
		col.separator()
		
		
		col = layout.column(align=True)
		col.row().prop(self, "generate_wheels")
		col.separator()
		
		
		col = layout.column(align=True)
		col.row().prop(self, "quick_stats_toggle")
		if self.quick_stats_toggle:
			statCol = col.box().column(align=True)
			row = statCol.row()
			row.prop(self, "quick_stats_speed", slider=True)
			row.prop(self, "quick_stats_stunts", slider=True)
			row = statCol.row()
			row.prop(self, "quick_stats_acceleration", slider=True)
			row.prop(self, "quick_stats_strength", slider=True)
			row = statCol.row()
			row.prop(self, "quick_stats_handling", slider=True)
			row.prop(self, "quick_stats_endurance", slider=True)
		col.separator()
		
		
		col = layout.column(align=True)
		col.row().prop(self, "quick_phys_toggle")
		if self.quick_phys_toggle:
			physBox = col.box()
			physCol = physBox.column_flow(columns=2, align=True)
			physCol.prop(self, "quick_phys_handbrake",slider=True)
			physCol.prop(self, "quick_phys_turning_sensitivity",slider=True)
			physCol.prop(self, "quick_phys_tire_grip",slider=True)
			physCol.prop(self, "quick_phys_bouncing",slider=True)
			
			physCol = physBox.column_flow(columns=2, align=True)
			physCol.prop(self, "quick_phys_lifts_others",slider=True)
			physCol.prop(self, "quick_phys_gets_lifted",slider=True)
			physCol.prop(self, "quick_phys_pushes_others",slider=True)
			physCol.prop(self, "quick_phys_gets_pushed",slider=True)
			physCol.label(text="Aerial")
			physCol.prop(self, "quick_phys_aerial_rotation_speed",slider=True)
			physCol.prop(self, "quick_phys_aerial_control_gliding",slider=True)
			
			physBox.label(text="Crash Test")
			physCol = physBox.column_flow(columns=2, align=True)
			physCol.prop(self, "quick_phys_crash_radius",slider=True)
			physCol.prop(self, "quick_phys_crash_magnitude",slider=True)
			physCol.prop(self, "quick_phys_crash_roof",slider=True)
			
			physCol = physBox.column_flow(columns=2, align=True)
			physCol.label(text="Engine Sound:")
			physCol.prop(self, "quick_phys_engine_sound", text="")
	
	#- sorting method (inspired by https://data-flair.training/blogs/python-switch-case)
	def polySortIndex(self, mesh):
		return [poly for poly in mesh.polygons]
	
	def polySortMaterial(self, mesh):
		polys = []
		for i in range(len(mesh.materials)):
			polys += [poly for poly in mesh.polygons if poly.material_index == i]
		
		return polys
	
	def polySort(self, case):
		switch = {
			'index': self.polySortIndex,
			'material': self.polySortMaterial,
			}
		return switch.get(case)
	
	#- grouping method -------------------------------
	def polyGroupNone(self, polys, obj, paints):
		for poly in polys:
			
			self.gen(generatePoly(poly, obj.data.vertices, paints[poly.material_index], 10 ** self.model_precision),2)
	
	def polyGroupMaterial(self, polys, obj, paints):
		mats = obj.material_slots
		
		if len(mats) > 0:
			for i in range(len(mats)):
				self.gen('//'+ (f' {mats[i].name} ').center(28, '-'),2)
				
				for poly in [pol for pol in polys if pol.material_index == i]:
					
					self.gen(generatePoly(poly, obj.data.vertices, paints[poly.material_index], 10 ** self.model_precision),2)
		else:
			self.polyGroupNone(polys, obj, paints)
	
	def polyGroupFaceMap(self, polys, obj, paints):
		mesh = obj.data
		
		if len(obj.face_maps) > 0:
			for iFM in range(-1, len(obj.face_maps)):
				if iFM >= 0:
					self.gen('//'+ (f' {obj.face_maps[iFM].name} ').center(28, '-'),2)
				
				for poly in [pol for pol in polys if mesh.face_maps[0].data[pol.index].value == iFM]:
					
					self.gen(generatePoly(poly, mesh.vertices, paints[poly.material_index], 10 ** self.model_precision),2)
		else:
			self.polyGroupNone(polys, obj, paints)
	
	def polyGroup(self, case):
		switch = {
			'none': self.polyGroupNone,
			'material': self.polyGroupMaterial,
			'face_map': self.polyGroupFaceMap,
			}
		return switch.get(case)


def menu_func(self, context):
	self.layout.operator(OBJECT_OT_model_to_rad.bl_idname, icon='AUTO')


def register():
	bpy.utils.register_class(OBJECT_OT_model_to_rad)
	bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)


def unregister():
	bpy.utils.unregister_class(OBJECT_OT_model_to_rad)
	bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)


if __name__ == "__main__":
	register()
