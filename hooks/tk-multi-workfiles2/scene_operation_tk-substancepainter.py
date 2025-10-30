# Copyright 2025 Donat Van Bellinghen
#
# Inspired by original work by Diego Garcia Huerta (2019)

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Your use of the Flow Production Tracking Pipeline Toolkit is governed by the applicable
# license agreement between you and Autodesk.

__author__ = "Donat Van Bellinghen"
__contact__ = "https://www.linkedin.com/in/donat-van-bellinghen-98002914/"
__credits__ = ["Diego Garcia Huerta", "Donat Van Bellinghen"]

import os
import sys

import substance_painter as sp
import tank as sgtk
from sgtk.platform.qt6 import QtCore, QtGui, QtWidgets

HookClass = sgtk.get_hook_baseclass()


def simple_save_dialog(main_window):
    dialog = QtWidgets.QDialog(main_window)
    dialog.setWindowTitle("Save your project ?")
    dialog.setWindowModality(QtCore.Qt.WindowModal)
    dialog.setFixedSize(250, 120)

    layout = QtWidgets.QVBoxLayout(dialog)

    label = QtWidgets.QLabel("Do you want to save the current project ?")
    layout.addWidget(label, alignment=QtCore.Qt.AlignCenter)

    button_box = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.Yes | QtWidgets.QDialogButtonBox.No
    )
    layout.addWidget(button_box)

    # Connect buttons
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)

    result = dialog.exec()

    if result == QtWidgets.QDialog.Accepted:
        return True
    else:
        return False


class SceneOperation(HookClass):
    """
    Hook called to perform scene operations in Substance 3D Painter.

    This hook implements the logic for the open, save, save as, and new file
    actions in the Workfiles2 app.
    """

    def execute(
        self,
        operation,
        file_path,
        context,
        parent_action,
        file_version,
        read_only,
        **kwargs,
    ):
        """
        Main hook entry point
        This method is called by the Workfiles2 app to perform an action
        on the current scene.

        :param str operation:       String
                                Scene operation to perform

        :param file_path:       String
                                File path to use if the operation
                                requires it (e.g. open)

        :param context:         Context
                                The context the file operation is being
                                performed in.

        :param parent_action:   This is the action that this scene operation is
                                being executed for.  This can be one of:
                                - open_file
                                - new_file
                                - save_file_as
                                - version_up

        :param file_version:    The version/revision of the file to be opened.  If this is 'None'
                                then the latest version should be opened.

        :param read_only:       Specifies if the file should be opened read-only or not

        :returns:               Depends on operation:
                                'current_path' - Return the current scene
                                                 file path as a String
                                'reset'        - True if scene was reset to an empty
                                                 state, otherwise False
                                all others     - None
        """
        app = self.parent
        engine = app.engine

        if operation == "current_path":
            # This is called by Workfiles to find out the path of the current
            # open project.
            return engine.get_project_path()

        elif operation == "open":
            # This is called when a user clicks "Open" in the Workfiles UI.
            # It opens the specified project file.
            sp.project.open(file_path)

        elif operation == "save":
            # This is called when a user clicks "Save" in the Workfiles UI.
            # It saves the current project.
            sp.project.save(sp.project.ProjectSaveMode.Incremental)

        # ---- Save the current file as a new file
        elif operation == "save_as":
            # This is called when a user clicks "Save As" in the Workfiles UI.
            # It saves the current project to the specified path.
            sp.project.save_as(file_path, sp.project.ProjectSaveMode.Full)

        # ---- Reset the scene to an empty state for a new file
        elif operation == "reset":
            # If no project is open, nothing to do
            if not sp.project.is_open():
                return True

            # If a project is open, check if we need to save it
            if sp.project.needs_saving():
                if simple_save_dialog(sp.ui.get_main_window()):
                    sp.project.save(sp.project.ProjectSaveMode.Incremental)

            sp.project.close()
            return True

        # ---- Prepare for a new file operation
        elif operation == "prepare_new" and parent_action == "new_file":
            tk_substancepainter = engine.import_module("tk_substancepainter")
            _, new_proj_dialog = engine.show_modal(
                "New Substance Project",
                app,
                tk_substancepainter.NewProjectDialog,
                context,
            )

            if new_proj_dialog.exit_code == QtWidgets.QDialog.Rejected:
                return

            mesh_path = new_proj_dialog.get_mesh_file_path()
            mesh_path = engine.convert_unc_path_to_mapped_drive_path(mesh_path)
            sp_template = new_proj_dialog.get_selected_sp_template_path()

            resolution = new_proj_dialog.get_resolution()

            normal_map_format = new_proj_dialog.get_normal_map_format()

            tangent_space = new_proj_dialog.get_tangent_space()

            use_uvtile_workflow = sp.project.ProjectWorkflow.Default
            if new_proj_dialog.get_use_uvtile_workflow():
                use_uvtile_workflow = sp.project.ProjectWorkflow.UVTile

            # Determine the export path for the textures
            resolved_export_path = ""
            export_area = engine.get_texture_export_work_area_template()
            if export_area:
                fields = context.as_template_fields(export_area)
                resolved_export_path = export_area.apply_fields(fields)
                resolved_export_path = engine.convert_unc_path_to_mapped_drive_path(
                    resolved_export_path
                )

            # Declare the settings for the project:
            # Note : Project settings override the template parameters.
            project_settings = sp.project.Settings(
                import_cameras=False,
                normal_map_format=normal_map_format,
                tangent_space_mode=tangent_space,
                project_workflow=use_uvtile_workflow,
                export_path=resolved_export_path,
                default_texture_resolution=resolution,
            )

            # NOTE : It seems that if the mesh has no UV's the create() method will fail,
            # which is not the case when the user creates a project from the UI,
            # in that case an auto-unwrap is done.

            try:
                sp.project.create(
                    mesh_file_path=mesh_path,
                    settings=project_settings,
                    template_file_path=sp_template,
                )
            except sp.exception.ProjectError as e:
                self.logger.error(f"ProjectError : {e}")
            except Exception as e:
                self.logger.error(f"Error creating the project : {e}")
