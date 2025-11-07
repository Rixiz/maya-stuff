import maya.cmds as cmds
import os

def create_texture_nodes_from_directory(directory, prefix, extension):
    renderer = cmds.optionMenu('renderer_menu', q=True, value=True)
    
    # シェーダー名を取得（入力がない場合はデフォルト名を使用）
    shader_name = cmds.textField('shader_name_field', q=True, text=True).strip()
    if not shader_name:
        shader_name = 'VRayMtl' if renderer == 'VRayMtl' else 'aiStandardSurface'
    
    # 選択されたオブジェクトとシェーダーノードを取得
    selected_objects = cmds.ls(sl=True, transforms=True)
    selected_shaders = cmds.ls(sl=True, materials=True)

    if not selected_objects and not selected_shaders:
        cmds.warning("Please select at least one object or one material.")
        return
    
    if selected_shaders:
        shader_node = selected_shaders[0]

        # オプションメニューで選択されたマテリアルと一致するか確認
        if (renderer == 'VRayMtl' and cmds.nodeType(shader_node) != 'VRayMtl') or (renderer == 'aiStandardSurface' and cmds.nodeType(shader_node) != 'aiStandardSurface'):
            cmds.warning("Selected material does not match the chosen material type.")
            return

    project_dir = cmds.workspace(q=True, rd=True)
    sourceimages_dir = os.path.join(project_dir, "sourceimages")

    # ファイル名のパターンに基づいてファイルを検索
    texture_patterns = {
        'Albedo': ['_Albedo', '_Diffuse', '_BaseColor', '_Color'],
        'Metalness': ['_Metalness', '_Metallic'],
        'Roughness': ['_Roughness', '_Rough', '_Glossiness', '_Gloss'],
        'Normal': ['_Normal'],
        'Opacity': ['_Opacity'],
        'Translucency': ['_Translucency', '_SSS']
    }

    file_paths = {}
    
    for file in os.listdir(directory):
        # prefixが一致しない場合、または拡張子が一致しない場合はスキップ
        if not file.startswith(prefix) or not file.endswith(extension):
            continue
        for texture_type, patterns in texture_patterns.items():
            for pattern in patterns:
                if pattern in file:
                    full_path = os.path.join(directory, file)
                    start_dir = directory.split('sourceimages')[0]
                    cmds.warning(directory.split('sourceimages')[0])
                    relative_path = os.path.relpath(full_path, start=start_dir)
                    file_paths[texture_type] = relative_path
                    break
    
    if not file_paths:
        cmds.warning("No valid texture files found in the directory.")
        return


    # create file nodes based on found textures
    file_nodes = {}
    for name, path in file_paths.items():
        file_node = cmds.shadingNode('file', asTexture=True, name=f'{name}_file')
        place2d_node = cmds.shadingNode('place2dTexture', asUtility=True, name=f'{name}_place2d')
        cmds.connectAttr(f'{place2d_node}.outUV', f'{file_node}.uvCoord')
        cmds.connectAttr(f'{place2d_node}.outUvFilterSize', f'{file_node}.uvFilterSize')

        # Metalness, Roughness, Opacityに対してalphaIsLuminanceを有効にする
        if name in ['Metalness', 'Roughness', 'Opacity']:
            cmds.setAttr(f'{file_node}.alphaIsLuminance', True)

        # 特定のテクスチャに対してuvTilingModeを設定
        if name in ['Albedo', 'Metalness', 'Roughness', 'Normal', 'Opacity']:
            cmds.setAttr(f"{file_node}.uvTilingMode", 3)

        # ファイルテクスチャ名を設定
        cmds.setAttr(f'{file_node}.fileTextureName', path, type='string')
 
        # Metalness, Roughness, Normal, Opacityに対してRawカラースペースを設定
        if name in ['Metalness', 'Roughness', 'Normal', 'Opacity']:
            cmds.setAttr(f'{file_node}.colorSpace', 'Raw', type='string')

        # Albedoに対してsRGBカラースペースを設定
        if name == 'Albedo':
            cmds.setAttr(f'{file_node}.colorSpace', 'sRGB', type='string')

        cmds.setAttr(f'{file_node}.ignoreColorSpaceFileRules', True)  # ignore CS File Rule を有効にする
        file_nodes[name] = file_node

    # シェーダーノードを作成または取得
    if selected_shaders:
        shader_node = selected_shaders[0]
        
        connections = cmds.listConnections(shader_node, destination=False, source=True)
        if connections:
            for conn in connections:
                if cmds.nodeType(conn) == 'file':
                    place2d_conns = cmds.listConnections(conn, type='place2dTexture')
                    if place2d_conns:
                        cmds.delete(place2d_conns)
                    cmds.delete(conn)

    else:
        if renderer == 'VRayMtl':
            shader_node = cmds.shadingNode('VRayMtl', asShader=True, name=shader_name)
        elif renderer == 'aiStandardSurface':
            shader_node = cmds.shadingNode('aiStandardSurface', asShader=True, name=shader_name)
        # シェーダーグループを作成
        shading_group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=f'{shader_node}SG')
        cmds.connectAttr(f'{shader_node}.outColor', f'{shading_group}.surfaceShader', force=True)

    # ファイルノードをシェーダーノードに接続
    if renderer == 'VRayMtl':
        cmds.setAttr(f'{shader_node}.bumpMapType', 1)
        if 'Albedo' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Albedo"]}.outColor', f'{shader_node}.diffuseColor', force=True)
        if 'Metalness' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Metalness"]}.outAlpha', f'{shader_node}.metalness', force=True)
        if 'Roughness' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Roughness"]}.outAlpha', f'{shader_node}.reflectionGlossiness', force=True)
            if cmds.checkBox('cb_invert_alpha', q=True, value=True):
                cmds.setAttr(f'{file_nodes["Roughness"]}.invert', 1)
            if cmds.checkBox('cb_use_roughness', q=True, value=True):
                cmds.setAttr(f'{shader_node}.useRoughness', 1)
        if 'Normal' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Normal"]}.outColor', f'{shader_node}.bumpMap', force=True)
        if 'Opacity' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Opacity"]}.outColor', f'{shader_node}.opacityMap', force=True)
        if 'Translucency' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Translucency"]}.outColor', f'{shader_node}.translucencyColor', force=True)
    elif renderer == 'aiStandardSurface':
        if 'Albedo' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Albedo"]}.outColor', f'{shader_node}.baseColor', force=True)
        if 'Metalness' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Metalness"]}.outAlpha', f'{shader_node}.metalness', force=True)
        if 'Roughness' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Roughness"]}.outAlpha', f'{shader_node}.specularRoughness', force=True)
            if cmds.checkBox('cb_invert_alpha', q=True, value=True):
                cmds.setAttr(f'{file_nodes["Roughness"]}.invert', 1)
        if 'Normal' in file_nodes:
            normal_map_node = cmds.shadingNode('aiNormalMap', asUtility=True, name='NormalMap_node')
            cmds.connectAttr(f'{file_nodes["Normal"]}.outColor', f'{normal_map_node}.input', force=True)
            cmds.setAttr(f'{normal_map_node}.strength', 1)
            cmds.connectAttr(f'{normal_map_node}.outValue', f'{shader_node}.normalCamera', force=True)
        if 'Opacity' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Opacity"]}.outColor', f'{shader_node}.opacity', force=True)
        if 'Translucency' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Translucency"]}.outColor', f'{shader_node}.subsurfaceColor', force=True)

    # シェーダーグループを選択されたオブジェクトに適用
    if selected_objects:
        for obj in selected_objects:
            cmds.sets(obj, e=True, forceElement=shading_group)
    else:
        cmds.warning("No objects selected. Only shader modifications applied.")

def select_initial_albedo_file(*args):
    base_file = cmds.fileDialog2(fileFilter='Image Files (*.png *.jpeg *.bmp *.exr *.tga *.jpg *.tiff *.tif *);;', fileMode=1, caption='Select First Texture File')
    if base_file:
        directory = os.path.dirname(base_file[0])
        prefix = os.path.basename(base_file[0]).rsplit('_', 1)[0]
        extension = os.path.basename(base_file[0]).split('.')[-1]
        create_texture_nodes_from_directory(directory, prefix, extension)
    elif not base_file:
        cmds.warning("Please select at least one texture file.")
        return

def create_texture_nodes(*args):
    renderer = cmds.optionMenu('renderer_menu', q=True, value=True)
    
    # シェーダー名を取得（入力がない場合はデフォルト名を使用）
    shader_name = cmds.textField('shader_name_field', q=True, text=True).strip()
    if not shader_name:
        shader_name = 'VRayMtl' if renderer == 'VRayMtl' else 'aiStandardSurface'
    
    # 選択されたオブジェクトとシェーダーノードを取得
    selected_objects = cmds.ls(sl=True, transforms=True)
    selected_shaders = cmds.ls(sl=True, materials=True)

    if not selected_objects and not selected_shaders:
        cmds.warning("Please select at least one object or one material.")
        return

    if selected_shaders:
        shader_node = selected_shaders[0]

        # オプションメニューで選択されたマテリアルと一致するか確認
        if (renderer == 'VRayMtl' and cmds.nodeType(shader_node) != 'VRayMtl') or (renderer == 'aiStandardSurface' and cmds.nodeType(shader_node) != 'aiStandardSurface'):
            cmds.warning("Selected material does not match the chosen material type.")
            return

    
    # チェックされたもののみ実行するためのフラグとファイルパスのリストを用意
    create_flags = {
        'Albedo': cmds.checkBox('cb_albedo', q=True, value=True),
        'Metalness': cmds.checkBox('cb_metalness', q=True, value=True),
        'Roughness': cmds.checkBox('cb_roughness', q=True, value=True),
        'Normal': cmds.checkBox('cb_normal', q=True, value=True),
        'Opacity': cmds.checkBox('cb_opacity', q=True, value=True),
        'Translucency': cmds.checkBox('cb_translucency', q=True, value=True)
    }
    if not any(create_flags.values()):
        cmds.warning("Please select at least one texture type.")
        return

    file_paths = {}
    for name in create_flags:
        if create_flags[name]:
            file_path = cmds.fileDialog2(fileFilter='Image Files (*.png *.jpeg *.bmp *.exr *.tga *.jpg *.tiff *.tif *);;', fileMode=1, caption=f'Select {name} Image File')
            if file_path:
                file_paths[name] = file_path[0]
            else:
                create_flags[name] = False  # ファイルが選択されなかった場合はフラグをFalseに設定
                cmds.warning("Please select at least one texture file.")
                return

    # create file nodes based on selected checkboxes
    file_nodes = {}
    for name in create_flags:
        if create_flags[name]:
            file_node = cmds.shadingNode('file', asTexture=True, isColorManaged=True, name=f'{name}_file')
            place2d_node = cmds.shadingNode('place2dTexture', asUtility=True, name=f'{name}_place2d')
            cmds.connectAttr(f'{place2d_node}.outUV', f'{file_node}.uvCoord')
            cmds.connectAttr(f'{place2d_node}.outUvFilterSize', f'{file_node}.uvFilterSize')
            if name in ['Metalness', 'Roughness', 'Opacity']:
                cmds.setAttr(f'{file_node}.alphaIsLuminance', True)
            if name in ['Albedo', 'Metalness', 'Roughness', 'Normal', 'Opacity', 'Translucency']:
                cmds.setAttr(f"{file_node}.uvTilingMode", 3)
            cmds.setAttr(f'{file_node}.fileTextureName', file_paths[name], type='string')
            if name in ['Metalness', 'Roughness', 'Normal', 'Opacity']:
                cmds.setAttr(f'{file_node}.colorSpace', 'Raw', type='string')
            cmds.setAttr(f'{file_node}.ignoreColorSpaceFileRules', True)  # ignore CS File Rule を有効にする
            file_nodes[name] = file_node

    # シェーダーノードを作成または取得
    if selected_shaders:
        shader_node = selected_shaders[0]
        
        connections = cmds.listConnections(shader_node, destination=False, source=True)
        if connections:
            for conn in connections:
                if cmds.nodeType(conn) == 'file':
                    place2d_conns = cmds.listConnections(conn, type='place2dTexture')
                    if place2d_conns:
                        cmds.delete(place2d_conns)
                    cmds.delete(conn)

    else:
        if renderer == 'VRayMtl':
            shader_node = cmds.shadingNode('VRayMtl', asShader=True, name=shader_name)
        elif renderer == 'aiStandardSurface':
            shader_node = cmds.shadingNode('aiStandardSurface', asShader=True, name=shader_name)
        # シェーダーグループを作成
        shading_group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=f'{shader_node}SG')
        try:
            cmds.connectAttr(f'{shader_node}.outColor', f'{shading_group}.surfaceShader', force=True)
        except:
            cmds.warning("Couldn't connect node. Make sure render engine is installed.")
            for unused_node in [shader_node, file_node, shading_group, place2d_node]:
                cmds.delete(unused_node)
            return

    # ファイルノードをシェーダーノードに接続
    if renderer == 'VRayMtl':
        cmds.setAttr(f'{shader_node}.bumpMapType', 1)
        if 'Albedo' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Albedo"]}.outColor', f'{shader_node}.diffuseColor', force=True)
        if 'Metalness' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Metalness"]}.outAlpha', f'{shader_node}.metalness', force=True)
        if 'Roughness' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Roughness"]}.outAlpha', f'{shader_node}.reflectionGlossiness', force=True)
            # Roughnessの反転処理
            if cmds.checkBox('cb_invert_alpha', q=True, value=True):
                cmds.setAttr(f'{file_node}.invert', 1)
            if create_flags['Roughness'] and cmds.checkBox('cb_use_roughness', q=True, value=True):
                cmds.setAttr(f'{shader_node}.useRoughness', 1)
        if 'Normal' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Normal"]}.outColor', f'{shader_node}.bumpMap', force=True)
        if 'Opacity' in file_nodes:
            # OpacityにはColorチャンネルを使用
            cmds.connectAttr(f'{file_nodes["Opacity"]}.outColor', f'{shader_node}.opacityMap', force=True)
        if 'Translucency' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Translucency"]}.outColor', f'{shader_node}.translucencyColor', force=True)
    elif renderer == 'aiStandardSurface':
        if 'Albedo' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Albedo"]}.outColor', f'{shader_node}.baseColor', force=True)
        if 'Metalness' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Metalness"]}.outAlpha', f'{shader_node}.metalness', force=True)
        if 'Roughness' in file_nodes:
            cmds.connectAttr(f'{file_nodes["Roughness"]}.outAlpha', f'{shader_node}.specularRoughness', force=True)
            if cmds.checkBox('cb_invert_alpha', q=True, value=True):
                cmds.setAttr(f'{file_node}.invert', 1)
        if 'Normal' in file_nodes:
            # Create a normal map node for Arnold
            normal_map_node = cmds.shadingNode('aiNormalMap', asUtility=True, name='NormalMap_node')
            cmds.connectAttr(f'{file_nodes["Normal"]}.outColor', f'{normal_map_node}.input', force=True)
            cmds.setAttr(f'{normal_map_node}.strength', 1)
            cmds.connectAttr(f'{normal_map_node}.outValue', f'{shader_node}.normalCamera', force=True)
        if 'Opacity' in file_nodes:
            # OpacityにはColorチャンネルを使用
            cmds.connectAttr(f'{file_nodes["Opacity"]}.outColor', f'{shader_node}.opacity', force=True)
        if 'Translucency' in file_nodes:
            # OpacityにはColorチャンネルを使用
            cmds.connectAttr(f'{file_nodes["Translucency"]}.outColor', f'{shader_node}.subsurfaceColor', force=True)
    # シェーダーグループを選択されたオブジェクトに適用
    if selected_objects:
        for obj in selected_objects:
            cmds.sets(obj, e=True, forceElement=shading_group)
    else:
        cmds.warning("No objects selected. Only shader modifications applied.")
    
def select_material_from_selected_objects(*args):
    # 選択されたオブジェクトを取得
    selected_objects = cmds.ls(sl=True, long=True, transforms=True)
    
    if not selected_objects:
        cmds.warning("Please select at least one object.")
        return
    
    # オブジェクトに割り当てられているシェーダーを取得
    materials = set()
    for obj in selected_objects:
        # オブジェクトのシェイプを取得
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True)
        if shapes:
            for shape in shapes:
                # シェイプに接続されているシェーディンググループを取得
                shading_groups = cmds.listConnections(shape, type='shadingEngine')
                if shading_groups:
                    for sg in shading_groups:
                        # シェーディンググループに接続されているマテリアルを取得
                        surface_shaders = cmds.listConnections(sg + '.surfaceShader', destination=False, source=True)
                        if surface_shaders:
                            for shader in surface_shaders:
                                # フルパスを取得
                                full_path_shader = cmds.ls(shader, long=True)
                                if full_path_shader:
                                    materials.add(full_path_shader[0])
    
    if materials:
        cmds.select(list(materials), replace=True)
    else:
        cmds.warning("No materials found for the selected objects.")

def update_checkbox(*args):
    renderer = cmds.optionMenu('renderer_menu', query=True, value=True)
    if renderer == 'aiStandardSurface':
        cmds.checkBox('cb_use_roughness', edit=True, enable=False)
    else:
        cmds.checkBox('cb_use_roughness', edit=True, enable=True)

def update_mode_selection(*args):
    mode_select = cmds.optionMenu('selection_mode_menu', query=True, value=True)
    if mode_select == 'Auto':
        for cb in ['cb_albedo', 'cb_metalness', 'cb_roughness', 'cb_normal', 'cb_opacity', 'cb_translucency']:
            cmds.checkBox(cb, edit=True, enable=False)
    else:
        for cb in ['cb_albedo', 'cb_metalness', 'cb_roughness', 'cb_normal', 'cb_opacity', 'cb_translucency']:
            cmds.checkBox(cb, edit=True, enable=True)

def create(*args):
    mode_select = cmds.optionMenu('selection_mode_menu', query=True, value=True)
    if mode_select == 'Auto':
        select_initial_albedo_file()
    else:
        create_texture_nodes()
    

# UIの作成
if cmds.window('texture_window', exists=True):
    cmds.deleteUI('texture_window')

window = cmds.window('texture_window', title='RixTexAssigner', widthHeight=(160, 340), sizeable=False, mxb = False, mnb = False, tlb=True)
cmds.columnLayout(adjustableColumn=True, rowSpacing=2, columnAlign='center', columnAttach=('both', 3))

# Renderer selection
cmds.optionMenu('renderer_menu', label='Material', changeCommand=update_checkbox)
cmds.menuItem(label='VRayMtl')
cmds.menuItem(label='aiStandardSurface')

# Shader name input
cmds.textField('shader_name_field', placeholderText='Material Name (Optional)', width=140)
cmds.button(label='Pick Material from Object', command=select_material_from_selected_objects, height=20, bgc=(0.2, 0.3, 0.2))

# Checkboxes
cmds.frameLayout(label='Select Textures', marginWidth=2, marginHeight=2)
cmds.columnLayout(adjustableColumn=True, rowSpacing=2, columnAlign='center')
# Auto/Manual Selection
cmds.optionMenu('selection_mode_menu', label='Selection Mode', cc=update_mode_selection)
cmds.menuItem(label='Manual')
cmds.menuItem(label='Auto')
cmds.checkBox('cb_albedo', label='Albedo | Diffuse')
cmds.checkBox('cb_metalness', label='Metalness')
cmds.checkBox('cb_roughness', label='Rough | Gloss')
cmds.checkBox('cb_normal', label='Normal')
cmds.checkBox('cb_opacity', label='Opacity')
cmds.checkBox('cb_translucency', label='Translucency | SSS')
cmds.setParent('..')
cmds.setParent('..')

# Roughness Options
cmds.frameLayout(label='Roughness Options', marginWidth=2, marginHeight=2)
cmds.columnLayout(adjustableColumn=True, rowSpacing=2, columnAlign='center')
cmds.checkBox('cb_invert_alpha', label='Invert Alpha')
cmds.checkBox('cb_use_roughness', label=' VRay<Use Roughness>', value=True)
cmds.setParent('..')
cmds.setParent('..')

# Create button
cmds.button(label='Create　/　Replace', command=create, height=30, bgc=(0.2, 0.2, 0.5))
cmds.setParent('..')

cmds.showWindow(window)
