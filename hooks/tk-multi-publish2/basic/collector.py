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

import sgtk
import substance_painter as sp

HookBaseClass = sgtk.get_hook_baseclass()


SESSION_PUBLISH_TYPE = "Substance Painter Project File"


class SubstancePainterSessionCollector(HookBaseClass):
    """
    Collector that operates on the current Substance 3D Painter session.

    """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this collector expects to receive
        through the settings parameter in the process_current_session and
        process_file methods.

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

        # grab any base class settings
        collector_settings = super().settings or {}

        # settings specific to this collector
        substancepainter_session_settings = {
            "Work Template": {
                "type": "template",
                "default": None,
                "description": "Template path for artist work files. Should "
                "correspond to a template defined in "
                "templates.yml. If configured, is made available"
                "to publish plugins via the collected item's "
                "properties. ",
            },
        }

        # update the base settings with these settings
        collector_settings.update(substancepainter_session_settings)

        return collector_settings

    def process_current_session(self, settings, parent_item):
        """
        Analyzes the current session open in Substance 3D Painter and parents a
        subtree of items under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """
        publisher = self.parent
        engine = publisher.engine

        # First, create an item representing the current Substance 3D Painter session file.
        session_item = self.collect_current_substancepainter_session(
            settings, parent_item
        )

        # Create an item for each texture set
        all_texture_sets = sp.textureset.all_texture_sets()

        for texture_set in all_texture_sets:
            self.create_texture_set_export_item(settings, session_item, texture_set)

    def collect_current_substancepainter_session(self, settings, parent_item):
        """
        Creates an item that represents the current Substance 3D Painter session.

        :param parent_item: Parent Item instance

        :returns: Item of type substancepainter.session
        """

        publisher = self.parent
        engine = publisher.engine

        # get the path to the current file
        path = engine.get_project_path()

        # determine the display name for the item
        if path:
            file_info = publisher.util.get_file_path_components(path)
            display_name = file_info["filename"]
        else:
            display_name = "Current Substance 3D Painter Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "substancepainter.session",
            "Substance 3D Painter project",
            display_name,
        )

        # get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location, os.pardir, "icons", "substance_painter_icon.png"
        )
        session_item.set_icon_from_path(icon_path)

        work_template_setting = settings.get("Work Template")

        work_template = publisher.engine.get_template_by_name(
            work_template_setting.value
        )

        # store the template on the item for use by publish plugins. we
        # can't evaluate the fields here because there's no guarantee the
        # current session path won't change once the item has been created.
        # the attached publish plugins will need to resolve the fields at
        # execution time.
        session_item.properties["work_template"] = work_template
        session_item.properties["publish_type"] = SESSION_PUBLISH_TYPE

        self.logger.info("Collected current Substance 3D Painter session")

        return session_item

    def create_texture_set_export_item(self, settings, parent_item, texture_set):
        item = parent_item.create_item(
            "substancepainter.textureset",
            "Texture Set",
            texture_set.name,
        )

        # Store the sp texture set (type: substance_painter.textureset.TextureSet) on the item
        item.properties["texture_set"] = texture_set

        # get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location, os.pardir, "icons", "texture_set_icon.png"
        )
        item.set_icon_from_path(icon_path)

        return item
