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
import ctypes

import logging
import sgtk
from tank.platform import Engine
import substance_painter as sp


from PySide6 import QtWidgets, QtGui, QtCore
# from sgtk.platform.qt6 import QtWidgets, QtGui, QtCore # DOES NOT WORK


# Although the engine has logging already, this logger is needed for callback based logging
# where an engine may not be present.
logger = sgtk.LogManager.get_logger(__name__)


class SubstancePainterEngine(Engine):
    """
    Toolkit engine for Adobe Substance Painter
    """

    @property
    def context_change_allowed(self):
        """
        Whether the engine allows a context change without the need for a restart.
        """
        return True

    @property
    def has_ui(self):
        """
        Detect and return if Substance Painer has an ui
        Assuming Substance Painter always runs with an ui
        """
        return True

    @property
    def has_qt6(self):
        return True

    @property
    def host_info(self):
        """
        :returns: A {"name": application name, "version": application version}
                  dictionary with informations about the application hosting this
                  engine.

        """
        host_info = {"name": "substancepainter", "version": "unknown"}
        host_info["version"] = sp.application.version()

        return host_info

    ##########################################################################################
    # init and destroy

    def init_engine(self):
        """
        Initializes the Substance painter engine.
        """
        self.logger.debug(f"{self}: Initializing...")

        self._menu_name = "ShotGrid"
        self.substance_main_window = sp.ui.get_main_window()
        self._dock_widgets = {}

    def pre_app_init(self):
        """
        Runs after the engine is set up but before any apps have been initialized.
        """

        substance_major_version = sp.application.version_info()[0]
        if substance_major_version >= self.get_setting(
            "compatibility_dialog_min_version"
        ):
            logger.warning(
                "<b>Warning - ShotGrid Compatibility:</b><br>"
                "ShotGrid has not yet been fully tested"
                f" with Substance Painter version {substance_major_version}.<br>"
                "You can continue to use Toolkit but you may experience bugs or instabilities."
            )

        self.tk_substancepainter = self.import_module("tk_substancepainter")

        self.menu_generator = self.tk_substancepainter.MenuGenerator(
            self, self._menu_name, self.substance_main_window
        )

        self.callback_handler = self.tk_substancepainter.CallbackHandler(self)

        self.callback_handler.register_callbacks()

    def post_app_init(self):
        """
        Called when all apps have initialized
        """

        self.menu_generator.setup_menu_items()

        # Run a series of app instance commands at startup.
        self._run_app_instance_commands()

    def post_context_change(self, old_context, new_context):
        # Refresh the ShotGrid menu
        self.menu_generator.setup_menu_items()

    def _run_app_instance_commands(self):
        """
        Runs the series of app instance commands listed in the 'run_at_startup' setting
        of the environment configuration yaml file.
        """

        # Build a dictionary mapping app instance names to dictionaries of
        # commands they registered with the engine.
        app_instance_commands = {}
        for command_name, value in self.commands.items():
            app_instance = value["properties"].get("app")
            if app_instance:
                # Add entry 'command name: command function' to the command
                # dictionary of this app instance.
                command_dict = app_instance_commands.setdefault(
                    app_instance.instance_name, {}
                )
                command_dict[command_name] = value["callback"]

        # Run the series of app instance commands listed in the 'run_at_startup' setting.
        for app_setting_dict in self.get_setting("run_at_startup", []):
            app_instance_name = app_setting_dict["app_instance"]
            # Menu name of the command to run or '' to run all commands of the given app instance.
            setting_command_name = app_setting_dict["name"]

            # Retrieve the command dictionary of the given app instance.
            command_dict = app_instance_commands.get(app_instance_name)

            if command_dict is None:
                self.logger.warning(
                    "%s configuration setting 'run_at_startup' requests app '%s' that is not installed.",
                    self.name,
                    app_instance_name,
                )
            else:
                if not setting_command_name:
                    # Run all commands of the given app instance.
                    for command_name, command_function in command_dict.items():
                        self.logger.debug(
                            "%s startup running app '%s' command '%s'.",
                            self.name,
                            app_instance_name,
                            command_name,
                        )
                        command_function()
                else:
                    # Run the command whose name is listed in the 'run_at_startup' setting.
                    # Run this command once Maya will have completed its UI update and be idle
                    # in order to run it after the ones that restore the persisted Shotgun app panels.
                    command_function = command_dict.get(setting_command_name)
                    if command_function:
                        self.logger.debug(
                            "%s startup running app '%s' command '%s'.",
                            self.name,
                            app_instance_name,
                            setting_command_name,
                        )
                        command_function()
                    else:
                        known_commands = ", ".join(
                            "'%s'" % name for name in command_dict
                        )
                        self.logger.warning(
                            "%s configuration setting 'run_at_startup' requests app '%s' unknown command '%s'. "
                            "Known commands: %s",
                            self.name,
                            app_instance_name,
                            setting_command_name,
                            known_commands,
                        )

    def destroy_engine(self):
        """
        Called when the engine is being destroyed.
        """

        self.logger.debug(f"{self}: Destroying...")

        # Unregister the callbacks
        self.callback_handler.unregister_callbacks()

        # Destroy the menu
        self.menu_generator.destroy_menu()

    ##########################################################################################
    # ui

    def get_dialog_parent(self):
        """
        Get the QWidget parent for all dialogs created through
        show_dialog & show_modal.
        """
        return self.substance_main_window

    def _create_dialog(self, title, bundle, widget, parent):
        """
        Overriden from the base Engine class - create a TankQDialog with the specified widget
        embedded.

        :param title: The title of the window
        :param bundle: The app, engine or framework object that is associated with this window
        :param widget: A QWidget instance to be embedded in the newly created dialog.
        :param parent: The parent QWidget for the dialog
        """

        from sgtk.platform.qt import QtCore

        # call the base implementation to create the dialog:
        dialog = sgtk.platform.Engine._create_dialog(
            self, title, bundle, widget, parent
        )

        self._apply_external_styleshet(self, dialog)

        # raise and activate the dialog:
        dialog.raise_()
        dialog.activateWindow()

        if sgtk.util.is_windows():
            # special case to get windows to raise the dialog
            ctypes.windll.user32.SetActiveWindow(dialog.winId())

        return dialog

    def show_modal(self, title, bundle, widget_class, *args, **kwargs):
        """
        Override show_modal to handle Substance Painter's event loop properly.
        """
        # from PySide6 import QtWidgets
        from sgtk.platform.qt import QtCore, QtGui

        # Reset cursor before showing dialog
        while QtWidgets.QApplication.overrideCursor():
            QtWidgets.QApplication.restoreOverrideCursor()

        dialog, widget = self._create_dialog_with_widget(
            title, bundle, widget_class, *args, **kwargs
        )

        dialog.parent().setStyleSheet(dialog.parent().styleSheet())

        # finally launch it, modal state
        status = dialog.exec_()

        # lastly, return the instantiated widget
        return (status, widget)

    def show_panel(self, panel_id, title, bundle, widget_class, *args, **kwargs):
        """
        Shows a dockable panel
        :param panel_id: Unique identifier for the panel, as obtained by register_panel().
        :param title: The title of the panel
        :param bundle: The app, engine or framework object that is associated with this window
        :param widget_class: The class of the UI to be constructed. This must derive from QWidget.

        Additional parameters specified will be passed through to the widget_class constructor.

        :returns: the created widget_class instance
        """

        self.logger.debug(f"Begin showing panel {panel_id}")

        # Create a unique widget ID based on the panel_id
        widget_id = f"sgtk_{panel_id}"

        # Check if we already have a dock widget for this panel
        if panel_id in self._dock_widgets:
            self.logger.debug(f"Found existing dock widget for {panel_id}")
            dock_widget = self._dock_widgets[panel_id]

            # Show and raise the dock widget
            dock_widget.show()
            dock_widget.raise_()

            # Get the widget instance from the dock widget
            widget_instance = dock_widget.widget()

            return widget_instance

        # If widget doesn't exist, create it
        self.logger.debug(f"Creating new widget {widget_id}")

        parent = self.substance_main_window

        # Instantiate the widget class
        widget_instance = widget_class(*args, **kwargs)

        # Set the widget properties
        widget_instance.setObjectName(widget_id)
        widget_instance.setWindowTitle(title)
        widget_instance.setParent(parent)

        sg_panel_icon = os.path.join(
            self.disk_location, "resources", "icons", "shotgrid.png"
        )
        icon = QtGui.QIcon(sg_panel_icon)
        widget_instance.setWindowIcon(icon)

        # Apply external stylesheet if provided by the bundle
        self._apply_external_styleshet(bundle, widget_instance)

        # Add the widget as a dock widget in Substance Painter
        dock_widget = sp.ui.add_dock_widget(
            widget_instance, ui_modes=sp.ui.UIMode.Edition
        )

        dock_widget.show()
        dock_widget.raise_()

        # Store the dock widget reference
        self._dock_widgets[panel_id] = dock_widget

        self.logger.debug(f"Panel {panel_id} docked successfully")

        return widget_instance

    ##########################################################################################
    # public methods

    def get_texture_export_work_area_template(self):
        """
        Returns the configured work file template for the engine.
        """

        return self.get_template("textures_export_work_area")

    def convert_unc_path_to_mapped_drive_path(self, filepath):
        """
        Converts the UNC path to a mapped network drive path
        Only applies to Windows
        """

        return self.tk_substancepainter.utils._convert_unc_path_to_mapped_drive_path(
            self, filepath
        )

    def convert_mapped_drive_path_to_unc_path(self, filepath):
        """
        Converts the mapped network drive path to a UNC path
        Only applies to Windows
        """

        return self.tk_substancepainter.utils._convert_mapped_drive_path_to_unc_path(
            self, filepath
        )

    def get_project_path(self):
        """
        Get the file path of the currently open Substance Painter project

        Note that when creating a new project by using a Substance Painter
        template and before saving, the sp.project.file_path() returns the path of
        the template. In that case we consider the file path as being None
        """

        if not sp.project.is_open():
            return None

        project_path = sp.project.file_path()

        _, extension = os.path.splitext(project_path)

        if extension == ".spt":
            return None

        else:
            return self.convert_mapped_drive_path_to_unc_path(project_path)

    #####################################################################################
    # Logging

    def _emit_log_message(self, handler, record):
        """
        Emits a log to Substance Painter's Log panel.

        :param handler: Log handler that this message was dispatched from
        :type handler: :class:`~python.logging.LogHandler`
        :param record: Std python logging record
        :type record: :class:`~python.logging.LogRecord`
        """

        # msg = handler.format(record)

        formatter = logging.Formatter("%(message)s")

        msg = formatter.format(record)

        if record.levelno >= logging.ERROR:
            fct = self._show_error_dialog
        elif record.levelno >= logging.WARNING:
            fct = self._show_warning_dialog
        else:
            fct = sp.logging.info

        # Sends the message to the script editor.
        self.async_execute_in_main_thread(fct, msg)

    def _show_warning_dialog(self, message):
        sp.logging.warning(message)
        QtWidgets.QMessageBox.warning(
            self.substance_main_window, "ShotGrid Warning", message
        )

    def _show_error_dialog(self, message):
        sp.logging.error(message)
        QtWidgets.QMessageBox.critical(
            self.substance_main_window, "ShotGrid Error", message
        )
