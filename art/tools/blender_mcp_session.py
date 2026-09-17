"""Start an interactive Blender session with the MCP for Blender addon.

Enables the addon for THIS session only and never writes it into the user
preferences, so a normal Blender start has no open code-execution socket.
Telemetry stays off: the addon reads its consent preference fail-closed,
and with a session-only enable no preference entry (default: consent on)
is created. The MCP server side is started with DISABLE_TELEMETRY=true
(see art/BLENDER_WORKFLOW.md).

Usage (GUI, not --background - the addon refuses to serve in background mode):
    blender --python art/tools/blender_mcp_session.py [-- path/to/file.blend]

Requires the addon file once per Blender version:
    uvx mcp-for-blender@2.0.0 install-addon
"""

import sys

import addon_utils
import bpy

ADDON = "blender_mcp"


def main() -> None:
    known = {mod.__name__ for mod in addon_utils.modules()}
    if ADDON not in known:
        raise SystemExit(
            f"[blender_mcp_session] addon '{ADDON}' not found - run: "
            "uvx mcp-for-blender@2.0.0 install-addon"
        )

    # default_set=False: not stored in preferences, gone after this session.
    addon_utils.enable(ADDON, default_set=False, persistent=False)

    entry = bpy.context.preferences.addons.get(ADDON)
    if entry is not None and hasattr(entry.preferences, "telemetry_consent"):
        entry.preferences.telemetry_consent = False
    print(
        f"[blender_mcp_session] {ADDON} enabled for this session only; "
        f"preferences entry: {'yes, consent forced off' if entry else 'none (consent reads as off)'}; "
        "server auto-starts on localhost:9876"
    )

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if argv:
        bpy.ops.wm.open_mainfile(filepath=argv[0])


main()
