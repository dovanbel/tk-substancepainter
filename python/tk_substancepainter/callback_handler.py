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

logger = sgtk.LogManager.get_logger(__name__)


class CallbackHandler(object):
    def __init__(self, engine):
        self.engine = engine
        self.callbacks_registered = False
        self.project_events = [
            sp.event.ProjectOpened,
            sp.event.ProjectSaved,
            sp.event.ProjectCreated,
            sp.event.ProjectClosed,
        ]

    def register_callbacks(self):
        if not self.engine or self.engine.get_setting("automatic_context_switch"):
            for ev in self.project_events:
                sp.event.DISPATCHER.connect_strong(ev, self.on_project_event)

            self.callbacks_registered = True
            logger.debug("Callbacks registered")

    def unregister_callbacks(self):
        if self.callbacks_registered:
            for ev in self.project_events:
                sp.event.DISPATCHER.disconnect(ev, self.on_project_event)

            self.callbacks_registered = False
            logger.debug("Callbacks Unregistered")

    @staticmethod
    def on_project_event(event):
        engine = sgtk.platform.current_engine()

        if not engine:
            # If we don't have an engine for some reason then we don't have
            # anything to do.
            logger.debug(
                "No currently initialized engine found; aborting the refresh of the engine"
            )
            return

        if not sp.project.is_open():
            # No substance scene has been opened yet, so we just leave the engine in the current
            # context and move on.
            logger.debug("No open scene, aborting the refresh of the engine.")
            return

        current_context = engine.context

        # Get the path of the current open Substance scene file.
        current_project_path = sp.project.file_path()

        if not current_project_path:
            return

        current_project_path = current_project_path.replace("/", os.path.sep)
        if os.path.splitext(current_project_path)[1].lower() == ".spt":
            # If the current project uses the filepath of the template file, just ignore
            return

        try:
            tk = sgtk.sgtk_from_path(current_project_path)
            logger.debug(
                "Extracted sgtk instance: '%r' from path: '%r'",
                tk,
                current_project_path,
            )
        except sgtk.TankError as e:
            logger.warning(
                f"Project file: '{current_project_path}' does not appear to belong to a ShotGrid project.\n"
                "Disabling the ShotGrid engine and menu."
            )
            sp.logging.warning("ShotGrid: Engine cannot be started: %s" % e)
            # Disable the ShotGrid menu
            engine.menu_generator.disable_menu()
            return

        new_context = tk.context_from_path(current_project_path, current_context)
        logger.debug(
            "Given the path: '%s' the following context was extracted: '%r'",
            current_project_path,
            new_context,
        )

        if new_context != current_context:
            logger.debug("Changing the context to '%r", new_context)
            engine.change_context(new_context)
