# api.py

import aiohttp
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://pulse.neat.no/api/v1"

class NeatPulseAPIError(Exception):
    """General API error."""

class AuthenticationError(NeatPulseAPIError):
    """Authentication failed."""

class NeatPulseAPI:
    def __init__(self, session, access_token, organization_id):
        self.session = session
        self.access_token = access_token
        self.organization_id = organization_id

    async def request(self, method, endpoint, **kwargs):
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        headers["Accept"] = "application/json"
        kwargs["headers"] = headers
        url = f"{BASE_URL}/{endpoint}"
        try:
            async with self.session.request(method, url, **kwargs, timeout=10) as resp:
                if resp.status == 401:
                    error_text = await resp.text()
                    _LOGGER.error(f"Authentication failed ({resp.status}): {error_text}")
                    raise AuthenticationError("Invalid access token")
                elif resp.status == 429:
                    retry_after = int(resp.headers.get("Retry-After", "60"))
                    _LOGGER.warning(f"Rate limit exceeded, retrying after {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    return await self.request(method, endpoint, **kwargs)
                elif resp.status >= 400:
                    error_text = await resp.text()
                    _LOGGER.error(f"API request failed ({resp.status}): {error_text}")
                    raise NeatPulseAPIError(f"API request failed: {resp.status}")
                return await resp.json()
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Network error during API request: {err}")
            raise NeatPulseAPIError("Network error during API request") from err
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout during API request")
            raise NeatPulseAPIError("Timeout during API request")

    async def get_endpoint_sensor_data(self, endpoint_id):
        endpoint = f"orgs/{self.organization_id}/endpoints/{endpoint_id}/sensor"
        return await self.request("GET", endpoint)

    async def get_endpoint_details(self, endpoint_id):
        endpoint = f"orgs/{self.organization_id}/endpoints/{endpoint_id}"
        return await self.request("GET", endpoint)
