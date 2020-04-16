import signal
from datetime import datetime
from typing import Awaitable, Optional, Dict, Union
from urllib.parse import urlencode

from tornado.escape import json_decode
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPResponse
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.log import app_log
from tornado.options import define, options
from tornado.web import Application, RequestHandler

define("port", default=8010, help="run on the given port", type=int)
define("debug", default=True, help="debug mode", type=bool)
define("chat", default=None, help="chat id", type=str)
define("token", default=None, help="bot token", type=str)


class StatusHandler(RequestHandler):
    """
    Bot status handler
    """

    async def prepare(self) -> Optional[Awaitable[None]]:
        header = "Content-Type"
        body = "application/json"
        self.set_header(header, body)

    async def get(self):
        response = {
            "bot_status": "online",
            "version": "1.4.0",
            "datetime_now": datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"),
        }
        self.set_status(200)
        self.write(response)
        await self.finish()


class ResponseHandler(RequestHandler):
    """
    Send feedback message type to tlgrm chat
    """

    async def post(self):
        data = json_decode(self.request.body)
        response = await self.do_post(data)
        self.set_header("Content-Type", "application/json")
        self.set_status(response.code)
        self.write(dict(code=response.code, reason=response.reason))
        await self.finish()

    async def do_post(self, data: dict) -> HTTPResponse:
        text = self._parse_data(data)
        post_data = [
            ("chat_id", CHAT_ID),
            ("text", text),
            ("parse_mode", "html"),
        ]
        request = HTTPRequest(url=URL, method="POST", body=urlencode(post_data))
        http_client = AsyncHTTPClient()
        try:
            response = await http_client.fetch(request)
        except Exception as e:
            app_log.error(f"Error: {e}")
        else:
            result_json = json_decode(response.body)
            if response.code == 200:
                app_log.info(
                    f"Data send to chat {result_json['result']['chat']['title']} with reason: {response.reason}"
                )
            else:
                app_log.log(
                    f"Data do NOT send to destination with reason: {response.reason}"
                )
            return response

    def _parse_data(self, data: dict) -> str:
        result = ""
        if data:
            result_dict = {}
            keys_order = self._get_keys_order(data)
            for k, v in data.items():
                if isinstance(v, dict):
                    for key, value in v.items():
                        if key == "value":
                            result_dict[
                                list(keys_order.keys())[
                                    list(keys_order.values()).index(k)
                                ]
                            ] = value
                        elif key == "type":
                            self._parse(
                                result_dict,
                                value,
                                list(keys_order.keys())[
                                    list(keys_order.values()).index(k)
                                ],
                            )
                        elif key == "font-style":
                            self._parse(
                                result_dict,
                                value,
                                list(keys_order.keys())[
                                    list(keys_order.values()).index(k)
                                ],
                            )
            result = "\n".join(result_dict.values())
        return result

    def _get_keys_order(self, data_d) -> Dict[int, str]:
        keys_order = {}
        for i, j in enumerate(data_d.keys()):
            keys_order[i] = j
        return keys_order

    def _parse(
        self, result: dict, type_d: Union[dict, str], idx: Optional[int]
    ) -> Dict[int, str]:
        if isinstance(type_d, dict):
            if "value" and "url" in type_d.keys():
                for key, value in type_d.items():
                    if key == "url" and value:
                        result[idx] = f'<a href="{value}">{result.get(idx)}</a>'
        else:
            if type_d == "bold":
                result[idx] = f"<strong>{result.get(idx)}</strong>"
            elif type_d == "italic":
                result[idx] = f"<i>{result.get(idx)}</i>"
        return result


class TlgrmBotApplication(Application):
    is_closing = False

    def singnal_handler(self, signum, frame):
        app_log.info("exiting...")
        self.is_closing = True

    def try_exit(self):
        if self.is_closing:
            IOLoop.instance().stop()
            app_log.info("exit success")


if __name__ == "__main__":
    options.parse_command_line()

    CHAT_ID = options.chat
    URL = f"https://api.telegram.org/bot{options.token}/sendMessage"

    application = TlgrmBotApplication(
        [(r"/api/feedback", ResponseHandler), (r"/api/status", StatusHandler),],
        debug=options.debug,
    )

    http_server = HTTPServer(application)
    http_server.listen(options.port)

    app_log.info(f"Server is running at http://127.0.0.1:{options.port}")
    app_log.info(f"Quit the server with Control-C")

    signal.signal(signal.SIGINT, application.singnal_handler)
    PeriodicCallback(application.try_exit, 100).start()
    IOLoop.instance().start()
