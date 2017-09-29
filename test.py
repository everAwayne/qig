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
    info = await session.api('session_detail')
    #info = await session.api('log_out')
    #info = await session.api('accounts')
    #info = await session.api('market_navigation')
    #info = await session.api('market_navigation', '195235')
    #info = await session.api('market_navigation', '264133')
    #info = await session.api('market_navigation', '264134')
    #info = await session.api('market_detail', 'CS.D.AUDUSD.CFD.IP')
    #info = await session.api('market_detail_mul', ['CS.D.AUDUSD.CFD.IP','CS.D.EURCHF.CFD.IP'])
    #info = await session.api('market_detail_mul', ['CS.D.AUDUSD.CFD.IP','CS.D.EURCHF.CFD.IP'], filter='SNAPSHOT_ONLY')
    #info = await session.api('market_search', searchTerm='EURCHF')
    #info = await session.api('prices', epic='CS.D.EURCHF.CFD.IP', resolution='MINUTE')
    #info = await session.api('all_watchlist')
    #info = await session.api('create_watchlist', 'test', ['CS.D.AUDUSD.CFD.IP'])
    #info = await session.api('delete_watchlist', '6491145')
    #info = await session.api('watchlist_detail', '6491559')
    #info = await session.api('add_market_to_watchlist', '6491559', 'CS.D.EURCHF.CUF.IP')
    #info = await session.api('remove_market_from_watchlist', '6491559', 'CS.D.EURCHF.CUF.IP')
    print(info)
    r.hset('ods', 'CST', session._headers["CST"])
    r.hset('ods', 'X-SECURITY-TOKEN', session._headers["X-SECURITY-TOKEN"])


loop = asyncio.get_event_loop()
loop.run_until_complete(test())
