import aiohttp
import asyncio
from .log import logger
from .error import *
from .api import IGWebAPI


__all__ = ['IGStreamAPI']


CONNECT_PATH = "/lightstreamer/create_session.txt"
BIND_PATH = "/lightstreamer/bind_session.txt"
CONTROL_PATH = "/lightstreamer/control.txt"
OP_ADD = "add"
OK_MSG = "OK"
ERR_MSG = "ERROR"
PROBE_MSG = "PROBE"
LOOP_MSG = "LOOP"
SYNC_ERR_MSG = "SYNC ERROR"
END_MSG = "END"
PREAMBLE_MSG = "Preamble"


class IGStreamAPI:
    """Implement stream API of IG.
    """

    def __init__(self, api_prefix, app_key, account, password, adapter_set, loop=None, **kwargs):
        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()
        self._api_prefix = api_prefix
        self._app_key = app_key
        self._account = account
        self._password = password
        self._adapter_set = adapter_set
        self._stream_endpoint = None
        self._account_id = None
        self._CST = None
        self._XST = None
        self.web_api = IGWebAPI(api_prefix, app_key, account, password, read_timeout=10, conn_timeout=5)
        self._session = aiohttp.ClientSession(read_timeout=0, conn_timeout=10)
        self._stream = None
        self._meta_data = {}
        self._control_endpoint = None
        self._subscribe_map = {}

    def __del__(self):
        self._session.close()

    async def _refresh_credential(self):
        info = await self.web_api.api('session_detail')
        self._stream_endpoint = info["lightstreamerEndpoint"]
        self._account_id = info["accountId"]
        self._CST = self.web_api.headers["CST"]
        self._XST = self.web_api.headers["X-SECURITY-TOKEN"]

    async def _readline(self):
        try:
            line = await self._stream.content.readline()
        except Exception as exc:
            exc_info = (type(exc), exc, exc.__traceback__)
            logger.error("Read Error: ", exc_info=exc_info)
            exc.__traceback__ = None
            return None

        line = line.decode('utf-8').rstrip()
        return line

    async def _readlines(self):
        try:
            data = await self._stream.content.read()
        except Exception as exc:
            exc_info = (type(exc), exc, exc.__traceback__)
            logger.error("Read Error: ", exc_info=exc_info)
            exc.__traceback__ = None
            return []

        data = data.decode('utf-8').rstrip()
        lines = data.split('\r\n')
        return lines

    async def _handle_stream(self):
        line = await self._readline()
        if line == OK_MSG:
            while True:
                line = await self._readline()
                if line:
                    k, v = line.split(":", 1)
                    self._meta_data[k] = v
                else:
                    break
            self._control_endpoint = self._meta_data.get("ControlAddress")
            if self._control_endpoint is None:
                self._control_endpoint = self._stream_endpoint
            else:
                self._control_endpoint = 'https://' + self._control_endpoint
            return True
        else:
            lines = await self._readlines()
            lines.insert(0, line)
            logger.error('\n'.join(lines))
            return False

    async def _stream_connet(self):
        logger.debug('stream connect')
        assert self._stream is None, "Last stream still exist"
        dct = {
            "LS_adapter_set": self._adapter_set,
            "LS_user": self._account_id,
            "LS_password": "CST-{CST}|XST-{XST}".format(CST=self._CST, XST=self._XST)
        }
        retry = 3
        while True:
            retry -= 1
            try:
                self._stream = await self._session.post(self._stream_endpoint + CONNECT_PATH, data=dct)
            except aiohttp.ServerTimeoutError as exc:
                if not retry:
                    raise APITimeoutError('Connect timeout when stream connect')
            else:
                break
        ret = await self._handle_stream()
        if not ret:
            raise RuntimeError("stream connect fail")

    async def _rebind(self):
        logger.debug("rebind")
        assert self._stream is None, "Last stream still exist"
        dct = {
            "LS_session": self._meta_data["SessionId"]
        }
        retry = 3
        while True:
            retry -= 1
            try:
                self._stream = await self._session.post(self._control_endpoint + BIND_PATH, data=dct)
            except aiohttp.ServerTimeoutError as exc:
                if not retry:
                    raise APITimeoutError('Connect timeout when rebind')
            else:
                break
        ret = await self._handle_stream()
        return ret

    async def _subscribe(self):
        for sub_id in self._subscribe_map:
            dct = {
                "LS_session": self._meta_data["SessionId"],
                "LS_Table": sub_id,
                "LS_op": OP_ADD,
                "LS_mode": self._subscribe_map[sub_id]['conf']['mode'],
                "LS_schema": " ".join(self._subscribe_map[sub_id]['conf']['fields']),
                "LS_id": " ".join(self._subscribe_map[sub_id]['conf']['items'])
            }
            retry = 3
            while True:
                retry -= 1
                try:
                    async with self._session.post(self._control_endpoint + CONTROL_PATH, data=dct) as resp:
                        info = await resp.text()
                        if not info.startswith(OK_MSG):
                            logger.error("Subscribe Error")
                            logger.error(info)
                            logger.error(dct)
                except aiohttp.ServerTimeoutError as exc:
                    if not retry:
                        raise APITimeoutError('Connect timeout when subscribe')
                else:
                    break

    def _reset_context(self):
        self._session.close()
        self._stream = None
        self._session = aiohttp.ClientSession(read_timeout=0, conn_timeout=10)
        for sub_id in self._subscribe_map:
            self._subscribe_map[sub_id]['items'] = {}
        self._meta_data = {}
        self._control_endpoint = None

    def _data_decode(self, c_v, l_v):
        if c_v == "$":
            return u''
        elif c_v == "#":
            return None
        elif not c_v:
            return l_v
        elif c_v[0] in "#$":
            c_v = c_v[1:]
        return c_v

    def _data_parse(self, msg):
        ls = msg.split(',', 1)
        sub_id, item = int(ls[0]), ls[1]
        ls = item.split("|")
        item_pos = int(ls[0])
        field_dct = dict(list(zip(self._subscribe_map[sub_id]['conf']['fields'], ls[1:])))

        last_item = self._subscribe_map[sub_id]['items'].get(item_pos, {})
        self._subscribe_map[sub_id]['items'][item_pos] = dict([
            (k, self._data_decode(v, last_item.get(k))) for k, v in field_dct.items()
        ])

        item_info = {
            "name": self._subscribe_map[sub_id]['conf']['items'][item_pos-1],
            "values": self._subscribe_map[sub_id]['items'][item_pos]
        }
        return item_info

    def add_listener(self, handler):
        self._handler = asyncio.coroutines.coroutine(handler)

    def subscribe(self, conf):
        sub_id = len(self._subscribe_map)+1
        self._subscribe_map[sub_id] = {'conf': conf, 'items': {}}

    async def start(self):
        try:
            handler = getattr(self, "_handler")
        except AttributeError:
            raise RuntimeError("Can't find listener")
        await self._refresh_credential()
        await self._stream_connet()
        self._loop.create_task(self._subscribe())

        while True:
            rebind = False
            reconnect = False
            while True:
                line = await self._readline()

                if line is None:
                    raise RuntimeError("read data error")
                elif line == PROBE_MSG:
                    pass
                elif line.startswith(ERR_MSG):
                    logger.error("ERR receive")
                    logger.error(line)
                    raise RuntimeError("stream receive ERR_MSG")
                elif line.startswith(SYNC_ERR_MSG):
                    logger.error("SYNC_ERR receive")
                    logger.error(line)
                    raise RuntimeError("stream receive SYNC_ERR_MSG")
                elif line.startswith(LOOP_MSG):
                    logger.info("LOOP receive")
                    logger.info(line)
                    rebind = True
                    break
                elif line.startswith(END_MSG):
                    logger.error("END receive")
                    logger.error(line)
                    asyncio.sleep(15)
                    reconnect = True
                    break
                elif line.startswith(PREAMBLE_MSG):
                    pass
                else:
                    info = self._data_parse(line)
                    await self._handler(info)

            if rebind:
                self._stream = None
                ret = await self._rebind()
                if not ret:
                    reconnect = True
            if reconnect:
                logger.debug("reconnect")
                self._reset_context()
                await self._stream_connet()
                self._loop.create_task(self._subscribe())
