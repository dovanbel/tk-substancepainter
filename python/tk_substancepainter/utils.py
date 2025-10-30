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
import platform
import sys

import sgtk
import substance_painter as sp


def _convert_unc_path_to_mapped_drive_path(engine, filepath):
    """
    Replace the UNC prefix in 'filepath' with the corresponding mapped drive prefix
    based on the 'windows_path_mappings' setting of the engine

    Parameters
    ----------
    engine : the substance painter engine
    filepath : str
        The full path to convert.

    Returns
    -------
    str
        The converted path if a mapping applies, otherwise the original filepath.
    """

    if not platform.system() == "Windows":
        # If the OS is not Windows, nothing to do
        return filepath

    mappings = engine.get_setting("windows_path_mappings")

    if not mappings:
        return filepath

    filepath = os.path.normpath(filepath)
    normalized_filepath = filepath.lower()

    for mapping in mappings:
        unc_prefix = mapping.get("unc_prefix", "")
        mapped_prefix = mapping.get("mapped_drive_prefix", "")

        if not unc_prefix or not mapped_prefix:
            continue

        # Case-insensitive match on the prefix
        if normalized_filepath.startswith(unc_prefix.lower()):
            # Replace only the prefix, preserving case of the rest
            return filepath.replace(unc_prefix, mapped_prefix, 1)

    return filepath



def _convert_mapped_drive_path_to_unc_path(engine, filepath):

    if not platform.system() == "Windows":
        # If the OS is not Windows, nothing to do
        return filepath

    mappings = engine.get_setting("windows_path_mappings")

    if not mappings:
        return filepath

    filepath = os.path.normpath(filepath)
    normalized_filepath = filepath.lower()

    for mapping in mappings:
        unc_prefix = mapping.get("unc_prefix", "")
        mapped_prefix = mapping.get("mapped_drive_prefix", "")

        if not unc_prefix or not mapped_prefix:
            continue

        # Case-insensitive match on the prefix
        if normalized_filepath.startswith(mapped_prefix.lower()):
            # Replace only the prefix, preserving case of the rest
            return filepath.replace(mapped_prefix, unc_prefix, 1)

    return filepath