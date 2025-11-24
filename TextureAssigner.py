import maya.cmds as cmds
import os

# --- 設定: テクスチャごとのパラメーター定義 ---
TEXTURE_SETTINGS = {
    "Albedo": {"colorspace": "sRGB", "alphaIsLuminance": False},
    "Metalness": {"colorspace": "Raw", "alphaIsLuminance": True},
    "Roughness": {"colorspace": "Raw", "alphaIsLuminance": True},
    "Normal": {"colorspace": "Raw", "alphaIsLuminance": False},
    "Opacity": {"colorspace": "Raw", "alphaIsLuminance": True},
    "Translucency": {"colorspace": "sRGB", "alphaIsLuminance": False},
}

# --- 設定: ファイル名検索用パターン ---
TEXTURE_PATTERNS = {
    "Albedo": ["_Albedo", "_Diffuse", "_BaseColor", "_Color"],
    "Metalness": ["_Metalness", "_Metallic"],
    "Roughness": ["_Roughness", "_Rough", "_Glossiness", "_Gloss"],
    "Normal": ["_Normal"],
    "Opacity": ["_Opacity"],
    "Translucency": ["_Translucency", "_SSS"],
}

# --- 設定: レンダラーごとの接続ルール ---
# {TextureType: (AttributeName, SourceChannel)}
# SourceChannel: 'outColor' or 'outAlpha'
RENDERER_MAPPINGS = {
    "VRayMtl": {
        "Albedo": ("diffuseColor", "outColor"),
        "Metalness": ("metalness", "outAlpha"),
        "Roughness": ("reflectionGlossiness", "outAlpha"),
        "Normal": ("bumpMap", "outColor"),
        "Opacity": ("opacityMap", "outColor"),  # VRay opacity often uses color
        "Translucency": ("translucencyColor", "outColor"),
    },
    "aiStandardSurface": {
        "Albedo": ("baseColor", "outColor"),
        "Metalness": ("metalness", "outAlpha"),
        "Roughness": ("specularRoughness", "outAlpha"),
        "Normal": ("normalCamera", "outColor"),  # Special case handled in logic
        "Opacity": ("opacity", "outColor"),
        "Translucency": ("subsurfaceColor", "outColor"),
    },
}


def get_shader_node(renderer, shader_name_input=None):
    """選択または新規作成でシェーダーノードを取得する"""
    selected_shaders = cmds.ls(sl=True, materials=True)

    # 既存シェーダーが選択されている場合
    if selected_shaders:
        shader_node = selected_shaders[0]
        # 型チェック
        if (renderer == "VRayMtl" and cmds.nodeType(shader_node) != "VRayMtl") or (
            renderer == "aiStandardSurface"
            and cmds.nodeType(shader_node) != "aiStandardSurface"
        ):
            cmds.warning("Selected material does not match the chosen material type.")
            return None
        return shader_node

    # 新規作成の場合
    shader_name = shader_name_input.strip() if shader_name_input else renderer
    if renderer == "VRayMtl":
        shader = cmds.shadingNode("VRayMtl", asShader=True, name=shader_name)
    else:
        shader = cmds.shadingNode("aiStandardSurface", asShader=True, name=shader_name)

    # SG作成と接続
    sg = cmds.sets(
        renderable=True, noSurfaceShader=True, empty=True, name=f"{shader}SG"
    )
    cmds.connectAttr(f"{shader}.outColor", f"{sg}.surfaceShader", force=True)

    # オブジェクトへの割り当て
    selected_objects = cmds.ls(sl=True, transforms=True)
    if selected_objects:
        for obj in selected_objects:
            cmds.sets(obj, e=True, forceElement=sg)

    return shader


def clean_old_connections(shader_node):
    """シェーダーに接続されている既存のファイルノードを掃除する"""
    connections = cmds.listConnections(shader_node, destination=False, source=True)
    if connections:
        for conn in connections:
            if cmds.nodeType(conn) == "file":
                place2d_conns = cmds.listConnections(conn, type="place2dTexture")
                if place2d_conns:
                    # 他で使われていないか厳密にチェックするのが理想だが、
                    # このツールの仕様上、リプレイス動作として削除する
                    cmds.delete(place2d_conns)
                cmds.delete(conn)


def create_and_connect_textures(file_paths, renderer):
    """
    メインロジック: パス辞書を受け取り、ノード作成・接続を一括で行う
    file_paths: {"Albedo": "path/to/file.png", ...}
    """
    shader_name_input = cmds.textField("shader_name_field", q=True, text=True)
    shader_node = get_shader_node(renderer, shader_name_input)
    if not shader_node:
        return

    # 既存接続のクリア
    clean_old_connections(shader_node)

    # 1. 共有 place2dTexture ノードの作成
    place2d_name = "Shared_Place2d"
    # 接頭辞があれば名前を工夫する（Autoモード時など）
    first_path = next(iter(file_paths.values()))
    prefix = os.path.basename(first_path).split("_")[0]
    if prefix:
        place2d_name = f"{prefix}_place2d"

    place2d_node = cmds.shadingNode("place2dTexture", asUtility=True, name=place2d_name)

    # 2. Fileノードの作成と設定
    file_nodes = {}
    for tex_type, path in file_paths.items():
        settings = TEXTURE_SETTINGS.get(tex_type, {})

        file_node = cmds.shadingNode(
            "file", asTexture=True, isColorManaged=True, name=f"{tex_type}_file"
        )
        file_nodes[tex_type] = file_node

        # 基本設定
        cmds.setAttr(f"{file_node}.fileTextureName", path, type="string")
        cmds.setAttr(f"{file_node}.uvTilingMode", 3)  # UDIM etc
        cmds.setAttr(f"{file_node}.ignoreColorSpaceFileRules", True)

        # カラースペース設定
        cs = settings.get("colorspace", "sRGB")
        cmds.setAttr(f"{file_node}.colorSpace", cs, type="string")

        # Alpha is Luminance
        if settings.get("alphaIsLuminance", False):
            cmds.setAttr(f"{file_node}.alphaIsLuminance", True)

        # Place2d 接続
        cmds.connectAttr(f"{place2d_node}.outUV", f"{file_node}.uvCoord")
        cmds.connectAttr(f"{place2d_node}.outUvFilterSize", f"{file_node}.uvFilterSize")

    # 3. シェーダーへの接続
    mapping = RENDERER_MAPPINGS.get(renderer)

    # VRay固有設定
    if renderer == "VRayMtl":
        cmds.setAttr(f"{shader_node}.bumpMapType", 1)  # Normal Map
        if "Roughness" in file_paths and cmds.checkBox(
            "cb_use_roughness", q=True, value=True
        ):
            cmds.setAttr(f"{shader_node}.useRoughness", 1)

    for tex_type, file_node in file_nodes.items():
        if tex_type not in mapping:
            continue

        target_attr, source_channel = mapping[tex_type]

        # Normal Map 特殊処理 (Arnold)
        if renderer == "aiStandardSurface" and tex_type == "Normal":
            normal_map_node = cmds.shadingNode(
                "aiNormalMap", asUtility=True, name="NormalMap_node"
            )
            cmds.connectAttr(
                f"{file_node}.outColor", f"{normal_map_node}.input", force=True
            )
            cmds.setAttr(f"{normal_map_node}.strength", 1)
            cmds.connectAttr(
                f"{normal_map_node}.outValue", f"{shader_node}.normalCamera", force=True
            )
            continue

        # Roughness 反転処理
        if tex_type == "Roughness" and cmds.checkBox(
            "cb_invert_alpha", q=True, value=True
        ):
            cmds.setAttr(f"{file_node}.invert", 1)

        # 通常接続
        try:
            cmds.connectAttr(
                f"{file_node}.{source_channel}",
                f"{shader_node}.{target_attr}",
                force=True,
            )
        except Exception as e:
            print(f"Connection warning: {e}")


# --- Auto Mode Logic ---
def execute_auto_mode():
    renderer = cmds.optionMenu("renderer_menu", q=True, value=True)

    # ファイル選択ダイアログ
    base_file = cmds.fileDialog2(
        fileFilter="Image Files (*.png *.jpeg *.bmp *.exr *.tga *.jpg *.tiff *.tif *);;",
        fileMode=1,
        caption="Select First Texture File (Auto Mode)",
    )
    if not base_file:
        return

    full_path = base_file[0]
    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)

    # Prefix推定ロジック (最後のアンダースコアより前を取得)
    if "_" in filename:
        prefix = filename.rsplit("_", 1)[0]
    else:
        prefix = os.path.splitext(filename)[0]

    extension = os.path.splitext(filename)[-1]  # .png etc

    file_paths = {}

    # ディレクトリ走査
    for file in os.listdir(directory):
        if not file.startswith(prefix) or not file.endswith(extension):
            continue

        for tex_type, patterns in TEXTURE_PATTERNS.items():
            for pattern in patterns:
                if pattern in file:
                    # 相対パス取得ロジック（sourceimages基準）
                    full_p = os.path.join(directory, file)
                    # Note: プロジェクト設定によっては絶対パスの方が安全な場合もあるが、元の挙動を尊重
                    project_dir = cmds.workspace(q=True, rd=True)
                    sourceimages_dir = os.path.join(project_dir, "sourceimages")

                    if sourceimages_dir in full_p:
                        # sourceimages以下の相対パスにする試み
                        try:
                            # sourceimagesの一つ上からの相対パスを取得していた元のロジックを再現/修正
                            # ここではシンプルにフルパスまたはsourceimages相対にする
                            # Mayaはsourceimages内なら相対パスとして扱いやすい
                            rel_path = os.path.relpath(full_p, start=project_dir)
                            # もし sourceimages/file.png ならそのまま使う
                            file_paths[tex_type] = full_p
                        except:
                            file_paths[tex_type] = full_p
                    else:
                        file_paths[tex_type] = full_p
                    break

    if not file_paths:
        cmds.warning("No matching texture files found.")
        return

    create_and_connect_textures(file_paths, renderer)


# --- Manual Mode Logic ---
def execute_manual_mode():
    renderer = cmds.optionMenu("renderer_menu", q=True, value=True)

    create_flags = {
        "Albedo": cmds.checkBox("cb_albedo", q=True, value=True),
        "Metalness": cmds.checkBox("cb_metalness", q=True, value=True),
        "Roughness": cmds.checkBox("cb_roughness", q=True, value=True),
        "Normal": cmds.checkBox("cb_normal", q=True, value=True),
        "Opacity": cmds.checkBox("cb_opacity", q=True, value=True),
        "Translucency": cmds.checkBox("cb_translucency", q=True, value=True),
    }

    if not any(create_flags.values()):
        cmds.warning("Please select at least one texture type.")
        return

    file_paths = {}
    for name, is_checked in create_flags.items():
        if is_checked:
            file_path = cmds.fileDialog2(
                fileFilter="Image Files (*.png *.jpeg *.bmp *.exr *.tga *.jpg *.tiff *.tif *);;",
                fileMode=1,
                caption=f"Select {name} Image File",
            )
            if file_path:
                file_paths[name] = file_path[0]
            else:
                cmds.warning(f"Selection cancelled for {name}.")
                return  # Cancel whole operation if one is cancelled (Safe behavior)

    create_and_connect_textures(file_paths, renderer)


# --- UI Events ---


def on_create_clicked(*args):
    mode_select = cmds.optionMenu("selection_mode_menu", query=True, value=True)
    if mode_select == "Auto":
        execute_auto_mode()
    else:
        execute_manual_mode()


def select_material_from_selected_objects(*args):
    selected_objects = cmds.ls(sl=True, long=True, transforms=True)
    if not selected_objects:
        cmds.warning("Please select at least one object.")
        return

    materials = set()
    for obj in selected_objects:
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []
        for shape in shapes:
            sgs = cmds.listConnections(shape, type="shadingEngine") or []
            for sg in sgs:
                shaders = (
                    cmds.listConnections(
                        sg + ".surfaceShader", destination=False, source=True
                    )
                    or []
                )
                for shader in shaders:
                    materials.add(shader)

    if materials:
        cmds.select(list(materials), replace=True)
        # UI上の名前フィールドも更新すると親切
        cmds.textField("shader_name_field", e=True, text=list(materials)[0])
    else:
        cmds.warning("No materials found.")


def update_ui_state(*args):
    """UIの有効無効をまとめて管理"""
    renderer = cmds.optionMenu("renderer_menu", query=True, value=True)
    mode_select = cmds.optionMenu("selection_mode_menu", query=True, value=True)

    # Roughness Checkbox
    use_rough_enable = renderer == "VRayMtl"
    cmds.checkBox("cb_use_roughness", edit=True, enable=use_rough_enable)

    # Texture Type Checkboxes
    manual_enable = mode_select == "Manual"
    checkboxes = [
        "cb_albedo",
        "cb_metalness",
        "cb_roughness",
        "cb_normal",
        "cb_opacity",
        "cb_translucency",
    ]
    for cb in checkboxes:
        cmds.checkBox(cb, edit=True, enable=manual_enable)


# --- UI Layout ---

if cmds.window("texture_window", exists=True):
    cmds.deleteUI("texture_window")

window = cmds.window(
    "texture_window",
    title="Texture Assigner",
    widthHeight=(160, 340),
    sizeable=False,
    mxb=False,
    mnb=False,
    tlb=True,
)
cmds.columnLayout(
    adjustableColumn=True, rowSpacing=2, columnAlign="center", columnAttach=("both", 3)
)

# Renderer selection
cmds.optionMenu("renderer_menu", label="Material", changeCommand=update_ui_state)
cmds.menuItem(label="VRayMtl")
cmds.menuItem(label="aiStandardSurface")

# Shader name input
cmds.textField(
    "shader_name_field", placeholderText="Material Name (Optional)", width=140
)
cmds.button(
    label="Pick Material from Object",
    command=select_material_from_selected_objects,
    height=20,
    bgc=(0.2, 0.3, 0.2),
)

# Checkboxes
cmds.frameLayout(label="Select Textures", marginWidth=2, marginHeight=2)
cmds.columnLayout(adjustableColumn=True, rowSpacing=2, columnAlign="center")

# Auto/Manual Selection
cmds.optionMenu("selection_mode_menu", label="Selection Mode", cc=update_ui_state)
cmds.menuItem(label="Manual")
cmds.menuItem(label="Auto")

cmds.checkBox("cb_albedo", label="Albedo | Diffuse")
cmds.checkBox("cb_metalness", label="Metalness")
cmds.checkBox("cb_roughness", label="Rough | Gloss")
cmds.checkBox("cb_normal", label="Normal")
cmds.checkBox("cb_opacity", label="Opacity")
cmds.checkBox("cb_translucency", label="Translucency | SSS")
cmds.setParent("..")
cmds.setParent("..")

# Roughness Options
cmds.frameLayout(label="Roughness Options", marginWidth=2, marginHeight=2)
cmds.columnLayout(adjustableColumn=True, rowSpacing=2, columnAlign="center")
cmds.checkBox("cb_invert_alpha", label="Invert Alpha")
cmds.checkBox("cb_use_roughness", label=" VRay<Use Roughness>", value=True)
cmds.setParent("..")
cmds.setParent("..")

# Create button
cmds.button(
    label="Create / Replace", command=on_create_clicked, height=30, bgc=(0.2, 0.2, 0.5)
)
cmds.setParent("..")

cmds.showWindow(window)
# 初期状態のUI更新
update_ui_state()
