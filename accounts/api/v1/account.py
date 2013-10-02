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

"""
Stack endpoint for Accounts v1 ReST API.
"""

from webob import exc

from accounts.api.v1 import util
from tdafcommon.openstack.common import wsgi
from accounts.rpc import api as engine_api
from accounts.rpc import client as rpc_client

from tdafcommon.openstack.common import log as logging
from tdafcommon.openstack.common.gettextutils import _

logger = logging.getLogger(__name__)

class AccountsController(object):
    """
    WSGI controller for stacks resource in Accounts v1 API
    Implements the API actions
    """

    def __init__(self, options):
        self.options = options
        self.engine = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    '''Accounts methods
    '''
    @util.tenant_local
    def echo(self, req):
        """
        Echo test method for Accounts API - Sends echo request to RPC backend
        """
        res = self.engine.echo(req.context,'Test message')
        return {'tenant_id': req.context.tenant_id, 'res': res}
    
    @util.tenant_local
    def get_list(self, req):
        """
        Get status of Accounts service for this tenant and id
        """
        return self.engine.get_list(req.context,req.context.tenant_id)
    
    @util.tenant_local
    def create_accounts(self, req, body={}):
        """
        Create Accounts service for this tenant
        Body must contain the service_type_id and service_name
        """
        return self.engine.start_accounts(req.context,req.context.tenant_id,body['service_type_id'],body['service_name'])
    
    @util.identified_accounts
    def delete_accounts(self, req):
        """
        Delete Accounts service for this tenant
        """
        return self.engine.stop_accounts_stack(req.context,req.context.tenant_id,req.context.accounts_id)
    
    @util.identified_accounts
    def get_accounts(self, req):
        """
        Get tenant Accounts details
        """
        
        #Call to RPC to get real details
        return self.engine.get_accounts(req.context,req.context.tenant_id,req.context.accounts_id)
    
class AccountsSerializer(wsgi.JSONResponseSerializer):
    """Handles serialization of specific controller method responses."""

    def _populate_response_header(self, response, location, status):
        response.status = status
        response.headers['Location'] = location.encode('utf-8')
        response.headers['Content-Type'] = 'application/json'
        return response

    def create(self, response, result):
        self._populate_response_header(response,
                                       result['stack']['links'][0]['href'],
                                       201)
        response.body = self.to_json(result)
        return response


def create_resource(options):
    """
    Accounts resource factory method.
    """
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = AccountsSerializer()
    return wsgi.Resource(AccountsController(options), deserializer, serializer)
