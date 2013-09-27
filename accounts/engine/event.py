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

from tdafcommon.db import api as db_api
from tdafcommon.openstack.common import exception
from tdafcommon.openstack.common import log as logging

logger = logging.getLogger(__name__)


class Event(object):
    '''Class representing a Resource state change.'''

    def __init__(self, context, stack, resource,
                 action, status, reason,
                 physical_resource_id, resource_properties,
                 timestamp=None, id=None):
        '''
        Initialise from a context, stack, resource, event information and
        current resource data. The timestamp and database ID may also be
        initialised if the event is already in the database.
        '''
        self.context = context
        self.resource = resource
        self.stack = stack
        self.action = action
        self.status = status
        self.reason = reason
        self.physical_resource_id = physical_resource_id
        try:
            self.resource_properties = dict(resource_properties)
        except ValueError as ex:
            self.resource_properties = {'Error': str(ex)}
        self.timestamp = timestamp
        self.id = id

    @classmethod
    def load(cls, context, event_id, event=None, stack=None):
        '''Retrieve an Event from the database.'''
        #from accounts.engine import parser

        ev = event if event is not None else\
            db_api.event_get(context, event_id)
        if ev is None:
            message = 'No event exists with id "%s"' % str(event_id)
            raise exception.NotFound(message)

        #st = stack if stack is not None else\
        #    parser.Stack.load(context, ev.stack_id)
        #resource = st[ev.logical_resource_id]
        return None
        '''return cls(context, st, resource,
                   ev.resource_action, ev.resource_status,
                   ev.resource_status_reason,
                   ev.physical_resource_id, ev.resource_properties,
                   ev.created_at, ev.id)'''

    def store(self):
        '''Store the Event in the database.'''
        ev = {
            'logical_resource_id': self.resource.name,
            'physical_resource_id': self.physical_resource_id,
            'stack_id': self.stack.id,
            'resource_action': self.action,
            'resource_status': self.status,
            'resource_status_reason': self.reason,
            'resource_type': self.resource.type(),
            'resource_properties': self.resource_properties,
        }

        if self.timestamp is not None:
            ev['created_at'] = self.timestamp

        if self.id is not None:
            logger.warning('Duplicating event')

        new_ev = db_api.event_create(self.context, ev)
        self.id = new_ev.id
        return self.id
