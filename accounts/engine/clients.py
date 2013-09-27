# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

from oslo.config import cfg

from tdafcommon.openstack.common import importutils
from tdafcommon.openstack.common import log as logging

logger = logging.getLogger(__name__)


from tdafcommon.common import tdafcommon_keystoneclient as rkc
try:
    from heatclient import client as heatclient
except ImportError:
    swiftclient = None
    logger.info('heatclient not available')

class OpenStackClients(object):
    '''
    Convenience class to create and cache client instances.
    '''

    def __init__(self, context):
        self.context = context
        self._keystone = None
        self._heat = None

    @property
    def auth_token(self):
        # if there is no auth token in the context
        # attempt to get one using the context username and password
        return self.context.auth_token or self.keystone().auth_token

    def keystone(self):
        if self._keystone:
            return self._keystone

        self._keystone = rkc.KeystoneClient(self.context)
        return self._keystone

    def url_for(self, **kwargs):
        return self.keystone().url_for(**kwargs)

    def heat(self):
        if heatclient is None:
            return None
        if self._heat:
            return self._heat

        con = self.context
        if self.auth_token is None:
            logger.error("Heat connection failed, no auth_token!")
            return None

        args = {
            'auth_version': '2.0',
            'tenant_name': con.tenant,
            'user': con.username,
            'key': None,
            'authurl': None,
            'preauthtoken': self.auth_token,
            'preauthurl': self.url_for(service_type='orchestration')
        }
        self._heat = heatclient.Connection(**args)
        return self._heat
