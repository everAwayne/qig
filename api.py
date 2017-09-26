import json
import aiohttp
import asyncio
from log import logger
from error import *


PROD_API_PREFIX = "https://api.ig.com/gateway/deal"
DEMO_API_PREFIX = "https://demo-api.ig.com/gateway/deal"


CST = "b4a2f7229f39cb214c40e46c1e0f98331dbf4f1db4eda5e1e47aabc6d53b532001113"
X_SECURITY_TOKEN = "a353a62bdd1def5ff54abe34950ee8edcb9be9dd812deec81a5e9eb25720fd4601113"


class IGSessionBase:
    """Session that maintain the communication with IG.

    Offer all available api
    """
    _api_prefix = None
    _api_map = {
        '/session'
    }

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
        self._session = aiohttp.ClientSession(headers=self._headers, raise_for_status=True, **kwargs)

    async def _log_in_2(self):
        api = "/session"
        headers = self._headers.copy()
        headers["Version"] = "2"
        headers["CST"] = ""
        headers["X-SECURITY-TOKEN"] = ""
        data = {
            "encryptedPassword": False,
            "identifier": self.account,
            "password": self.password,
        }
        async with self._session.post(self._api_prefix+api, headers=headers, json=data) as resp:
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
            except (asyncio.TimeoutError, aiohttp.ServerTimeoutError) as exc:
                logger.error("Retry to login")
                t -= 1
                continue
            else:
                return
        else:
            raise LoginRetryError()

    async def api(self, api_name, *args, **kwargs):
        func_name = api_name.replace('/', '_')
        try:
            func = getattr(self, func_name)
        except AttributeError:
            raise UnkownAPIError(api_name)

        while True:
            try:
                result = await func(*args, **kwargs)
            except asyncio.TimeoutError as exc:
                raise APITimeoutError('Read timeout')
            except aiohttp.ServerTimeoutError as exc:
                raise APITimeoutError('Connect timeout')
            except aiohttp.ClientResponseError as exc:
                logger.error("Code[%s] %s" % (exc.code, exc.message))
                if exc.code == 401:
                    logger.info("Relogin")
                    await self.log_in()
            else:
                return result

    async def _accounts(self):
        api = "/accounts"
        headers = self._headers.copy()
        headers["Version"] = "1"
        async with self._session.get(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _marketnavigation(self, node_id=''):
        api = "/marketnavigation"
        headers = self._headers.copy()
        if node_id:
            api += '/'+node_id
        headers["Version"] = "1"
        async with self._session.get(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _markets(self, epics, filter='ALL', searchTerm=''):
        api = "/markets"
        headers = self._headers.copy()
        params = {}
        if searchTerm:
            headers["Version"] = "1"
            params['searchTerm'] = searchTerm
        else:
            assert epics, "epics can't be empty"
            if len(epics)==1:
                api += '/' + epics[0]
                headers["Version"] = "3"
            else:
                headers["Version"] = "2"
                params['epics'] = ','.join(epics[:50])
                assert filter in ['ALL', 'SNAPSHOT_ONLY'], 'filter is illegal'
                params['filter'] = filter
        async with self._session.get(self._api_prefix+api, headers=headers, params=params) as resp:
            info = await resp.json()
            return info

    async def _prices(self, epic, resolution, start_date='', end_date='', max=10, page_size=20, page_num=1):
        api = "/prices"
        api += '/' + epic
        headers = self._headers.copy()
        headers["Version"] = "3"
        params = {}
        assert resolution in ["SECOND", "MINUTE", "MINUTE_2", "MINUTE_3", "MINUTE_5",
                                "MINUTE_10", "MINUTE_15", "MINUTE_30", "HOUR", "HOUR_2",
                                "HOUR_3", "HOUR_4", "DAY", "WEEK", "MONTH"], "resolution is illegal"
        params['resolution'] = resolution
        if start_date:
            params['from'] = start_date
        if end_date:
            params['to'] = end_date
        params['max'] = max
        params['pageSize'] = page_size
        params['pageNumber'] = page_num
        async with self._session.get(self._api_prefix+api, headers=headers, params=params) as resp:
            info = await resp.json()
            return info



class IGSessionDemo(IGSessionBase):
    """IGSession for demo environment
    """
    _api_prefix = DEMO_API_PREFIX

    def __init__(self, app_key, account, password, read_timeout=10, conn_timeout=5, **kwargs):
        super(IGSessionDemo, self).__init__(app_key, account, password, read_timeout=read_timeout,
                                            conn_timeout=conn_timeout, **kwargs)
        pass


class IGSessionProd(IGSessionBase):
    """IGSession for prod environment
    """
    _api_prefix = PROD_API_PREFIX
