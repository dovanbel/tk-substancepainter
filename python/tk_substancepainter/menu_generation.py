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


import sgtk
import substance_painter as sp
from sgtk.platform.qt6 import QtCore, QtGui, QtWidgets


class MenuGenerator(object):
    """
    Handles the creation, display, and management of the ShotGrid
    menu within Adobe Substance 3D Painter.

    This class builds a QMenu based on the commands registered with the engine,
    including context information, favorites, and commands grouped by app.
    """

    def __init__(self, engine, sg_menu_name, main_window):
        # Initializes the menu generator.

        self._engine = engine
        self._main_window = main_window

        menu_bar = self._main_window.menuBar()

        # Create the QMenu object for the ShotGrid menu
        self._shotgrid_menu = QtWidgets.QMenu(title=sg_menu_name)
        menu_bar.addMenu(self._shotgrid_menu)

    def disable_menu(self):
        self._shotgrid_menu.clear()

        sgtk_disabled = QtGui.QAction("Sgtk is disabled.", self._shotgrid_menu)
        self._shotgrid_menu.addAction(sgtk_disabled)

    def destroy_menu(self):
        menu_bar = self._main_window.menuBar()
        menu_bar.removeAction(self._shotgrid_menu.menuAction())

        self._shotgrid_menu.clear()
        self._shotgrid_menu = None

    def setup_menu_items(self):
        """
        Render the entire Shotgun menu.
        In order to have commands enable/disable themselves based on the
        enable_callback, re-create the menu items every time.
        """

        # Reset the menu, remove all items
        self._shotgrid_menu.clear()

        # now add the context item on top of the main menu
        self._context_menu = self._add_context_menu()

        # add menu divider
        self._add_divider(self._shotgrid_menu)

        # now enumerate all items and create menu objects for them
        menu_items = []
        for cmd_name, cmd_details in self._engine.commands.items():
            menu_items.append(AppCommand(cmd_name, self, cmd_details))

        # sort list of commands in name order
        menu_items.sort(key=lambda x: x.name)

        # now add favourites
        for fav in self._engine.get_setting("menu_favourites"):
            self._add_favourite(fav, menu_items)

        # add menu divider
        self._add_divider(self._shotgrid_menu)

        # now add all apps to main menu
        self._add_app_menus(menu_items)

    def _add_favourite(self, fav, menu_items):
        """
        Finds a command specified in the 'menu_favourites' setting and adds it
        directly to the top level of the menu.
        """
        app_instance_name = fav["app_instance"]
        menu_name = fav["name"]

        # scan through all menu items
        for cmd in menu_items:
            if (
                cmd.get_app_instance_name() == app_instance_name
                and cmd.name == menu_name
            ):
                # found our match!
                cmd.add_command_to_menu(self._shotgrid_menu)
                # mark as a favourite item
                cmd.favourite = True

    def _add_app_menus(self, menu_items):
        """
        Organizes all commands by their parent app and adds them to the menu.
        - Commands with a 'context_menu' type are added to the context sub-menu.
        - Other commands are grouped into a dictionary by app name.
        """
        commands_by_app = {}
        for cmd in menu_items:
            if cmd.get_type() == "context_menu":
                # context menu!
                cmd.add_command_to_menu(self._context_menu)

            else:
                # normal menu
                app_name = cmd.get_app_name()
                if app_name is None:
                    # un-parented app
                    app_name = "Other Items"
                if app_name not in commands_by_app:
                    commands_by_app[app_name] = []
                commands_by_app[app_name].append(cmd)

        self._add_commands_by_app_to_menu(commands_by_app)

    def _add_divider(self, parent_menu):
        """Adds a separator line to a QMenu."""
        divider = QtGui.QAction(parent_menu)
        divider.setSeparator(True)
        parent_menu.addAction(divider)
        return divider

    def _add_sub_menu(self, menu_name, parent_menu):
        """Adds a new sub-menu to a parent QMenu."""
        sub_menu = QtWidgets.QMenu(title=menu_name, parent=parent_menu)
        parent_menu.addMenu(sub_menu)
        return sub_menu

    def _add_menu_item(self, name, parent_menu, callback, properties=None):
        """Adds a single action item to a QMenu."""
        action = QtGui.QAction(name, parent_menu)
        parent_menu.addAction(action)
        action.triggered.connect(callback)

        if properties:
            if "tooltip" in properties:
                action.setTooltip(properties["tooltip"])
                action.setStatustip(properties["tooltip"])
            if "enable_callback" in properties:
                action.setEnabled(properties["enable_callback"]())

        return action

    def _add_context_menu(self):
        """
        Adds the top-level context menu. This menu displays the current Toolkit
        context and provides actions like "Jump to ShotGrid" and
        "Jump to File System".
        """

        ctx = self._engine.context
        ctx_name = str(ctx)

        # create the menu object

        ctx_menu = self._add_sub_menu(ctx_name, self._shotgrid_menu)

        self._add_menu_item("Jump to ShotGrid", ctx_menu, self._jump_to_sg)

        # Add the menu item only when there are some file system locations.
        if ctx.filesystem_locations:
            self._add_menu_item("Jump to File System", ctx_menu, self._jump_to_fs)

        # divider (apps may register entries below this divider)
        self._add_divider(ctx_menu)

        return ctx_menu

    def _jump_to_sg(self):
        """
        Callback to launch a web browser and navigate to the current context's
        URL in ShotGrid.
        """
        url = self._engine.context.shotgun_url
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def _jump_to_fs(self):
        """
        Callback to open the file system browser to the context's locations on disk.
        """
        # launch one window for each location on disk
        paths = self._engine.context.filesystem_locations
        for path in paths:
            url = QtCore.QUrl.fromLocalFile(path)
            if not QtGui.QDesktopServices.openUrl(url):
                self._engine.logger.error("Failed to open folder: %s", path)

    def _add_commands_by_app_to_menu(self, commands_by_app):
        """
        Iterates over the commands grouped by app and adds them to the menu.

        - If an app has multiple commands, a sub-menu is created for it.
        - If an app has only one command, it's added directly to the main menu.
        """
        for app_name in sorted(commands_by_app.keys()):
            if len(commands_by_app[app_name]) > 1:
                # more than one menu entry fort his app
                # make a sub menu and put all items in the sub menu
                app_menu = self._add_sub_menu(app_name, self._shotgrid_menu)

                # get the list of menu cmds for this app
                cmds = commands_by_app[app_name]
                # make sure it is in alphabetical order
                cmds.sort(key=lambda x: x.name)

                for cmd in cmds:
                    cmd.add_command_to_menu(app_menu)
            else:
                # this app only has a single entry.
                # display that on the menu
                # todo: Should this be labelled with the name of the app
                # or the name of the menu item? Not sure.
                cmd_obj = commands_by_app[app_name][0]
                if not cmd_obj.favourite:
                    # skip favourites since they are already on the menu
                    cmd_obj.add_command_to_menu(self._shotgrid_menu)


class AppCommand(object):
    """
    A wrapper class for a single command dictionary from `engine.commands`.

    This makes it easier to access command properties and provides helper methods
    for interacting with the command's associated app and metadata.
    """

    def __init__(self, name, parent, command_dict):
        self.name = name
        self.parent = parent
        self.properties = command_dict["properties"]
        self.callback = command_dict["callback"]
        self.favourite = False

    def get_app_name(self):
        """
        Returns the display name of the app that this command belongs to.
        """
        if "app" in self.properties:
            return self.properties["app"].display_name
        return None

    def get_app_instance_name(self):
        """
        Returns the name of the app instance, as defined in the environment.
        Returns None if not found.
        """
        if "app" not in self.properties:
            return None

        app_instance = self.properties["app"]
        engine = app_instance.engine

        for app_instance_name, app_instance_obj in engine.apps.items():
            if app_instance_obj == app_instance:
                # found our app!
                return app_instance_name

        return None

    def get_documentation_url_str(self):
        """
        Returns the documentation URL for the associated app as a string.
        """
        if "app" in self.properties:
            app = self.properties["app"]
            return app.documentation_url
        return None

    def get_type(self):
        """
        Returns the command type, e.g., 'context_menu' or 'default'.
        """
        return self.properties.get("type", "default")

    def add_command_to_menu(self, menu):
        """
        Adds this app command to the given QMenu.

        It supports creating nested sub-menus if the command name contains '/'.
        """

        # create menu sub-tree if need to:
        # Support menu items seperated by '/'
        parent_menu = menu

        parts = self.name.split("/")
        for item_label in parts[:-1]:
            # see if there is already a sub-menu item
            sub_menu = self._find_sub_menu_item(parent_menu, item_label)
            if sub_menu:
                # already have sub menu
                parent_menu = sub_menu
            else:
                parent_menu = self.parent._add_sub_menu(item_label, parent_menu)

        # Add the final action to the determined parent menu.
        self.parent._add_menu_item(
            parts[-1], parent_menu, self.callback, self.properties
        )

    def _find_sub_menu_item(self, menu, label):
        """
        Helper to find an existing sub-menu QAction within a parent menu by its label.
        """
        for action in menu.actions():
            if action.text() == label:
                return action.menu()
        return None
