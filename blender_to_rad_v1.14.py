bl_info = {
    "name": "Export to rad (NFM)",
    "author": "Cephalobyte",
    "version": (1, 14, 0),
    "blender": (3, 2, 0),
    "location": "View3D > Object Context Menu > Create NfM Car Maker file",
    "description": "Creates a '.rad' text file from the selected object, compatible with _Need for Madness? Car Maker_.",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

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
			
			if pos1[1] == pos2[1] and pos1[2] == pos2[2] and pos1[0] == -pos2[0]: # if two symmetrical verts are found
				posList.remove(pos1) # remove them from the list
				posList.remove(pos2)
				return [pos1, pos2] # and return the pair
	
	return [[], []] # return empty list if nothing is found


def generateWheels(mesh, preciFac, op):
	iMeshVerts = [e.vertices[0] for e in mesh.edges] + [e.vertices[1] for e in mesh.edges] # list all vertices that appear in edges
	lonePoss = sorted([[round(ax * preciFac) for ax in v.co] for v in mesh.vertices if v.index not in iMeshVerts], key=lambda x: x[1]) # if a vertex index doesn't appear in any edge, consider it lonely, then take all its position axies and round them once multiplied by the precision factor to store them in a list of loose vertex positions and sort by y axis
	
	posPairs = [detectPosPair(lonePoss), detectPosPair(lonePoss)] # report any mirrored lone vertices
	
	for pair in posPairs:
		if pair == [[], []] and len(lonePoss) > 0: # as long as there is an empty pair in posPairs and a loose vertex left,
			lonePos = lonePoss[0] # pick the first lone vertex
			pair[0] = lonePos # and make a pair out of it
			pair[1] = [-lonePos[0], lonePos[1], lonePos[2]] # (mirror)
			
			lonePoss.pop(0) # then remove it from the lone positions list
				
	posPairs = [pair for pair in posPairs if pair != [[], []]] # remove all remaining empty pairs
	
	txt = ''
#	for i in range(len(posPairs)):
	for i, pair in enumerate(['back','front']):
		if i >= len(posPairs): break #if there isn't any pair left
	
		w = [0,26,20,18,10] # default wheel values
		col = [140,140,140] # default rim color
		if op.quick_wheel_toggle:
			w.clear()
			for prop in ['hide','width','height','rim_size','rim_depth']:
				w.append(eval(f'op.quick_wheel_{pair}_{prop}'))
			
			col = eval(f'op.quick_wheel_{pair}_rim_color')
			if op.srgb_linear_convert: col = list(map(sRGBToLinear, col))
			col = [round(c*255) for c in col]
		print(posPairs,i)
		txt += f'gwgr({w[0]})\n'
		txt += f'rims({col[0]},{col[1]},{col[2]},{w[3]},{w[4]})\n'
		for j in range(2):
			steer = 1-i
			left = j*2-1
			pos = posPairs[i][j]
			
			txt += 'w('
			txt += f'{left * abs(pos[0])},'
			txt += f'{-pos[2]},'
			txt += f'{-pos[1]},'
			txt += f'{steer*11},{left*-w[1]},{w[2]})\n'
		txt += '\n'
	return txt


def checkStats(self, context):
	if self.quick_stats_toggle:
		statsPoints = self.quick_stats_speed + self.quick_stats_acceleration + self.quick_stats_stunts + self.quick_stats_strength + self.quick_stats_endurance
		reptype = {'INFO'}
		match statsPoints:
			case 520:
				msg = "Car is class C"
			case 560:
				msg = "Car is class B & C"
			case 600:
				msg = "Car is class B"
			case 640:
				msg = "Car is class A & B"
			case 680:
				msg = "Car is class A"
			case _:
				msg = ("Make sure that the total of the stats (excluding handling) equals either 520, 560, 600, 640 or 680! Current sum: %i" %
				(statsPoints))
				reptype = {'WARNING'}
		self.report(reptype, msg)
	return None


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
#		op.gen(generateWheels(mesh, preciFac),0)
		op.gen(generateWheels(mesh, preciFac, op),0)
	
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
	#- Wheels ----------------------------------------
	generate_wheels: bpy.props.BoolProperty(
		name="Generate Wheels",
		description="I can automatically place the wheels based on loose vertices (vertices with no edges/faces).\nI will generate 2 wheels (and maximum 4 wheels) per loose vertex:\n    one at its exact position,\n    one mirrored on the X axis.\nIf the vertex is already mirrored, then I generate one wheel per vertex",
		default=True,
	)
	quick_wheel_toggle: bpy.props.BoolProperty(
		name="Quick Wheels",
		description="If you want to, I can set up your wheels' size and stuff so you can immediately start playing once import is complete!",
		default=False,
	)
	#- Back -------------------
	quick_wheel_back_height: bpy.props.IntProperty(
		name="Height",
		default=20,
	)
	quick_wheel_back_width: bpy.props.IntProperty(
		name="Width",
		default=26,
	)
	quick_wheel_back_rim_color: bpy.props.FloatVectorProperty(
		name="Rim RGB Color",
		min=0, max=1,
		default=(0.54902,0.54902,0.54902),
		subtype="COLOR_GAMMA",
	)
	quick_wheel_back_rim_size: bpy.props.IntProperty(
		name="Rim Size",
		default=18,
	)
	quick_wheel_back_rim_depth: bpy.props.IntProperty(
		name="Rim Depth",
		default=10,
	)
	quick_wheel_back_hide: bpy.props.IntProperty(
		name="Hide",
		description="Use this variable to hide the car wheels inside the car if you need to (if they are getting drawn over the car when they\nshould be drawn behind it).\n\nIf you have created a car model with specific places for the wheels go inside them (inside the car), if when you place the\nwheels there they don\u2019t get drawn inside the car (they get drawn over it instead), use this variable to adjust that.\n\nYou can also use this variable to do the opposite, to make the wheels get drawn over the car if they are getting drawn\nbehind it when they shouldn\u2019t.\n\nThe Hide variable takes values from -40 to 40:\nA +ve value from 1 to 40 makes the wheels more hidden, where 40 is the maximum the car wheel can be hidden.\nA -ve value from -1 to -40 does exactly the opposite and makes the wheels more apparent (this if the car wheels appear\ninside the car when they should be outside).\nA 0 value means do nothing.\nMost of the time you will need to use this variable, it will be to enter +ve values from 1-40 for hiding the car wheels.",
		default=0,
		min=-40, max=40,
	)
	#- Front ------------------
	quick_wheel_front_height: bpy.props.IntProperty(
		name="Height",
		default=20,
	)
	quick_wheel_front_width: bpy.props.IntProperty(
		name="Width",
		default=26,
	)
	quick_wheel_front_rim_color: bpy.props.FloatVectorProperty(
		name="Rim RGB Color",
		min=0, max=1,
		default=(0.54902,0.54902,0.54902),
		subtype="COLOR_GAMMA",
	)
	quick_wheel_front_rim_size: bpy.props.IntProperty(
		name="Rim Size",
		default=18,
	)
	quick_wheel_front_rim_depth: bpy.props.IntProperty(
		name="Rim Depth",
		default=10,
	)
	quick_wheel_front_hide: bpy.props.IntProperty(
		name="Hide",
		description="Use this variable to hide the car wheels inside the car if you need to (if they are getting drawn over the car when they\nshould be drawn behind it).\n\nIf you have created a car model with specific places for the wheels go inside them (inside the car), if when you place the\nwheels there they don\u2019t get drawn inside the car (they get drawn over it instead), use this variable to adjust that.\n\nYou can also use this variable to do the opposite, to make the wheels get drawn over the car if they are getting drawn\nbehind it when they shouldn\u2019t.\n\nThe Hide variable takes values from -40 to 40:\nA +ve value from 1 to 40 makes the wheels more hidden, where 40 is the maximum the car wheel can be hidden.\nA -ve value from -1 to -40 does exactly the opposite and makes the wheels more apparent (this if the car wheels appear\ninside the car when they should be outside).\nA 0 value means do nothing.\nMost of the time you will need to use this variable, it will be to enter +ve values from 1-40 for hiding the car wheels.",
		default=0,
		min=-40, max=40,
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
		default=120, update=checkStats,
	)
	quick_stats_acceleration: bpy.props.IntProperty(
		name="Acceleration",
		min=16, max=200,
		default=100, update=checkStats,
	)
	quick_stats_stunts: bpy.props.IntProperty(
		name="Stunts",
		min=16, max=200,
		default=100, update=checkStats,
	)
	quick_stats_strength: bpy.props.IntProperty(
		name="Strength",
		min=16, max=200,
		default=100, update=checkStats,
	)
	quick_stats_endurance: bpy.props.IntProperty(
		name="Endurance",
		min=16, max=200,
		default=100, update=checkStats,
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
		description="This defines the hand braking power of the car.\nThe more handbrake the car has the faster it brakes when you press Spacebar while driving.\nBut also the lesser the Handbrake the more the car can drift when you press Spacebar.",
#		description="Crash Look Test!\nThis defines how the car will look when it gets damaged.\nOr in other words what the car will look like as it gets damaged until it becomes wasted!\n\nIMPORTANT:\nYou need to perform a 'Normal Crash' test with a 'Roof Crash' test until the car gets totally destroyed (gets wasted and burns).\nYou need to also try a 'Normal Crash' test alone (without the roof crash) until the car gets wasted!\nA 'Roof Crash' happens significantly more when the car falls on its roof from a high jumps.\nA 'Normal Crash' is what happens as the car crashes normally with other cars and obstacles.\n\nClick any of adjustment variable names \u2018Radius\u2019, \u2018Magnitude\u2019 and \u2018Roof Destruction\u2019 to learn about their effect.\n\n>  You must perform the crash test more then once in order to make sure that this is how your want the car to look as it gets damaged\nuntil total destruction.",
		min=0, max=100,
		default=50,
	)
	quick_phys_turning_sensitivity: bpy.props.IntProperty(
		name="Turning Sensitivity",
		description="This defines how fast the car turns (or how fast the wheels respond to turning).\nThe more turning sensitive the faster the car turns and responds.\n\nWhen designing a fast car that is more racing oriented high turning sensitivity is     \nrecommended for the car to be able to take sharp and quick turns.\nHowever too much turning sensitivity can make the car hard to drive!\n\nWhen designing a slower and bigger car (like El King) lower turning sensitivity is\nrecommended for a more realistic effect.",
		min=0, max=100,
		default=50,
	)
	quick_phys_tire_grip: bpy.props.IntProperty(
		name="Tire Grip",
		description="This defines the griping power of the car\u2019s wheels on the ground.\n\nThe more griping the more the cars sticks to track.\nThe less gripping the more the car drifts in the turns.\n\nSome drifting can be helpful as it makes the car drive smoother while less drifting can\nmake the car more irritable, it depends on how you like to drive the car and how it\nfeels for you.",
		min=0, max=100,
		default=50,
	)
	quick_phys_bouncing: bpy.props.IntProperty(
		name="Bouncing",
		description="This defines how the car bounces back when it hits the ground or obstacles.\n\nBouncing can help when performing stunts as when you land up side down\nif the car bounces it can be filliped over before landing again to avoid a 'bad landing'.\n\nHowever bouncing is not helpful in controlling the car and in racing.",
		min=0, max=100,
		default=50,
	)
	quick_phys_lifts_others: bpy.props.IntProperty(
		name="Lifts Others",
		description="This defines if the car lifts up other cars when it collides with them from the front and\nhow high it can lift them.\n\nDoes the car have a pointy nose like MAX Revenge, Radical One or La Vita Crab, a\npointy nose/front part that can go under the wheels of other cars and lift them?\nIf so then give it some Lifts Others.\n\nIf it has a nose/front part that is a block like most cars then give it 0 Lifts Others.",
		min=0, max=100,
		default=50,
	)
	quick_phys_gets_lifted: bpy.props.IntProperty(
		name="Gets Lifted",
		description="This defines if the car can get lifted over other cars when it collides with them and how\nhigh it can get lifted.\n\nIs the car higher off the ground like Wow Caninaro or has big wheels like Dr Monstaa,\nshould its jump over cars when it collides with them?\nIf so then give it some Gets Lifted depending on how high it should go.\n\nIf the car is lower to the ground like most cars then it should have 0 Gets Lifted",
		min=0, max=100,
		default=50,
	)
	quick_phys_pushes_others: bpy.props.IntProperty(
		name="Pushes Others",
		description="This defines if the car pushes other cars away when it collides with them and how far it\ncan push them.\n\nIs the car a heavy car with a strong body like MASHEEN or El King, where when it\ncollides with other cars it pushes them away?\nOr does the car have special bumpers or body parts for pushing cars away like Sword of\nJustice has?\nIf so then give it some Pushes Others depending how strong you think it can push cars.\n\nIf it is a car like any other car, with an average weight and body strength then you should\ngive it 0 Pushes Others.",
		min=0, max=100,
		default=50,
	)
	quick_phys_gets_pushed: bpy.props.IntProperty(
		name="Gets Pushed",
		description="This defines if the car gets pushed away when it collides with other cars and how far it\ngets pushed away.\n\nIf the car is lighter then most cars, then it should get pushed away when it collides with\nothers cars.\nGetting pushed can be helpful if the car is week because it gets it away from the danger\n(from the car that hit it) faster, making it take lesser hits and escape better.\nHowever getting pushed is not helpful when racing.",
		min=0, max=100,
		default=50,
	)
	quick_phys_aerial_rotation_speed: bpy.props.IntProperty(
		name="Rotation Speed",
		description="This adjusts how fast the car can rotate and flip in the air when its performing a stunt.\n\nThis variable also depends on how much the \u2018Stunts\u2019 stat of the car is, if the car has a\nhigh Stunts stat then this variable will have a much bigger effect, if it has low Stunts stat\nthe variable will have a lower effect.\n\nIf you think the car is rotating too fast or too slow in the air when performing a stunt use\nthis variable to adjust that.\n\nIf the aerial rotation is too fast it can make the car hard to control in the air as it flips and\nhard to land upright.\n\nIf the car is a big and heavy car like MASHHEN or El King then it should have low\naerial rotation for a realistic effect.",
		min=0, max=100,
		default=50,
	)
	quick_phys_aerial_control_gliding: bpy.props.IntProperty(
		name="Control/Gliding",
		description="This adjusts the cars ability to push itself in the air and glide when performing stunts!\n\nIf you don\u2019t know, in the game:\nBackward looping pushes the car upwards. \nForward looping pushes the car forwards. \nLeft and right rolling pushes the car left and right. \n\nThis variable adjust the power if this aerial push.\n\nThe variable also depends on how much the \u2018Stunts\u2019 stat of the car is, if the car has a\nhigh Stunts stat then this variable will have a much bigger effect, if it has low Stunts stat\nthe variable will have a lower effect.\n\nIf the car has some kind of wings or fins like Radical One or Kool Kat have then it should\nhave higher aerial control and gliding ability.",
		min=0, max=100,
		default=50,
	)
	quick_phys_crash_radius: bpy.props.IntProperty(
		name="Radius",
		description="Crash Radius:\nThe radius around the crash at which the polygons/pieces that lay inside it get\naffected.\n\nOr basically in other words the number of pieces that get affected on collision (the pieces\naround the crash location).\n\nIncreasing the radius will result in more pieces/polygons around the point of collision\ngetting crashed and distorted.\nDecreasing the radius means less pieces/polygons around the collision point getting\ndistorted and crashed.",
		min=0, max=100,
		default=50,
	)
	quick_phys_crash_magnitude: bpy.props.IntProperty(
		name="Magnitude",
		description="Crash Magnitude:\nThe magnitude of the distortion and indentation to occur on the effected pieces/polygons.\n\nOr basically in other words the amount of destruction that happens to each piece when\ncrashed.\n\nHigher magnitude means the piece gets more destructed from an amount of damage,\nlower magnitude means the piece gets less destructed from that same amount of damage.",
		min=0, max=100,
		default=50,
	)
	quick_phys_crash_roof: bpy.props.IntProperty(
		name="Roof Destruction",
		description="Roof Destruction:\nThe amount of destruction to occur on the car\u2019s top.\nThe length of indentation and destruction to happen from above.\n\nTo really see this variable's effect try crashing the roof alone (without a normal crash),\ntry more then once while fixing the car and changing the variable\u2019s value to see the\ndifference.\n\nThe roof crash normally happens in the game when the car lands upside down from a\njump or when a big car like Dr Monstaa steps on it.",
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
		row = col.row()
		row.prop(self, "generate_wheels")
		if self.generate_wheels:
			row.prop(self, "quick_wheel_toggle")
			if self.quick_wheel_toggle:
				wheelBox = col.box()
				row = wheelBox.row(heading="BACK Wheels")
				row.prop(self, "quick_wheel_back_height")
				row.prop(self, "quick_wheel_back_width")
				row = wheelBox.row()
				row.prop(self, "quick_wheel_back_rim_color")
				row = wheelBox.row()
				row.prop(self, "quick_wheel_back_rim_size")
				row.prop(self, "quick_wheel_back_rim_depth")
				row.prop(self, "quick_wheel_back_hide")
				
				wheelBox = col.box()
				row = wheelBox.row(heading="FRONT Wheels")
				row.prop(self, "quick_wheel_front_height")
				row.prop(self, "quick_wheel_front_width")
				row = wheelBox.row()
				row.prop(self, "quick_wheel_front_rim_color")
				row = wheelBox.row()
				row.prop(self, "quick_wheel_front_rim_size")
				row.prop(self, "quick_wheel_front_rim_depth")
				row.prop(self, "quick_wheel_front_hide")
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