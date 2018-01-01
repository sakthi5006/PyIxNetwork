"""
:author: yoram@ignissoft.com
"""

from sys import platform
import requests
import time
import re

from trafficgenerator.tgn_utils import TgnError


class IxnRestWrapper(object):

    null = 'null'

    def __init__(self, logger):
        """ Init IXN REST package.

        :param looger: application logger, if stream handler and log level is DEBUG -> enable IXN Python debug.
        """

        self.logger = logger

    def waitForComplete(self, response, timeout=90):
        if 'errors' in response.json():
            raise TgnError(response.json()['errors'][0])
        if response.json()['state'].lower() == 'error':
            raise TgnError('post {} failed'.format(response.url))
        if response.json()['state'].lower() == 'success':
            return
        for _ in range(timeout):
            response = requests.get(self.root_url)
            if type(response.json()) == dict:
                state = response.json()['state']
            else:
                state = response.json()[0]['state']
            if state.lower() not in ['in_progress', 'down']:
                return
            time.sleep(1)
        raise TgnError('{} operation failed, state is {} after {} seconds'.
                       format(self.session, response.json()['state'], timeout))

    def request(self, command, url, **kwargs):
        self.logger.debug('{} - {} - {}'.format(command.__name__, url, kwargs))
        response = command(url, **kwargs)
        self.logger.debug('{}'.format(response))
        if response.status_code == 400:
            raise TgnError('failed to {} {} {} - status code {}'.
                           format(command.__name__, url, kwargs, response.status_code))
        return response

    def get(self, url):
        return self.request(requests.get, url)

    def post(self, url, data=None):
        response = self.request(requests.post, url, json=data)
        if 'id' in response.json():
            self.waitForComplete(response)
        return response

    def options(self, url):
        return self.request(requests.options, url)

    def patch(self, url, data=None):
        response = self.request(requests.patch, url, json=data)
        if response.status_code != 200:
            raise TgnError('object {} failed to set attributes {}'.format(url, data))

    def connect(self, ip, port):
        self.server_url = 'http://{}:{}'.format(ip, port)
        response = self.post(self.server_url + '/api/v1/sessions')
        self.session = response.json()['links'][0]['href'] + '/'
        self.root_url = self.server_url + self.session

    def getRoot(self):
        return self.session + 'ixnetwork'

    def commit(self):
        pass

    def execute(self, command, objRef=None, *arguments):
        data = {}
        if objRef:
            operations_url = '{}/operations/'.format(re.sub('\/[0-9]+', '', objRef.replace(self.session, '')))
        else:
            operations_url = 'ixnetwork/operations/'
        for argument in arguments:
            data['arg' + str(len(data) + 1)] = argument
        response = self.post(self.root_url + operations_url + command, data)
        return response.json()['result']

    def getVersion(self):
        return self.execute('getVersion')

    def newConfig(self):
        self.execute('newConfig')

    def loadConfig(self, configFileName):
        data = {'filename': configFileName}
        self.post(self.root_url + 'ixnetwork/operations/loadConfig', data)

    def saveConfig(self, configFileName):
        data = {'filename': configFileName}
        self.post(self.root_url + 'ixnetwork/operations/saveConfig', data)

    def getList(self, objRef, childList):
        response = self.get(self.server_url + objRef + '/' + childList)
        if type(response.json()) is list:
            return [self._get_href(c) for c in response.json()]
        else:
            return [self._get_href(response.json())]

    def getAttribute(self, objRef, attribute):
        response = self.get(self.server_url + objRef)
        return response.json().get(attribute, '::ixNet::OK')

    def getListAttribute(self, objRef, attribute):
        value = self.getAttribute(objRef, attribute)
        if type(value) is dict:
            return [v[0] for v in value.values()]
        elif type(value[0]) is list:
            return [v[0] for v in value]
        else:
            return value

    def help(self, objRef):
        response = self.options(self.server_url + objRef)
        children = response.json()['custom']['children']
        children_list = [c['name'] for c in children]
        attributes = response.json()['custom']['attributes']
        attributes_list = [a['name'] for a in attributes]
        operations = response.json()['custom']['operations']
        operations_list = [o['operation'] for o in operations]
        return children_list, attributes_list, operations_list

    def add(self, parent, obj_type, **attributes):
        """ IXN API add command

        @param parent: object parent - object will be created under this parent.
        @param object_type: object type.
        @param attributes: additional attributes.
        @return: STC object reference.
        """

        response = self.post(self.server_url + parent.ref + '/' + obj_type, attributes)
        return self._get_href(response.json())

    def setAttributes(self, objRef, **attributes):
        self.patch(self.server_url + objRef, attributes)

    def remapIds(self, objRef):
        return objRef

    def regenerate(self, traffic, *traffic_items):
        self.execute('generateifrequired', traffic.ref, traffic.ref)

    def startStatelessTraffic(self, traffic, traffic_items):
        self.execute('startstatelesstraffic', traffic.ref, [ti.ref for ti in traffic_items])

    def stopStatelessTraffic(self, traffic, traffic_items):
        self.execute('stopstatelesstraffic', traffic.ref, [ti.ref for ti in traffic_items])

    def _get_href(self, response_entry):
        return response_entry['links'][0]['href']
