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


import enum
import os
import sys

import sgtk
import substance_painter as sp
from sgtk.platform.qt6 import QtCore, QtGui, QtWidgets




logger = sgtk.LogManager.get_logger("__name__")


class NewProjectDialog(QtWidgets.QWidget):
    """
    ShotGrid compatible New Substance Painter Project Dialog
    """

    # TODO : should use sgtk frameworks to only show published models to the user

    def __init__(self, context):
        # first, call the base class and let it do its thing.
        QtWidgets.QWidget.__init__(self)

        self._engine = sgtk.platform.current_engine()
        # Retrieve the substance painter templates and store them
        self._sp_templates = self._get_templates()

        self._asset_root_directory = self._get_asset_root_path(context)
        self.selected_mesh_file_path = None

        self.exit_code = QtWidgets.QDialog.Rejected
        # Create the UI
        self._create_ui()

    @property
    def hide_tk_title_bar(self):
        return False

    ############## public methods

    def get_mesh_file_path(self):
        """
        Get the selected file path
        """
        return self.selected_mesh_file_path

    def get_selected_sp_template_path(self):
        """
        Get the dropdown selection
        """
        sp_template_item = self.sp_template_dropdown.currentData()

        if sp_template_item:
            return sp_template_item.filepath
        else:
            return None

    def get_resolution(self):
        return self.resolution_dropdown.currentData()

    def get_normal_map_format(self):
        return self.normalmap_dropdown.currentData()

    def get_tangent_space(self):
        if self.tangent_space_checkbox.isChecked():
            return sp.project.TangentSpace.PerFragment
        else:
            return sp.project.TangentSpace.PerVertex

    def get_use_uvtile_workflow(self):
        """
        Get the Use UVtile checkbox state
        """
        return self.use_uvtile_checkbox.isChecked()

    ###################### private methods

    def _create_ui(self):
        """
        Create the user interface
        """
        # Main layout
        main_layout = QtWidgets.QVBoxLayout()

        # Template menu
        sp_template_layout = QtWidgets.QHBoxLayout()
        sp_template_dropdown_label = QtWidgets.QLabel("Template")
        self.sp_template_dropdown = QtWidgets.QComboBox()

        self.sp_template_dropdown.addItem("Select template...", None)
        for sp_template in self._sp_templates:
            self.sp_template_dropdown.addItem(sp_template.name, sp_template)

        sp_template_layout.addWidget(sp_template_dropdown_label)
        sp_template_layout.addWidget(self.sp_template_dropdown)

        # File selection section
        file_layout = QtWidgets.QHBoxLayout()
        file_label = QtWidgets.QLabel("File:   ")
        self.file_path_label = QtWidgets.QLabel("No file selected")
        self.select_file_button = QtWidgets.QPushButton("Select...")
        self.select_file_button.clicked.connect(self._on_select_file)

        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_path_label)
        file_layout.addStretch()
        file_layout.addWidget(self.select_file_button)

        # Project Settings section
        settings_layout = QtWidgets.QVBoxLayout()
        settings_label = QtWidgets.QLabel("Project Settings")
        font = settings_label.font()
        font.setBold(True)
        settings_label.setFont(font)

        resolution_layout = QtWidgets.QHBoxLayout()
        resolution_label = QtWidgets.QLabel("Document Resolution")
        self.resolution_dropdown = QtWidgets.QComboBox()
        for val in [1024, 2048, 4096]:
            self.resolution_dropdown.addItem(str(val), val)
        # Set default selection to 2048
        self.resolution_dropdown.setCurrentIndex(1)
        resolution_layout.addWidget(resolution_label)
        resolution_layout.addWidget(self.resolution_dropdown)

        normalmap_format_layout = QtWidgets.QHBoxLayout()
        normalmap_format_label = QtWidgets.QLabel("Normal Map Format")
        self.normalmap_dropdown = QtWidgets.QComboBox()
        self.normalmap_dropdown.addItem("OpenGL", sp.project.NormalMapFormat.OpenGL)
        self.normalmap_dropdown.addItem("DirectX", sp.project.NormalMapFormat.DirectX)
        normalmap_format_layout.addWidget(normalmap_format_label)
        normalmap_format_layout.addWidget(self.normalmap_dropdown)

        tangent_space_layout = QtWidgets.QHBoxLayout()
        self.tangent_space_checkbox = QtWidgets.QCheckBox(
            "Compute Tangent Space Per Fragment"
        )
        self.tangent_space_checkbox.setChecked(True)
        tangent_space_layout.addWidget(self.tangent_space_checkbox)

        uv_layout = QtWidgets.QHBoxLayout()
        self.use_uvtile_checkbox = QtWidgets.QCheckBox("Use UV Tile workflow (UDIM)")
        self.use_uvtile_checkbox.setChecked(False)
        uv_layout.addWidget(self.use_uvtile_checkbox)

        settings_layout.addWidget(settings_label)
        settings_layout.addLayout(resolution_layout)
        settings_layout.addLayout(normalmap_format_layout)
        settings_layout.addLayout(tangent_space_layout)
        settings_layout.addLayout(uv_layout)

        # Ok and Cancel Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        self.ok_button = QtWidgets.QPushButton("Ok")
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self._on_ok_clicked)
        button_layout.addWidget(self.ok_button)
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        button_layout.addWidget(self.cancel_button)

        # Add all elements to main layout
        main_layout.addLayout(sp_template_layout)
        main_layout.addLayout(file_layout)
        main_layout.addLayout(settings_layout)
        main_layout.addStretch()
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)
        self.resize(540, 200)

    def _on_select_file(self):
        """
        Open file chooser dialog and store the selected file path
        """
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select 3d mesh",
            self._asset_root_directory,  # Default directory
            "Mesh Files (*.fbx *.abc *.obj *.dae *.ply *.gltf *.glb *.usd *.usda *.usdc *.usdz)",
        )

        if file_path:
            self.selected_mesh_file_path = os.path.normpath(file_path)
            self.file_path_label.setText(file_path)
            self.ok_button.setEnabled(True)

    def _on_ok_clicked(self):
        """
        Handle Ok button click - accept and close the dialog
        """
        self.exit_code = QtWidgets.QDialog.Accepted
        self.close()

    def _on_cancel_clicked(self):
        """
        Handle Cancel button click - reject and close the dialog
        """
        self.exit_code = QtWidgets.QDialog.Rejected
        self.close()

    def _get_asset_root_path(self, context):
        """
        Based on the context, find the root directory of the modeling step
        """

        template = self._engine.get_template("modeling_root_area")
        modeling_step_name = self._engine.get_setting("modeling_step_name")

        if not template:
            return None

        fields = context.as_template_fields(template)
        fields["Step"] = modeling_step_name

        missing_keys = template.missing_keys(fields)
        if missing_keys:
            logger.debug(f"Not enough keys to apply fields: {fields}"
                        f" to template: {template}"
                         "Will use OS default directory")
            return None

        path = template.apply_fields(fields)

        return path

    ############## private methods related to substance painter templates

    @classmethod
    def _get_user_templates_directory(cls):
        """
        Returns the platform-specific path to the user's Substance 3D Painter
        user templates directory.

        :return: Path to the user templates directory.
        """
        if sys.platform == "win32":
            import winreg

            win_reg_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            )
            user_documents_dir = os.path.expandvars(
                winreg.QueryValueEx(win_reg_key, "Personal")[0]
            )

            user_templates_path = os.path.join(
                user_documents_dir,
                "Adobe",
                "Adobe Substance 3D Painter",
                "assets",
                "templates",
            )
            return user_templates_path

        else:  # macOS and Linux
            user_templates_path = os.path.expanduser(
                r"~/Documents/Adobe/Adobe Substance 3D Painter/assets/templates"
            )
            return user_templates_path

    @classmethod
    def _get_starter_assets_templates_directory(cls):
        """
        Returns the directory holding the starter assets templates
        i.e. the templates that come standard with Substance 3D Painter
        """

        if sys.platform == "win32":
            path = r"C:\Program Files\Adobe\Adobe Substance 3D Painter\resources\starter_assets\templates"
        elif sys.platform == "darwin":
            path = "/Applications/Adobe Substance 3D Painter.app/Contents/Resources/starter_assets/templates"  ### to be verified
        elif sys.platform.startswith("linux"):
            path = "/opt/Adobe/Adobe_Substance_3D_Painter/resources/starter_assets/templates"  ### to be verified

        return path

    def _get_templates(self):
        starter_assets_templates_dir = self._get_starter_assets_templates_directory()
        starter_assets_templates = [
            SPTemplateItem(os.path.join(starter_assets_templates_dir, f))
            for f in os.listdir(starter_assets_templates_dir)
            if os.path.isfile(os.path.join(starter_assets_templates_dir, f))
        ]
        starter_assets_templates.sort()

        user_templates = []

        user_templates_dir = self._get_user_templates_directory()
        if os.path.isdir(user_templates_dir):
            user_templates = [
                SPTemplateItem(os.path.join(user_templates_dir, f))
                for f in os.listdir(user_templates_dir)
                if os.path.isfile(os.path.join(user_templates_dir, f))
            ]
            user_templates.sort()

        return starter_assets_templates + user_templates


class SPTemplateItem:
    """
    Simple class to manage substance painter templates
    """

    def __init__(self, filepath):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.name = None
        self.type = None

        file_no_ext = os.path.splitext(self.filename)[0]
        if "starter_assets" in filepath:
            self.name = f"{file_no_ext} (starter_assets)"
            self.type = SPTemplateType.STARTER_ASSETS
        else:
            self.name = f"{file_no_ext} (your_assets)"
            self.type = SPTemplateType.USER_ASSETS

    def __lt__(self, other):
        return self.name < other.name

    def __repr__(self):
        return self.name


class SPTemplateType(enum.Enum):
    STARTER_ASSETS = "starter_assets"
    USER_ASSETS = "your_assets"
