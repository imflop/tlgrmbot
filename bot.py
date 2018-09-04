import json
import requests
from requests import Response
from datetime import datetime
from tornado.log import app_log
from tornado.ioloop import IOLoop
from tornado.options import define, options
from tornado.httpserver import HTTPServer
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPResponse
from tornado.web import Application, RequestHandler, gen


define('port', default=8010, help='run on the given port', type=int)
define('debug', default=True, help='debug mode', type=bool)
define('chat', default=None, help='id of chat to send messages', type=str)
define('token', default=None, help='bot token', type=str)


class StatusHandler(RequestHandler):
    """
    Simple status class
    """
    def get(self):
        response = {
            'version': '0.0.1',
            'last_build': datetime.strftime(datetime.now(), '%Y.%m.%d %H:%M:%S')
        }
        self.set_header('Content-Type', 'application/json')
        self.set_status(200)
        self.write(response)
        self.finish()


class FeedbackHandler(RequestHandler):
    """
    Send feedback to tlgrm
    """
    @gen.coroutine
    def post(self):
        data = json.loads(self.request.body.decode('utf-8'))
        # response = yield self.do_post(data)
        # self.set_header('Content-Type', 'application/json')
        # self.set_status(response.code)
        # self.write(dict(code=response.code, reason=response.reason))
        response = self.__requests_do_post(data)
        self.set_header('Content-Type', 'application/json')
        self.set_status(response.status_code)
        self.write(dict(code=response.status_code, reason=response.reason))
        self.finish()

    @gen.coroutine
    def do_post(self, data: dict) -> HTTPResponse:
        text = "{text}\n\n<strong>{username}</strong>\t{email}\t{site}".format(
            username=data['user'], email=data['email'], text=data['text'], site=data['site']
        )
        post_data = [('chat_id', CHAT_ID), ('text', text), ('parse_mode', 'html')]
        http_client = AsyncHTTPClient()
        request = HTTPRequest(url=URL, method='POST', body=json.dumps(post_data))
        response = yield http_client.fetch(request)
        x = json.loads(response.body.decode('utf-8'))
        app_log.log(x)
        if response.code == 200:
            app_log.info('Data send to destination with reason: {reason}'.format(reason=response.reason))
        else:
            app_log.log('Data do NOT send to destination with reason: {reason}'.format(reason=response.reason))
        return response

    def __requests_do_post(self, data: dict) -> Response:
        text = "{text}\n\n<strong>{username}</strong>\t{email}\t{site}".format(
            username=data['user'], email=data['email'], text=data['text'], site=data['site']
        )
        post_data = [('chat_id', CHAT_ID), ('text', text), ('parse_mode', 'html')]
        response = requests.post(URL, post_data)
        if response.status_code == 200:
            app_log.info('Data send to destination with reason: {reason}'.format(reason=response.reason))
        else:
            app_log.log('Data do NOT send to destination with reason: {reason}'.format(reason=response.reason))
        return response


if __name__ == '__main__':
    options.parse_command_line()

    application = Application([
        (r'/api/feedback', FeedbackHandler),
        (r'/api/status', StatusHandler)
    ], debug=options.debug)

    http_server = HTTPServer(application)
    http_server.listen(options.port)

    CHAT_ID = options.chat
    URL = "https://api.telegram.org/bot{token}/sendMessage".format(token=options.token)

    app_log.info('Server is running at http://127.0.0.1:{port}'.format(port=options.port))
    app_log.info('Quit the server with Control-C')

    IOLoop.instance().start()
