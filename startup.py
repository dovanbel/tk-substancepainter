# Copyright 2025 Donat Van Bellinghen

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


import os
import plistlib
import shutil
import sys

import tank as sgtk
from tank.platform import LaunchInformation, SoftwareLauncher, SoftwareVersion

__author__ = "Donat Van Bellinghen"
__contact__ = "https://www.linkedin.com/in/donat-van-bellinghen-98002914/"
__credits__ = ["Diego Garcia Huerta", "Donat Van Bellinghen"]

logger = sgtk.LogManager.get_logger(__name__)

# We use this to indicate that we could not retrieve the version for the
# binary/executable, so we allow the engine to run with it
UNKNOWN_VERSION = "UNKNOWN_VERSION"

MINIMUM_SUPPORTED_VERSION = "11.0.0"


class SubstancePainterLauncher(SoftwareLauncher):
    """
    Handles launching SubstancePainter executables. Automatically starts up
    a tk-substancepainter engine with the current context in the new session
    of SubstancePainter.
    """

    # This dictionary defines a list of executable template strings for each
    # of the supported operating systems. The templates are used for both
    # globbing and regex matches by replacing the named format placeholders.
    # with an appropriate glob or regex string.

    # No regex for Adobe Substance Painter (no mention of the version number in the path)
    COMPONENT_REGEX_LOOKUP = {}

    EXECUTABLE_TEMPLATES = {
        "darwin": [
            "/Applications/Adobe Substance 3D Painter/Adobe Substance 3D Painter.app",
        ],
        "win32": [
            "C:/Program Files/Adobe/Adobe Substance 3D Painter/Adobe Substance 3D Painter.exe",
        ],
        "linux": [
            "/opt/Adobe/Adobe_Substance_3D_Painter/Adobe_Substance_3D_Painter",
        ],
    }

    @property
    def minimum_supported_version(self):
        """
        The minimum software version that is supported by the launcher.
        """
        return MINIMUM_SUPPORTED_VERSION

    def prepare_launch(self, exec_path, args, file_to_open=None):
        """
        Prepares an environment to launch Substance 3D Painter in that will automatically
        load Toolkit and the tk-substancepainter engine when Substance 3D Painter starts.

        :param str exec_path: Path to Substance 3D Painter executable to launch.
        :param str args: Command line arguments as strings.
        :param str file_to_open: (optional) Full path name of a file to open on
                                            launch.
        :returns: :class:`LaunchInformation` instance
        """

        # Get the susbtance painter user directory
        substance_user_directory = self._get_substance_painter_user_directory()

        # Get the substance painter user python startup directory
        user_python_startup_directory = os.path.join(
            substance_user_directory, "python", "startup"
        )
        user_export_presets_directory = os.path.join(
            substance_user_directory, "assets", "export-presets"
        )

        bootstrap_script_filepath = os.path.join(
            self.disk_location, "startup", "shotgrid_bootstrap.py"
        )
        # Copy the bootstrap python script to the user's substance python startup dir
        # This will make substance import the code automatically during launch
        self.copy_file(
            bootstrap_script_filepath, user_python_startup_directory, overwrite=True
        )

        # Copy the ShotGrid export presets to the user's substance painter documents
        # If exports presets already exists, leave them untouched
        sg_export_presets = self._get_shotgrid_export_presets()
        for exp in sg_export_presets:
            self.copy_file(exp, user_export_presets_directory, overwrite=False)

        # Prepare the launch environment with variables required by the
        # classic bootstrap approach.
        self.logger.debug(
            "Preparing SubstancePainter Launch via Toolkit Classic methodology ..."
        )

        required_env = {}
        required_env["SGTK_ENGINE"] = self.engine_name
        required_env["SGTK_CONTEXT"] = sgtk.context.serialize(self.context)

        # Pass the file to open to the engine via an environment variable.
        if file_to_open:
            required_env["SGTK_FILE_TO_OPEN"] = file_to_open

        return LaunchInformation(path=exec_path, environ=required_env)

    def copy_file(self, source_path, target_directory, overwrite=False):
        """
        Copy a file to a target directory

        Args:
            source_path: Full path to the source file
            target_directory: Path to the target directory
            overwrite: If False (default), skips copy if target file exists

        Returns:
            str or None: Path to the copied file, or None if skipped
        """

        # Check if source file exists
        if not os.path.isfile(source_path):
            self.logger.error(f"Error: Source file does not exist: {source_path}")
            raise FileNotFoundError(f"Source file does not exist: {source_path}")

        # Check if target directory exists
        if not os.path.isdir(target_directory):
            self.logger.error(
                f"Error: Target directory does not exist: {target_directory}"
            )
            raise NotADirectoryError(
                f"Target directory does not exist: {target_directory}"
            )

        # Get the filename from the source path
        filename = os.path.basename(source_path)
        # Build the full target path
        target_path = os.path.join(target_directory, filename)

        # If target file exists and overwrite is False, skip the copy
        if os.path.exists(target_path) and not overwrite:
            self.logger.info(f"File already exists, skipping copy: {target_path}")
            return None

        try:
            # Copy the file
            shutil.copy2(source_path, target_path)
            self.logger.info(
                f"Successfully copied '{filename}' to '{target_directory}'"
            )
            return target_path

        except Exception as e:
            self.logger.error(f"Error during copy: {e}")
            raise

    def _get_icon(self, exec_path):
        """
        Find the icon for the application.

        :param str exec_path: Path to the executable.
        :returns: Full path to application icon as a string or None.
        """
        icon_path = None

        if sys.platform == "darwin":
            # The user-provided path for the icon on macOS.
            # The executable path is the .app bundle itself.
            icon_path = os.path.join(exec_path, "Contents", "Resources", "painter.icns")

        elif sys.platform == "win32":
            # On Windows, the icon is typically embedded in the executable.
            # We can just return the path to the executable and the OS will handle it.
            icon_path = exec_path

        elif sys.platform.startswith("linux"):
            # On Linux, the icon is often a PNG file in a resources or icons folder
            # near the executable.
            icon_path = os.path.join(
                os.path.dirname(exec_path), "resources", "icon.png"
            )

        if icon_path and os.path.exists(icon_path):
            self.logger.debug("Found application icon at: %s", icon_path)
            return icon_path

        # the engine icon
        self.logger.debug("Using fallback engine icon.")
        engine_icon = os.path.join(self.disk_location, "icon_256.png")
        return engine_icon

    def scan_software(self):
        """
        Scan the filesystem for Substance 3D Painter executables.

        :return: A list of :class:`SoftwareVersion` objects.
        """
        self.logger.debug("Scanning for Substance 3D Painter executables...")

        supported_sw_versions = []
        for sw_version in self._find_software():
            (supported, reason) = self._is_supported(sw_version)

            if supported:
                supported_sw_versions.append(sw_version)
            else:
                self.logger.debug(
                    "SoftwareVersion %s is not supported: %s" % (sw_version, reason)
                )

        return supported_sw_versions

    def _find_software(self):
        """
        Find executables in the default install locations.
        """

        # all the executable templates for the current OS
        platform = "linux" if sys.platform.startswith("linux") else sys.platform
        executable_templates = self.EXECUTABLE_TEMPLATES.get(platform, [])

        # all the discovered executables
        sw_versions = []

        for executable_template in executable_templates:
            self.logger.debug("Processing template %s.", executable_template)

            executable_matches = self._glob_and_match(
                executable_template, self.COMPONENT_REGEX_LOOKUP
            )

            # Extract all products from that executable.
            for executable_path, key_dict in executable_matches:
                # extract the matched keys form the key_dict (default to None
                # if not included)
                if sys.platform == "win32":
                    executable_version = self.get_windows_executable_version(
                        executable_path
                    )
                elif sys.platform == "darwin":
                    executable_version = self._get_mac_executable_version(
                        executable_path
                    )
                else:
                    executable_version = key_dict.get("version", UNKNOWN_VERSION)

                self.logger.debug(
                    "Software found: %s | %s.", executable_version, executable_template
                )
                sw_versions.append(
                    SoftwareVersion(
                        executable_version,
                        "Adobe Substance 3D Painter",
                        executable_path,
                        self._get_icon(executable_path),
                    )
                )

        return sw_versions

    def _get_mac_executable_version(self, bundle_path):
        """
        Get the version number from the app bundle's Info.plist file.

        :param str bundle_path: Path to the .app bundle.
        :return: The version string or UNKNOWN_VERSION.
        """
        try:
            plist_path = os.path.join(bundle_path, "Contents", "Info.plist")
            with open(plist_path, "rb") as fp:
                plist_data = plistlib.load(fp)
            return plist_data.get("CFBundleShortVersionString", UNKNOWN_VERSION)
        except Exception as e:
            self.logger.warning("Could not read version from %s: %s", plist_path, e)
            return UNKNOWN_VERSION

    def _get_windows_executable_version(self, filepath):
        """
        Extracts the "FileVersion" information string from a Windows executable's
        """
        from ctypes import (
            POINTER,
            byref,
            c_uint,
            c_ushort,
            c_void_p,
            c_wchar_p,
            cast,
            create_string_buffer,
            windll,
        )

        size = windll.version.GetFileVersionInfoSizeW(filepath, None)
        if not size:
            return ""

        res = create_string_buffer(size)
        if not windll.version.GetFileVersionInfoW(filepath, 0, size, res):
            return ""

        # --- Get language and codepage ---
        lpTranslate = c_void_p()
        cbTranslate = c_uint()
        if not windll.version.VerQueryValueW(
            res, "\\VarFileInfo\\Translation", byref(lpTranslate), byref(cbTranslate)
        ):
            return ""

        if not cbTranslate.value:
            return ""

        # Each translation entry is two WORDs: language ID and code page.
        array_type = c_ushort * (cbTranslate.value // 2)
        translations = cast(lpTranslate.value, POINTER(array_type)).contents
        lang, codepage = translations[0], translations[1]

        # --- Extract the requested string ---
        sub_block = "\\StringFileInfo\\%04x%04x\\%s" % (lang, codepage, "FileVersion")
        lpBuffer = c_void_p()
        size = c_uint()
        if not windll.version.VerQueryValueW(
            res, sub_block, byref(lpBuffer), byref(size)
        ):
            return ""

        # lpBuffer points to a null-terminated wide string
        result = cast(lpBuffer.value, c_wchar_p).value.strip("\x00")

        return result

    def _get_shotgrid_export_presets(self):
        sg_export_presets_dir = os.path.join(
            self.disk_location, "resources", "export-presets"
        )

        sg_export_presets = [
            os.path.join(sg_export_presets_dir, f)
            for f in os.listdir(sg_export_presets_dir)
            if os.path.splitext(f)[1] == ".spexp"
        ]

        return sg_export_presets

    def _get_substance_painter_user_directory(self):
        """
        Returns the platform-specific path to the user's Substance 3D Painter
        directory.

        :return: Path to the user directory.
        """
        if sys.platform == "win32":
            import winreg

            win_reg_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            )
            user_documents_path = os.path.expandvars(
                winreg.QueryValueEx(win_reg_key, "Personal")[0]
            )

            sp_user_dir = os.path.join(
                user_documents_path,
                "Adobe",
                "Adobe Substance 3D Painter",
            )
            return sp_user_dir

        else:  # macOS and Linux
            sp_user_dir = os.path.expanduser(
                r"~/Documents/Adobe/Adobe Substance 3D Painter"
            )
            return sp_user_dir
