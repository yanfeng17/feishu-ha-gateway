"""Feishu (Lark) client for interacting with Feishu Open Platform."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, Optional
from dataclasses import asdict

import aiohttp
import requests

from .events import IncomingMessageEvent, OutgoingMessageRequest

logger = logging.getLogger(__name__)


class FeishuClientError(Exception):
    """Base exception for Feishu client failures."""


class FeishuClient:
    """Encapsulates the Feishu client lifecycle and API interactions."""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        verification_token: str,
        on_message: Callable[[IncomingMessageEvent], None],
    ) -> None:
        """
        Initialize Feishu client.
        
        Args:
            app_id: Feishu application ID
            app_secret: Feishu application secret
            verification_token: Token for webhook verification
            on_message: Callback function for incoming messages
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.verification_token = verification_token
        self._on_message = on_message
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._contact_cache: Dict[str, str] = {}
        
        logger.info(f"[Feishu] Client initialized with app_id: {app_id[:10]}...")

    async def handle_webhook(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming webhook event from Feishu.
        
        Args:
            event_data: Raw event data from Feishu
            
        Returns:
            Response dict for Feishu server
        """
        # 1. Handle URL verification
        if event_data.get("type") == "url_verification":
            challenge = event_data.get("challenge", "")
            logger.info("[Feishu] URL verification request received")
            return {"challenge": challenge}
        
        # 2. Verify token
        header = event_data.get("header", {})
        if header.get("token") != self.verification_token:
            logger.warning("[Feishu] Invalid verification token")
            return {"success": False, "error": "invalid_token"}
        
        # 3. Handle message events
        if header.get("event_type") == "im.message.receive_v1":
            try:
                await self._handle_message_event(event_data)
                return {"success": True}
            except Exception as e:
                logger.error(f"[Feishu] Error handling message event: {e}", exc_info=True)
                return {"success": False, "error": str(e)}
        
        logger.debug(f"[Feishu] Unhandled event type: {header.get('event_type')}")
        return {"success": True}

    async def _handle_message_event(self, event_data: Dict[str, Any]) -> None:
        """Process incoming message event."""
        event = event_data.get("event", {})
        message = event.get("message", {})
        sender = event.get("sender", {})
        
        msg_id = message.get("message_id")
        msg_type = message.get("message_type")
        chat_type = message.get("chat_type")
        
        # Only handle text messages for now
        if msg_type != "text":
            logger.debug(f"[Feishu] Skipping non-text message: {msg_type}")
            return
        
        # Determine if it's a group chat
        is_group = chat_type == "group"
        
        # In group chat, only respond when mentioned
        if is_group:
            mentions = message.get("mentions", [])
            if not mentions:
                logger.debug("[Feishu] Group message without mention, skipping")
                return
        
        # Parse message content
        try:
            content_json = json.loads(message.get("content", "{}"))
            content = content_json.get("text", "").strip()
            
            # Remove @mentions from content
            if is_group:
                # Feishu includes @_user_1 in the text, remove it
                content = content.replace("@_user_1", "").strip()
        except json.JSONDecodeError:
            logger.error("[Feishu] Failed to parse message content")
            return
        
        # Build incoming message event
        sender_id = sender.get("sender_id", {}).get("open_id", "")
        sender_name = await self._get_user_name(sender_id)
        
        room_id = message.get("chat_id") if is_group else None
        room_name = await self._get_chat_name(room_id) if room_id else None
        
        incoming_event = IncomingMessageEvent(
            msg_id=msg_id,
            sender=sender_id,
            sender_name=sender_name,
            receiver=self.app_id,
            content=content,
            is_group=is_group,
            timestamp=int(message.get("create_time", time.time())),
            room_id=room_id,
            room_name=room_name,
            at_me=True if is_group else None,
        )
        
        logger.info(f"[Feishu] Received message from {sender_name}: {content[:50]}")
        
        # Trigger callback directly (no thread executor needed)
        self._on_message(incoming_event)

    async def send_text(self, request: OutgoingMessageRequest) -> None:
        """
        Send text message to Feishu.
        
        Args:
            request: Outgoing message request
        """
        access_token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        # Build message content
        content = {"text": request.content}
        
        # Determine receive_id_type
        # Feishu uses open_id for users and chat_id for groups
        # We'll assume target starting with "oc_" is chat_id, otherwise open_id
        if request.target.startswith("oc_"):
            receive_id_type = "chat_id"
        else:
            receive_id_type = "open_id"
        
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        params = {"receive_id_type": receive_id_type}
        
        data = {
            "receive_id": request.target,
            "msg_type": "text",
            "content": json.dumps(content),
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, params=params, json=data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    result = await response.json()
                    
                    if result.get("code") == 0:
                        logger.info(f"[Feishu] Message sent successfully to {request.target}")
                    else:
                        logger.error(f"[Feishu] Failed to send message: {result.get('msg')}")
                        raise FeishuClientError(f"Send message failed: {result.get('msg')}")
        except Exception as e:
            logger.error(f"[Feishu] Error sending message: {e}")
            raise FeishuClientError(f"Failed to send message: {e}")

    async def send_image(self, target: str, image_url: str) -> None:
        """
        Send image message to Feishu.
        
        Args:
            target: Target user or group ID
            image_url: URL of the image to send
        """
        access_token = await self._get_access_token()
        
        # 1. Download image
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    image_data = await response.read()
        except Exception as e:
            logger.error(f"[Feishu] Failed to download image: {e}")
            raise FeishuClientError(f"Failed to download image: {e}")
        
        # 2. Upload image to Feishu
        upload_url = "https://open.feishu.cn/open-apis/im/v1/images"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        form_data = aiohttp.FormData()
        form_data.add_field("image_type", "message")
        form_data.add_field("image", image_data, filename="image.jpg", content_type="image/jpeg")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(upload_url, headers=headers, data=form_data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    result = await response.json()
                    
                    if result.get("code") != 0:
                        raise FeishuClientError(f"Upload image failed: {result.get('msg')}")
                    
                    image_key = result.get("data", {}).get("image_key")
                    if not image_key:
                        raise FeishuClientError("No image_key in response")
        except Exception as e:
            logger.error(f"[Feishu] Failed to upload image: {e}")
            raise
        
        # 3. Send image message
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        receive_id_type = "chat_id" if target.startswith("oc_") else "open_id"
        
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        params = {"receive_id_type": receive_id_type}
        
        data = {
            "receive_id": target,
            "msg_type": "image",
            "content": json.dumps({"image_key": image_key}),
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, params=params, json=data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    result = await response.json()
                    
                    if result.get("code") == 0:
                        logger.info(f"[Feishu] Image sent successfully to {target}")
                    else:
                        logger.error(f"[Feishu] Failed to send image: {result.get('msg')}")
                        raise FeishuClientError(f"Send image failed: {result.get('msg')}")
        except Exception as e:
            logger.error(f"[Feishu] Error sending image message: {e}")
            raise

    async def _get_access_token(self) -> str:
        """Get or refresh tenant access token."""
        # Check if token is still valid
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        
        # Fetch new token
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
        headers = {"Content-Type": "application/json"}
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    result = await response.json()
                    
                    if result.get("code") != 0:
                        raise FeishuClientError(f"Get access token failed: {result.get('msg')}")
                    
                    self._access_token = result.get("tenant_access_token")
                    expires_in = result.get("expire", 7200)
                    self._token_expires_at = time.time() + expires_in - 300  # Refresh 5 minutes early
                    
                    logger.info("[Feishu] Access token refreshed successfully")
                    return self._access_token
        except Exception as e:
            logger.error(f"[Feishu] Failed to get access token: {e}")
            raise FeishuClientError(f"Failed to get access token: {e}")

    async def _get_user_name(self, user_id: str) -> str:
        """Get user name by user_id (open_id)."""
        if user_id in self._contact_cache:
            return self._contact_cache[user_id]
        
        # For now, return user_id as name
        # Can implement user info API call if needed
        return user_id

    async def _get_chat_name(self, chat_id: str) -> str:
        """Get chat name by chat_id."""
        if chat_id in self._contact_cache:
            return self._contact_cache[chat_id]
        
        # For now, return chat_id as name
        # Can implement chat info API call if needed
        return chat_id
