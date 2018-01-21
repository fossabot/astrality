from configparser import ConfigParser, ExtendedInterpolation
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from astral import Location

from conky import create_conky_temp_files
from time_of_day import PERIODS

Config = Dict['str', Any]
FONT_CATEGORIES = ('primary', 'secondary',)


def infer_config_location(
    config_directory: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Try to find the configuration directory for solarity, based on filesystem
    or specific environment variables if they are present several places to put
    it. See README.md
    """
    if not config_directory:
        if 'SOLARITY_CONFIG_HOME' in os.environ:
            # The user has set a custom config directory for solarity
            config_directory = os.environ['SOLARITY_CONFIG_HOME']
        else:
            # Follow the XDG directory standard
            config_directory = os.getenv('XDG_CONFIG_HOME', '~/.config') + '/solarity'

    config_file = config_directory + '/solarity.conf'

    if not os.path.isfile(config_file):
        print(
            'Configuration file not found in its expected path ' \
            f'"{config_file}".'
        )
        config_directory = str(Path(__file__).parents[1])
        config_file = config_directory + '/solarity.conf.example'
        print(f'Using example configuration instead: "{config_file}"')
    else:
        print(f'Using configuration file "{config_file}"')

    return config_directory, config_file


def user_configuration(config_directory: Optional[str] = None) -> Config:
    """
    Create a configuration dictionary which should directly reflect the
    hierarchy of a typical `solarity.conf` file. Users should be able to insert
    elements from their configuration directly into conky module templates. The
    mapping should be:

    ${solarity:conky:main-font} -> config['conky']['main-font']

    Some additional configurations are automatically added to the root level of
    the dictionary such as:
    - config['config-dir']
    - config['config-file']
    - config['conky-module-paths']
    """
    config_directory, config_file = infer_config_location(config_directory)

    # Populate the config dictionary with items from the `solarity.conf`
    # configuration file
    config_parser = ConfigParser(interpolation=ExtendedInterpolation())
    config_parser.read(config_file)
    config = {
        category: dict(items)
        for category, items
        in config_parser.items()
    }

    # Insert infered paths from config_directory
    config_module_paths = {
        module: config_directory + '/conky_themes/' + module
        for module
        in config_parser['conky']['modules'].split()
    }

    conky_module_templates = {
        module: path + '/template.conf'
        for module, path
        in config_module_paths.items()
    }

    config.update({
        'config-directory': config_directory,
        'config-file': config_file,
        'conky-module-paths': config_module_paths,
        'conky-module-templates': conky_module_templates,
        'wallpaper-theme-directory': \
            config_directory + \
            '/wallpaper_themes/' + \
            config['wallpaper']['theme'],
    })

    # Populate rest of config based on a partially filled config
    # Initialize astral Location() object from user configuration
    config['location']['astral'] = astral_location(
        latitude=float(config['location']['latitude']),
        longitude=float(config['location']['longitude']),
        elevation=float(config['location']['elevation']),
    )

    # Find wallpaper paths corresponding to the wallpaper theme set by the user
    config['wallpaper-paths'] = wallpaper_paths(
        config_path=config['config-directory'],
        wallpaper_theme=config['wallpaper']['theme'],
    )

    # Import the colorscheme specified by the users wallpaper theme
    config['colors'] = import_colors(config['wallpaper-theme-directory'])

    # Create temporary conky files used by conky, but files are overwritten
    # when the time of day changes
    config['conky-temp-files'] = create_conky_temp_files(config)

    return config


def astral_location(
    latitude: float,
    longitude: float,
    elevation: float,
) -> Location:
    # Initialize a custom location for astral, as it doesn't necessarily include
    # your current city of residence
    location = Location()

    # These two doesn't really matter
    location.name = 'CityNotImportant'
    location.region = 'RegionIsNotImportantEither'

    # But these are important, and should be provided by the user
    location.latitude = latitude
    location.longitude = longitude
    location.elevation = elevation
    location.timezone = 'UTC'

    return location


def wallpaper_paths(
    config_path: str,
    wallpaper_theme: str,
) -> Dict[str, str]:
    """
    Given the configuration directory and wallpaper theme, this function
    returns a dictionary containing:

    {..., 'period': 'full_wallpaper_path', ...}

    """
    wallpaper_directory = config_path + '/wallpaper_themes/' + wallpaper_theme

    paths = {
        period: wallpaper_directory + '/' + period
        for period
        in PERIODS
    }
    return paths

def import_colors(wallpaper_theme_directory: str):
    color_config_parser = ConfigParser(interpolation=ExtendedInterpolation())
    color_config_path = wallpaper_theme_directory + '/colors.conf'
    color_config_parser.read(color_config_path)
    print(f'Using color config from "{color_config_path}"')

    colors = {}
    for color_category in FONT_CATEGORIES:
        colors[color_category] = {}
        for period in PERIODS:
            colors[color_category][period] = color_config_parser[color_category][period]

    return colors
