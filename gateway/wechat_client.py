"""Thin wrapper around wcferry for interacting with WeChat."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from queue import Empty
from typing import Callable

try:
    from wcferry import Wcf, WxMsg
except ImportError as exc:  # pragma: no cover - runtime guard
    raise RuntimeError(
        "wcferry is required to run the WeChat gateway. Please install it on a Windows host with WeChat."  # noqa: E501
    ) from exc

from .events import IncomingMessageEvent, OutgoingMessageRequest


class WeChatClientError(Exception):
    """Base exception for client failures."""


@dataclass
class _RuntimeState:
    wxid: str = ""
    name: str = ""


class WeChatClient:
    """Encapsulates the wcferry client lifecycle."""

    def __init__(self, on_message: Callable[[IncomingMessageEvent], None]) -> None:
        self._on_message = on_message
        self._wcf = Wcf()
        self._state = _RuntimeState()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._contact_cache = {}

    def start(self) -> None:
        try:
            self._state.wxid = self._wcf.get_self_wxid()
            self._state.name = self._wcf.get_user_info().get("name", "")
            self._refresh_contacts()
            self._wcf.enable_receiving_msg()
            self._thread = threading.Thread(target=self._loop, name="WeChatMessageLoop", daemon=True)
            self._thread.start()
        except Exception as exc:  # pragma: no cover - defensive
            raise WeChatClientError("Failed to initialise WeChat client") from exc

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        try:
            self._wcf.cleanup()
        except Exception:  # pragma: no cover - best effort
            pass

    def send_text(self, request: OutgoingMessageRequest) -> None:
        target = request.target
        if not target:
            raise WeChatClientError("Target wxid is required")
        try:
            at_str = ",".join(request.at_list) if request.at_list else ""
            self._wcf.send_text(request.content, target, at_str)
        except Exception as exc:  # pragma: no cover
            raise WeChatClientError("Failed to send message") from exc

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                msg: WxMsg | None = self._wcf.get_msg()
            except Empty:
                continue
            except Exception:
                time.sleep(1)
                continue

            if not msg:
                continue
            event = self._build_event(msg)
            if event:
                self._on_message(event)

    def _build_event(self, msg: WxMsg) -> IncomingMessageEvent | None:
        if not msg.is_text():
            return None

        sender_name = self._resolve_name(msg.sender)
        if not sender_name:
            self._refresh_contacts()
            sender_name = self._resolve_name(msg.sender)
        room_name = self._resolve_name(msg.roomid) if msg.roomid else None
        event = IncomingMessageEvent(
            msg_id=str(msg.id),
            sender=msg.sender,
            sender_name=sender_name,
            receiver=self._state.wxid,
            content=msg.content,
            is_group=bool(msg.roomid),
            timestamp=int(msg.ts),
            room_id=msg.roomid or None,
            room_name=room_name,
            at_me=msg.is_at(self._state.wxid) if msg.roomid else None,
        )
        return event

    def _refresh_contacts(self) -> None:
        try:
            self._wcf.get_contacts()
            self._contact_cache.clear()
            for item in self._wcf.contacts:
                wxid = item.get("wxid")
                if wxid:
                    self._contact_cache[wxid] = item.get("name") or item.get("remark") or ""
        except Exception:
            pass

    def _resolve_name(self, wxid: str | None) -> str:
        if not wxid:
            return ""
        return self._contact_cache.get(wxid, "")
