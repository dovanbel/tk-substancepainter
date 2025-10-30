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

HookClass = sgtk.get_hook_baseclass()


class SceneOperation(HookClass):
    """
    Hook called to perform scene operations in Substance 3D Painter for the
    tk-multi-snapshot app.

    This hook implements the logic for getting the current scene path,
    opening a snapshot, and saving a snapshot.
    """

    def execute(self, operation, file_path, context, *args, **kwargs):
        """
        Main hook entry point

        :param str operation:       Scene operation to perform (e.g., "current_path",
                                    "open", "save", "save_as").

        :param str file_path:       File path to use if the operation
                                    requires it (e.g., "open", "save_as").

        :param context:             The context the file operation is being
                                    performed in.

        :returns:   Depends on operation:
                    'current_path' - Return the current scene
                                     file path as a String
                    all others     - None
        """
        engine = sgtk.platform.current_engine()

        # ---- Get the current scene path
        if operation == "current_path":
            # This is called by the app to find out the path of the current
            # open project, which is the source for the snapshot. The app
            # uses this path to create the snapshot filename.
            return engine.get_project_path()

        # ---- Open a file
        elif operation == "open":
            # This is called when a user double-clicks a snapshot in the UI
            # to restore it. The app provides the file_path to open.
            sp.project.open(file_path)

        # ---- Save the current file
        elif operation == "save":
            # This is called when a user is working on a snapshot and saves it
            # via the app's "Save" command.
            sp.project.save(sp.project.ProjectSaveMode.Full)

        # ---- Save the current file as a new file
        elif operation == "save_as":
            # This is the most important operation for this hook. It's called
            # when the user clicks the "Create Snapshot" button. The app provides
            # the file_path where the new snapshot file should be saved.
            sp.project.save_as(file_path, sp.project.ProjectSaveMode.Incremental)

            ### NOTE: the substance painter api proposes another method :
            #  sp.project.save_as_copy()
            # perhaps this method should be used for tk-multi-snapshot ?
