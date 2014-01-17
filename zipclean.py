#!/usr/bin/python3

import argparse
import logging
import json
import sys
import os
from collections import Counter

from zipbase import US_ZIP

from progressbar import ProgressBar, AnimatedMarker, Percentage, ETA

# TODO: some function (e.g: list_guide) are used in more then one modules
# (e.g: publish and zipclean). In the future these function should be
# grouped into one module (libguide maybe?).

def main():

    parser = argparse.ArgumentParser(
            description="remove zip code from all us postal addresses found"\
                    " in mtrip guides.")

    parser.add_argument(
            'path',
            help='root directory that contain all the guides',
            )

    parser.add_argument(
            '-g',
            '--guide-name',
            help='the filename of the guides for which content is to be'\
                    ' published. It defaults to the naming convention for'\
                    ' guide filenames which is result.json',
            type = str,
            default='result.json'
            )

    default_frequency = 1
    parser.add_argument(
            '-f',
            '--frequency',
            help='the frequency (in occurence per guide) at which a certain '\
                    '5 number digit needs to appear in a guide to be'\
                    'considered a zipcode.',
            type = int,
            default=default_frequency
            )

    parser.add_argument(
            '-m',
            '--message-debug',
            help='enable debug message to log file. Defaults to false',
            action='store_true'
            )

    default_log_file = '/var/log/zipclean.py.log'
    parser.add_argument(
            '-l',
            '--log-file',
            help='path to the event log file. Defaults to {0}'.format(
                default_log_file),
            default = default_log_file
            )

    current_version = "0.1.1"
    parser.add_argument(
            '-v',
            '--version',
            help='prints the current version and quit',
            action='store_true'
            )

    parser.add_argument(
            '-t',
            '--test',
            help='run the doctest suite and exit.',
            action = 'store_true'
            )

    args = parser.parse_args()

    if args.test:
        import doctest
        doctest.testmod()
        exit(0)

    if args.version:
        print(current_version)
        exit(0)

    config_logger(args.log_file, args.message_debug)

    zipclean(args.path, args.guide_name, args.frequency)
    return

def die(msg, err_code=-1):
    """
    writes msg to stderr and quit with err_code.
    """
    sys.stderr.write(msg+"\n")
    return

def config_logger(filename, debug):
    """
    apply the relevent logger configuration passed as command line
    argument by user.
    """

    logging_level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
            format='%(asctime)s %(module)s %(levelname)s %(message)s',
            level=logging_level,
            filename=filename
            )

    # requests library is noisy so we disable it's logger.
    requests_log = logging.getLogger("requests")
    requests_log.setLevel(logging.WARNING)

    return

def zipclean(path, guide_name, frequency):
    """
    remove zip code from US postal addresses when they are found in mtrip
    guide.
    """
    logging.info('zipcode cleaning from directory {0} started'.format(path))

    guide_filenames = list_guide(path, guide_name)

    if len(guide_filenames) == 0:
        msg ='there was not guide with filename {0}'\
                'found under {1} so no zipcode cleaning was'\
                ' performed'.format(guide_name, path)
        logging.warning(msg)
        die(msg)

    for g in guide_filenames:
        guide_data = None
        with open(g,'r') as guide:
            guide_data = json.load(guide)

        if not guide_data:
            logging.error("could not load content from {0}".format(g))
            continue

        clean_guide_data = clean_guide(guide_data, frequency)
        with open(g, 'w') as guide:
            json.dump(clean_guide_data, guide)

        logging.info('zipcode cleaning for {0} done'.format(g))

    logging.info('zipcode cleaning from directory {0} finished'.format(path))
    return

def clean_guide(guide_data, frequency):
    """
    Removes the zipcode from the guide and return a new guide without them.
    """

    zipcodes = gather_zipcodes(guide_data, frequency)
    clean_guide = remove_zip(guide_data, zipcodes)

    return clean_guide

def remove_zip(guide_data, zipcodes):
    """
    modify the guide_data so that the strings in the zipcodes set are removed
    from addresses.
    """

    # addresses are located in pois.
    pois = None
    try:
        pois = guide_data['Cities'][0]['pois']
    except KeyError:
        logging.warning("tried to process a guide without pois")
        return guide_data

    for poi in pois:
        try:
            address = poi['address']['address']
            components = address.split()
            new_components = [c for c in components if not c in zipcodes]
            if len(new_components) > 0 and new_components[-1].isdigit():
                new_components = new_components[:-1]
            new_address = " ".join(new_components)
            poi['address']['address'] = new_address
        except KeyError:
            pass

    return guide_data

def gather_zipcodes(guide, frequency):
    """
    Open a guide and gather zipcodes from the guide. Return a set of
    those zipcodes.
    """

    addresses = list_addresses(guide)
    zip_candidates = list_zip_candidate(addresses)

    zip_frequency = Counter(zip_candidates)

    # only keep the zip that are occuring with a frequency that is greater
    # then the frequency argument.
    result = {code for code in zip_frequency if
            zip_frequency[code] >= frequency}
    return result

def list_zip_candidate(addresses):
    """
    returns a list of potential zipcodes. A zip code is a 5 character num
    substring foud inside an address.
    """

    result = []
    def extract_zip(address):
        components = address.split()
        zip_candidates = [c for c in components if iszipcode(c)]
        return zip_candidates

    for address in addresses:
        candidates = extract_zip(address)
        result.extend(candidates)

    return result

def iszipcode(s):
    """
    return true if the given string s is considered to be a us zipcode or
    false otherwise.
    """

    # string is a zipcode IF it's in the giant zipcode database.
    result = s in US_ZIP
    return result

def list_addresses(guide):
    """
    return a list of all addresses string in a guide.
    """

    # addresses are located in pois.
    pois = None
    try:
        pois = guide['Cities'][0]['pois']
    except:
        logging.warning("tried to process a guide without pois")
        return []

    addresses = [addr(p) for p in pois if addr(p)]
    return addresses

def addr(poi):
    """
    return the address string from the poi structure if it exists.
    """

    addr = None
    try:
        addr = poi['address']['address']
    finally:
        return addr

def guide_file(path,guide_name):
    """ Return the json filename guide found in path. None if it cannot be
    found. """

    dir_content = [os.path.join(path,content) for content in os.listdir(path)
            if guide_name in os.path.join(path,content)]

    if len(dir_content) > 0:
        return dir_content[0]
    else:
        return None

def list_guide(path, guide_name):
    """
    returns a list of all the mtrip guide files that can be found under
    path.
    """

    # list all directories in the path.
    directories = [os.path.join(path,d) for d in os.listdir(path) if
            os.path.isdir(os.path.join(path,d))]

    # get the result filename from the dir
    guides = [guide_file(d,guide_name) for d in directories if guide_file(d,
        guide_name)]

    return guides

if __name__ == '__main__':
    main()
