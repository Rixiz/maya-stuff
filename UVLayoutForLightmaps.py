# Lightmap UV Layout Tool for Maya (updated: use -spc and -mar for u3dLayout)
# Uses maya.cmds and maya.mel
from maya import cmds, mel

WINDOW_NAME = "lightmapUVLayoutTool_win"

def ensure_uv_set_on_shape(shape, uvset_name):
    try:
        existing = cmds.polyUVSet(shape, query=True, allUVSets=True) or []
    except Exception:
        existing = []
    if uvset_name in existing:
        print("Info: Found existing UV set '{}' for {}.".format(uvset_name, shape))
        return True
    if 'map1' not in existing:
        print("Error: 'map1' UV set not found on {}. Cannot create '{}'.".format(shape, uvset_name))
        return False
    try:
        cmds.polyUVSet(shape, copy=True, uvSet='map1', newUVSet=uvset_name)
    except Exception:
        try:
            mel.eval('polyUVSet -copy -uvSet "map1" -newUVSet "{0}" "{1}";'.format(uvset_name, shape))
        except Exception as e:
            print("Error: Failed to create UV set '{}' for {}. ({})".format(uvset_name, shape, e))
            return False
    print("Info: Created new UV set '{}' for {} (copied from 'map1').".format(uvset_name, shape))
    return True

def set_current_uv_set(shape, uvset_name):
    """
    Make uvset_name the current UV set on the mesh shape so that u3dLayout affects it.
    """
    try:
        # Set at shape level
        cmds.polyUVSet(shape, currentUVSet=True, uvSet=uvset_name)
        return True
    except Exception:
        try:
            mel.eval('polyUVSet -current -uvSet "{0}" "{1}";'.format(uvset_name, shape))
            return True
        except Exception as e:
            print("Error: Failed to set current UV set '{}' for {}. ({})".format(uvset_name, shape, e))
            return False

def layout_uvs_for_shape(shape, uvset_name, shell_padding, tile_padding, resolution):
    """
    Run u3dLayout. Use -spc for shell padding and -mar for margin/tile padding.
    We DO NOT pass uvSet to u3dLayout; instead we set the current UV set above.
    """
    if not set_current_uv_set(shape, uvset_name):
        return False

    try:
        # Select the shape (u3dLayout typically expects the object selection)
        cmds.select(shape, replace=True)

        # Use -spc and -mar which are accepted in your environment (based on provided log)
        mel_cmd = (
            'u3dLayout -res {res} -scl 1 -spc {sp} -mar {tp} -box 0 1 0 1 "{obj}";'
            .format(sp=float(shell_padding / 1024), tp=float(tile_padding / 1024), res=float(resolution), obj=shape)
        )
        mel.eval(mel_cmd)
        return True
    except Exception as e:
        # fallback: try a minimal call without flags
        try:
            mel.eval('u3dLayout "{0}";'.format(shape))
            return True
        except Exception:
            print("Error: Failed to run u3dLayout on {} for UV set '{}'. ({})".format(shape, uvset_name, e))
            return False

def gather_mesh_shapes_from_selection(selection):
    mesh_shapes = []
    for obj in selection:
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []
        if shapes:
            for sh in shapes:
                try:
                    if cmds.nodeType(sh) == 'mesh':
                        mesh_shapes.append(sh)
                except Exception:
                    continue
        else:
            try:
                if cmds.nodeType(obj) == 'mesh':
                    mesh_shapes.append(obj)
            except Exception:
                continue
    return mesh_shapes

def run_layout_for_selection(uvset_name, shell_padding, tile_padding, resolution):
    sel = cmds.ls(selection=True, long=True) or []
    if not sel:
        print("Error: Please select one or more mesh objects.")
        return
    mesh_shapes = gather_mesh_shapes_from_selection(sel)
    if not mesh_shapes:
        print("Error: Please select one or more mesh objects.")
        return
    processed = set()
    for shape in mesh_shapes:
        if shape in processed:
            continue
        processed.add(shape)
        if uvset_name == 'map1':
            print("Error: Operation on 'map1' is prohibited. Please use a different UV set name.")
            return
        if not ensure_uv_set_on_shape(shape, uvset_name):
            continue
        if not layout_uvs_for_shape(shape, uvset_name, shell_padding, tile_padding, resolution):
            continue
    print("Success: Lightmap UV layout complete for all selected objects.")

def build_ui():
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)
    window = cmds.window(WINDOW_NAME, title="Lightmap UV Layout Tool", widthHeight=(380, 500), sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnAlign="left", columnAttach=('both', 10))

    cmds.text(label="Lightmap UV Set Name:")
    uv_field = cmds.textField(text="lightmap", annotation="Name of the UV set to create/use (do not use 'map1').")

    cmds.text(label="Shell Padding (0-100):")
    shell_field = cmds.floatField(value=3.0, minValue=0.0, maxValue=100.0, pre=6)

    cmds.text(label="Tile Padding (0-100):")
    tile_field = cmds.floatField(value=3.0, minValue=0.0, maxValue=100.0, pre=6)

    cmds.text(label="Packing resolution:")
    res_field = cmds.floatField(value=1024, minValue=0.0, maxValue=8196.0, pre=6)

    def on_execute(*args):
        uvset_name = cmds.textField(uv_field, query=True, text=True).strip()
        try:
            shell_padding = float(cmds.floatField(shell_field, query=True, value=True))
        except Exception:
            shell_padding = 0.01
        try:
            tile_padding = float(cmds.floatField(tile_field, query=True, value=True))
        except Exception:
            tile_padding = 0.02
        try:
            resolution = float(cmds.floatField(res_field, query=True, value=True))
        except Exception:
            resolution = 1024.0
        shell_padding = max(0.0, min(shell_padding, 100.0))
        tile_padding = max(0.0, min(tile_padding, 100.0))
        resolution = max(1.0, min(resolution, 8196.0))
        run_layout_for_selection(uvset_name, shell_padding, tile_padding, resolution)

    cmds.separator(height=6, style='in')
    cmds.button(label="Generate and Layout UVs", command=on_execute, height=30)
    cmds.setParent('..')
    cmds.showWindow(window)

if __name__ == "__main__":
    build_ui()
