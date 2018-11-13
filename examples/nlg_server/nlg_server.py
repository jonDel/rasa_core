from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import logging

from flask import Flask, request, jsonify
from gevent import ssl
from gevent.pywsgi import WSGIServer

from rasa_core.domain import Domain
from rasa_core.nlg import TemplatedNaturalLanguageGenerator
from rasa_core.trackers import DialogueStateTracker
from rasa_core.utils import get_group_args

logger = logging.getLogger(__name__)

DEFAULT_SERVER_PORT = 5056
SSL_GROUP = 'ssl'


def create_argument_parser():
    """Parse all the command line arguments for the nlg server script."""

    parser = argparse.ArgumentParser(
            description='starts the nlg endpoint')
    parser.add_argument(
            '-p', '--port',
            default=DEFAULT_SERVER_PORT,
            type=int,
            help="port to run the server at")
    parser.add_argument(
            '-d', '--domain',
            type=str,
            default=None,
            help="path of the domain file to load utterances from")
    ssl_arg = parser.add_argument_group(SSL_GROUP)
    ssl_arg.add_argument(
            '--keyfile',
            default=None,
            type=str,
            help="path of the file containing the ssl private key")
    ssl_arg.add_argument(
            '--certfile',
            default=None,
            type=str,
            help="path of the file containing the ssl certificate")
    ssl_arg.add_argument(
            '--ca_certs',
            default=None,
            type=str,
            help="path of the file containing a list of root certificates")
    ssl_arg.add_argument(
            '--ssl_version',
            default=None,
            type=type(ssl.PROTOCOL_TLS),
            help="version of the SSL protocol to connect to the server")
    return parser


def generate_response(nlg_call, domain):
    kwargs = nlg_call.get("arguments", {})
    template = nlg_call.get("template")
    sender_id = nlg_call.get("tracker", {}).get("sender_id")
    events = nlg_call.get("tracker", {}).get("events")
    tracker = DialogueStateTracker.from_dict(
                    sender_id, events, domain.slots)
    channel_name = nlg_call.get("channel")

    return TemplatedNaturalLanguageGenerator(domain.templates).generate(
            template, tracker, channel_name, **kwargs)


def create_app(domain):
    app = Flask(__name__)

    logging.basicConfig(level=logging.DEBUG)

    @app.route("/nlg", methods=['POST', 'OPTIONS'])
    def nlg():
        """Check if the server is running and responds with the version."""
        nlg_call = request.json

        response = generate_response(nlg_call, domain)
        return jsonify(response)

    return app


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    # Running as standalone python application
    arg_parser = create_argument_parser()
    cmdline_args = arg_parser.parse_args()
    ssl_args = get_group_args(SSL_GROUP, arg_parser, cmdline_args)
    domain = Domain.load(cmdline_args.domain)
    app = create_app(domain)
    http_server = WSGIServer(('0.0.0.0', cmdline_args.port), app, **ssl_args)

    http_server.start()
    logger.info("NLG endpoint is up and running. on {}"
                "".format(http_server.address))

    http_server.serve_forever()
