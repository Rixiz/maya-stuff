import maya.cmds as cmds
import random
import math
from functools import wraps


# --- Undo一時停止用のデコレータ ---
def no_undo(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cmds.undoInfo(swf=False)
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error in {func.__name__}: {e}")
            raise
        finally:
            cmds.undoInfo(swf=True)

    return wrapper


class RelativeArrayTool:
    def __init__(self):
        self.window_name = "RelativeArrayToolWin"
        self.group_name = "Array_Output_Grp"
        self.source_obj = None

        self.build_ui()

    def build_ui(self):
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)

        cmds.window(
            self.window_name, title="Relative Array Tool", widthHeight=(340, 380)
        )

        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)

        # --- Target ---
        cmds.frameLayout(label="Target Settings", collapsable=False, marginWidth=5)
        cmds.columnLayout(adjustableColumn=True)
        cmds.button(
            label="選択オブジェクトをターゲットにする",
            command=self.set_target,
            height=30,
        )
        self.lbl_target = cmds.text(label="Target: None", align="center", height=20)
        cmds.setParent("..")
        cmds.setParent("..")

        # --- Parameters ---
        cmds.frameLayout(
            label="Local Parameters (Relative)",
            collapsable=False,
            marginWidth=5,
            marginHeight=5,
        )
        cmds.columnLayout(adjustableColumn=True, rowSpacing=8)

        # Count
        self.sl_count = cmds.intSliderGrp(
            label="Count",
            field=True,
            minValue=1,
            maxValue=100,
            value=5,
            columnWidth3=(60, 50, 100),
            dragCommand=self.update_array,
            changeCommand=self.update_array,
        )

        cmds.separator(style="in")

        def create_vector_row(label_text, default_val, step=0.1):
            cmds.rowLayout(
                numberOfColumns=4,
                columnWidth4=(60, 70, 70, 70),
                adjustableColumn=4,
                columnAlign=(1, "right"),
            )
            cmds.text(label=label_text)
            fx = cmds.floatField(
                value=default_val[0],
                precision=3,
                step=step,
                changeCommand=self.update_positions,
                dragCommand=self.update_positions,
            )
            fy = cmds.floatField(
                value=default_val[1],
                precision=3,
                step=step,
                changeCommand=self.update_positions,
                dragCommand=self.update_positions,
            )
            fz = cmds.floatField(
                value=default_val[2],
                precision=3,
                step=step,
                changeCommand=self.update_positions,
                dragCommand=self.update_positions,
            )
            cmds.setParent("..")
            return fx, fy, fz

        # Offset
        cmds.rowLayout(
            numberOfColumns=5,
            columnWidth5=(60, 40, 60, 60, 60),
            adjustableColumn=5,
            columnAlign=(1, "right"),
        )
        cmds.text(label="Offset")
        cmds.button(
            label="Auto",
            width=35,
            command=self.auto_offset_calc,
            annotation="ローカル幅で自動整列",
        )
        self.f_off_x = cmds.floatField(
            value=2.0,
            precision=3,
            step=0.1,
            changeCommand=self.update_positions,
            dragCommand=self.update_positions,
        )
        self.f_off_y = cmds.floatField(
            value=0.0,
            precision=3,
            step=0.1,
            changeCommand=self.update_positions,
            dragCommand=self.update_positions,
        )
        self.f_off_z = cmds.floatField(
            value=0.0,
            precision=3,
            step=0.1,
            changeCommand=self.update_positions,
            dragCommand=self.update_positions,
        )
        cmds.setParent("..")

        # Rotate
        self.f_rot_x, self.f_rot_y, self.f_rot_z = create_vector_row(
            "Rotate", (0.0, 0.0, 0.0)
        )

        # Scale (Relative Multiplier)
        self.f_scl_x, self.f_scl_y, self.f_scl_z = create_vector_row(
            "Scale *", (1.0, 1.0, 1.0), step=0.01
        )

        cmds.separator(style="none", height=5)
        self.f_rnd_x, self.f_rnd_y, self.f_rnd_z = create_vector_row(
            "Rnd Pos", (0.0, 0.0, 0.0)
        )

        cmds.setParent("..")
        cmds.setParent("..")

        # --- Bake ---
        cmds.columnLayout(adjustableColumn=True, parent=self.window_name)
        cmds.separator(style="none", height=10)
        cmds.button(
            label="ベイク (確定)",
            command=self.bake_geometry,
            height=40,
            backgroundColor=[0.3, 0.4, 0.4],
        )

        cmds.showWindow(self.window_name)

    def set_target(self, *args):
        sel = cmds.ls(selection=True)
        if sel:
            self.source_obj = sel[0]
            cmds.text(self.lbl_target, edit=True, label=f"Target: {self.source_obj}")
            if cmds.objExists(self.group_name):
                cmds.delete(self.group_name)
            self.update_array()
        else:
            cmds.warning("オブジェクトを選択してください。")

    def auto_offset_calc(self, *args):
        if not self.source_obj or not cmds.objExists(self.source_obj):
            return
        bbox = cmds.xform(
            self.source_obj, query=True, boundingBox=True, objectSpace=True
        )
        width_x = bbox[3] - bbox[0]
        cmds.floatField(self.f_off_x, edit=True, value=width_x)
        cmds.floatField(self.f_off_y, edit=True, value=0.0)
        cmds.floatField(self.f_off_z, edit=True, value=0.0)
        self.update_positions()

    def get_instances(self):
        if not cmds.objExists(self.group_name):
            return []
        children = (
            cmds.listRelatives(self.group_name, children=True, fullPath=True) or []
        )
        return children

    @no_undo
    def update_array(self, *args):
        if not self.source_obj or not cmds.objExists(self.source_obj):
            return

        target_count = cmds.intSliderGrp(self.sl_count, query=True, value=True)

        if not cmds.objExists(self.group_name):
            cmds.group(empty=True, name=self.group_name)
            # グループはTranslate/Rotateのみ一致させる（Scaleは1,1,1のままにしておくのが安全）
            temp_const = cmds.parentConstraint(
                self.source_obj, self.group_name, maintainOffset=False
            )
            cmds.delete(temp_const)

        current_instances = self.get_instances()
        current_count = len(current_instances)

        if current_count < target_count - 1:
            needed = target_count - 1 - current_count
            for _ in range(needed):
                dup = cmds.instance(self.source_obj)[0]
                cmds.parent(dup, self.group_name)

        elif current_count > target_count - 1:
            excess = current_count - (target_count - 1)
            cmds.delete(current_instances[-excess:])

        self.update_positions_core()

    @no_undo
    def update_positions(self, *args):
        self.update_positions_core()

    def update_positions_core(self):
        """相対スケール計算を実装したコアロジック"""
        if not cmds.objExists(self.group_name):
            return

        # 各種入力値
        off = [
            cmds.floatField(f, query=True, value=True)
            for f in (self.f_off_x, self.f_off_y, self.f_off_z)
        ]
        rot = [
            cmds.floatField(f, query=True, value=True)
            for f in (self.f_rot_x, self.f_rot_y, self.f_rot_z)
        ]
        scl_input = [
            cmds.floatField(f, query=True, value=True)
            for f in (self.f_scl_x, self.f_scl_y, self.f_scl_z)
        ]
        rnd = [
            cmds.floatField(f, query=True, value=True)
            for f in (self.f_rnd_x, self.f_rnd_y, self.f_rnd_z)
        ]

        # 【修正点】元オブジェクトの現在のスケールを取得
        # Freezeしていない場合、ここに(2.0, 2.0, 2.0)などの値が入っている
        try:
            base_scale = cmds.getAttr(f"{self.source_obj}.scale")[
                0
            ]  # returns [(x,y,z)]
        except:
            base_scale = (1.0, 1.0, 1.0)

        instances = self.get_instances()

        for i, obj in enumerate(instances):
            idx = i + 1

            # Translate & Rotate (加算)
            t_final = [off[k] * idx for k in range(3)]
            r_final = [rot[k] * idx for k in range(3)]

            # Scale (乗算)
            # 計算式: 最終スケール = 元のスケール * (入力値 ^ インデックス)
            # これにより、入力値が1.0なら「元のスケール」が維持される
            s_final = [base_scale[k] * pow(scl_input[k], idx) for k in range(3)]

            # Random
            random.seed(i * 123)
            rt = [
                random.uniform(-rnd[k], rnd[k]) if rnd[k] > 0 else 0 for k in range(3)
            ]

            # 適用
            cmds.xform(
                obj,
                translation=(
                    t_final[0] + rt[0],
                    t_final[1] + rt[1],
                    t_final[2] + rt[2],
                ),
                rotation=r_final,
                scale=s_final,
                objectSpace=True,
                relative=False,
            )

    def bake_geometry(self, *args):
        if cmds.objExists(self.group_name):
            new_name = cmds.rename(self.group_name, f"{self.source_obj}_Array_Baked")
            self.source_obj = None
            cmds.text(self.lbl_target, edit=True, label="Target: None")
            print(f"Baked: {new_name}")


RelativeArrayTool()
