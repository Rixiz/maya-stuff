# -*- coding: utf-8 -*-

import maya.cmds as cmds
import re


def lock_selected_vertices(*args):
    """
    Locks the transformation of the currently selected vertices.
    """
    # Get the selected components as a flattened list
    # e.g., ['pCube1.vtx[0]', 'pCube1.vtx[1]', ... ]
    selected_vertices = cmds.ls(selection=True, flatten=True)

    if not selected_vertices:
        cmds.warning("No vertices are selected.")
        return

    locked_count = 0
    for vtx_component in selected_vertices:
        # Check if the selected item is a vertex (.vtx)
        if ".vtx[" in vtx_component:
            # Use regex to extract the object name and vertex index
            # e.g., 'pCube1.vtx[123]' -> obj='pCube1', index='123'
            match = re.search(r"(.+)\.vtx\[(\d+)\]", vtx_component)
            if match:
                object_name = match.group(1)
                vertex_index = match.group(2)

                # Get the shape node from the object name
                shapes = cmds.listRelatives(object_name, shapes=True, path=True)
                if not shapes:
                    continue

                shape_name = shapes[0]

                # Lock the position attributes for each axis
                try:
                    cmds.setAttr(f"{shape_name}.pnts[{vertex_index}].pntx", lock=True)
                    cmds.setAttr(f"{shape_name}.pnts[{vertex_index}].pnty", lock=True)
                    cmds.setAttr(f"{shape_name}.pnts[{vertex_index}].pntz", lock=True)
                    locked_count += 1
                except Exception as e:
                    print(f"Failed to lock vertex {vtx_component}: {e}")

    if locked_count > 0:
        print(f"Success: Locked {locked_count} vertices.")
    else:
        cmds.warning("No valid vertices found to lock.")


def unlock_all_vertices_on_object(*args):
    """
    Unlocks all vertices on the selected object(s).
    """
    # Get the selected objects (transform nodes)
    selected_objects = cmds.ls(selection=True, objectsOnly=True)

    if not selected_objects:
        cmds.warning("No objects are selected.")
        return

    unlocked_obj_count = 0
    for obj in selected_objects:
        # Get the shape node from the object
        shapes = cmds.listRelatives(obj, shapes=True, path=True)
        if not shapes:
            print(f"Skipping {obj}: No polygon shape found.")
            continue

        shape_name = shapes[0]

        # Get the total number of vertices for the object
        try:
            num_vertices = cmds.polyEvaluate(shape_name, vertex=True)
        except:
            # Skip if it's not a polygon mesh
            print(f"Skipping {obj}: Not a polygon mesh.")
            continue

        # Loop through all vertices and unlock them
        for i in range(num_vertices):
            try:
                cmds.setAttr(f"{shape_name}.pnts[{i}].pntx", lock=False)
                cmds.setAttr(f"{shape_name}.pnts[{i}].pnty", lock=False)
                cmds.setAttr(f"{shape_name}.pnts[{i}].pntz", lock=False)
            except Exception as e:
                # Ignore errors, e.g., if already unlocked
                pass

        print(f"Success: Unlocked all vertices on {obj}.")
        unlocked_obj_count += 1

    if unlocked_obj_count == 0:
        cmds.warning("No valid objects found to unlock.")


def create_vertex_locker_ui():
    """
    Creates the UI window for the tool.
    """
    window_id = "VertexLockerWindow"

    if cmds.window(window_id, exists=True):
        cmds.deleteUI(window_id)

    cmds.window(window_id, title="Vertex Locker", widthHeight=(70, 140))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=1, columnAttach=("both", 0))

    cmds.button(
        label="Lock Selected Vertices",
        command=lock_selected_vertices,
        height=25,
        backgroundColor=(0.8, 0.4, 0.4),
    )

    cmds.button(
        label="Unlock All on Object",
        command=unlock_all_vertices_on_object,
        height=25,
        backgroundColor=(0.4, 0.8, 0.4),
    )

    cmds.showWindow(window_id)


# --- Run the script ---
if __name__ == "__main__":
    create_vertex_locker_ui()
