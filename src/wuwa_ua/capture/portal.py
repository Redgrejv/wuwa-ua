from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from queue import Empty, Queue
from typing import Any

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gio, GLib, Gst  # noqa: E402

import numpy as np  # noqa: E402

from wuwa_ua.types import Frame  # noqa: E402

PORTAL_BUS = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
PORTAL_REQUEST = "org.freedesktop.portal.Request"
SCREENCAST = "org.freedesktop.portal.ScreenCast"
SOURCE_TYPES = {"monitor": 1, "window": 2}
PERSIST_UNTIL_REVOKED = 2
QUEUE_SIZE = 2
FRAME_TIMEOUT = 5.0


class CaptureError(Exception):
    pass


class PortalCapture:
    def __init__(self, restore_token: str = "", source: str = "window") -> None:
        if source not in SOURCE_TYPES:
            raise CaptureError(f"невідоме джерело захоплення: {source}")
        Gst.init(None)
        self._source = source
        self._requested_token = restore_token
        self.restore_token = restore_token
        self._queue: Queue[Frame] = Queue(maxsize=QUEUE_SIZE)
        self._pipeline: Gst.Element | None = None
        self._context = GLib.MainContext.new()
        self._loop = GLib.MainLoop.new(self._context, False)
        self._loop_thread: threading.Thread | None = None
        self._node_id: int | None = None
        self._session: str | None = None
        self._token_serial = 0
        self._proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            None,
            PORTAL_BUS,
            PORTAL_PATH,
            SCREENCAST,
            None,
        )

    def start(self) -> None:
        self._negotiate()
        if self._node_id is None:
            raise CaptureError("портал не повернув PipeWire-вузол")
        self._build_pipeline(self._node_id)

    def frames(self) -> Iterator[Frame]:
        while True:
            try:
                yield self._queue.get(timeout=FRAME_TIMEOUT)
            except Empty as exc:
                raise CaptureError("потік кадрів зупинився") from exc

    def stop(self) -> None:
        if self._pipeline is not None:
            self._pipeline.set_state(Gst.State.NULL)
            self._pipeline = None
        if self._loop.is_running():
            self._loop.quit()
        if self._session is not None:
            self._close_session()

    def _next_token(self) -> str:
        self._token_serial += 1
        return f"wuwaua{self._token_serial}"

    def _request_path(self, token: str) -> str:
        connection = self._proxy.get_connection()
        sender = connection.get_unique_name().removeprefix(":").replace(".", "_")
        return f"{PORTAL_PATH}/request/{sender}/{token}"

    def _call(self, method: str, build_args: Any, token: str) -> dict[str, Any]:
        """Викликає метод портала й чекає на його Response.

        Підписка створюється ДО виклику: портал може відповісти на неінтерактивний запит
        раніше, ніж метод поверне handle, і тоді підписка постфактум пропустить сигнал назавжди.
        """
        connection = self._proxy.get_connection()
        pending = GLib.MainLoop()
        outcome: dict[str, Any] = {}
        failure: list[str] = []

        def on_response(
            _connection: Gio.DBusConnection,
            _sender: str,
            _path: str,
            _interface: str,
            _signal: str,
            parameters: GLib.Variant,
        ) -> None:
            code, payload = parameters.unpack()
            if code != 0:
                failure.append(f"портал відхилив запит {method} (код {code})")
            else:
                outcome.update(payload)
            pending.quit()

        subscription = connection.signal_subscribe(
            PORTAL_BUS,
            PORTAL_REQUEST,
            "Response",
            self._request_path(token),
            None,
            Gio.DBusSignalFlags.NONE,
            on_response,
        )
        try:
            self._proxy.call_sync(method, build_args, Gio.DBusCallFlags.NONE, -1, None)
            pending.run()
        finally:
            connection.signal_unsubscribe(subscription)

        if failure:
            raise CaptureError(failure[0])
        return outcome

    def _negotiate(self) -> None:
        token = self._next_token()
        session = self._call(
            "CreateSession",
            GLib.Variant(
                "(a{sv})",
                (
                    {
                        "session_handle_token": GLib.Variant("s", "wuwaua"),
                        "handle_token": GLib.Variant("s", token),
                    },
                ),
            ),
            token,
        )
        self._session = str(session["session_handle"])

        token = self._next_token()
        options = {
            "types": GLib.Variant("u", SOURCE_TYPES[self._source]),
            "multiple": GLib.Variant("b", False),
            "persist_mode": GLib.Variant("u", PERSIST_UNTIL_REVOKED),
            "handle_token": GLib.Variant("s", token),
        }
        if self._requested_token:
            options["restore_token"] = GLib.Variant("s", self._requested_token)
        self._call("SelectSources", GLib.Variant("(oa{sv})", (self._session, options)), token)

        token = self._next_token()
        started = self._call(
            "Start",
            GLib.Variant(
                "(osa{sv})",
                (self._session, "", {"handle_token": GLib.Variant("s", token)}),
            ),
            token,
        )

        self.restore_token = str(started.get("restore_token", self._requested_token))
        streams = started.get("streams", [])
        if not streams:
            raise CaptureError("портал не повернув жодного потоку")
        self._node_id = int(streams[0][0])

    def _close_session(self) -> None:
        connection = self._proxy.get_connection()
        try:
            connection.call_sync(
                PORTAL_BUS,
                self._session,
                "org.freedesktop.portal.Session",
                "Close",
                None,
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )
        except GLib.Error:
            pass
        self._session = None

    def _build_pipeline(self, node_id: int) -> None:
        description = (
            f"pipewiresrc path={node_id} ! videoconvert ! "
            "video/x-raw,format=BGR ! appsink name=sink emit-signals=true max-buffers=1 drop=true"
        )
        try:
            self._pipeline = Gst.parse_launch(description)
        except GLib.Error as exc:
            raise CaptureError(f"не вдалося зібрати конвеєр GStreamer: {exc.message}") from exc
        sink = self._pipeline.get_by_name("sink")
        sink.connect("new-sample", self._on_sample)
        self._pipeline.set_state(Gst.State.PLAYING)
        self._loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._loop_thread.start()

    def _run_loop(self) -> None:
        self._context.push_thread_default()
        try:
            self._loop.run()
        finally:
            self._context.pop_thread_default()

    def _on_sample(self, sink: Gst.Element) -> Gst.FlowReturn:
        sample = sink.emit("pull-sample")
        if sample is None:
            return Gst.FlowReturn.ERROR
        buffer = sample.get_buffer()
        caps = sample.get_caps().get_structure(0)
        width = caps.get_value("width")
        height = caps.get_value("height")
        success, info = buffer.map(Gst.MapFlags.READ)
        if not success:
            return Gst.FlowReturn.ERROR
        try:
            image = np.frombuffer(info.data, dtype=np.uint8).reshape((height, width, 3)).copy()
        finally:
            buffer.unmap(info)
        if self._queue.full():
            try:
                self._queue.get_nowait()
            except Empty:
                pass
        self._queue.put(Frame(image=image, timestamp=time.monotonic()))
        return Gst.FlowReturn.OK
