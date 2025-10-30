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


"""
This file is automatically copied into the user documents substance painter python startup folder
This file is loaded automatically by Substance Painter at startup and the start_plugin() function is executed,
which sets up the Toolkit context and prepares the tk-substancepainter engine.
"""

import os
import substance_painter as sp

__author__ = "Donat Van Bellinghen"
__contact__ = "https://www.linkedin.com/in/donat-van-bellinghen-98002914/"
__credits__ = ["Diego Garcia Huerta", "Donat Van Bellinghen"]


def start_toolkit_classic():
    """
    Parse enviornment variables for an engine name and
    serialized Context to use to startup Toolkit and
    the tk-substancepainter engine and environment.
    """
    import sgtk

    logger = sgtk.LogManager.get_logger(__name__)

    logger.debug("Launching toolkit in classic mode.")

    # Get the name of the engine to start from the environement
    env_engine = os.environ.get("SGTK_ENGINE")
    if not env_engine:
        sp.logging.error("ShotGrid: Missing required environment variable SGTK_ENGINE.")
        return

    # Get the context load from the environment.
    env_context = os.environ.get("SGTK_CONTEXT")
    if not env_context:
        sp.logging.error(
            "ShotGrid: Missing required environment variable SGTK_CONTEXT."
        )
        return
    try:
        # Deserialize the environment context
        context = sgtk.context.deserialize(env_context)
    except Exception as e:
        sp.logging.error(
            "ShotGrid: Could not create context! ShotGrid Pipeline Toolkit will "
            f"be disabled. Details: {e}"
        )
        return

    try:
        # Start up the toolkit engine from the environment data
        logger.debug(
            f"Launching engine instance '{env_engine}' for context {env_context}"
        )
        sgtk.platform.start_engine(env_engine, context.sgtk, context)
    except Exception as e:
        sp.logging.error(f"ShotGrid: Could not start engine: {e}")
        return





def start_plugin():

    # Verify sgtk can be loaded.
    try:
        import sgtk
    except Exception as e:
        sp.logging.info(
            f"ShotGrid Bootstrap: Could not import sgtk! Aborting engine startup: {e}"
        )
        return

    # start up toolkit logging to file
    sgtk.LogManager().initialize_base_file_handler("tk-substancepainter")

    start_toolkit_classic()

    # Check if a file was specified to open and open it.
    file_to_open = os.environ.get("SGTK_FILE_TO_OPEN")
    if file_to_open:
        sp.logging.info(f"ShotGrid: Opening '{file_to_open}'...")
        sp.project.open(file_to_open)

    del_vars = [
        "SGTK_ENGINE",
        "SGTK_CONTEXT",
        "SGTK_FILE_TO_OPEN",
    ]
    for var in del_vars:
        if var in os.environ:
            del os.environ[var]

