import maya.cmds as cmds
from functools import partial

class VertexColorTool:
    """
    Mayaの頂点カラーを操作するためのUI付きツール（エラー修正版）。
    - リファレンスカラーの設定と適用（プレビュー表示付き）
    - シーン内の頂点カラーのリスト化
    - 特定の色を持つオブジェクトの選択
    - 頂点カラー表示のオン/オフ切り替え
    - リファレンスカラーの自動更新
    """
    def __init__(self):
        self.window_name = "vertexColorToolWindow"
        self.reference_color = [0.5, 0.5, 0.5]
        self.color_swatch = None
        self.color_field = None
        self.color_list_widget = None

        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)

        self.window = cmds.window('self.window_name', title='vertexColorAssigner', widthHeight=(230, 900), mxb = False, mnb = False, tlb=True)
        main_layout = cmds.columnLayout(
            adjustableColumn=True, 
            columnAlign="left",  # UI要素を左揃えにする
            rowSpacing=5, 
            p=self.window
        )
        # リファレンスカラー表示
        self.color_swatch = cmds.canvas(width=340, height=50, rgbValue=self.reference_color, p=main_layout)
        cmds.separator(h=5, style='none')

        # リファレンスカラー入力フィールド
        self.color_field = cmds.floatFieldGrp(
			columnWidth4=(160, 55, 55, 55),
            numberOfFields=3,
			precision=2,
            value1=self.reference_color[0],
            value2=self.reference_color[1],
            value3=self.reference_color[2],
            # 値が変更されたらリファレンスカラーを更新する
            changeCommand=self.update_reference_color_from_fields,
            p=main_layout
        )

        cmds.separator(h=2, style='in', p=main_layout)

        # カラー適用ボタン
        cmds.button(label="Apply Reference Color to Selected Objects", command=self.apply_reference_color, p=main_layout, height=45, bgc=(0.2, 0.3, 0.2))

        cmds.separator(h=2, style='in', p=main_layout)

        # シーンカラーリスト
        cmds.text(label="Scene Colors:", p=main_layout)
        self.color_list_widget = cmds.textScrollList(
            allowMultiSelection=False,
            height=200,
            # リストの選択が変更されたらリファレンスカラーを更新する
            selectCommand=self.update_reference_color_from_list,
            p=main_layout
        )

        cmds.button(label="Refresh List", command=self.refresh_color_list, p=main_layout)
        cmds.button(label="Select Objects by Color", command=self.select_objects_by_color, p=main_layout)

        cmds.separator(h=15, style='in', p=main_layout)

        # 頂点カラー表示切り替えボタン
        cmds.button(label="Enable Vertex Color Display", command=partial(self.toggle_vertex_color_display, True), p=main_layout)
        cmds.button(label="Disable Vertex Color Display", command=partial(self.toggle_vertex_color_display, False), p=main_layout)

        cmds.separator(h=10, style='none', p=main_layout)

        # ツール起動時にリストを更新してウィンドウを表示
        self.refresh_color_list()
        cmds.showWindow(self.window)

    def update_reference_color_display(self):
        """リファレンスカラーの表示（色見本と入力フィールド）を更新します。"""
        # 色見本を更新
        cmds.canvas(self.color_swatch, edit=True, rgbValue=self.reference_color)
        
        # ▼▼▼▼▼ エラー修正箇所 ▼▼▼▼▼
        # floatFieldGrpの値を個別に設定します
        cmds.floatFieldGrp(self.color_field, edit=True,
                           value1=self.reference_color[0],
                           value2=self.reference_color[1],
                           value3=self.reference_color[2])
        # ▲▲▲▲▲ エラー修正箇所 ▲▲▲▲▲

    def update_reference_color_from_fields(self, *args):
        """入力フィールドの変更を検知し、リファレンスカラーを更新します。"""
        r = cmds.floatFieldGrp(self.color_field, query=True, value1=True)
        g = cmds.floatFieldGrp(self.color_field, query=True, value2=True)
        b = cmds.floatFieldGrp(self.color_field, query=True, value3=True)
        self.reference_color = [r, g, b]
        # 色見本のみ更新（入力フィールドはユーザーが操作中のため更新しない）
        cmds.canvas(self.color_swatch, edit=True, rgbValue=self.reference_color)
        print(f"Reference color updated from fields to: {self.reference_color}")

    def update_reference_color_from_list(self):
        """シーンカラーリストの選択を検知し、リファレンスカラーを更新します。"""
        selected_items = cmds.textScrollList(self.color_list_widget, query=True, selectItem=True)
        if selected_items:
            try:
                color_str = selected_items[0].split(',')
                self.reference_color = [float(c.strip()) for c in color_str]
                # 色見本と入力フィールドの両方を更新
                self.update_reference_color_display()
                print(f"Reference color updated from list to: {self.reference_color}")
            except ValueError:
                cmds.warning("Invalid color format in the list.")

    def apply_reference_color(self, *args):
        """選択されたポリゴンオブジェクトの全頂点にリファレンスカラーを適用します。"""
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            cmds.warning("No objects selected. Please select one or more mesh objects.")
            return

        mesh_transforms = cmds.filterExpand(selection, selectionMask=12) # 12 = ポリゴンメッシュ
        if not mesh_transforms:
             cmds.warning("No mesh objects found in selection.")
             return

        for obj in mesh_transforms:
            try:
                cmds.polyColorPerVertex(obj, rgb=self.reference_color, colorDisplayOption=True)
            except Exception as e:
                cmds.warning(f"Could not apply color to {obj}: {e}")

        print(f"Applied color {self.reference_color} to {len(mesh_transforms)} object(s).")
        self.refresh_color_list()

    def refresh_color_list(self, *args):
        cmds.textScrollList(self.color_list_widget, edit=True, removeAll=True)
        scene_colors = set()
        meshes = cmds.ls(type='mesh', long=True)

        for mesh in meshes:
            # ... (中略) ...
            try:
                colors = cmds.polyColorPerVertex(f'{mesh}.vtx[*]', query=True, rgb=True)
                if not colors:
                    continue

                for i in range(0, len(colors), 3):
                    # ▼▼▼▼▼ 修正点1 ▼▼▼▼▼
                    # 内部で比較する際も小数点以下2桁に丸めます
                    color = tuple(round(c, 2) for c in colors[i:i+3])
                    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
                    scene_colors.add(color)
            except:
                pass

        sorted_colors = sorted(list(scene_colors))
        for color in sorted_colors:
            # ▼▼▼▼▼ 修正点2 ▼▼▼▼▼
            # f-stringの書式指定子を使って、小数点以下2桁表示を強制します
            color_str = f"{color[0]:.2f}, {color[1]:.2f}, {color[2]:.2f}"
            # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
            cmds.textScrollList(self.color_list_widget, edit=True, append=color_str)
            
        print(f"Found {len(sorted_colors)} unique colors in the scene. List refreshed.")

    def select_objects_by_color(self, *args):
        """カラーリストで選択された色を持つオブジェクトを全て選択します。"""
        selected_items = cmds.textScrollList(self.color_list_widget, query=True, selectItem=True)
        if not selected_items:
            cmds.warning("No color selected from the list.")
            return

        try:
            target_color_str = selected_items[0].split(',')
            target_color = tuple(float(c.strip()) for c in target_color_str)
        except (ValueError, IndexError) as e:
            cmds.warning(f"Invalid color format selected: {selected_items[0]}. Error: {e}")
            return

        cmds.select(clear=True)
        objects_to_select = set()
        meshes = cmds.ls(type='mesh', long=True)

        for mesh in meshes:
            vtx_count = cmds.polyEvaluate(mesh, vertex=True)
            if vtx_count == 0: continue

            try:
                colors = cmds.polyColorPerVertex(f'{mesh}.vtx[*]', query=True, rgb=True)
                if not colors: continue

                for i in range(0, len(colors), 3):
                    color = tuple(round(c, 3) for c in colors[i:i+3])
                    if color == target_color:
                        transform = cmds.listRelatives(mesh, parent=True, fullPath=True)
                        if transform:
                            objects_to_select.add(transform[0])
                        break
            except:
                pass

        if objects_to_select:
            cmds.select(list(objects_to_select), replace=True)
            print(f"Selected {len(objects_to_select)} object(s) with color {target_color}.")
        else:
            cmds.warning(f"No objects found with color {target_color}.")

    def toggle_vertex_color_display(self, enable, *args):
        """選択されたオブジェクトの頂点カラー表示の有効/無効を切り替えます。"""
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            cmds.warning("No objects selected.")
            return

        for obj in selection:
            shapes = cmds.listRelatives(obj, shapes=True, fullPath=True, type='mesh') or []
            if cmds.nodeType(obj) == 'mesh':
                shapes.append(obj)
            if not shapes: continue

            for shape in shapes:
                try:
                    cmds.setAttr(f"{shape}.displayColors", enable)
                except Exception as e:
                    cmds.warning(f"Could not set displayColors on {shape}: {e}")

        status = "Enabled" if enable else "Disabled"
        print(f"{status} vertex color display for selected object(s).")


# ツールを起動
VertexColorTool()