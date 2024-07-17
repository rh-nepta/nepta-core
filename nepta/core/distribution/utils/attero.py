import logging

logger = logging.getLogger(__name__)

try:
    import atteroctl
except ImportError:
    logger.error("Pyattero library is not available in the system. Attero component cannot be used.")

    class Null(object):
        def __getattribute__(self, item):
            raise ImportError(
                "Attero library is not imported. If you want to use Attero component, " "install pyattero library."
            )

    atteroctl = Null()


class Attero(object):
    MaxAttempts = 5

    @staticmethod
    def clear_existing_impairments():
        logger.info("Clearing Attero existing configuration.")
        controler = atteroctl.attero.Control()
        controler.conn()
        controler.clear_impairments()
        controler.configure()
        controler.end()

    @staticmethod
    def set_delay_and_bottleneck_bandwidth(direction, delay, bandwidth):
        i = 0
        while True:
            try:
                Attero.set_delay(direction, delay)
                Attero.set_bandwidth(direction, bandwidth)
            except Exception as e:
                logger.error(
                    "Attero cannot set impairments [delay: %s, bandwidth: %s, attempt: %s]" % (delay, bandwidth, i)
                )
                logger.error(e)
                i += 1
                if i >= Attero.MaxAttempts:
                    raise e
            else:
                break

    @staticmethod
    def set_delay(direction, delay):
        logger.info("Setting Attero to create a delay of %s ms in %s direction." % (delay, direction))
        controller = atteroctl.attero.Control()
        controller.conn()
        flow_option = atteroctl.options.Flow(direction)
        flow_option.set_option(atteroctl.options.Latency(delay))
        controller.set_option(flow_option)
        controller.configure()
        controller.end()

    @staticmethod
    def set_bandwidth(direction, bandwidth):
        logger.info("Setting Attero to create a bottleneck of %s kbps in %s direction." % (bandwidth, direction))
        controller = atteroctl.attero.Control()
        controller.conn()
        flow_option = atteroctl.options.Flow(direction)
        flow_option.set_option(atteroctl.options.Bandwidth(bandwidth))
        controller.set_option(flow_option)
        controller.configure()
        controller.end()

    @staticmethod
    def start():
        controller = atteroctl.attero.Control()
        controller.conn()
        controller.start()
        controller.end()

    @staticmethod
    def stop():
        controller = atteroctl.attero.Control()
        controller.conn()
        controller.stop()
        controller.end()
