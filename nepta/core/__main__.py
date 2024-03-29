#!/usr/bin/python3
# coding=utf8
import sys
import importlib
import os
import argparse
import logging
import shlex
import time
import uuid
from datetime import datetime as dt
from typing import Type

from nepta.core import strategies, synchronization, model
from nepta.core.strategies.generic import CompoundStrategy
from nepta.core.distribution.env import Environment

from nepta.dataformat import Section, DataPackage

LOG_FILENAME = '/var/log/performance-network_perftest.log'
LOG_FMT = '%(asctime)s %(name)s %(levelname)s 🔥 %(message)s'

# Create root logger instance and set default logging level, output format and handler
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

LogFormatter: Type[logging.Formatter] = logging.Formatter
try:
    import coloredlogs

    LogFormatter = coloredlogs.ColoredFormatter
except ImportError:
    root_logger.warning('Cannot import "coloredlogs" package.')

# Log into STDERR - with INFO messages (will be easily displayable in Beaker
# logs due to its smaller size)
std_handler = logging.StreamHandler()
std_formatter = LogFormatter(LOG_FMT)
std_handler.setFormatter(std_formatter)
std_handler.setLevel(logging.INFO)
root_logger.addHandler(std_handler)

try:
    # Log into log file - with DEBUG messages
    file_handler = logging.FileHandler(LOG_FILENAME)
    file_formatter = LogFormatter(LOG_FMT)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
except PermissionError:
    logging.error(f'Cannot create file logger into {LOG_FILENAME}')

# Local logger instance
logger = logging.getLogger(__name__)


def get_configuration(fqdn, conf):
    conf_bundle = model.bundles.HostBundle.find(fqdn, conf)
    if conf_bundle is None:
        raise FileNotFoundError('%s configuration for host %s does not exists.' % (conf, fqdn))
    else:
        return conf_bundle


def get_synchronization(sync, conf):
    if sync == 'beaker':
        return synchronization.BeakerSynchronization()
    elif sync == 'perfqe':
        return synchronization.PerfSynchronization(conf.get_subset(model.bundles.SyncServer)[0].value)
    else:
        return synchronization.NoSynchronization()


def init_package(conf_name, start_time):
    pckg_path = '{}__{}__{}__{}__ts{}'.format(
        Environment.hostname, conf_name, Environment.distro, Environment.kernel, int(start_time)
    )
    logger.info('Creating nepta-dataformat package in : {}'.format(pckg_path))

    package = DataPackage.create(pckg_path)
    package.store.root = init_root_store()

    return package


def init_root_store():
    store_params = {'hostname': Environment.hostname, 'kernel': Environment.kernel, 'distro': Environment.distro}
    return Section('host', store_params)


def filter_conf(conf, exclude_components):
    modules_of_models = [getattr(model, x) for x in dir(model) if not x.startswith('__')]

    for class_name in exclude_components:
        for x in modules_of_models:
            if hasattr(x, class_name):
                obj = getattr(x, class_name)
                conf.filter_components(lambda x: type(x) != obj)
                break
        else:  # if no break
            logger.info("Object <\"%s\"> does not exist in models" % class_name)


def delete_subtree(conf, deleting_subtrees):
    for full_sub_tree_path in deleting_subtrees:
        current_node = conf
        tree_path = full_sub_tree_path.split('.')
        for subtree in tree_path[1:-1]:  # ignoring the first and the last node name,
            # the last name is used after for cycle
            if current_node.has_node(subtree):
                current_node = getattr(current_node, subtree)
            else:  # if there is a wrong name of subtree, end searching
                logger.info('%s sub tree was NOT found', full_sub_tree_path)
                break
        else:  # no break
            if current_node.has_node(tree_path[-1]):
                logger.info('Deleting: %s', full_sub_tree_path)
                delattr(current_node, tree_path[-1])


def create_desynchronize_strategy(strategy: CompoundStrategy, package: DataPackage) -> CompoundStrategy:
    """
    From running strategies filter Synchronization strategies and generate a new compound strategy containing
    de-synchronizations functions to prevent servers deadlock.
    :param strategy: running compound strategy
    :param package: dataformat result package
    :return: de-synchronization strategy
    """
    desync_strategy = CompoundStrategy()
    for strat in strategy.strategies:
        if isinstance(strat, strategies.sync.Synchronize):
            desync_strategy += strategies.sync.EndSyncBarriers(strat.configuration, strat.synchronizer, strat.condition)

    desync_strategy += strategies.save.save_package.Save(package)

    if Environment.in_rstrnt:
        desync_strategy += strategies.report.Report(package, result=False)
        desync_strategy += strategies.report.Abort()  # abort running job

    return desync_strategy


class ArgRangeMixin(argparse._AppendAction):
    NMIN = 1
    NMAX = 3

    def __call__(self, parser, args, values, option_string=None):
        if not self.NMIN <= len(values) <= self.NMAX:
            raise argparse.ArgumentError(
                self,
                f'Too many values "{values}! The allowed number of arguments is between {self.NMIN} and {self.NMAX}.',
            )
        super().__call__(parser, args, values, option_string)


class CheckEnvVariable(argparse._AppendAction):
    def __call__(self, parser, namespace, values, option_string=None):
        if values[0] in Environment.__dict__.keys():
            super().__call__(parser, namespace, values, option_string)
        else:
            raise argparse.ArgumentError(
                self, "Provided key \"{}\" is not defined in Environment so it cannot be overridden.".format(values[0])
            )


class RequiredLengthAppend(ArgRangeMixin, argparse._AppendAction):
    NMIN = 1
    NMAX = 2


def main():
    parser = argparse.ArgumentParser(
        description='Script for running whole network performance test suite. This test is'
        ' divided into separate phases, which take care of : setup servers,'
        'execute tests, save results. Each of these phases can be run'
        'ane by one or together according to your preferences.'
    )

    parser.add_argument(
        '-c', '--configuration', required=True, action='store', help='Specify which configuration is going to be run.'
    )

    # phase arguments
    parser.add_argument('--setup', action='store_true', help='[phase] Setup server for test.')
    parser.add_argument('--prepare', action='store_true', help='[phase] Prepare non-persistent settings before test.')
    parser.add_argument('--execute', action='store_true', help='[phase] Run test scenarios.')
    parser.add_argument(
        '--store', action='store_true', help='[phase] Save test results and meta variables into dataformat package'
    )
    parser.add_argument(
        '--store-logs',
        action='store_true',
        help='[phase] Save additional logs from testing server into dataformat package.',
    )
    parser.add_argument(
        '--store-remote-logs',
        action='store_true',
        help='[phase] Save additional logs from remote testing servers into dataformat package.',
    )
    parser.add_argument('--submit', action='store_true', help='[phase] Send dataformat package into result server.')

    # additional arguments
    parser.add_argument(
        '-e',
        '--environment',
        nargs=2,
        action=CheckEnvVariable,
        metavar=('ENV', 'VAR'),
        help='Override Environment object attribute with provided value.',
    )
    parser.add_argument(
        '--sync',
        choices=['beaker', 'perfqe', 'none'],
        action='store',
        default='none',
        help='Specify synchronization method used before and after test execution ' '[Default: %(default)s].',
    )
    parser.add_argument(
        '-s', '--scenario', dest='scenarios', action='append', type=str, help='Run only specified scenario.'
    )
    parser.add_argument(
        '-l',
        '--log',
        action='store',
        type=str.upper,
        help='Logging level [Default: %(default)s].',
        choices=['DEBUG', 'WARNING', 'INFO', 'ERROR', 'EXCEPTION'],
        default='INFO',
    )
    parser.add_argument(
        '--meta',
        nargs=2,
        action='append',
        metavar=('KEY', 'VALUE'),
        default=[],
        help='Append meta variables into package.',
    )
    parser.add_argument(
        '-f',
        '--filter',
        action='append',
        metavar='FILTERED_CLASS',
        help='Filter current configuration of these model object types.',
    )
    parser.add_argument(
        '-d',
        '--delete-tree',
        action='append',
        metavar='SUBTREE_PATH',
        help='Specify which sub-tree of configuration tree will be deleted.',
    )
    parser.add_argument(
        '-p', '--print', action='store_true', help='Print current configuration in tree format and exit.'
    )
    parser.add_argument(
        '-i',
        '--import',
        dest='imp',
        action=RequiredLengthAppend,
        nargs='+',
        metavar=('MODULE_NAME', 'PATH'),
        help='Dynamically import python modules with optional path.',
    )
    parser.add_argument(
        '-t',
        '--tag',
        action='append',
        help='Filter testing paths by specifying HW or SW tag. Only paths with specified tag will be tested.',
    )
    parser.add_argument(
        '--pcp',
        action='store_true',
        help='Enable PCP logging during testing.',
        default=False,
    )
    parser.add_argument(
        '--remote-pcp',
        action='store_true',
        help='Enable PCP logging during testing on remote machines.',
        default=False,
    )

    # Highest priority have arguments directly given from the commandline.
    # If no argument is given, we try to parse NETWORK_PERFTEST_ARGS environment
    # variable. If this variable does not exist, we use default arguments.
    if len(sys.argv) > 1:
        logger.info('we use parameters given from the command line')
        args = parser.parse_args()
    elif 'NETWORK_PERFTEST_ARGS' in os.environ.keys():
        logger.info('we use parameters loaded from NETWORK_PERFTEST_ARGS environment variable')
        cmdline_args = shlex.split(os.environ['NETWORK_PERFTEST_ARGS'])
        args = parser.parse_args(cmdline_args)
    else:
        logger.warning('no parameters were given, using default configuration')
        args = parser.parse_args()

    # setting log level
    std_handler.setLevel(args.log)

    # import modules defined on CLI
    if args.imp:
        for arg in args.imp:
            module = arg[0]
            if len(arg) == 1:
                logger.info(f'Importing {module}')
                importlib.import_module(module)
            else:
                path = arg[1]
                sys.path.insert(0, path)
                logger.info(f'Importing {module} from {path}')
                importlib.import_module(module)
                sys.path.pop(0)

    # overriding environments
    if args.environment:
        for k, v in args.environment:
            setattr(Environment, k, v)

    timestamp = time.time()
    conf = get_configuration(Environment.fqdn, args.configuration)
    sync = get_synchronization(args.sync, conf)
    package = init_package(args.configuration, timestamp)
    final_strategy = CompoundStrategy()

    if args.filter:
        filter_conf(conf, args.filter)

    if args.delete_tree:
        delete_subtree(conf, args.delete_tree)

    if not (args.pcp or args.remote_pcp):
        conf.filter_components(lambda x: type(x) != model.system.PCPConfiguration)

    if args.print:
        print(conf.str_tree())
        return

    extra_meta = {
        'DateTime': dt.utcfromtimestamp(int(timestamp)),
        'UUID': uuid.uuid4(),
    }
    extra_meta.update(args.meta)

    logger.info('Ours environment is:\n%s' % Environment)
    logger.info('Our configuration:\n%s' % conf)

    # preparing server for test without logging meta and report, which will be logged in the end of test
    if args.setup:
        # ugly WA for linux bridge
        if args.configuration == 'LinuxBridge':
            strategies.setup.Network = strategies.setup.network.OldNetwork
        final_strategy += strategies.setup.get_strategy(conf)

    if args.prepare:
        final_strategy += strategies.prepare.Prepare(conf)

    # Run test code path, saving attachments only if running test
    if args.execute:
        final_strategy += strategies.sync.Synchronize(conf, sync, 'ready')

        if args.pcp or args.remote_pcp:
            final_strategy += strategies.run.RunScenariosPCP(
                conf,
                package,
                args.scenarios,
                args.tag,
                args.pcp,
                args.remote_pcp,
            )
        else:
            final_strategy += strategies.run.RunScenarios(conf, package, args.scenarios, args.tag)

        final_strategy += strategies.sync.Synchronize(conf, sync, 'done')

    if args.store:
        final_strategy += strategies.save.meta.SaveMeta(conf, package, extra_meta)

    if args.store_logs:
        final_strategy += strategies.save.attachments.SaveAttachments(conf, package)

    # store dataformat package
    final_strategy += strategies.save.save_package.Save(package)

    final_strategy += strategies.sync.Synchronize(conf, sync, 'log')

    if args.store_remote_logs:
        final_strategy += strategies.save.save_package.OpenRemotePackages(package)
        final_strategy += strategies.save.logs.RemoteLogs(conf, package)
        final_strategy += strategies.save.save_package.SaveRemotePackages(package)

    # submit results to result server
    if args.submit:
        final_strategy += strategies.submit.ReliableSubmit(conf, package)

    # in the end of test tell beaker the test has PASSED
    if Environment.in_rstrnt:
        final_strategy += strategies.report.Report(package, final_strategy)

    final_strategy += strategies.sync.Synchronize(conf, sync, 'finished')

    try:
        final_strategy()
    except BaseException as e:
        logger.error('Error occurred during strategy execution.')
        logger.error(e)
        logger.warning('Setting pass to all barriers and aborting execution.')
        desync = create_desynchronize_strategy(final_strategy, package)
        desync()
        raise e

    result = True
    for strategy in final_strategy.strategies:
        if isinstance(strategy, strategies.run.RunScenarios):
            result &= strategy.aggregated_result

    logger.info('bye bye world...')
    return not result  # reversed logic -> 0 is OK, 1 is FAIL


if __name__ == '__main__':
    sys.exit(main())
