import atexit
import os
import signal
import sys
import time

from config import Config, user_configuration
from conky import exit_conky, start_conky_process, compile_conky_templates
from time_of_day import is_new_time_of_day, period_of_day
from wallpaper import exit_feh, update_wallpaper

atexit.register(exit_conky)
atexit.register(exit_feh)


def exit_handler(signal=None, frame=None):
    print('Solarity was interrupted')
    print('Cleaning up temporary files before exiting...')
    exit_conky(config)
    exit_feh()
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)


if __name__ == '__main__':
    # Some SIGINT signals are not properly interupted by python and converted
    # into KeyboardInterrupts, so we have to register a signal handler to
    # safeguard against such cases. This seems to be the case when conky is
    # launched as a subprocess, making it the process that receives the SIGINT
    # signal and not python.
    signal.signal(signal.SIGINT, exit_handler)

    try:
        config = user_configuration()
        period = period_of_day(config['location']['astral'])
        update_wallpaper(config, period)

        # We might need to wait some time before starting conky, as startup
        # scripts may alter screen layouts and interfer with conky
        time.sleep(int(config['conky'].get('startup-delay', '0')))
        compile_conky_templates(config, period)
        start_conky_process(config)

        while True:
            changed, period = is_new_time_of_day(
                period,
                config['location']['astral'],
            )

            if changed:
                print('New time of day detected: ' + period)
                # We are in a new time of day, and we can change the background
                # image
                update_wallpaper(config, period)
                compile_conky_templates(config, period)

            time.sleep(int(config['behaviour']['refresh-period']))

    except KeyboardInterrupt:
        exit_handler()
