import asyncio
import os
import time
import uuid

import requests


class GigaChatClient:
    """Обёртка над GigaChat API: получение токена + отправка сообщений."""

    def __init__(self):
        """Сохраняет параметры подключения к GigaChat и сбрасывает токен."""

        self.auth_url = os.getenv("GIGACHAT_AUTH_URL", "")
        self.chat_url = os.getenv(
            "GIGACHAT_CHAT_URL", ""
        )
        self.model = os.getenv("GIGACHAT_MODEL", "GigaChat-2-Pro")
        self.client_secret = os.getenv("GIGACHAT_CLIENT_SECRET", "")
        self.scope = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_B2B")
        self.verify_ssl = os.getenv("GIGACHAT_VERIFY_SSL", "false").lower() == "true"

        self._token = None
        self._token_expires_at = 0  # unix timestamp

    def _get_access_token(self):
        """Получает новый токен доступа от GigaChat."""
        headers = {
            "Authorization": f"Basic {self.client_secret}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
        }

        response = requests.post(
            self.auth_url,
            headers=headers,
            data={"scope": self.scope},
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        payload = response.json()

        self._token = payload["access_token"]
        # expires_at приходит в мс от GigaChat, с запасом в 60 сек
        self._token_expires_at = payload.get("expires_at", 0) / 1000 - 60

        return self._token

    def _ensure_token(self):
        """Гарантирует, что у клиента есть актуальный токен доступа."""

        if not self._token or time.time() >= self._token_expires_at:
            self._get_access_token()
        return self._token

    def complete(self, messages, temperature=0.7, max_tokens=None):
        """Синхронная обёртка над запросом к GigaChat для совместимости."""

        return self._complete_sync(messages, temperature=temperature, max_tokens=max_tokens)

    async def acomplete(self, messages, temperature=0.7, max_tokens=None):
        """Асинхронно отправляет сообщения в GigaChat и возвращает ответ."""

        token = self._ensure_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                self.chat_url,
                headers=headers,
                json=body,
                verify=False,
            ),
        )

        if response.status_code == 401:
            self._get_access_token()
            headers["Authorization"] = f"Bearer {self._token}"
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    self.chat_url,
                    headers=headers,
                    json=body,
                    verify=self.verify_ssl,
                ),
            )

        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _complete_sync(self, messages, temperature=0.7, max_tokens=None):
        """Синхронно отправляет сообщения в GigaChat и возвращает текст ответа."""

        token = self._ensure_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens

        response = requests.post(
            self.chat_url,
            headers=headers,
            json=body,
            verify=False,
        )

        if response.status_code == 401:
            self._get_access_token()
            headers["Authorization"] = f"Bearer {self._token}"
            response = requests.post(
                self.chat_url, headers=headers, json=body, verify=self.verify_ssl
            )

        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
