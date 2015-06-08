from __future__ import absolute_import
from flask import Flask, Response, request
import click
import importlib
import os
import pkg_resources
import rq_dashboard


def get_version(package='rq_dashboard'):
    return pkg_resources.get_distribution(package).version


def add_basic_auth(blueprint, username, password, realm='RQ Dashboard'):
    """Add HTTP Basic Auth to a blueprint.

    Note this is only for casual use!

    """
    @blueprint.before_request
    def basic_http_auth(*args, **kwargs):
        auth = request.authorization
        if (
                auth is None
                or auth.password != password
                or auth.username != username):
            return Response(
                'Please login',
                401,
                {'WWW-Authenticate': 'Basic realm="{}"'.format(realm)})


def make_flask_app(config, username, password, url_prefix):
    """Return Flask app with default configuration and registered blueprint."""
    app = Flask(__name__)
    # Start configuration with our built in defaults.
    app.config.from_object(rq_dashboard.default_settings)
    # Override with any settings in config file, if given.
    if config:
        app.config.from_object(importlib.import_module(config))
    # Override from a configuration file in the env variable, if present.
    if 'RQ_DASHBOARD_SETTINGS' in os.environ:
        app.config.from_envvar('RQ_DASHBOARD_SETTINGS')

    blueprint = rq_dashboard.blueprint.blueprint
    if username:
        add_basic_auth(blueprint, username, password)
    app.register_blueprint(blueprint, url_prefix=url_prefix)

    return app


@click.command()
@click.option(
    '-b', '--bind', default='0.0.0.0',
    help='IP or hostname on which to bind HTTP server')
@click.option(
    '-p', '--port', default=9181, type=int,
    help='Port on which to bind HTTP server')
@click.option(
    '--url-prefix', default='',
    help='URL prefix e.g. for use behind a reverse proxy')
@click.option(
    '--username', default=None,
    help='HTTP Basic Auth username (not used if not set)')
@click.option(
    '--password', default=None,
    help='HTTP Basic Auth password')
@click.option(
    '-c', '--config', default=None,
    help='Configuration file (Python module on search path)')
@click.option(
    '-H', '--redis-host', default=None,
    help='IP address or hostname of Redis server')
@click.option(
    '-P', '--redis-port', default=None, type=int,
    help='Port of Redis server')
@click.option(
    '--redis-password', default=None,
    help='Password for Redis server')
@click.option(
    '-D', '--redis-database', default=None, type=int,
    help='Database of Redis server')
@click.option(
    '-u', '--redis-url', default=None,
    help='Redis URL connection (overrides other individual settings')
@click.option(
    '--interval', default=None, type=int,
    help='Refresh interval in ms')
def run(
        bind, port, url_prefix, username, password,
        config,
        redis_host, redis_port, redis_password, redis_database, redis_url,
        interval):
    """Run the RQ Dashboard Flask server as a stand alone.

    Configuration can either be set on the command line or through environment
    variables of the form RQ_DASHBOARD_*.

    Configuration can also be provided in a Python module referenced using
    --config, or with a .cfg file referenced by the RQ_DASHBOARD_SETTINGS
    environment variable.

    """
    click.echo('RQ Dashboard version {}'.format(get_version()))
    app = make_flask_app(config, username, password, url_prefix)
    if redis_url:
        app.config['REDIS_URL'] = redis_url
    if redis_host:
        app.config['REDIS_HOST'] = redis_host
    if redis_port:
        app.config['REDIS_PORT'] = redis_port
    if redis_password:
        app.config['REDIS_PASSWORD'] = redis_password
    if redis_database:
        app.config['REDIS_DB'] = redis_database
    if interval:
        app.config['RQ_POLL_INTERVAL'] = interval
    app.run(host=bind, port=port)


def main():
    run(auto_envvar_prefix='RQ_DASHBOARD')
