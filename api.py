import json
import aiohttp
import asyncio
from log import logger
from error import *


DEMO_API = "https://demo-api.ig.com/gateway/deal"
PROD_API = "https://api.ig.com/gateway/deal"
DEMO_APP_KEY = "8c0dfcb7a549e8046c9c75f055629c75630b65df"
DEMO_ACCOUNT = "WAYNEEVER"
DEMO_PASSWORD = "W12345678r"

CST = "b4a2f7229f39cb214c40e46c1e0f98331dbf4f1db4eda5e1e47aabc6d53b532001113"
X_SECURITY_TOKEN = "a353a62bdd1def5ff54abe34950ee8edcb9be9dd812deec81a5e9eb25720fd4601113"


class IGSessionBase:
    """Session that maintain the communication with IG.

    Offer all available api
    """
    _api = None

    def __init__(self, app_key, account, password, **kwargs):
        self.app_key = app_key
        self.account = account
        self.password = password
        self.client_id = None
        self.account_id = None
        self._headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json; charset=UTF-8",
            "X-IG-API-KEY": self.app_key,
        }
        self._session = aiohttp.ClientSession(headers=self._headers, **kwargs)

    async def _log_in_2(self):
        api = "/session"
        headers = self._headers.copy()
        headers["Version"] = "2"
        data = {
            "encryptedPassword": False,
            "identifier": self.account,
            "password": self.password,
        }
        async with self._session.post(self._api+api, headers=headers, json=data) as resp:
            info = await resp.json()
            self.client_id = info.get('clientId')
            self.account_id = info.get('currentAccountId')
            self._headers['CST'] = resp.headers.get('CST')
            self._headers['X-SECURITY-TOKEN'] = resp.headers.get('X-SECURITY-TOKEN')

    async def log_in(self):
        t = 3
        while t>0:
            try:
                await self._log_in_2()
            except asyncio.TimeoutError as exc:
                logger.error("Retry to login")
                t -= 1
                continue
            else:
                return
        else:
            raise LoginRetryError()

    async def account_info(self):
        api = "/accounts"
        headers = self._headers.copy()
        headers["Version"] = "1"
        async with self._session.get(self._api+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def marketnavigation(self):
        api = "/marketnavigation"
        headers = self._headers.copy()
        headers["Version"] = "1"
        async with self._session.get(self._api+api, headers=headers) as resp:
            info = await resp.json()
            return info


class IGSessionDemo(IGSessionBase):
    """IGSession for demo environment
    """
    _api = DEMO_API

    def __init__(self, app_key, account, password, read_timeout=10, conn_timeout=5, **kwargs):
        super(IGSessionDemo, self).__init__(app_key, account, password, read_timeout=read_timeout,
                                            conn_timeout=conn_timeout, **kwargs)
        pass


class IGSessionProd(IGSessionBase):
    """IGSession for prod environment
    """
    _api = PROD_API


if __name__ == '__main__':
    async def test():
        session = IGSessionDemo(DEMO_APP_KEY, DEMO_ACCOUNT, DEMO_PASSWORD)
        await session.log_in()
        info = await session.marketnavigation()
        print(info)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
