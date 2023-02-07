from unittest import TestCase, skip
from nepta.core.model import bundles, network, system, attachments
import ipaddress as ia


class TestBundles(TestCase):
    def test_budnle_variables(self):
        host = 'popicci.server.u.nas'
        conf = 'LetNaMesiac'
        host_b = bundles.HostBundle(host, conf)

        self.assertEqual(host, host_b.get_hostname())
        self.assertEqual(conf, host_b.get_conf_name())

    def test_simple_add_bundles(self):
        b1 = bundles.Bundle()
        sys1 = system.Package('tcpdump')
        net1 = network.LinuxBridge('br1')
        b1.add_component(sys1)
        b1.br1 += net1

        self.assertIn(sys1, b1)
        self.assertIn(net1, b1)

        b2 = bundles.Bundle()
        sys2 = system.Package('wget')
        net2 = network.EthernetInterface('eth1', '00:11:22:33:44:55')
        b2.add_multiple_components(sys2, net2)

        self.assertIn(sys2, b2)
        self.assertIn(net2, b2)

        b3 = b1 + b2
        self.assertIsInstance(b3, bundles.Bundle)
        self.assertIsNot(b1, b3)
        self.assertIsNot(b2, b3)

        b1 += b2
        self.assertIn(sys1, b1)
        self.assertIn(sys2, b1)
        self.assertIn(net1, b1)
        self.assertIn(net2, b1)
        self.assertNotIn(net1, b2)
        self.assertNotIn(sys1, b2)

    def test_simple_add_hostbundles(self):
        b1 = bundles.HostBundle('db.server.com', 'NIC')
        sys1 = system.Package('tcpdump')
        net1 = network.LinuxBridge('br1')
        b1.add_component(sys1)
        b1 += net1

        self.assertIn(sys1, b1)
        self.assertIn(net1, b1)

        b2 = bundles.HostBundle('net.server.com', 'NIC')
        sys2 = system.Package('wget')
        net2 = network.EthernetInterface('eth1', '00:11:22:33:44:55')
        b2.add_multiple_components(sys2, net2)

        self.assertIn(sys2, b2)
        self.assertIn(net2, b2)

        b3 = b1 + b2
        self.assertIsInstance(b3, bundles.Bundle)
        self.assertIsNot(b1, b3)
        self.assertIsNot(b2, b3)

        b1 += b2
        self.assertIn(sys1, b1)
        self.assertIn(sys2, b1)
        self.assertIn(net1, b1)
        self.assertIn(net2, b1)
        self.assertNotIn(net1, b2)
        self.assertNotIn(sys1, b2)

    def test_bundle_basic_iterator(self):
        b1 = bundles.Bundle()

        sys1 = system.Package('wget')
        sys2 = system.Repository('epel', 'http://internet.com')
        sys3 = system.SystemService('network')

        net1 = network.EthernetInterface('eth1', '00:11:22:33:44:55:66')
        net2 = network.EthernetInterface('eth1', '00:11:22:33:44:55:66')
        net3 = network.TeamMasterInterface('team1')

        b1.add_multiple_components(sys1, sys2, sys3, net1, net2, net3)
        ordered_items = [sys1, sys2, sys3, net1, net2, net3]

        for tested, verify in zip(ordered_items, b1):
            self.assertIs(tested, verify)

    def test_new_hierarchical_bundles(self):
        sys1 = system.Package('wget')
        sys2 = system.Repository('epel', 'http://internet.com')
        sys3 = system.SystemService('network')

        net1 = network.EthernetInterface('eth1', '00:11:22:33:44:55:66')
        net2 = network.EthernetInterface('eth1', '00:11:22:33:44:55:66')
        net3 = network.TeamMasterInterface('team1')

        main_bundle = bundles.Bundle()
        main_bundle.add_multiple_components(sys1, net1)

        net_bundle = bundles.Bundle().add_multiple_components(net2, net3)
        sys_bundle = bundles.Bundle()
        sys_bundle.sys2 = sys2
        sys_bundle.sys3 = sys3

        main_bundle.intf = net_bundle
        main_bundle.sys = sys_bundle

        self.assertEqual(main_bundle.intf, net_bundle)
        self.assertEqual(main_bundle.sys, sys_bundle)

        test_items = [sys1, sys2, sys3, net1, net2, net3]
        for item in main_bundle:
            self.assertIn(item, test_items, 'There are more objects than is specified.')

        for item in test_items:
            self.assertIn(item, main_bundle.get_all_components(), 'There are missing some specified objects.')

        self.assertIs(sys2, main_bundle.sys.sys2, 'Cannot access correct model.')
        self.assertIs(sys3, main_bundle.sys.sys3, 'Cannot access correct model.')
        self.assertEqual(len(main_bundle), len(test_items), 'There are more/less models than shoudl be!')

    def test_cycle_in_hierarchical_bundles(self):
        sys1 = system.Package('wget')
        sys2 = system.Repository('epel', 'http://internet.com')
        sys3 = system.SystemService('network')

        p1 = system.Package('python3')
        p2 = system.Package('gcc')

        a1 = attachments.Command('ip l')
        a2 = attachments.Directory('/var/')

        net1 = network.EthernetInterface('eth1', '00:11:22:33:44:55:66')
        net2 = network.EthernetInterface('eth2', '00:11:22:33:44:55:67')
        net3 = network.EthernetInterface('eth3', '00:11:22:33:44:55:68')
        net4 = network.EthernetInterface('eth4', '00:11:22:33:44:55:69')

        net5 = network.TeamMasterInterface('team1')
        net6 = network.TeamMasterInterface('team1')

        main_bundle = bundles.Bundle()
        main_bundle.add_multiple_components(sys1)

        intf_bundle = bundles.Bundle().add_multiple_components(net1, net2, net3, net4)
        team_master_bundle = bundles.Bundle().add_multiple_components(net5, net6)
        sys_bundle = bundles.Bundle().add_multiple_components(sys2, sys3)

        # creating tree of bundles
        pckg_bundle = bundles.Bundle().add_multiple_components(p1, p2)
        attch_bundle = bundles.Bundle().add_multiple_components(a1, a2)
        sys_bundle.pckg = pckg_bundle
        sys_bundle.attch = attch_bundle

        main_bundle.intf = intf_bundle
        main_bundle.team_master = team_master_bundle
        main_bundle.sys = sys_bundle

        # creating bypass
        team_master_bundle.intf = intf_bundle

        # creating cycle
        intf_bundle.team = team_master_bundle

        # creating cycle to tree root
        attch_bundle.main = main_bundle

        # verify !!
        test_items = [sys1, sys2, sys3, p1, p2, a1, a2, net1, net2, net3, net4, net5, net6]

        self.assertEqual(len(main_bundle), len(test_items), 'There are more/less models than shoudl be!')
        for item in main_bundle:
            self.assertIn(item, test_items, 'There are more objects than is specified.')

        for item in test_items:
            self.assertIn(item, main_bundle.get_all_components(), 'There are missing some specified objects.')

    def test_override_bundle(self):
        sys1 = system.Package('wget')
        sys2 = system.Repository('epel', 'http://internet.com')
        sys3 = system.SystemService('network')

        sys4 = system.Package('ip')
        sys5 = system.Repository('epel-universe', 'http://internet.com')
        sys6 = system.SystemService('NetworkManager')

        net1 = network.EthernetInterface('eth1', '00:11:22:33:44:55:66')
        net2 = network.EthernetInterface('eth1', '00:11:22:33:44:55:66')
        net3 = network.TeamMasterInterface('team1')

        main_bundle = bundles.Bundle()
        main_bundle.add_multiple_components(sys1, net1)

        net_bundle = bundles.Bundle().add_multiple_components(net2, net3)
        sys_bundle = bundles.Bundle().add_multiple_components(sys2, sys3)
        new_sys_bundle = bundles.Bundle().add_multiple_components(sys4, sys5, sys6)

        main_bundle.intf = net_bundle
        main_bundle.sys = sys_bundle

        # Overwriting original sys bundle
        main_bundle.sys = new_sys_bundle

        test_items = [sys1, sys4, sys5, sys6, net1, net2, net3]
        for item in main_bundle:
            self.assertIn(item, test_items, 'There are more objects than is specified.')

        for item in test_items:
            self.assertIn(item, main_bundle.get_all_components(), 'There are missing some specified objects.')

    def test_delete_local_bundle(self):
        sys1 = system.Package('wget')
        sys2 = system.Repository('epel', 'http://internet.com')
        sys3 = system.SystemService('network')

        net1 = network.EthernetInterface('eth1', '00:11:22:33:44:55:66')
        net2 = network.EthernetInterface('eth1', '00:11:22:33:44:55:66')
        net3 = network.TeamMasterInterface('team1')

        main_bundle = bundles.Bundle()
        main_bundle.add_multiple_components(sys1, net1)

        net_bundle = bundles.Bundle().add_multiple_components(net2, net3)
        sys_bundle = bundles.Bundle().add_multiple_components(sys2, sys3)

        main_bundle.intf = net_bundle
        main_bundle.sys = sys_bundle
        main_bundle.sys2 = sys_bundle

        test_items = [sys1, net1, net2, net3]
        main_bundle.sys = sys_bundle
        del main_bundle.sys
        del main_bundle.sys2

        self.assertNotIn(sys_bundle, main_bundle._parents)
        self.assertNotIn(sys_bundle, main_bundle._bundles.values())

        for item in main_bundle:
            self.assertIn(item, test_items, 'There are more objects than is specified.')

        for item in test_items:
            self.assertIn(item, main_bundle.get_all_components(), 'There are missing some specified objects.')

    def test_bundle_flush(self):
        sys1 = system.Package('wget')
        sys2 = system.Repository('epel', 'http://internet.com')
        sys3 = system.SystemService('network')

        net1 = network.EthernetInterface('eth1', '00:11:22:33:44:55:66')
        net2 = network.EthernetInterface('eth1', '00:11:22:33:44:55:66')
        net3 = network.TeamMasterInterface('team1')

        main_bundle = bundles.Bundle()
        main_bundle.add_multiple_components(sys1, net1)

        net_bundle = bundles.Bundle().add_multiple_components(net2, net3)
        sys_bundle = bundles.Bundle().add_multiple_components(sys2, sys3)

        main_bundle.intf = net_bundle
        main_bundle.sys = sys_bundle

        # delete all components
        main_bundle.flush_components()

        self.assertEqual(len(main_bundle), 0)

    def test_filter(self):
        sys1 = system.Package('wget')
        sys2 = system.Repository('epel', 'http://internet.com')
        sys3 = system.SystemService('network')

        p1 = system.Package('python3')
        p2 = system.Package('gcc')

        a1 = attachments.Command('ip l')
        a2 = attachments.Directory('/var/')

        net1 = network.EthernetInterface('eth1', '00:11:22:33:44:55:66')
        net2 = network.EthernetInterface('eth2', '00:11:22:33:44:55:67')
        net3 = network.EthernetInterface('eth3', '00:11:22:33:44:55:68')
        net4 = network.EthernetInterface('eth4', '00:11:22:33:44:55:69')

        net5 = network.TeamMasterInterface('team1')
        net6 = network.TeamMasterInterface('team1')

        r1 = network.Route4(ia.IPv4Network('10.0.0.0/24'), net5, ia.IPv4Address('8.8.8.8'))
        r2 = network.Route4(ia.IPv4Network('10.1.0.0/24'), net6, ia.IPv4Address('8.8.8.8'))
        r3 = network.Route4(ia.IPv4Network('10.2.0.0/24'), net6, ia.IPv4Address('8.8.8.8'))

        main_bundle = bundles.Bundle()
        main_bundle.add_multiple_components(sys1)

        intf_bundle = bundles.Bundle().add_multiple_components(net1, net2, net3, net4)
        team_master_bundle = bundles.Bundle()
        team_master_bundle.team0 = net5
        team_master_bundle.team1 = net6
        sys_bundle = bundles.Bundle().add_multiple_components(sys2, sys3)
        route_bundle = bundles.Bundle().add_multiple_components(r1, r2)
        route_bundle.r2 = [r3]

        # creating tree of bundles
        pckg_bundle = bundles.Bundle().add_component(p1)
        pckg_bundle.p2 = p2
        attch_bundle = bundles.Bundle().add_multiple_components(a1, a2)
        sys_bundle.pckg = pckg_bundle
        sys_bundle.attch = attch_bundle

        main_bundle.intf = intf_bundle
        main_bundle.team_master = team_master_bundle
        main_bundle.sys = sys_bundle
        main_bundle.routes = route_bundle

        # creating bypass
        team_master_bundle.intf = intf_bundle

        # creating cycle
        intf_bundle.team = team_master_bundle

        test_interfaces = [net1, net2, net3, net4, net5, net6]
        interfaces = main_bundle.get_subset(m_class=network.Interface)
        test_pckgs = [sys1, p1, p2]
        pckgs = main_bundle.get_subset(m_type=system.Package)
        routes = main_bundle.get_subset(m_class=network.Route4)

        self.assertIsNot(main_bundle.intf, interfaces.intf, 'Deep copy uses shallow copy in subtrees.')
        self.assertIsNot(main_bundle.sys.pckg, pckgs.sys.pckg, 'Deep copy uses shallow copy in subtrees.')
        self.assertIn(net1, interfaces.intf, 'Tree has different structure.')
        self.assertIn(p1, pckgs.sys.pckg, 'Tree has different structure.')

        for item in interfaces:
            self.assertIn(item, test_interfaces, 'There are more objects than is specified.')

        for item in test_interfaces:
            self.assertIn(item, interfaces.get_all_components(), 'There are missing some specified objects.')

        for item in pckgs:
            self.assertIn(item, test_pckgs, 'There are more objects than is specified.')

        for item in test_pckgs:
            self.assertIn(item, pckgs.get_all_components(), 'There are missing some specified objects.')

        for route in [r1, r2, r3]:
            self.assertIn(route, routes, f'{route} is missing in configuration bundle')

    def test_filter_exclude(self):
        sys1 = system.Package('wget')
        sys2 = system.Repository('epel', 'http://internet.com')
        sys3 = system.SystemService('network')

        p1 = system.Package('python3')
        p2 = system.Package('gcc')

        a1 = attachments.Command('ip l')
        a2 = attachments.Directory('/var/')

        net1 = network.EthernetInterface('eth1', '00:11:22:33:44:55:66')
        net2 = network.EthernetInterface('eth2', '00:11:22:33:44:55:67')
        net3 = network.EthernetInterface('eth3', '00:11:22:33:44:55:68')
        net4 = network.EthernetInterface('eth4', '00:11:22:33:44:55:69')

        net5 = network.TeamMasterInterface('team1')
        net6 = network.TeamMasterInterface('team1')

        main_bundle = bundles.Bundle()
        main_bundle.add_multiple_components(sys1)

        intf_bundle = bundles.Bundle().add_multiple_components(net1, net2, net3, net4)
        team_master_bundle = bundles.Bundle()
        team_master_bundle.team0 = net5
        team_master_bundle.team1 = net6
        sys_bundle = bundles.Bundle().add_multiple_components(sys2, sys3)

        # creating tree of bundles
        pckg_bundle = bundles.Bundle().add_component(p1)
        pckg_bundle.p2 = p2
        attch_bundle = bundles.Bundle().add_multiple_components(a1, a2)
        sys_bundle.pckg = pckg_bundle
        sys_bundle.attch = attch_bundle

        main_bundle.intf = intf_bundle
        main_bundle.team_master = team_master_bundle
        main_bundle.sys = sys_bundle

        # creating bypass
        team_master_bundle.intf = intf_bundle

        # creating cycle
        intf_bundle.team = team_master_bundle

        test_interfaces = [net1, net2, net3, net4, net5, net6]
        main_withou_intf = main_bundle.get_subset(m_class=network.Interface, exclude=True)
        test_pckgs = [sys1, p1, p2]
        without_pckgs = main_bundle.get_subset(m_type=system.Package, exclude=True)

        self.assertIsNot(main_bundle.intf, main_withou_intf.intf, 'Deep copy uses shallow copy in subtrees.')
        self.assertIsNot(main_bundle.sys.pckg, without_pckgs.sys.pckg, 'Deep copy uses shallow copy in subtrees.')

        for item in main_withou_intf:
            self.assertNotIn(item, test_interfaces, 'There are more objects than is specified.')

        for item in test_interfaces:
            self.assertNotIn(item, main_withou_intf.get_all_components(), 'There are wrong objects.')
            self.assertIn(item, without_pckgs.get_all_components(), 'There are missing some specified objects.')

        for item in without_pckgs:
            self.assertNotIn(item, test_pckgs, 'There are more objects than is specified.')

        for item in test_pckgs:
            self.assertNotIn(item, without_pckgs.get_all_components(), 'There are wrongobjects.')
            self.assertIn(item, main_withou_intf.get_all_components(), 'There are missing some specified objects.')

    def test_clone_bundle(self):
        b = bundles.Bundle()
        b.packages.wget = system.Package('wget')
        b.packages.iperf3 = system.Package('iperf3')
        b.int1 = network.Interface('igb0')
        b += network.Interface('igb1')

        clone = b.clone()

        self.assertNotEqual(id(b), id(clone))
        self.assertNotEqual(id(b.packages), id(clone.packages))
        self.assertNotEqual(id(b.packages.wget), id(clone.packages.wget))
        self.assertNotEqual(id(b.packages.iperf3), id(clone.packages.iperf3))
        self.assertNotEqual(id(b.int1), id(clone.int1))
        self.assertNotEqual(id(b[0]), id(clone[0]))


class TestMergeBundles(TestCase):
    def test_merge_no_key_over_lap(self):
        b1 = bundles.Bundle()

        b1.intf.eth0 = network.EthernetInterface('eth0', '00:00:00:00:00:00')
        b1.intf.eth1 = network.EthernetInterface('eth1', '00:00:00:00:00:00')

        b1.intf.master.team0 = network.TeamMasterInterface('team0')
        b1.intf.slave.slave0 = network.TeamChildInterface(b1.intf.eth0)
        b1.intf.slave.slave1 = network.TeamChildInterface(b1.intf.eth1)

        b1.virt.guests.guest0 = system.VirtualGuest('guest0')
        p0 = system.Package('libvirt')
        p1 = system.Package('qemu-kvm')
        b1.virt.pkgs = bundles.Bundle().add_multiple_components(*[p0, p1])

        b2 = bundles.Bundle()
        b2.repo.ovs = system.Repository('ovs', 'https://ovs.repo')
        b2.attch.url.google = attachments.Url('www.google.com')
        b2.attch.url.dsl = attachments.Url('www.dsl.sk')
        b2.attch.cmd.ipx = attachments.Command('ip x sta')
        cmd1 = attachments.Command('ip l')
        b2.attch.cmd.add_component(cmd1)

        b3 = b1 + b2

        self.assertTrue(hasattr(b3, 'intf'))
        self.assertTrue(hasattr(b3, 'virt'))
        self.assertTrue(hasattr(b3, 'attch'))
        self.assertTrue(hasattr(b3, 'repo'))

        self.assertIsNot(b3.intf, b1.intf)
        self.assertIsNot(b3.virt, b1.virt)
        self.assertIsNot(b3.repo, b2.repo)
        self.assertIsNot(b3.attch, b2.attch)

        self.assertEqual(b1.intf.eth0, b3.intf.eth0)
        self.assertEqual(b2.attch.url.dsl, b3.attch.url.dsl)

        self.assertIn(p0, b3)
        self.assertIn(p1, b3)
        self.assertIn(cmd1, b3)

        for model in b1:
            self.assertIn(model, b3)

        for model in b2:
            self.assertIn(model, b3)

        b1 += b2

        self.assertTrue(hasattr(b1, 'attch'))
        self.assertTrue(hasattr(b1, 'repo'))

        self.assertIsNot(b1.repo, b2.repo)
        self.assertIsNot(b1.attch, b2.attch)

        self.assertEqual(b1.attch.url.dsl, b3.attch.url.dsl)
        self.assertIn(cmd1, b1)

        for model in b2:
            self.assertIn(model, b1)

    def test_add_merge_with_key_over_lap(self):
        b2 = bundles.Bundle()
        b2.repo.ovs = system.Repository('ovs', 'https://ovs.repo')
        b2.attch.url.google = attachments.Url('www.google.com')
        b2.attch.url.dsl = attachments.Url('www.dsl.sk')
        b2.attch.cmd.ipx = attachments.Command('ip x sta')
        cmd1 = attachments.Command('ip l')
        b2.attch.cmd.add_component(cmd1)

        b3 = bundles.Bundle()
        b3.repo.brctl = system.Repository('brctl', 'https://brctl.com')
        b3.attch.dir.dir1 = attachments.Directory('/var/log/')
        b3.attch.dir.dir2 = attachments.Directory('/etc/sysconfig/')
        b3.attch.file.file1 = attachments.File('.bashrc')
        f2 = attachments.File('/bool/config')
        b3.attch.file.add_component(f2)

        b4 = b2 + b3
        self.assertTrue(hasattr(b4, 'attch'))
        self.assertTrue(hasattr(b4, 'repo'))
        self.assertTrue(hasattr(b4.attch, 'dir'))
        self.assertTrue(hasattr(b4.attch, 'url'))

        for model in b2:
            self.assertIn(model, b4)
        for model in b3:
            self.assertIn(model, b4)

        b2 += b3
        self.assertTrue(hasattr(b2.attch, 'dir'))
        self.assertTrue(hasattr(b2.attch, 'file'))

        for model in b3:
            self.assertIn(model, b2)

    def test_add_merge_with_key_over_lap_recursive(self):
        b2 = bundles.Bundle()
        b2.repo.ovs = system.Repository('ovs', 'https://ovs.repo')
        b2.attch.url.google = attachments.Url('www.google.com')
        b2.attch.url.dsl = attachments.Url('www.dsl.sk')
        b2.attch.cmd.ipx = attachments.Command('ip x sta')
        cmd1 = attachments.Command('ip l')
        b2.attch.cmd.add_component(cmd1)

        b3 = bundles.Bundle()
        b3.repo.brctl = system.Repository('brctl', 'https://ovs.repo')
        b3.attch.url.dennik = attachments.Url('www.dennikn.com')
        b3.attch.url.fb = attachments.Url('www.facebook.sk')
        b3.attch.cmd.lsmod = attachments.Command('lsmod')
        cmd2 = attachments.Command('ip a')
        b3.attch.cmd.add_component(cmd2)

        b4 = b2 + b3
        self.assertTrue(hasattr(b4, 'attch'))
        self.assertTrue(hasattr(b4, 'repo'))
        self.assertTrue(hasattr(b4.attch, 'url'))
        self.assertTrue(hasattr(b4.attch, 'cmd'))

        for model in b2:
            self.assertIn(model, b4)
        for model in b3:
            self.assertIn(model, b4)

        b2 += b3
        self.assertTrue(hasattr(b2.attch, 'url'))
        self.assertTrue(hasattr(b2.attch, 'cmd'))

        for model in b3:
            self.assertIn(model, b2)

    def test_add_merge_various_combination(self):
        b2 = bundles.Bundle()
        b2.repo.ovs = system.Repository('ovs', 'https://ovs.repo')
        b2.attch.url.google = attachments.Url('www.google.com')
        b2.attch.url.dsl = attachments.Url('www.dsl.sk')
        b2.attch.cmd.ipx = attachments.Command('ip x sta')
        cmd1 = attachments.Command('ip l')
        b2.attch.cmd.add_component(cmd1)
        # b2.attch.cmd.root = b2

        b3 = bundles.Bundle()
        b3.repo.brctl = system.Repository('brctl', 'https://brctl.com')
        b3.attch.dir.dir1 = attachments.Directory('/var/log/')
        b3.attch.dir.dir2 = attachments.Directory('/etc/sysconfig/')
        b3.attch.file.file1 = attachments.File('.bashrc')
        f2 = attachments.File('/bool/config')
        b3.attch.file.add_component(f2)
        b3.attch.url.dennik = attachments.Url('www.dennikn.com')
        b3.attch.url.fb = attachments.Url('www.facebook.sk')
        b3.attch.cmd.lsmod = attachments.Command('lsmod')
        cmd2 = attachments.Command('ip a')
        b3.attch.cmd.add_component(cmd2)
        # b3.attch.cmd.root = b3

        b4 = b2 + b3
        self.assertTrue(hasattr(b4, 'attch'))
        self.assertTrue(hasattr(b4, 'repo'))
        self.assertTrue(hasattr(b4.attch, 'dir'))
        self.assertTrue(hasattr(b4.attch, 'url'))

        for model in b2:
            self.assertIn(model, b4)
        for model in b3:
            self.assertIn(model, b4)

        b2 += b3
        self.assertTrue(hasattr(b2.attch, 'dir'))
        self.assertTrue(hasattr(b2.attch, 'file'))

        for model in b3:
            self.assertIn(model, b2)

    def test_raise_exception(self):
        b2 = bundles.Bundle()
        b2.repo.ovs = system.Repository('ovs', 'https://ovs.repo')
        b2.attch.url.google = attachments.Url('www.google.com')
        b2.attch.url.dsl = attachments.Url('www.dsl.sk')
        b2.attch.cmd.ipx = attachments.Command('ip x sta')

        b3 = bundles.Bundle()
        b3.repo.ovs = system.Repository('ovs', 'https://ovs.repo')
        b3.attch.url.google = attachments.Url('www.google.com')
        b3.attch.url.dsl = attachments.Url('www.dsl.sk')
        b3.attch.cmd.ipx = attachments.Command('ip x sta')

        try:
            b2 + b3
        except bundles.MergeBundleException:
            pass
        else:  # if exception is not raised
            raise AssertionError

        try:
            b2 += b3
        except bundles.MergeBundleException:
            pass
        else:  # if exception is not raised
            raise AssertionError

    # @skip
    def test_print(self):
        b2 = bundles.Bundle()
        b2.repo.ovs = system.Repository('ovs', 'https://ovs.repo')
        b2.attch.url.google = attachments.Url('www.google.com')
        b2.attch.url.dsl = attachments.Url('www.dsl.sk')
        b2.attch.cmd.ipx = attachments.Command('ip x sta')

        net1 = network.EthernetInterface('eth1', '00:11:22:33:44:55:66')
        net2 = network.EthernetInterface('eth2', '00:11:22:33:44:55:67')
        net3 = network.EthernetInterface('eth3', '00:11:22:33:44:55:68')
        net4 = network.EthernetInterface('eth4', '00:11:22:33:44:55:69')

        net5 = network.EthernetInterface('eth5', '01:11:22:33:44:55:66')
        net6 = network.EthernetInterface('eth6', '01:11:22:33:44:55:67')
        net7 = network.EthernetInterface('eth7', '01:11:22:33:44:55:68')
        net8 = network.EthernetInterface('eth8', '01:11:22:33:44:55:69')

        team0 = network.TeamMasterInterface('team1')
        team1 = network.TeamMasterInterface('team1')

        intf_bundle = bundles.Bundle().add_multiple_components(net1, net2, net3)
        intf_bundle.net4 = net4
        team_master_bundle = bundles.Bundle()
        team_master_bundle.team0 = team0
        team_master_bundle.team1 = team1

        b2.intf = intf_bundle
        b2.intf.nontest = [net5, net6, net7, net8]
        b2.intf.team = team_master_bundle
        b2.intf.team.rooot = b2

        print()
        print(b2.str_tree())


class TestSyncHost(TestCase):
    def test_sync_all(self):
        st = 'sync_host'
        h1 = bundles.HostBundle('h1', 'SDF')
        h2 = bundles.HostBundle('h2', 'SDF')
        h3 = bundles.HostBundle('h3', 'SDF')

        bundles.SyncHost.sync_all(h1, h2, h3, subtree=st)

        self.assertEqual(len(getattr(h1, st)), 2)
        self.assertEqual(len(getattr(h2, st)), 2)

        self.assertIsInstance(getattr(h3, st)[0], bundles.SyncHost)
        self.assertIsInstance(getattr(h3, st)[1], bundles.SyncHost)
