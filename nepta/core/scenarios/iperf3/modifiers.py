import os.path

from nepta.dataformat import Section


def udp(test):
    test.udp = True
    test.bitrate = 0


def reversed_dir(test):
    test.reverse = True


def sctp(test):
    test.sctp = True


def zerocopy_mod(test):
    test.zerocopy = True


def make_alias(name, base):
    cls = type(name, (base,), {})
    return cls


def make_single_stream(name, base, modifiers):
    class Scenario(base):
        def init_test(self, path, size):
            test = super().init_test(path, size)
            for mod in modifiers:
                mod(test)
            return test

    Scenario.__name__ = name
    Scenario.__qualname__ = name
    return Scenario


def make_multi_stream(name, base, modifiers):
    class Scenario(base):
        def init_all_tests(self, path, size):
            tests = super().init_all_tests(path, size)
            for test in tests:
                for mod in modifiers:
                    mod(test)
            return tests

    Scenario.__name__ = name
    Scenario.__qualname__ = name
    return Scenario


def make_perun_single_stream(name, perun_mixin, profiler_class, base_stream, modifiers=None):
    modifiers = modifiers or []

    class Scenario(perun_mixin, base_stream):
        def init_test(self, path, size):
            iperf_test = profiler_class(
                client=path.their_ip.ip,
                bind=path.mine_ip.ip,
                time=self.test_length,
                len=size,
                interval=self.interval,
                perun_output_file=os.path.join(self.perun_directory, f'{path.id}_{size}.perf.data'),
            )
            if path.cpu_pinning:
                iperf_test.affinity = ','.join([str(x) for x in path.cpu_pinning[0]])
            elif self.cpu_pinning:
                iperf_test.affinity = ','.join([str(x) for x in self.cpu_pinning[0]])
            for mod in modifiers:
                mod(iperf_test)
            return iperf_test

        def store_instance(self, section, test):
            section.subsections.append(Section('item', key='perun_data', value=test.perun_output_file))
            return super().store_instance(section, test)

    Scenario.__name__ = name
    Scenario.__qualname__ = name
    return Scenario


def make_perun_multi_stream(name, perun_mixin, profiler_class, base_stream, modifiers=None):
    modifiers = modifiers or []

    class Scenario(perun_mixin, base_stream):
        def init_all_tests(self, path, size):
            tests = super().init_all_tests(path, size)
            test = tests.pop(0)
            perf_test = profiler_class(
                perun_output_file=os.path.join(self.perun_directory, f'{path.id}_{size}.perf.data'),
                **test.__dict__,
            )
            perf_test.time -= 1
            tests.insert(0, perf_test)
            for t in tests:
                for mod in modifiers:
                    mod(t)
            return tests

        def store_instance(self, section, tests):
            section.subsections.append(Section('item', key='perun_data', value=tests[0].perun_output_file))
            return super().store_instance(section, tests)

    Scenario.__name__ = name
    Scenario.__qualname__ = name
    return Scenario
