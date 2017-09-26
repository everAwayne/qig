import asyncio
import redis
from api import IGSessionDemo

DEMO_APP_KEY = "8c0dfcb7a549e8046c9c75f055629c75630b65df"
DEMO_ACCOUNT = "WAYNEEVER"
DEMO_PASSWORD = "W12345678r"

r = redis.Redis('192.168.0.10',6379,9)
dct = r.hgetall('ods')
CST = dct[b'CST'].decode('utf-8')
X_SECURITY_TOKEN = dct[b'X-SECURITY-TOKEN'].decode('utf-8')

async def test():
    session = IGSessionDemo(DEMO_APP_KEY, DEMO_ACCOUNT, DEMO_PASSWORD)
    session._headers["CST"] = CST
    session._headers["X-SECURITY-TOKEN"] = X_SECURITY_TOKEN
    #await session.log_in()
    #info = await session.api('/accounts')
    #info = await session.api('/marketnavigation')
    #info = await session.api('/marketnavigation', '195235')
    #info = await session.api('/marketnavigation', '264133')
    #info = await session.api('/marketnavigation', '264134')
    #info = await session.api('/markets', ['CS.D.AUDUSD.CFD.IP'])
    #info = await session.api('/markets', ['CS.D.AUDUSD.CFD.IP','CS.D.EURCHF.CFD.IP'])
    #info = await session.api('/markets', ['CS.D.AUDUSD.CFD.IP','CS.D.EURCHF.CFD.IP'], filter='SNAPSHOT_ONLY')
    #info = await session.api('/markets', searchTerm='EURCHF')
    #info = await session.api('/prices', epic='CS.D.EURCHF.CFD.IP', resolution='MINUTE')
    print(info)
    r.hset('ods', 'CST', session._headers["CST"])
    r.hset('ods', 'X-SECURITY-TOKEN', session._headers["X-SECURITY-TOKEN"])


loop = asyncio.get_event_loop()
loop.run_until_complete(test())
