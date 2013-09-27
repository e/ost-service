# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012, Red Hat, Inc.
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
Client side of the accounts engine RPC API.
"""

from accounts.rpc import api

import tdafcommon.openstack.common.rpc.proxy


class EngineClient(tdafcommon.openstack.common.rpc.proxy.RpcProxy):
    '''Client side of the accounts engine rpc API.

    API version history:

        1.0 - Initial version.
    '''

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self):
        super(EngineClient, self).__init__(
            topic=api.ENGINE_TOPIC,
            default_version=self.BASE_RPC_API_VERSION)

    def echo(self, ctxt, msg):
        """
        The echo method returns same message between '*'.

        :param ctxt: RPC context.
        :param msg: Message to be send to backend
        """
        return self.call(ctxt, self.make_msg('echo',
                                             msg=msg))

    def get_list(self, ctxt, tenant_id):
        """
        Get Accounts services list for the tenant (ctxt should contain tenant_id).

        :param ctxt: RPC context
        :param tenant_id: tenant_id to check for Accounts
        
        Returns: Response got from RPC server.
        Response sample: {'result': True, 'accounts': [{'id': '8483934393','name':'Accounts prepro','type':1 ,'endpoint': 'http://10.1.1.1:5001', 'status': 'COMPLETED' }]}
        """
        return self.call(ctxt, self.make_msg('get_list',
                                             tenant_id=tenant_id))

    def start_accounts(self, ctxt, tenant_id, accounts_type_id, accounts_name):
        """
        Instantiate a new Accounts service for the required tenant

        :param ctxt: RPC context
        :param tenant_id: tenant_id for the new Accounts Service
        :param accounts_type_id: accounts_type_id for the new accounts
        :param accounts_name: name to use for this new accounts
        
        Returns: Response got from RPC server.
        Response sample: {'result': True, 'accounts_id': '8483934393'}
        """
        return self.call(ctxt, self.make_msg('start_accounts',
                                             tenant_id=tenant_id,
                                             accounts_type_id=accounts_type_id,
                                             accounts_name=accounts_name))

    def stop_accounts(self, ctxt, tenant_id, accounts_id):
        """
        Stop (and destroye) a an existing Accounts service for the required tenant

        :param ctxt: RPC context
        :param tenant_id: tenant_id owner of the Accounts
        :param accounts_id: Accounts Service to stop
        
        Returns: Response got from RPC server.
        Response sample: {'result': True}
        """
        return self.call(ctxt, self.make_msg('stop_accounts',
                                             tenant_id=tenant_id,
                                             accounts_id=accounts_id))

    def get_accounts(self, req):
        """
        Get tenant Accounts details
        :param ctxt: RPC context
        :param tenant_id: tenant_id owner of the Rsuh
        :param accounts_id: Accounts to stop
        
        Returns: Response got from RPC server.
        Response sample: {'result': True, 'id': '8483934393','name':'Accounts prepro','type':1 ,'endpoint': 'http://10.1.1.1:5001', 'status': 'COMPLETED', 'extdata': '{}'}
        """
        
        #Call to RPC to get real details
        return self.engine.get_accounts(req.context,req.context.tenant_id,req.context.accounts_id)
