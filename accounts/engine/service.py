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

import functools
import json

from oslo.config import cfg
import webob

from tdafcommon.openstack.common import timeutils
from tdafcommon.common import context
from tdafcommon.db import api as db_api
from accounts.engine import api
from accounts.rpc import api as rpc_api
from accounts.engine import clients

from tdafcommon.openstack.common import log as logging
from tdafcommon.openstack.common import threadgroup
from tdafcommon.openstack.common.gettextutils import _
from tdafcommon.openstack.common.rpc import service
from tdafcommon.openstack.common import uuidutils
from tdafcommon.openstack.common import exception
from tdafcommon.heatapi import heat

import json
import re

logger = logging.getLogger(__name__)


def request_context(func):
    @functools.wraps(func)
    def wrapped(self, ctx, *args, **kwargs):
        if ctx is not None and not isinstance(ctx, context.RequestContext):
            ctx = context.RequestContext.from_dict(ctx.to_dict())
        return func(self, ctx, *args, **kwargs)
    return wrapped

class EngineServiceWrapper(service.Service):
    """
    Manages the running instances from creation to destruction.
    All the methods in here are called from the RPC backend.  This is
    all done dynamically so if a call is made via RPC that does not
    have a corresponding method here, an exception will be thrown when
    it attempts to call into this class.  Arguments to these methods
    are also dynamically added and will be named as keyword arguments
    by the RPC caller.
    """
    def __init__(self, host, topic, manager=None):
        super(EngineServiceWrapper, self).__init__(host, topic)

    def _start_in_thread(self, service_id, func, *args, **kwargs):
        if service_id not in self.rsg:
            self.rsg[service_id] = threadgroup.ThreadGroup()
            self.rsg[service_id].add_thread(func, *args, **kwargs)

    def _timer_in_thread(self, service_id, func, *args, **kwargs):
        """
        Define a periodic task, to be run in a separate thread, in the stack
        threadgroups.  Periodicity is cfg.CONF.periodic_interval
        """
        if service_id not in self.rsg:
            self.rsg[service_id] = threadgroup.ThreadGroup()
        self.rsg[service_id].add_timer(cfg.CONF.periodic_interval,
                                     func, *args, **kwargs)
    def _service_task(self):
        """
        This is a dummy task which gets queued on the service.Service
        threadgroup.  Without this service.Service sees nothing running
        i.e has nothing to wait() on, so the process exits.
        This could also be used to trigger periodic non-stack-specific
        housekeeping tasks
        """

    def _start_watch_task(self, service_id, cnxt):
        self._timer_in_thread(service_id, self._periodic_watcher_task, rid=service_id)

    def start(self):
        super(EngineServiceWrapper, self).start()
        # Create dummy service task, because when there is nothing queued
        # on self.tg the process exits
        # rsg == "Service Groups" (the r was there before and I will let it live)
        self.rsg = {}
        logger.warning('periodic_interval:' + str(cfg.CONF.periodic_interval))
        self.tg.add_timer(cfg.CONF.periodic_interval, self._service_task)
        # for s in services: self._start_watch_task(r.id, admin_context)

    def echo(self,cnxt,msg):
        '''
        Echo RPC backend method. Return the same msg between '*' 
        '''
        return '*%s*'%msg

    @request_context
    def get_list(self, ctxt, tenant_id):
        """
        Get Service list for the tenant (ctxt should contain tenant_id).

        :param ctxt: RPC context (must contain tenant_id)
        :param tenant_id: tenant_id to check for Services
        
        Returns: JSON Specifying the list of services and their data
        Response sample: {'result': True, 'rush_services': [{'id': '8483934393','name':'Rush prepro','type':1 ,'endpoint': 'http://10.1.1.1:5001', 'status': 'CREATE_COMPLETE' }]}
        """
        
        try:
            #Check in db if this tenant has an instanced Service
            rt = db_api.service_tenant_get_all_by_tenant(ctxt, tenant_id)
            result = {'result': True, 'services': []}
            for rtentry in rt:
                service_entry = db_api.service_get(ctxt, rtentry.service_id)
                
                #Update status with heat data (Service DB can be out of sync with HEAT stack status)
                #Can be removed to improve query performance when status is CREATE_COMPLETE
                heatcln = heat.heatclient(cfg.CONF.tdaf_username, cfg.CONF.tdaf_user_password, cfg.CONF.tdaf_tenant_name)
                
                service_name = cfg.CONF.tdaf_service_prefix+str(tenant_id)+"-"+str(service_entry.name)
                stack_list = self.get_stack_list_for_tenant(heatcln,tenant_id)
                for stack in stack_list:
                    stack_info = stack._info;
                    if stack_info['stack_name'] == service_name:
                        break
                        
                if stack_info is not None and stack_info['stack_name'] == service_name:
                    #Stack info first
                    values = {'status':stack_info['stack_status']}
                    db_api.service_update(ctxt, rtentry.service_id, values)
                    
                self.update_service_endpointdata(ctxt,heatcln,service_entry.stack_id,rtentry.service_id)
                result['services'].append({'id': service_entry.id, 'name': service_entry.name, 'type': service_entry.service_type_id,
                                         'endpoint':service_entry.url, 'status': service_entry.status})
            return result
        except Exception as e:
            return {'result': False, 'error': str(e)}

    @request_context
    def start_service(self, ctxt, tenant_id, service_type_id, service_name):
        """
        Create new Rush service for the tenant

        :param ctxt: RPC context
        :param tenant_id: tenant_id to check for Rush
        :param service_type_id: service_type_id for the new rush
        :param service_name: rush name to use for this new rush
        
        Returns: JSON Specifying the creation start result and the rush_id. Rush can take longer
                 to be ready for serving (check with get_status)
        Response sample: {'result': True, 'rush_id': '8483934393'}
        """
        
        #Check in db if this tenant has an instanced Rush
        try:
            #Check that service_name is not empty
            if service_name is None or len(service_name) == 0:
                return {'result': False, 'error': 'STARTSERVICEEX01', 'error_desc': 'Service name not provided'}
            
            #Check if type_id exists
            rtc = db_api.service_type_get(ctxt,service_type_id)
            if not rtc:
                return {'result': False, 'error': 'STARTSERVICEEX02', 'error_desc': 'Service type does not exist'}
                
            service_id = uuidutils.generate_uuid()
            
            #Call HEAT to create the stack
            heatcln = heat.heatclient(cfg.CONF.tdaf_username, cfg.CONF.tdaf_user_password, cfg.CONF.tdaf_tenant_name)
            
            # Prapare dict for stack creation
            # For development I do not use the key
            stack_parms = {
                'KeyName': cfg.CONF.tdaf_instance_key
            }
            
            new_stack_name = cfg.CONF.tdaf_service_prefix+str(tenant_id)+"-"+str(service_name)
            
            stack_info = {
                'stack_name': new_stack_name,
                # 'parameters': stack_parms,
                'template': rtc.template.replace ('\n', '\\n'),
                'timeout_mins': 60,
            }
            logger.warning('')
            logger.warning('')
            logger.warning('')
            logger.warning('')
            logger.warning('')
            logger.warning('')
            logger.warning('')
            logger.warning('')
            logger.warning('hola')
            logger.warning('')
            logger.warning('')
            logger.warning('')
            logger.warning('')
            logger.warning('')
            logger.warning('')
            logger.warning('')
            heatcln.stacks.create(**stack_info)
        
            stack_list = self.get_stack_list_for_tenant(heatcln,tenant_id)
            if len(stack_list) > 0:
                #Check the name to select the one just created
                for stack in stack_list:
                    stack_info = stack._info;
                    if stack_info['stack_name'] == new_stack_name:
                        break

                if stack_info is not None and stack_info['stack_name'] == new_stack_name:
                    values = {'stack_id':stack_info['id'],'id':service_id,'service_type_id':service_type_id,'status': stack_info['stack_status'], 'name': service_name}
                    rc = db_api.service_create(ctxt, values)
                    values = {'service_id':service_id,'tenant_id':tenant_id}
                    tc = db_api.service_tenant_create(ctxt, values)
                    return {'result': True, 'service_id': service_id, 'misc': str(stack_info)}
                else:
                    return {'result': False, 'error': 'STARTSERVICEEX04', 'error_desc': 'OpenStack stack not found'}
            else:
                return {'result': False, 'error': 'STARTSERVICEEX03', 'error_desc': 'OpenStack stack could not be created'}
        except Exception as e:
            return {'result': False, 'error': str(e)}

    @request_context
    def stop_service(self, ctxt,tenant_id,service_id):
        """
        Deletes the Rush service identified by service_id for the tenant

        :param ctxt: RPC context
        :param tenant_id: tenant_id to check for Rush
        :param service_id: service_id to stop
        
        Returns: JSON Specifying the stop result and the service_id.
        Response sample: {'result': True, 'service_id': '8483934393'}
        """
        
        #Check in db if this tenant has an instanced Rush
        rsc = db_api.service_get(ctxt,service_id)
        if rsc:
            try:
                #Check if it is for this tenant
                rt = db_api.service_tenant_get_by_service_and_tenant(ctxt, service_id, tenant_id)
                if not rt or rt.first().tenant_id != tenant_id:
                    return {'result': False, 'error': 'STOPSERVICEEX02', 'error_desc': 'Could not find Service for the tenant'}
                    
                #Call HEAT to destroy the stack
                heatcln = heat.heatclient(cfg.CONF.tdaf_username, cfg.CONF.tdaf_user_password, cfg.CONF.tdaf_tenant_name)
                heatcln.stacks.delete(rsc.stack_id)
                
                rt.delete()
                rsc.delete()
                return {'result': True, 'service_id': service_id}
            except Exception as e:
                return {'result': False, 'error': str(e)}
        else:
            return {'result': False, 'error': 'STOPSERVICEEX01', 'error_desc': 'Could not find Service'}

    @request_context
    def get_service(self, ctxt,tenant_id,service_id):
        """
        Get the endpoint data for the Rush service identified by service_id for the tenant

        :param ctxt: RPC context
        :param tenant_id: tenant_id to check for Rush
        :param service_id: service_id to stop
        
        Returns: JSON Specifying the stop result and the service_id.
        Response sample: {'result': True, 'service_id': '8483934393', ''ws': 'http://10.95.158.11/rush'}
        """
        
        #Check in db if the rush exists
        rsc = db_api.service_get(ctxt,service_id)
        if rsc:
            try:
                #Check if it is for this tenant
                rt = db_api.service_tenant_get_all_by_tenant(ctxt, tenant_id)
                if not rt or rt.first().tenant_id != tenant_id:
                    return {'result': False, 'error': 'GETSERVICEEX02', 'error_desc': 'Could not find Rush for the tenant'}
                
                #Check if the data is fill in. If not, update
                if rsc.url is None:
                    heatcln = heat.heatclient(cfg.CONF.tdaf_username, cfg.CONF.tdaf_user_password, cfg.CONF.tdaf_tenant_name)
                    self.update_service_endpointdata(ctxt,heatcln,rsc.stack_id,service_id)
                    
                return {'result': True, 'service_id': service_id, 'url': str(rsc.url)}
            except Exception as e:
                return {'result': False, 'error': str(e)}
        else:
            return {'result': False, 'error': 'GETSERVICEEX02', 'error_desc': 'Could not find Service'}
    
    def get_stack_list_for_tenant(self,heatcln,tenant_id):
        """
        Get all the stacks heat has configured for a tenant

        :param heatcln: HEAT client alread initialized
        :param tenant_id: tenant_id to check
        
        Returns: List of Stack objects with a _info field stating a JSON with the stack data (as defined by HEAT)
        """
        #Build query to get stack id                
        stack_filters = {
            'stack_name': cfg.CONF.tdaf_service_prefix+str(tenant_id),
        }
        stack_search = {
            'filters': stack_filters,
        }
        stack_generator = heatcln.stacks.list(**stack_search)
        stack_list = []
        for stack in stack_generator:
            stack_list.append(stack)
        return stack_list

    def get_instance_and_ip_list_for_stack_id(self,heatcln,stack_id):
        """
        Get all the instance resources and ip resources configured for a stack_id

        :param heatcln: HEAT client alread initialized
        :param stack_id: stack_id to get all the resources from
        
        Returns: instance_list: list of resource instances found
                 ip_list: list of ip resources found
        """
        #Get the instance list for this stack
        resources = heatcln.resources.list(stack_id)
        instance_list = []
        ip_list = []
        
        for resource in resources:
            res_info = resource._info
            
            #Add those resources that are instances
            if res_info['resource_type'] == 'AWS::EC2::Instance':
                instance_list.append(resource)
            if res_info['resource_type'] == 'AWS::EC2::EIPAssociation':
                ip_list.append(resource)
        return instance_list,ip_list
    
    def update_service_endpointdata(self,ctxt,heatcln,stack_id,service_id):
        """
        Updates in the DB the service data based on the stack data

        :param ctxt: RPC context
        :param heatcln: HEAT client alread initialized
        :param stack_id: stack_id to get all the resources from
        :param service_id: service_id to be updated with the obtained info
        """
        #Get the instance list for this stack
        instance_list,ip_list = self.get_instance_and_ip_list_for_stack_id(heatcln,stack_id)
        
        #If there is any ip, use it as service WS
        if len(ip_list)>0:
            ip_info = ip_list[0]._info;
            values = {'url':'http://'+ip_info['physical_resource_id']+':5001'}
            db_api.service_stack_update(ctxt, service_id, values)

class EngineService(EngineServiceWrapper):

    def __init__(self, *args, **kwargs):
        super(EngineServiceWrapper, self).__init__(*args, **kwargs)
        self.start_accounts = self.start_service
        self.stop_accounts = self.stop_service

