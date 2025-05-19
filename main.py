import base64
import io
import os
from itertools import count
from sdbus.dbus_proxy_async_interface_base import DbusExportHandle

# The decky plugin module is located at decky-loader/plugin
# For easy intellisense checkout the decky-loader code repo
# and add the `decky-loader/plugin/imports` path to `python.analysis.extraPaths` in `.vscode/settings.json`
import decky
import asyncio
from asyncio import run as asyncio_run, get_event_loop
from typing import List, Dict, Tuple, Any

from sdbus import request_default_bus_name_async, dbus_method_async_override, set_context_default_bus, sd_bus_open_user
from sdbus_async.notifications import NotificationsInterface


def extract_embedded(struct: Tuple[str, Any]):
    if struct[0] != "(iiibiiay)":
        return None
    data = struct[1]
    width, height, rowstride, has_alpha, bits_per_sample, channels, pixels_data = data

    from PIL.Image import Image, frombuffer, frombytes
    im = frombytes("RGBA" if has_alpha else "RGB", (width, height), pixels_data)
    rawBytes = io.BytesIO()
    im.save(rawBytes,format="PNG")
    img_str = base64.b64encode(rawBytes.getvalue())
    return img_str


def find_image(app_icon: str | None, hints: Dict[str, Tuple[str, Any]]):
    if "image-data" in hints:
        return "b64", extract_embedded(hints["image-data"])
    elif "image-path" in hints:
        return "path", hints["image-path"]
    elif app_icon is not None:
        return "path", app_icon
    elif "icon_data" in hints:
        return "b64", extract_embedded(hints["icon_data"])
    return None


class CustomService(NotificationsInterface):
    counter: int = 0

    def __init__(self):
        super().__init__()

    @dbus_method_async_override()
    async def notify(
            self,
            app_name: str = '',
            replaces_id: int = 0,
            app_icon: str = '',
            summary: str = '',
            body: str = '',
            actions: List[str] = None,
            hints: Dict[str, Tuple[str, Any]] = None,
            expire_timeout: int = -1, ) -> int:
        self.counter += 1
        notif_id = self.counter
        data = find_image(app_icon, hints)
        await decky.emit(
            "show_notification",
            app_name,
            notif_id,
            list(data) if data is not None else None,
            summary,
            body,
            actions[0] if len(actions) > 0 else "",
            expire_timeout
        )
        return notif_id

    @dbus_method_async_override()
    async def get_capabilities(self) -> List[str]:
        return ["body", "body-markup", "body-images", "persistence", "sound", "icon-static", "actions"]

    @dbus_method_async_override()
    async def get_server_information(self) -> Tuple[str, str, str, str]:
        return "Decky desktop notifications", "LelouBil", "1.0", "1.2"

    @dbus_method_async_override()
    async def close_notification(self, notif_id: int) -> None:
        await decky.emit("close_notification", notif_id)


class Plugin:
    notifs: CustomService = None
    handle: DbusExportHandle = None

    async def notification_click(self, id: int, action: str):
        if self.notifs is None:
            decky.logger.error("Notificatin click event before init")
            return
        await self.notifs.action_invoked.emit(id, action)

    async def start_server(self):
        decky.logger.info("Starting server")
        decky.logger.info("Opening user bus")
        user = sd_bus_open_user()
        decky.logger.info(f"User bus open at : {user.address}")
        set_context_default_bus(user)
        decky.logger.info("Set user bus as default")
        self.notifs = CustomService()
        decky.logger.info("Acquiring name")
        await request_default_bus_name_async("org.freedesktop.Notifications", replace_existing=True)
        decky.logger.info("Exporting")
        self.handle = self.notifs.export_to_dbus("/org/freedesktop/Notifications")
        decky.logger.info("Setup finished")

    # Asyncio-compatible long-running code, executed in a task when the plugin is loaded
    async def _main(self):
        import PIL
        decky.logger.info(PIL.__version__)

        self.loop = asyncio.get_event_loop()
        decky.logger.info(f"Running as uid: {os.getuid()}")
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"
        decky.logger.info(f"DBUS addr: {os.environ['DBUS_SESSION_BUS_ADDRESS']}")

    # Function called first during the unload process, utilize this to handle your plugin being stopped, but not
    # completely removed
    async def _unload(self):
        decky.logger.info("Goodnight World!")
        if self.handle is not None:
            self.handle.stop()

    # Function called after `_unload` during uninstall, utilize this to clean up processes and other remnants of your
    # plugin that may remain on the system
    async def _uninstall(self):
        decky.logger.info("Goodbye World!")
        pass
