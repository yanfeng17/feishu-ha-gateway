"""Gateway manager that bridges WeChat/Feishu events to API consumers."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Union

from .broker import MessageBroker
from .config import GatewayConfig
from .events import IncomingMessageEvent, OutgoingMessageRequest

logger = logging.getLogger(__name__)


class GatewayManager:
    """Coordinates the WeChat/Feishu client and exposes async helpers for the API layer."""

    def __init__(self, config: GatewayConfig | None = None) -> None:
        self.config = config or GatewayConfig.load()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._broker = MessageBroker()
        self._client: Union[Any, None] = None  # Can be WeChatClient or FeishuClient
        self.channel_type = self.config.channel_type

    async def start(self) -> None:
        if self._loop:
            return
        self._loop = asyncio.get_running_loop()
        self._broker.attach_loop(self._loop)
        
        # Initialize client based on channel type
        if self.config.channel_type == "feishu":
            await self._start_feishu()
        elif self.config.channel_type == "wechat":
            await self._start_wechat()
        else:
            raise ValueError(f"Unsupported channel type: {self.config.channel_type}")
        
        logger.info(f"Gateway manager started with channel: {self.config.channel_type}")
        logger.info("Message pipeline optimized for low latency")

    async def _start_feishu(self) -> None:
        """Initialize Feishu client."""
        from .feishu_client import FeishuClient
        
        if not self.config.feishu_app_id or not self.config.feishu_app_secret:
            raise ValueError("Feishu app_id and app_secret are required")
        if not self.config.feishu_verification_token:
            raise ValueError("Feishu verification_token is required")
        
        self._client = FeishuClient(
            app_id=self.config.feishu_app_id,
            app_secret=self.config.feishu_app_secret,
            verification_token=self.config.feishu_verification_token,
            on_message=self._handle_incoming,
        )
        logger.info("[Feishu] Client initialized")

    async def _start_wechat(self) -> None:
        """Initialize WeChat client."""
        from .wechat_client import WeChatClient
        
        self._client = WeChatClient(on_message=self._handle_incoming)
        await asyncio.to_thread(self._client.start)
        logger.info("[WeChat] Client initialized")

    async def stop(self) -> None:
        if not self._client:
            return
        
        if self.config.channel_type == "wechat":
            await asyncio.to_thread(self._client.stop)
        
        logger.info("Gateway manager stopped")

    async def register_listener(self) -> asyncio.Queue:
        return await self._broker.subscribe()

    async def unregister_listener(self, queue: asyncio.Queue) -> None:
        await self._broker.unsubscribe(queue)

    def _handle_incoming(self, event: IncomingMessageEvent) -> None:
        """Handle incoming message and publish to subscribers.
        
        Note: This is called synchronously from the Feishu client.
        We schedule the async publish as a task to avoid blocking.
        """
        logger.debug("Incoming message event: %s", event)
        
        # Schedule async publish as a task (non-blocking)
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._broker.async_publish(event.asdict()), 
                self._loop
            )

    async def send_text(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self._client:
            raise RuntimeError("Gateway client not started")
        
        request = OutgoingMessageRequest(
            target=payload["target"],
            content=payload["content"],
            at_list=payload.get("at_list"),
        )
        
        if self.config.channel_type == "feishu":
            await self._client.send_text(request)
        elif self.config.channel_type == "wechat":
            await asyncio.to_thread(self._client.send_text, request)
        
        return {"status": "sent"}
    
    async def send_image(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send image message."""
        if not self._client:
            raise RuntimeError("Gateway client not started")
        
        target = payload["target"]
        image_url = payload["image_url"]
        
        if self.config.channel_type == "feishu":
            await self._client.send_image(target, image_url)
        else:
            raise NotImplementedError(f"Image sending not implemented for {self.config.channel_type}")
        
        return {"status": "sent"}
    
    async def handle_feishu_webhook(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Feishu webhook event."""
        if self.config.channel_type != "feishu":
            raise RuntimeError("Feishu webhook can only be handled in feishu channel mode")
        
        if not self._client:
            raise RuntimeError("Gateway client not started")
        
        return await self._client.handle_webhook(event_data)
