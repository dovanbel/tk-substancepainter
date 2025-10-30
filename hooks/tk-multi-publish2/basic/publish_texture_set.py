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
import pprint
import re
import tempfile
import traceback

import sgtk
import substance_painter as sp
from sgtk.platform.qt import QtCore, QtGui
from sgtk.util.filesystem import copy_file, ensure_folder_exists

HookBaseClass = sgtk.get_hook_baseclass()


TEXTURE_PUBLISH_TYPE = "Texture"

TEXTURE_SET_PUBLISH_TYPE = "Texture Set"

TEXTURE_ABSTRACT_PATH_REGEX = re.compile(
    "\$textureSet_[A-Za-z0-9]+_\$colorSpace\(\.\$udim\)"
)

# texture filename regex : needs to match the export preset in the 'shotgrid' export preset
# assuming it should be : '$textureSet_<MapName>_$colorSpace(.$udim)'
# no underscore is allowed in the <MapName>
TEXTURE_FILENAME_REGEX = re.compile(
    "[^.]+_(?P<texture_map>[^_.]+)_(?P<colorspace>[^_.]+)(?:\.(?P<udim>\d{4}))?\.(?P<extension>\w+$)"
)


class SubstancePainterTextureExportPlugin(HookBaseClass):
    """
    Plugin for exporting and publishing texture files

    This plugin is configured to run when the collector creates an item of type
    'substancepainter.textureset'

    """

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can contain simple html for formatting.
        """

        loader_url = "https://help.autodesk.com/view/SGDEV/ENU/?guid=SG_Supervisor_Artist_sa_integrations_sa_integrations_user_guide_html#the-loader"

        return f"""
        This plugin exports and publishes a textures to ShotGrid.
        A <b>Publish</b> entryies of type {TEXTURE_PUBLISH_TYPE} will be created, and the texture
        file will be copied to the publish location defined by the 'Publish Template' or 'Publish UDIM Template'
        setting.

        Additionally, a publish entry of type {TEXTURE_SET_PUBLISH_TYPE} will be created to represent the whole texture set
        Other artists will be able to access the published texture via the
        <b><a href='{loader_url}'>Loader</a></b>.

        The version number for the publish will be automatically calculated based
        on previous publishes of the same name.
        """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """

        # inherit the settings from the base publish plugin
        base_settings = super().settings or {}

        # settings specific to this class
        substancepainter_publish_settings = {
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published texture files without UDIMs. Should"
                "correspond to a template defined in "
                "templates.yml.",
            },
            "Publish UDIM Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published texture files with UDIMs. Should"
                "correspond to a template defined in "
                "templates.yml.",
            },
            "Publish Folder Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published texture files with UDIMs. Should"
                "correspond to a template defined in "
                "templates.yml.",
            },
            "ShotGrid Export Preset index": {
                "type": "int",
                "default": 0,
                "description": "Index of the chosen shotgrid export preset. Internal to this plugin",
            },
            "ShotGrid Export Presets list": {
                "type": "list",
                "default": None,
                "description": "A list of dictionaries representing export presets."
                "Each dictionary contains the following keys:"
                "    - 'name' (str): The name of the export preset."
                "    - 'preset' (substance_painter.export.ResourceExportPreset): The actual export preset object."
                "    - 'index' (int): A counter for the preset.",
            },
        }

        # update the base settings
        base_settings.update(substancepainter_publish_settings)

        return base_settings

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters
        """
        return ["substancepainter.textureset"]

    def accept(self, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via
        the item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.

        :param settings: Dictionary of Settings. The keys are strings, matching
                         the keys returned in the settings property. The values
                         are `Setting` instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """

        item.context_change_allowed = False

        # Get all the resource export presets from Substance Painter
        # NOTE: Assuming we have presets whose name starts with "shotgrid"
        resource_presets = sp.export.list_resource_export_presets()
        shotgrid_export_presets = []

        counter = 0
        for resource_preset in resource_presets:
            if resource_preset.resource_id.name.lower().startswith("shotgrid"):
                shotgrid_export_presets.append(
                    {
                        "name": resource_preset.resource_id.name,
                        "preset": resource_preset,
                        "index": counter,
                    }
                )
                counter += 1

        if not shotgrid_export_presets:
            self.logger.warning(
                "Did not find any export preset for ShotGrid"
                "At least one export preset whose name should "
                " start with 'shotgrid' should exist. Check"
                " your Substance Painter export presets."
            )
            return {"accepted": False, "checked": False}

        settings["ShotGrid Export Presets list"].value = shotgrid_export_presets

        self.logger.info(
            f"Substance Painter '{self.name}' plugin accepted to publish textures."
        )
        return {"accepted": True, "checked": True}

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity.

        This method is called after the user has ticked the checkbox for this
        plugin in the UI. It performs checks to ensure that the operation can
        proceed safely.

        :param settings: Dictionary of Settings. The keys are strings, matching
                         the keys returned in the settings property. The values
                         are `Setting` instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """

        publisher = self.parent
        engine = publisher.engine

        # Set the chosen export preset on the item
        for preset_dict in settings["ShotGrid Export Presets list"].value:
            if preset_dict["index"] == settings["ShotGrid Export Preset index"].value:
                item.properties["export_preset"] = preset_dict["preset"]

        # Need to check that the export preset is correct, matching our
        # convention of '$textureSet_<MapName>_$colorSpace(.$udim)'
        # Note : underscores are NOT allowed in the <MapName>
        maps = item.properties["export_preset"].list_output_maps()
        for mp in maps:
            map_filename = mp["fileName"]
            match = TEXTURE_ABSTRACT_PATH_REGEX.match(map_filename)
            if not match:
                self.logger.error(
                    f"Issue with the export preset: {item.properties['export_preset'].resource_id.name}"
                )
                self.logger.error(
                    f"The export filename: {map_filename} is not matching the requirements. "
                )
                self.logger.error(
                    "It should match the pattern : '$textureSet_<MapNameNoUnderscores>_$colorSpace(.$udim)'"
                )

                self.logger.error(
                    "Export preset validation failed",
                    extra={
                        "action_button": {
                            "label": "Copy Path",
                            "tooltip": "Copy correct path",
                            "callback": lambda: QtGui.QApplication.clipboard().setText(
                                "$textureSet_<MapNameNoUnderscores>_$colorSpace(.$udim)"
                            ),
                        }
                    },
                )

                self._show_preset_warning_dialog(
                    item.properties["export_preset"].resource_id.name
                )

                # QtWidgets.QMessageBox.warning(None,"ShotGrid Warning", "It should match the pattern : '$textureSet_<MapNameNoUnderscores>_$colorSpace(.$udim)'")

                return False

        # Work area for exported textures:
        work_export_path = ""
        export_area_template = engine.get_texture_export_work_area_template()
        if export_area_template:
            fields = publisher.context.as_template_fields(export_area_template)
            work_export_path = export_area_template.apply_fields(fields)
            work_export_path = engine.convert_unc_path_to_mapped_drive_path(
                work_export_path
            )
        else:
            self.logger.error("Couldn't find the export area template from the engine")
            return False

        # Construct the export configuration
        texture_set = item.properties["texture_set"]
        sg_export_preset = item.properties["export_preset"]

        export_config = {
            "exportPath": work_export_path,
            "defaultExportPreset": sg_export_preset.resource_id.url(),
            "exportShaderParams": False,
            "exportParameters": [
                {"parameters": {"dithering": True, "paddingAlgorithm": "infinite"}}
            ],
        }

        root_paths = []
        all_stacks = texture_set.all_stacks()
        if all_stacks:
            for stack in all_stacks:
                root_paths.append({"rootPath": f"{texture_set.name}/{stack.name()}"})
        else:
            root_paths = [{"rootPath": texture_set.name}]

        export_config["exportList"] = root_paths

        # store the export config on the item
        item.properties["export_config"] = export_config

        # Store the name of the texture set, removing any underscores
        item.properties["texture_set_name"] = texture_set.name.replace("_", "")

        return True

    def publish(self, settings, item):
        """
        :param settings: Dictionary of Settings. The keys are strings, matching
                         the keys returned in the settings property.
                         The values are `Setting` instances.
        :param item: Item to process
        """

        publisher = self.parent

        # Order Substance Painter to export the textures
        # This will export the textures without in a work folder
        # possibly overwriting previous exports
        export_result = sp.export.export_project_textures(
            item.properties["export_config"]
        )

        # In case of error, display a human readable message:
        if export_result.status != sp.export.ExportStatus.Success:
            self.logger.error(export_result.message)

        # Create a list to hold all texture filepaths
        exported_textures = []

        for k, v in export_result.textures.items():
            self.logger.info(f"Export Stack {k}:")
            for exported in v:
                exported_textures.append(exported)
                self.logger.info(f"Exported texure: {exported}")

        # Group texture paths by map type:
        # if using UDIMs, all UDIMs of the same map will be grouped together
        grouped_texture_paths = self._group_texture_sequences(exported_textures)

        # Use the version number from the publish data of the substance project
        # that was previously published
        item.properties["version_number"] = item.parent.get_property(
            "sg_publish_data", {}
        ).get("version_number")

        publish_dependencies_ids = []
        if "sg_publish_data" in item.parent.properties:
            publish_dependencies_ids.append(
                item.parent.properties.sg_publish_data["id"]
            )

        # Empty list that will hold the publish id of each published texture
        textures_publish_ids = []

        # Now we can publish each texture file group
        for grouped_texture_path in grouped_texture_paths:
            # If the 'grouped_texture_path' list contains a single filepath
            # it means we have no UDIMs
            if len(grouped_texture_path) == 1:
                publish_template_setting = settings.get("Publish Template")
            else:  # we have multiple files, meaning UDIMs are used
                publish_template_setting = settings.get("Publish UDIM Template")
            texture_publish_template = publisher.engine.get_template_by_name(
                publish_template_setting.value
            )

            # Fields : start by getting the common fields from the context
            fields = publisher.context.as_template_fields(texture_publish_template)
            fields["version"] = item.properties["version_number"]

            # We are not using a work template for the textures because, AFAIK
            # there is no way to fully customize the substance export system
            # Instead, we extract the rest of the fields by analyzing the file paths,
            # assuming we exported using a predefined 'shotgrid' export
            for texture_path in grouped_texture_path:
                filename = os.path.basename(texture_path)
                match = re.match(TEXTURE_FILENAME_REGEX, filename)
                fields["texture_set"] = item.properties["texture_set_name"]
                fields["texture_map"] = match.group("texture_map")
                fields["colorspace"] = match.group("colorspace")
                fields["extension"] = match.group("extension")
                if match.group("udim"):
                    fields["UDIM"] = int(match.group("udim"))

                texture_publish_file = texture_publish_template.apply_fields(fields)

                # Copy (and rename) each texture file to the publish destination
                try:
                    ensure_folder_exists(os.path.dirname(texture_publish_file))
                    copy_file(texture_path, texture_publish_file)
                except Exception:
                    raise Exception(
                        "Failed to copy work file from '%s' to '%s'.\n%s"
                        % (texture_path, texture_publish_file, traceback.format_exc())
                    )

            # Construct the (abstract) publish path
            fields.pop("UDIM", None)
            texture_publish_path = texture_publish_template.apply_fields(fields)

            # Create the publish name
            publish_name = f"{fields['Asset']}_{fields['task_name']}_{item.properties['texture_set_name']}_{fields['texture_map']}"

            publish_data = {
                "tk": publisher.sgtk,
                "context": item.context,
                "comment": item.description,
                "path": texture_publish_path,
                "name": publish_name,
                "version_number": item.properties["version_number"],
                "published_file_type": TEXTURE_PUBLISH_TYPE,
                "dependency_ids": publish_dependencies_ids,
            }

            # Try to generate a thumbnail from the first file in the group
            thumb_path = self._generate_thumbnail(grouped_texture_path[0])
            if thumb_path:
                publish_data["thumbnail_path"] = thumb_path

            sg_publish_data = sgtk.util.register_publish(**publish_data)
            self.logger.info("Texture Publish registered!")
            self.logger.debug(
                "ShotGrid Publish data...",
                extra={
                    "action_show_more_info": {
                        "label": "ShotGrid Publish Data",
                        "tooltip": "Show the complete ShotGrid Publish Entity dictionary",
                        "text": "<pre>%s</pre>" % (pprint.pformat(sg_publish_data),),
                    }
                },
            )

            # TODO check conflicting publishes somewhere....

            # Store the id of the registered texture publish
            textures_publish_ids.append(sg_publish_data["id"])

        # Store all the registered publish ids on the item properties
        item.properties["textures_publish_ids"] = textures_publish_ids

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        Use the finalize pass to register a 'texture set' publish.
        This 'texture set' publish will have each previously published textures
        in its dependencies. Can be used in the loader to create a shader using
        all the textures needed for a material

        :param settings: Dictionary of Settings. The keys are strings, matching
                         the keys returned in the settings property.
                         The values are `Setting` instances.
        :param item: Item to process
        """
        publisher = self.parent

        entity_name = publisher.context.entity.get("name")
        task_name = publisher.context.task.get("name")
        texture_set_name = item.properties["texture_set_name"]

        set_publish_name = f"{entity_name}_{task_name}_{texture_set_name}"

        publish_template_setting = settings.get("Publish Folder Template")
        set_publish_template = publisher.engine.get_template_by_name(
            publish_template_setting.value
        )

        fields = publisher.context.as_template_fields(set_publish_template)
        fields["version"] = item.properties["version_number"]
        fields["texture_set"] = texture_set_name
        set_publish_path = set_publish_template.apply_fields(fields)

        publish_data = {
            "tk": publisher.sgtk,
            "context": item.context,
            "comment": item.description,
            "path": set_publish_path,
            "name": set_publish_name,
            "version_number": item.properties["version_number"],
            "thumbnail_path": item.get_thumbnail_as_path(),
            "published_file_type": TEXTURE_SET_PUBLISH_TYPE,
            "dependency_ids": item.properties["textures_publish_ids"],
        }

        sg_publish_data = sgtk.util.register_publish(**publish_data)
        self.logger.info("Texture Set Publish registered!")
        self.logger.debug(
            "ShotGrid Publish data...",
            extra={
                "action_show_more_info": {
                    "label": "ShotGrid Publish Data",
                    "tooltip": "Show the complete ShotGrid Publish Entity dictionary",
                    "text": "<pre>%s</pre>" % (pprint.pformat(sg_publish_data),),
                }
            },
        )

    ############################################ Private methods

    def _group_texture_sequences(self, paths):
        """
        Groups texure file paths by their base name, treating numbered sequences (UDIMs) as the same file.

        Example:
            ['DefaultMaterial_BaseColor_ACEScg.1001.exr',
             'DefaultMaterial_BaseColor_ACEScg.1002.exr'] > will be grouped together
        """
        groups = {}

        for path in paths:
            filename = os.path.basename(path)
            # Match pattern like .1001, .1002, etc. before the extension
            # This regex finds .<digits> before the file extension
            key = re.sub(r"\.\d+(\.\w+)$", r".<UDIM>\1", filename)
            groups.setdefault(key, []).append(path)

        # Return as list of lists, maintaining insertion order
        return list(groups.values())

    def _generate_thumbnail(self, source_path):
        """
        Generate thumbnail using OpenImageIO.
        """
        try:
            import OpenImageIO as oiio
        except ImportError:
            self.logger.warning("OpenImageIO not available, cannot generate thumbnail")
            return None

        try:
            # Read the file
            buf = oiio.ImageBuf(source_path)
            resized_buf = oiio.ImageBufAlgo.fit(
                buf, roi=oiio.ROI(0, 512, 0, 512, 0, 1, 0, 3)
            )
            oiio.ImageBufAlgo.colorconvert(
                resized_buf, resized_buf, "scene_linear", "sRGB"
            )

            # Create temp filepath
            temp_dir = tempfile.gettempdir()
            thumb_filename = f"sgtk_thumb_{os.path.basename(source_path)}.jpg"
            thumb_path = os.path.join(temp_dir, thumb_filename)

            # Write the image buffer
            resized_buf.write(thumb_path)

            self.logger.debug(f"Generated thumbnail: {thumb_path}")
            return thumb_path

        except Exception as e:
            self.logger.debug(f"Failed to generate thumbnail: {e}")
            return None

    def _show_preset_warning_dialog(self, export_preset_name):
        """
        Show warning dialog for incorrect export preset

        """
        publisher = self.parent
        engine = publisher.engine

        # Create the dialog
        dialog = QtGui.QDialog()
        dialog.setWindowTitle("Shotgrid warning")
        dialog.setModal(True)
        dialog.setMinimumWidth(520)

        # Main layout
        layout = QtGui.QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Warning text
        text_label = QtGui.QLabel(
            f"Check your export preset: '{export_preset_name}'\n"
            "Every texture map should have the filename pattern set to:\n"
            "$textureSet_<MapName>_$colorSpace(.$udim).\n"
            "No underscores allowed in <MapName>"
        )

        layout.addWidget(text_label)

        image_path = os.path.join(
            engine.disk_location, "resources", "dialogs", "export_preset_info.png"
        )
        image_label = QtGui.QLabel()
        pixmap = QtGui.QPixmap(image_path)

        image_label.setPixmap(pixmap)
        image_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(image_label)

        # Button box
        button_box = QtGui.QDialogButtonBox()

        # OK button
        ok_button = button_box.addButton(QtGui.QDialogButtonBox.Ok)
        ok_button.setDefault(True)

        # Copy Path button
        copy_button = QtGui.QPushButton("Copy Filename Pattern")
        button_box.addButton(copy_button, QtGui.QDialogButtonBox.ActionRole)

        layout.addWidget(button_box)

        # Copy to clipboard action
        def copy_to_clipboard():
            QtGui.QApplication.clipboard().setText(
                "$textureSet_<MapName>_$colorSpace(.$udim)"
            )
            copy_button.setText("Copied!")
            QtCore.QTimer.singleShot(
                1500, lambda: copy_button.setText("Copy Filename Pattern")
            )

        # Connect buttons
        ok_button.clicked.connect(dialog.accept)
        copy_button.clicked.connect(copy_to_clipboard)

        # Show the dialog
        dialog.exec_()

    ############################################ Settings UI

    def create_settings_widget(self, parent):
        """
        Creates the widget for our plugin.
        :param parent: Parent widget for the settings widget.
        :type parent: :class:`QtGui.QWidget`
        :returns: Custom widget for this plugin.
        :rtype: :class:`QtGui.QWidget`
        """

        return TextureSetExportSettingsWidget(parent)

    def get_ui_settings(self, widget):
        """
        Retrieves the state of the ui and returns a settings dictionary.
        :param parent: The settings widget returned by :meth:`create_settings_widget`
        :type parent: :class:`QtGui.QWidget`
        :returns: Dictionary of settings.
        """

        return {
            "ShotGrid Export Preset index": widget.export_preset_index,
        }

    def set_ui_settings(self, widget, settings):
        """
        Populates the UI with the settings for the plugin.
        :param parent: The settings widget returned by :meth:`create_settings_widget`
        :type parent: :class:`QtGui.QWidget`
        :param list(dict) settings: List of settings dictionaries, one for each
            item in the publisher's selection.
        :raises NotImplementeError: Raised if this implementation does not
            support multi-selection.
        """
        if len(settings) > 1:
            raise NotImplementedError()
        settings = settings[0]

        widget.export_preset_list = [
            a["name"] for a in settings["ShotGrid Export Presets list"]
        ]
        widget.export_preset_index = settings["ShotGrid Export Preset index"]


try:
    from sgtk.platform.qt import QtCore, QtGui
except ImportError:
    CustomWidgetController = None
else:

    class TextureSetExportSettingsWidget(QtGui.QWidget):
        def __init__(self, parent):
            super().__init__(parent)

            self.export_preset_label = QtGui.QLabel("Export Preset:")
            self.export_preset_combobox = QtGui.QComboBox(self)
            self.export_preset_layout = QtGui.QHBoxLayout()
            self.export_preset_layout.addWidget(self.export_preset_label)
            self.export_preset_layout.addWidget(self.export_preset_combobox)

            sp = QtGui.QSizePolicy(
                QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Maximum
            )
            self.export_preset_combobox.setSizePolicy(sp)

            layout = QtGui.QVBoxLayout()
            layout.setAlignment(QtCore.Qt.AlignLeft)
            self.setLayout(layout)
            layout.addLayout(self.export_preset_layout)

        @property
        def export_preset_index(self):
            return self.export_preset_combobox.currentIndex()

        @export_preset_index.setter
        def export_preset_index(self, value):
            self.export_preset_combobox.setCurrentIndex(value)

        @property
        def export_preset_list(self):
            pass

        @export_preset_list.setter
        def export_preset_list(self, names):
            self.export_preset_combobox.addItems(names)
