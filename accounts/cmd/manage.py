# vim: tabstop=4 shiftwidth=4 softtabstop=4

# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
  CLI interface for Accounts management.
"""

import sys

from oslo.config import cfg

from tdafcommon.db import api as db_api
from tdafcommon.db import migration
from tdafcommon.openstack.common import log
from accounts import version
import traceback


CONF = cfg.CONF


def do_db_version():
    """Print database's current migration level."""
    print(migration.db_version())


def do_db_sync():
    """
    Place a database under migration control and upgrade,
    creating first if necessary.
    """
    migration.db_sync(CONF.command.version)


def add_command_parsers(subparsers):
    parser = subparsers.add_parser('db_version')
    parser.set_defaults(func=do_db_version)

    parser = subparsers.add_parser('db_sync')
    parser.set_defaults(func=do_db_sync)
    parser.add_argument('version', nargs='?')
    parser.add_argument('current_version', nargs='?')


command_opt = cfg.SubCommandOpt('command',
                                title='Commands',
                                help='Available commands',
                                handler=add_command_parsers)


def main():
    CONF.register_cli_opt(command_opt)
    try:
        #Check how to make this correctly
        version='2013072501'
        default_config_files = cfg.find_config_files('accounts', 'accounts-engine')
        CONF(sys.argv[1:], project='accounts', prog='accounts-manage',
             version=version,
             default_config_files=default_config_files)
        log.setup("accounts")
        db_api.configure()
    except RuntimeError as e:
        sys.exit("ERROR: %s" % e)

    try:
        CONF.command.func()
    except Exception as e:
        print traceback.format_exc()
        sys.exit("ERROR: %s" % e)
