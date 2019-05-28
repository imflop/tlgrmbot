import signal
from datetime import datetime
from urllib.parse import urlencode

from tornado.escape import json_decode
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPResponse
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.log import app_log
from tornado.options import define, options
from tornado.web import Application, RequestHandler

define('port', default=8010, help='run on the given port', type=int)
define('debug', default=True, help='debug mode', type=bool)
define('notify-chat', default=None, help='notify chat id', type=str)
define('feedback-chat', default=None, help='feedback chat id', type=str)
define('token', default=None, help='bot token', type=str)


class StatusHandler(RequestHandler):
    """
    Simple status class
    """

    async def get(self):
        response = {
            'version': '1.3.1',
            'datetime_now': datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
        }
        self.set_header('Content-Type', 'application/json')
        self.set_status(200)
        self.write(response)
        await self.finish()


class NotifyHandler(RequestHandler):
    """
    Send notify message type to tlgrm chat
    """

    async def post(self):
        data = json_decode(self.request.body)
        response = await self.do_post(data)
        self.set_header('Content-Type', 'application/json')
        self.set_status(response.code)
        self.write(dict(code=response.code, reason=response.reason))
        await self.finish()

    async def do_post(self, data: dict) -> HTTPResponse:
        text = f"{data['title']}\n\n<strong>{data['user']}</strong>\t{data['email']}\t{data['site']}"
        post_data = [('chat_id', NOTIFY_CHAT_ID), ('text', text), ('parse_mode', 'html')]
        http = AsyncHTTPClient()
        request = HTTPRequest(url=URL, method="POST", body=urlencode(post_data))
        response = await http.fetch(request)
        result_json = json_decode(response.body)
        app_log.info(
            f"Sended {str(result_json['ok'])} to chat {result_json['result']['chat']['title']} at "
            f"{datetime.utcfromtimestamp(int(result_json['result']['date'])).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return response


class FeedbackHandler(RequestHandler):
    """
    Send feedback message type to tlgrm chat
    """

    async def post(self):
        data = json_decode(self.request.body)
        response = await self.do_post(data)
        self.set_header('Content-Type', 'application/json')
        self.set_status(response.code)
        self.write(dict(code=response.code, reason=response.reason))
        await self.finish()

    async def do_post(self, data: dict) -> HTTPResponse:
        text = f"{data['text']}\n\n<strong>{data['user']}</strong>\t{data['email']}\t{data['site']}"
        post_data = [('chat_id', FEEDBACK_CHAT_ID), ('text', text), ('parse_mode', 'html')]
        request = HTTPRequest(url=URL, method='POST', body=urlencode(post_data))
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
                app_log.log(f"Data do NOT send to destination with reason: {response.reason}")
            return response


class TlgrmBotApplication(Application):
    is_closing = False

    def singnal_handler(self, signum, frame):
        app_log.info("exiting...")
        self.is_closing = True

    def try_exit(self):
        if self.is_closing:
            IOLoop.instance().stop()
            app_log.info("exit success")


if __name__ == '__main__':
    options.parse_command_line()

    NOTIFY_CHAT_ID = options.notify_chat
    FEEDBACK_CHAT_ID = options.feedback_chat
    URL = f"https://api.telegram.org/bot{options.token}/sendMessage"

    application = TlgrmBotApplication([
        (r'/api/notify', NotifyHandler),
        (r'/api/feedback', FeedbackHandler),
        (r'/api/status', StatusHandler)
    ], debug=options.debug)

    http_server = HTTPServer(application)
    http_server.listen(options.port)

    app_log.info(f"Server is running at http://127.0.0.1:{options.port}")
    app_log.info(f"Quit the server with Control-C")

    signal.signal(signal.SIGINT, application.singnal_handler)
    PeriodicCallback(application.try_exit, 100).start()
    IOLoop.instance().start()
