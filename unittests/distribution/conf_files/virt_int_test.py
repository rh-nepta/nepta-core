from unittest import TestCase
from xml_diff import compare
import lxml.etree

from nepta.core.model.system import VirtualGuest
from nepta.core.model.network import OVSGuestTap, OVSGuestVlanTap, BridgeGuestTap, OVSwitch, LinuxBridge
from nepta.core.distribution.conf_files import GuestTap


class TapTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guest = VirtualGuest('guest1')
        self.ovs = OVSwitch('ovs1')
        self.br = LinuxBridge('br1')
        self.maxDiff = None

    def assertEqualXML(self, xml1, xml2):
        et1 = lxml.etree.fromstring(xml1)
        et2 = lxml.etree.fromstring(xml2)
        return compare(et1, et2)

    def test_ovs_tap(self):
        tap1 = OVSGuestTap(self.guest, self.ovs, '00:00:00:11:11:11')
        tap1_file = GuestTap(tap1)

        expected_out = """\
            <interface type='bridge'>
              <mac address='%s'/>
              <source bridge='%s'/>
              <model type='virtio'/>
              <virtualport type='openvswitch'>
              </virtualport>
            </interface>
            """ % (
            tap1.mac,
            self.ovs.name,
        )
        self.assertEqualXML(expected_out, tap1_file._make_content())

    def test_ovs_vlan_tap(self):
        tap1 = OVSGuestVlanTap(self.guest, self.ovs, '88:00:00:11:11:11', 20)
        tap1_file = GuestTap(tap1)

        expected_out = """\
            <interface type='bridge'>
              <mac address='%s'/>
              <source bridge='%s'/>
              <model type='virtio'/>
              <virtualport type='openvswitch'>
              </virtualport>
              <vlan>
                <tag id='20'/>
              </vlan>
            </interface>
            """ % (
            tap1.mac,
            self.ovs.name,
        )
        self.assertEqualXML(expected_out, tap1_file._make_content())

    def test_bridge_tap(self):
        tap1 = BridgeGuestTap(self.guest, self.br, '00:99:00:11:11:11')
        tap1_file = GuestTap(tap1)

        expected_out = """\
            <interface type='bridge'>
              <mac address='%s'/>
              <source bridge='%s'/>
              <model type='virtio'/>
            </interface>
            """ % (
            tap1.mac,
            self.br.name,
        )
        self.assertEqualXML(expected_out, tap1_file._make_content())
