from aiohttp_sse_client import client as sse_client
import json
import asyncio
import aiohttp

from .endpoints import endpoints as _e


class Client:
    def __init__(self, *, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.jwt = ""

        self._waiters = {}
        self._stream_key: str = ""

    def event(self, coro):
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("Event registered must be a coroutine function")

        setattr(self, coro.__name__, coro)
        return coro

    def dispatch(self, event, *args, **kwargs):
        method = "on_" + event

        if method in self._waiters:
            to_remove = []
            waiters = self._waiters[method]
            for i, (cond, fut, stop) in enumerate(waiters):
                if fut.cancelled():
                    to_remove.append(i)
                    continue

                try:
                    result = bool(cond(*args))
                except Exception as e:
                    fut.set_exception(e)
                else:
                    if result:
                        fut.set_result(
                            args[0]
                            if len(args) == 1
                            else args
                            if len(args) > 0
                            else None
                        )
                        if stop:
                            del waiters[i]
                            return None
                        to_remove.append(i)

            if len(to_remove) == len(waiters):
                del self._waiters[method]
            else:
                for i in to_remove[::-1]:
                    del waiters[i]

        coro = getattr(self, method, None)
        if coro is not None:
            dispatch = self._run_event(coro, method, *args, **kwargs)
            return asyncio.ensure_future(dispatch, loop=self.loop)

    def wait_for(self, event, condition=None, timeout=None, stopPropagation=False):
        event = event.lower()
        future = self.loop.create_future()

        if condition is None:

            def everything(*a):
                return True

            condition = everything

        if event not in self._waiters:
            self._waiters[event] = []

        self._waiters[event].append((condition, future, stopPropagation))

        return asyncio.wait_for(future, timeout)

    async def _run_event(self, coro, event_name, *args, **kwargs):
        try:
            await coro(*args, **kwargs)
        except Exception:
            pass

    async def _initiate_event_source(self):
        async with sse_client.EventSource(
            f"{_e['SSE_DONATION']['URL']}{await self.get_stream_key()}"
        ) as event_source:
            try:
                async for message in event_source:
                    donations = json.loads(f"{message.data}")
                    self.dispatch("donations", donations)
            except Exception:
                pass

    def run(self, email_or_jwt, password=None, otp=None, stream_key=None):
        self.loop.run_until_complete(
            self.start(email_or_jwt, password, otp=otp, stream_key=stream_key)
        )

    async def start(self, email_or_jwt, password=None, otp=None, stream_key=None):
        if email_or_jwt:
            await self.login(email_or_jwt, password, otp)
        elif stream_key:
            self._stream_key = stream_key

        await self._initiate_event_source()

    async def login(self, email_or_jwt, password=None, otp=None):
        if password:
            response = await self._request(
                _e["LOGIN"]["METHOD"],
                _e["LOGIN"]["URL"],
                json={"email": email_or_jwt, "password": password, "otp": otp},
                get_complete=True,
            )
            if response["status"] != 200:
                raise Exception(response["data"])
            self.jwt = response["headers"]["authorization"]
            user = response["data"]
        else:
            self.jwt = email_or_jwt
            user = await self.get_user()
        self._stream_key = await self.get_stream_key()

        self.dispatch("login", user)

    async def stop(self):
        self.jwt = ""

    async def get_user(self):
        return (await self._request(_e["USER"]["METHOD"], _e["USER"]["URL"]))["data"]

    async def get_stream_key(self):
        if not self._stream_key:
            response = await self._request(
                _e["STREAM_KEY"]["METHOD"], _e["STREAM_KEY"]["URL"]
            )
            self._stream_key = response["data"]["stream_key"]
        return self._stream_key

    async def set_stream_key(self, stream_key):
        self._stream_key = stream_key
        await self._initiate_event_source()

    async def get_balance(self):
        response = await self._request(_e["BALANCE"]["METHOD"], _e["BALANCE"]["URL"])
        return response["data"]["balance"]

    async def send_fake_donation(self):
        await self._request(
            _e["FAKE"]["METHOD"],
            _e["FAKE"]["URL"],
        )

    async def get_available_balance(self):
        response = await self._request(
            _e["AVAILABLE_BALANCE"]["METHOD"], _e["AVAILABLE_BALANCE"]["URL"]
        )
        return response["data"]["available-balance"]

    async def get_transactions(self, page=1, pageSize=15):
        response = await self._request(
            _e["TRANSACTIONS"]["METHOD"],
            _e["TRANSACTIONS"]["URL"],
            params={"page": page, "page_size": pageSize},
        )
        return response["data"]["transactions"] or []

    async def get_milestone_progress(self, start_date):
        response = await self._request(
            _e["MILESTONE_PROGRESS"]["METHOD"],
            _e["MILESTONE_PROGRESS"]["URL"],
            params={"start_date": start_date},
            headers={"stream-key": await self.get_stream_key()},
        )

        return response["data"]["progress"]

    async def get_leaderboard(self, period="all"):
        if period not in ["all", "year", "month", "week"]:
            raise Exception("Invalid Period Value")

        response = await self._request(
            _e["LEADERBOARD"]["METHOD"],
            _e["LEADERBOARD"]["URL"],
            headers={"stream-key": await self.get_stream_key()},
        )

        return response["data"]

    async def _request(
        self, method, url, json={}, params={}, headers={}, get_complete=False
    ):
        headers.update({"authorization": self.jwt})
        async with aiohttp.ClientSession(headers=headers) as session:
            async with getattr(session, method)(
                url,
                json=json,
                params=params,
            ) as r:
                if r.status > 300:
                    raise Exception(r.status)

                if get_complete:
                    data = {
                        "data": await r.json(),
                        "headers": r.headers,
                        "status": r.status,
                    }
                else:
                    data = await r.json()
        return data
