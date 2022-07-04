bl_info = {
    "name": "Export to rad (NFM)",
    "author": "Cephalobyte",
    "version": (1, 15, 0),
    "blender": (3, 2, 0),
    "location": "View3D > Object Context Menu > Create NfM Car Maker file",
    "description": "Creates a '.rad' text file from the selected object, compatible with _Need for Madness? Car Maker_.",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}


import bpy

class ExamplePanel(bpy.types.Panel):
    
    bl_idname = 'VIEW3D_PT_example_panel'
    bl_label = 'Example Panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    
    def draw(self, context):
        self.layout.label(text='Hello there')


CLASSES = [
		ExamplePanel,
]

def register():
		print('registered') # just for debug
		for klass in CLASSES:
				bpy.utils.register_class(klass)

def unregister():
		print('unregistered') # just for debug
		for klass in CLASSES:
				bpy.utils.unregister_class(klass)


if __name__ == '__main__':
		register()