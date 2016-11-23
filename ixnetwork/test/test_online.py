"""
IxNetwork package tests that require actual IxNetwork chassis and active ports.

These tests serve two purposes:
- Unit test for IxNetwork package.
- Code snippet showing how to work with IxNetwork package.

Test setup:
Two IXN ports connected back to back.

@author yoram@ignissoft.com
"""

import time

from ixnetwork.test.test_offline import IxnTestOffline, ixn_config_files


class IxnTestOnline(IxnTestOffline):

    ports = []

    def testReservePorts(self):
        self._load_config(self.ixn_config_file)
        self.ports = self.ixn.root.get_children('vport')
        self.ixn.root.get_object_by_name('Port 1').reserve(self.config.get('IxNetwork', 'port1'))
        self.ixn.root.get_object_by_name('Port 2').reserve(self.config.get('IxNetwork', 'port2'))
        pass

    def testReleasePorts(self):
        self.testReservePorts()
        for port in self.ports:
            port.release()
        pass

    def testInterfaces(self):
        self.testReservePorts()
        for port in self.ports:
            port.send_arp_ns()
            for interface in port.get_children('interface'):
                gateway = interface.get_child('ipv4', 'ipv6').get_attribute('gateway')
                interface.ping(gateway)
        pass

    def testProtocolsActions(self):
        self.testReservePorts()
        self.ixn.send_arp_ns()
        self.ixn.protocols_start()
        time.sleep(8)
        self.ixn.protocols_stop()
        time.sleep(8)
        self.ixn.protocol_start('ospf')
        time.sleep(8)
        self.ixn.protocol_stop('ospf')
        pass

    def testGUITraffic(self):
        self.testReservePorts()
        self.ixn.protocols_start()
        self.ixn.root.regenerate()
        self.ixn.traffic_apply()
        self.ixn.l23_traffic_start()
        time.sleep(8)
        self.ixn.l23_traffic_stop()
        pass

    def testNgpf(self):
        self.ixn_config_file = ixn_config_files[1]
        self.testReservePorts()
        topologies = self.ixn.root.get_children('topology')
        self.ixn.protocols_start()
        time.sleep(4)
        assert(topologies[0].get_attribute('status') == 'started')
        self.ixn.protocols_stop()
        time.sleep(2)
        assert(topologies[0].get_attribute('status') == 'notStarted')
        # No need to test since protocol start/stop methods will raise exception if the operation failed.
        topologies[0].start()
        topologies[1].start()
        topologies[0].stop()
        topologies[1].stop()
        device_group = topologies[0].get_child('deviceGroup')
        device_group.start()
        device_group.stop()
        ethernet = device_group.get_child('ethernet')
        ethernet.start()
        ethernet.stop()
        pass