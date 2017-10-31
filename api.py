import json
import aiohttp
import asyncio
from .log import logger
from .error import *


__all__ = ['IGWebAPI']


class IGWebAPI:
    """Implement web API of IG.

    - Auto re-login
    """

    def __init__(self, api_prefix, app_key, account, password, **kwargs):
        self._api_prefix = api_prefix
        self._app_key = app_key
        self._account = account
        self._password = password
        self._headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json; charset=UTF-8",
            "X-IG-API-KEY": self._app_key,
        }
        self._session = aiohttp.ClientSession(headers=self._headers, raise_for_status=True, **kwargs)

    def set_headers(self, headers):
        self._headers.update(headers)

    @property
    def headers(self):
        return self._headers

    async def log_in(self):
        t = 3
        while t>0:
            try:
                await self._log_in()
            except (asyncio.TimeoutError, aiohttp.ServerTimeoutError) as exc:
                logger.info("Retry to login")
                t -= 1
                continue
            else:
                return
        else:
            raise LoginRetryError()

    async def api(self, api_name, *args, **kwargs):
        func_name = '_' + api_name
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

    def __del__(self):
        self._session.close()

    async def _log_in(self):
        api = "/session"
        headers = self._headers.copy()
        headers["Version"] = "2"
        headers["CST"] = ""
        headers['X-SECURITY-TOKEN'] = ""
        data = {
            "encryptedPassword": False,
            "identifier": self._account,
            "password": self._password,
        }
        async with self._session.post(self._api_prefix+api, headers=headers, json=data) as resp:
            await resp.json()
            self._headers['CST'] = resp.headers.get('CST')
            self._headers['X-SECURITY-TOKEN'] = resp.headers.get('X-SECURITY-TOKEN')

    async def _session_detail(self):
        api = "/session"
        headers = self._headers.copy()
        headers["Version"] = "1"
        async with self._session.get(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _log_out(self):
        api = "/session"
        headers = self._headers.copy()
        headers["Version"] = "1"
        async with self._session.delete(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _get_encryption_key(self):
        api = "/session/encryptionKey"
        headers = self._headers.copy()
        headers["Version"] = "1"
        async with self._session.get(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _refresh_token(self, refresh_token):
        api = "/session/refresh-token"
        headers = self._headers.copy()
        headers["Version"] = "1"
        data = {
            "refresh_token": name
        }
        async with self._session.post(self._api_prefix+api, json=data) as resp:
            info = await resp.json()
            return info

    async def _accounts(self):
        api = "/accounts"
        headers = self._headers.copy()
        headers["Version"] = "1"
        async with self._session.get(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _market_navigation(self, node_id=''):
        api = "/marketnavigation"
        headers = self._headers.copy()
        if node_id:
            api += '/'+node_id
        headers["Version"] = "1"
        async with self._session.get(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _market_detail(self, epic):
        api = "/markets"
        headers = self._headers.copy()
        api += '/' + epic
        headers["Version"] = "3"
        async with self._session.get(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _market_detail_mul(self, epics, filter='ALL'):
        api = "/markets"
        headers = self._headers.copy()
        params = {}
        headers["Version"] = "2"
        params['epics'] = ','.join(epics[:50])
        params['filter'] = filter
        async with self._session.get(self._api_prefix+api, headers=headers, params=params) as resp:
            info = await resp.json()
            return info

    async def _market_search(self, searchTerm=''):
        api = "/markets"
        headers = self._headers.copy()
        params = {}
        headers["Version"] = "1"
        params['searchTerm'] = searchTerm
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

    async def _all_watchlist(self):
        api = "/watchlists"
        headers = self._headers.copy()
        headers["Version"] = "1"
        async with self._session.get(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _create_watchlist(self, name, epics):
        api = "/watchlists"
        headers = self._headers.copy()
        headers["Version"] = "1"
        data = {
            "name": name,
            "epics": epics,
        }
        async with self._session.post(self._api_prefix+api, headers=headers, json=data) as resp:
            info = await resp.json()
            return info

    async def _delete_watchlist(self, watchlist_id):
        api = "/watchlists"
        api += '/' + watchlist_id
        headers = self._headers.copy()
        headers["Version"] = "1"
        async with self._session.delete(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _watchlist_detail(self, watchlist_id):
        api = "/watchlists"
        api += '/' + watchlist_id
        headers = self._headers.copy()
        headers["Version"] = "1"
        async with self._session.get(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _add_market_to_watchlist(self, watchlist_id, epic):
        api = "/watchlists"
        api += '/' + watchlist_id
        headers = self._headers.copy()
        headers["Version"] = "1"
        data = {
            "epic": epic
        }
        async with self._session.put(self._api_prefix+api, headers=headers, json=data) as resp:
            info = await resp.json()
            return info

    async def _remove_market_from_watchlist(self, watchlist_id, epic):
        api = "/watchlists"
        api += '/' + watchlist_id + '/' + epic
        headers = self._headers.copy()
        headers["Version"] = "1"
        async with self._session.delete(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _client_sentiment_mul(self, marketids):
        api = "/clientsentiment"
        headers = self._headers.copy()
        params = {}
        headers["Version"] = "1"
        params['marketIds'] = ','.join(marketids)
        async with self._session.get(self._api_prefix+api, headers=headers, params=params) as resp:
            info = await resp.json()
            return info

    async def _client_sentiment(self, marketid):
        api = "/clientsentiment"
        api += '/' + marketid
        headers = self._headers.copy()
        headers["Version"] = "1"
        async with self._session.get(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _related_client_sentiment(self, marketid):
        api = "/clientsentiment/related"
        api += '/' + marketid
        headers = self._headers.copy()
        headers["Version"] = "1"
        async with self._session.get(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _history_activity(self, start_date='', end_date='', detailed=False, dealid='', page_size=50, filter=''):
        api = "/history/activity"
        headers = self._headers.copy()
        headers["Version"] = "3"
        params = {}
        params['from'] = start_date
        params['to'] = end_date
        params['detailed'] = detailed
        params['dealId'] = dealid
        params['filter'] = filter
        params['pageSize'] = page_size
        async with self._session.get(self._api_prefix+api, headers=headers, params=params) as resp:
            info = await resp.json()
            return info

    async def _confirm_deal(self, deal_reference):
        api = "/confirms"
        api += '/' + deal_reference
        headers = self._headers.copy()
        headers["Version"] = "1"
        async with self._session.get(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _get_positions(self, dealid):
        api = "/positions"
        api += '/' + dealid
        headers = self._headers.copy()
        headers["Version"] = "2"
        async with self._session.get(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _get_all_positions(self):
        api = "/positions"
        headers = self._headers.copy()
        headers["Version"] = "2"
        async with self._session.get(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _open_positions(self, deal_reference, currency, direction, epic, expiry,
                              force_open, guaranteed_stop, level, size, order_type,
                              limit_distance, limit_level, stop_distance, stop_level,
                              time_in_force, trailing_stop, trailing_stop_increment):
        api = "/positions/otc"
        headers = self._headers.copy()
        headers["Version"] = "2"
        assert direction in ["BUY", "SELL"], "direction error @open_positions"
        assert order_type in ["LIMIT", "MARKET"], "order_type error @open_positions"
        assert time_in_force in ["EXECUTE_AND_ELIMINATE", "FILL_OR_KILL"], "time_in_force error @open_positions"
        data = {
            'currencyCode': currency,
            'dealReference': deal_reference,
            'direction': direction,
            'epic': epic,
            'expiry': expiry,
            'forceOpen': force_open,
            'guaranteedStop': guaranteed_stop,
            'level': level,
            'size': size,
            'orderType': order_type,
            'limitDistance': limit_distance,
            'limitLevel': limit_level,
            'stopDistance': stop_distance,
            'stopLevel': stop_level,
            'timeInForce': time_in_force,
            'trailingStop': trailing_stop,
            'trailingStopIncrement': trailing_stop_increment,
        }
        async with self._session.post(self._api_prefix+api, headers=headers, json=data) as resp:
            info = await resp.json()
            return info

    async def _close_positions(self, dealid, direction, epic, expiry, level, size,
                               order_type, time_in_force):
        api = "/positions/otc"
        headers = self._headers.copy()
        headers["Version"] = "1"
        assert direction in ["BUY", "SELL"], "direction error @open_position"
        assert order_type in ["LIMIT", "MARKET"], "order_type error @open_position"
        assert time_in_force in ["EXECUTE_AND_ELIMINATE", "FILL_OR_KILL"], "time_in_force error @open_position"
        data = {
            'dealId': dealid,
            'direction': direction,
            'epic': epic,
            'expiry': expiry,
            'level': level,
            'size': size,
            'orderType': order_type,
            'timeInForce': time_in_force
        }
        async with self._session.delete(self._api_prefix+api, headers=headers, json=data) as resp:
            info = await resp.json()
            return info

    async def _update_positions(self, dealid, limit_level, stop_level, trailing_stop,
                                trailing_stop_distance, trailing_stop_increment):
        api = "/positions/otc"
        api += '/' + dealid
        headers = self._headers.copy()
        headers["Version"] = "2"
        data = {
            'limitLevel': limit_level,
            'stopLevel': stop_level,
            'trailingStop': trailing_stop,
            'trailingStopDistance': trailing_stop_distance,
            'trailingStopIncrement': trailing_stop_increment,
        }
        async with self._session.put(self._api_prefix+api, headers=headers, json=data) as resp:
            info = await resp.json()
            return info

    async def _get_all_workingorders(self):
        api = "/workingorders"
        headers = self._headers.copy()
        headers["Version"] = "2"
        async with self._session.get(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _create_workingorders(self, deal_reference, currency, direction, epic, expiry,
                                   force_open, guaranteed_stop, level, size, order_type,
                                   limit_distance, limit_level, stop_distance, stop_level,
                                   time_in_force, good_till_date):
        api = "/workingorders/otc"
        headers = self._headers.copy()
        headers["Version"] = "2"
        assert direction in ["BUY", "SELL"], "direction error @create_workingorders"
        assert order_type in ["LIMIT", "STOP"], "order_type error @create_workingorders"
        assert time_in_force in ["GOOD_TILL_CANCELLED", "GOOD_TILL_DATE"], "time_in_force error @create_workingorders"
        data = {
            'currencyCode': currency,
            'dealReference': deal_reference,
            'direction': direction,
            'epic': epic,
            'expiry': expiry,
            'forceOpen': force_open,
            'guaranteedStop': guaranteed_stop,
            'level': level,
            'size': size,
            'type': order_type,
            'limitDistance': limit_distance,
            'limitLevel': limit_level,
            'stopDistance': stop_distance,
            'stopLevel': stop_level,
            'timeInForce': time_in_force,
            'goodTillDate': good_till_date,
        }
        async with self._session.post(self._api_prefix+api, headers=headers, json=data) as resp:
            info = await resp.json()
            return info

    async def _delete_workingorders(self, dealid):
        api = "/workingorders/otc"
        api += '/' + dealid
        headers = self._headers.copy()
        headers["Version"] = "2"
        async with self._session.delete(self._api_prefix+api, headers=headers) as resp:
            info = await resp.json()
            return info

    async def _update_workingorders(self, dealid, level, order_type, limit_distance,
                                    limit_level, stop_distance, stop_level, time_in_force,
                                    good_till_date):
        api = "/workingorders/otc"
        api += '/' + dealid
        headers = self._headers.copy()
        headers["Version"] = "2"
        assert order_type in ["LIMIT", "STOP"], "order_type error @update_workingorders"
        assert time_in_force in ["GOOD_TILL_CANCELLED", "GOOD_TILL_DATE"], "time_in_force error @update_workingorders"
        data = {
            'level': level,
            'type': order_type,
            'limitDistance': limit_distance,
            'limitLevel': limit_level,
            'stopDistance': stop_distance,
            'stopLevel': stop_level,
            'timeInForce': time_in_force,
            'goodTillDate': good_till_date,
        }
        async with self._session.put(self._api_prefix+api, headers=headers, json=data) as resp:
            info = await resp.json()
            return info
