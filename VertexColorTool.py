import maya.cmds as cmds
from functools import partial


class VertexColorTool:
    """
    Maya Vertex Color Tool (v4.0 - Selection Mode Edition)

    更新履歴:
    - [New] 選択モード（Object / Vertex）の切り替えラジオボタンを追加
    - [Update] 指定した頂点カラーを持つコンポーネント（頂点）のみを選択するロジックを実装
    """

    def __init__(self):
        self.window_name = "vertexColorToolWindow"
        self.title = "Vertex Color Tool"
        self.size = (360, 720)

        # データ初期化
        self.current_color = [0.5, 0.5, 0.5]
        self.saved_palette = [
            [1.0, 1.0, 1.0],
            [0.0, 0.0, 0.0],
            [0.5, 0.5, 0.5],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.8, 0.5, 0.5],
            [0.5, 0.8, 0.5],
            [0.5, 0.5, 0.8],
            [1.0, 1.0, 0.0],
            [1.0, 0.0, 1.0],
            [0.0, 1.0, 1.0],
            [0.5, 0.2, 0.0],
            [0.2, 0.5, 0.0],
            [0.0, 0.2, 0.5],
            [0.2, 0.0, 0.5],
            [0.5, 0.0, 0.2],
            [0.0, 0.5, 0.2],
        ]

        self.widgets = {}
        self.build_ui()
        self.refresh_scene_colors()

    def build_ui(self):
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)

        self.window = cmds.window(
            self.window_name,
            title=self.title,
            widthHeight=self.size,
            mxb=False,
            mnb=False,
            tlb=True,
        )

        main_scroll = cmds.scrollLayout(childResizable=True, p=self.window)
        main_col = cmds.columnLayout(
            adjustableColumn=True, columnAlign="left", rowSpacing=5, p=main_scroll
        )

        # --- Color Selection ---
        cmds.frameLayout(
            label="Color Selection",
            collapsable=False,
            p=main_col,
            marginWidth=10,
            marginHeight=5,
        )
        col_layout = cmds.columnLayout(adjustableColumn=True)

        row_sel = cmds.rowLayout(
            numberOfColumns=2, adjustableColumn=2, columnWidth2=(60, 100), p=col_layout
        )
        self.widgets["swatch"] = cmds.canvas(
            width=60,
            height=50,
            rgbValue=self.current_color,
            pressCommand=self.open_color_picker,
            annotation="Click to open Color Editor",
            p=row_sel,
        )

        self.widgets["color_field"] = cmds.floatFieldGrp(
            label="",
            numberOfFields=3,
            precision=3,
            columnWidth4=(0, 40, 40, 40),
            value1=self.current_color[0],
            value2=self.current_color[1],
            value3=self.current_color[2],
            changeCommand=self.on_field_changed,
            p=row_sel,
        )

        cmds.setParent(col_layout)
        cmds.separator(h=5, style="none")
        cmds.button(
            label="Apply Color to Selection",
            command=self.apply_color,
            height=40,
            bgc=(0.3, 0.5, 0.3),
        )
        cmds.setParent(main_col)

        # --- Palette ---
        cmds.separator(h=5, style="in", p=main_col)
        cmds.text(
            label="Quick Palette:", align="left", font="boldLabelFont", p=main_col
        )

        p_btn_layout = cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, p=main_col)
        cmds.button(label="Add Current", command=self.add_to_palette, p=p_btn_layout)
        cmds.button(label="Clear", command=self.clear_palette, p=p_btn_layout)

        self.widgets["palette_layout"] = cmds.gridLayout(
            numberOfColumns=9, cellWidthHeight=(25, 25), p=main_col
        )
        self.refresh_palette_ui()

        # --- Scene Colors (Visual List) ---
        cmds.separator(h=15, style="in", p=main_col)

        # Header Row with Refresh Button
        header_row = cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, p=main_col)
        cmds.text(
            label="Scene Colors:", align="left", font="boldLabelFont", p=header_row
        )
        cmds.button(
            label="Refresh List",
            command=self.refresh_scene_colors,
            width=80,
            p=header_row,
        )

        # Selection Mode Radio Buttons (New)
        cmds.separator(h=5, style="none", p=main_col)
        self.widgets["select_mode"] = cmds.radioButtonGrp(
            label="Target: ",
            labelArray2=["Object", "Vertex"],
            numberOfRadioButtons=2,
            select=1,  # Default to Object mode
            columnWidth3=(40, 70, 70),
            p=main_col,
        )

        # List Container
        cmds.frameLayout(labelVisible=False, p=main_col, borderStyle="etchedIn")
        self.widgets["scene_list_layout"] = cmds.columnLayout(
            adjustableColumn=True, rowSpacing=1
        )
        cmds.setParent(main_col)

        # --- Display Settings ---
        cmds.separator(h=15, style="in", p=main_col)
        cmds.text(
            label="Display Settings:", align="left", font="boldLabelFont", p=main_col
        )

        cmds.button(
            label="Toggle Display (Selection)",
            command=self.toggle_selection_display,
            p=main_col,
            h=30,
        )

        scene_disp_grid = cmds.rowLayout(
            numberOfColumns=2, adjustableColumn=True, p=main_col
        )
        cmds.button(
            label="Show All (Scene)",
            command=partial(self.set_scene_display, True),
            p=scene_disp_grid,
        )
        cmds.button(
            label="Hide All (Scene)",
            command=partial(self.set_scene_display, False),
            p=scene_disp_grid,
        )

        cmds.showWindow(self.window)

    # ==========================================
    # Core Logic
    # ==========================================

    def set_color(self, rgb, update_field=True):
        self.current_color = rgb
        cmds.canvas(self.widgets["swatch"], edit=True, rgbValue=rgb)
        if update_field:
            cmds.floatFieldGrp(
                self.widgets["color_field"],
                edit=True,
                value1=rgb[0],
                value2=rgb[1],
                value3=rgb[2],
            )

    def open_color_picker(self, *args):
        cmds.colorEditor(rgbValue=self.current_color)
        if cmds.colorEditor(query=True, result=True):
            rgb = cmds.colorEditor(query=True, rgbValue=True)
            self.set_color(rgb)

    def on_field_changed(self, *args):
        r = cmds.floatFieldGrp(self.widgets["color_field"], query=True, value1=True)
        g = cmds.floatFieldGrp(self.widgets["color_field"], query=True, value2=True)
        b = cmds.floatFieldGrp(self.widgets["color_field"], query=True, value3=True)
        self.set_color([r, g, b], update_field=False)

    # ==========================================
    # Palette Logic
    # ==========================================

    def add_to_palette(self, *args):
        self.saved_palette.append(list(self.current_color))
        self.refresh_palette_ui()

    def clear_palette(self, *args):
        self.saved_palette = []
        self.refresh_palette_ui()

    def refresh_palette_ui(self):
        btns = cmds.gridLayout(
            self.widgets["palette_layout"], query=True, childArray=True
        )
        if btns:
            for btn in btns:
                cmds.deleteUI(btn)

        for rgb in self.saved_palette:
            cmds.button(
                label="",
                bgc=rgb,
                command=partial(self.set_color, rgb),
                parent=self.widgets["palette_layout"],
            )

    # ==========================================
    # Scene Color Logic (Selection Mode Supported)
    # ==========================================

    def get_scene_colors(self):
        scene_colors = set()
        meshes = cmds.ls(type="mesh", noIntermediate=True, long=True) or []

        for mesh in meshes:
            if cmds.polyEvaluate(mesh, vertex=True) == 0:
                continue
            if not cmds.polyColorSet(mesh, query=True, allColorSets=True):
                continue

            try:
                colors = cmds.polyColorPerVertex(f"{mesh}.vtx[*]", query=True, rgb=True)
                if not colors:
                    continue

                for i in range(0, len(colors), 3):
                    c = tuple(round(v, 3) for v in colors[i : i + 3])
                    scene_colors.add(c)
            except Exception:
                pass

        return sorted(list(scene_colors))

    def refresh_scene_colors(self, *args):
        unique_colors = self.get_scene_colors()

        children = cmds.columnLayout(
            self.widgets["scene_list_layout"], query=True, childArray=True
        )
        if children:
            for child in children:
                cmds.deleteUI(child)

        if not unique_colors:
            cmds.text(
                label="No vertex colors found.",
                parent=self.widgets["scene_list_layout"],
                align="center",
                h=20,
            )
            return

        for rgb in unique_colors:
            self.create_scene_color_row(rgb)

        print(f"Scene colors refreshed: {len(unique_colors)} colors found.")

    def create_scene_color_row(self, rgb):
        row = cmds.rowLayout(
            numberOfColumns=3,
            columnWidth3=(40, 90, 60),
            adjustableColumn=2,
            parent=self.widgets["scene_list_layout"],
            bgc=(0.2, 0.2, 0.2),
        )

        # 1. Swatch
        cmds.canvas(
            width=20,
            height=20,
            rgbValue=rgb,
            pressCommand=partial(self.set_color, list(rgb)),
            annotation="Click to pick this color",
        )

        # 2. Text
        label_text = f" {rgb[0]:.2f}, {rgb[1]:.2f}, {rgb[2]:.2f}"
        cmds.text(label=label_text, align="left")

        # 3. Select Button
        cmds.button(
            label="Select",
            height=20,
            command=partial(self.select_by_color, rgb),
            annotation="Select objects or vertices with this color",
        )

    def select_by_color(self, target_rgb, *args):
        """モードに応じてオブジェクトまたは頂点を選択"""

        # 現在のモードを取得 (1=Object, 2=Vertex)
        mode_idx = cmds.radioButtonGrp(
            self.widgets["select_mode"], query=True, select=True
        )
        is_vertex_mode = mode_idx == 2

        target_r = tuple(round(v, 3) for v in target_rgb)

        cmds.select(clear=True)

        selection_list = []

        meshes = cmds.ls(type="mesh", noIntermediate=True, long=True) or []

        # プログレスバー表示（メッシュが多い場合用）
        amount = len(meshes)

        for mesh in meshes:
            if not cmds.polyColorSet(mesh, query=True, allColorSets=True):
                continue

            # 頂点カラーを一括取得
            colors = cmds.polyColorPerVertex(f"{mesh}.vtx[*]", query=True, rgb=True)
            if not colors:
                continue

            # RGBリストを (r,g,b) タプルのリストに変換しつつ、ループ処理
            # colorsはフラットなリスト [r,g,b, r,g,b, ...]

            if is_vertex_mode:
                # --- Vertex Mode Logic ---
                # マッチする頂点インデックスを探す
                matched_indices = []
                for i in range(0, len(colors), 3):
                    c = tuple(round(v, 3) for v in colors[i : i + 3])
                    if c == target_r:
                        # インデックスは (i / 3)
                        matched_indices.append(i // 3)

                # インデックスから選択文字列を生成 (例: pCube1.vtx[5])
                if matched_indices:
                    # 最適化: 連続するインデックスをスライス表記にできればベストだが、
                    # ここではシンプルにリスト内包表記で文字列化
                    for idx in matched_indices:
                        selection_list.append(f"{mesh}.vtx[{idx}]")

            else:
                # --- Object Mode Logic ---
                # 1つでもマッチすればそのオブジェクトを選択候補へ
                found = False
                for i in range(0, len(colors), 3):
                    c = tuple(round(v, 3) for v in colors[i : i + 3])
                    if c == target_r:
                        found = True
                        break

                if found:
                    transform = cmds.listRelatives(mesh, parent=True, fullPath=True)
                    if transform:
                        selection_list.append(transform[0])

        # 選択実行
        if selection_list:
            cmds.select(selection_list)
            mode_str = "Vertices" if is_vertex_mode else "Objects"
            print(f"Selected {len(selection_list)} {mode_str} with color {target_rgb}")

            # Vertexモードの場合、自動的にコンポーネントモードに切り替えると親切
            if is_vertex_mode:
                cmds.selectMode(component=True)
                cmds.selectType(vertex=True, allObjects=False)
        else:
            cmds.warning(f"No items found with color {target_rgb}")

    # ==========================================
    # Application & Display
    # ==========================================

    def apply_color(self, *args):
        selection = cmds.ls(selection=True, flatten=True, long=True)
        if not selection:
            cmds.warning("Please select objects or components.")
            return
        try:
            cmds.polyColorPerVertex(
                selection, rgb=self.current_color, colorDisplayOption=True
            )
            print(f"Applied color {self.current_color}")
        except Exception as e:
            cmds.warning(f"Error applying color: {e}")

    def toggle_selection_display(self, *args):
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            cmds.warning("Select objects to toggle display.")
            return

        target_shapes = []
        for item in selection:
            if cmds.nodeType(item) == "transform":
                shapes = cmds.listRelatives(
                    item, shapes=True, type="mesh", fullPath=True, noIntermediate=True
                )
                if shapes:
                    target_shapes.extend(shapes)
            elif cmds.nodeType(item) == "mesh":
                target_shapes.append(item)

        if not target_shapes:
            return

        first_state = cmds.getAttr(f"{target_shapes[0]}.displayColors")
        new_state = not first_state

        for shape in target_shapes:
            cmds.setAttr(f"{shape}.displayColors", new_state)

        state_str = "ON" if new_state else "OFF"
        print(f"Toggled display to: {state_str}")

    def set_scene_display(self, enable, *args):
        meshes = cmds.ls(type="mesh", noIntermediate=True, long=True)
        if not meshes:
            return
        for mesh in meshes:
            cmds.setAttr(f"{mesh}.displayColors", enable)
        print(f"Set scene display to: {'ON' if enable else 'OFF'}")


# 実行
VertexColorTool()
