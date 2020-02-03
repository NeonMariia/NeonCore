"""
    Mycroft display service.

    This handles display of pictures

    TODO videos
    TODO multiple displays
"""
from mycroft.configuration import Configuration
from mycroft.messagebus.client import MessageBusClient
from mycroft.util import reset_sigint_handler, wait_for_exit_signal, \
    create_daemon, create_echo_function, check_for_signal
from mycroft.util.log import LOG
from mycroft.display import DisplayService


def main():
    """ Main function. Run when file is invoked. """
    reset_sigint_handler()
    check_for_signal("isSpeaking")
    bus = MessageBusClient()  # Connect to the Mycroft Messagebus
    Configuration.set_config_update_handlers(bus)

    LOG.info("Starting Display Services")
    bus.on('message', create_echo_function('Display', ['mycroft.display.service']))
    create_daemon(bus.run_forever)

    display = DisplayService(bus)  # Connect audio service instance to message bus

    wait_for_exit_signal()
    display.shutdown()


main()
