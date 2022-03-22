#!/usr/bin/env python

# manuf.py: Parser library for Wireshark's OUI database.
# Copyright (c) 2017 Michael Huang
#
# This library is free software. It is dual licensed under the terms of the GNU Lesser General
# Public License version 3.0 (or any later version) and the Apache License version 2.0.
#
# For more information, see:
#
# <http://www.gnu.org/licenses/>
# <http://www.apache.org/licenses/>
"""Parser library for Wireshark's OUI database.

Converts MAC addresses into a manufacturer using Wireshark's OUI database.

See README.md.

"""
from __future__ import print_function
from collections import namedtuple
import argparse
import re
import sys
import io

try:
    from urllib2 import urlopen
    from urllib2 import URLError
except ImportError:
    from urllib.request import urlopen
    from urllib.error import URLError

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import importlib
import os

# Vendor tuple
Vendor = namedtuple('Vendor', ['manuf', 'manuf_long', 'comment'])

class MacParser(object):
    """Class that contains a parser for Wireshark's OUI database.

    Optimized for quick lookup performance by reading the entire file into memory on
    initialization. Maps ranges of MAC addresses to manufacturers and comments (descriptions).
    Contains full support for netmasks and other strange things in the database.

    See https://www.wireshark.org/tools/oui-lookup.html

    Args:
        manuf_name (str): Location of the manuf database file. Defaults to "manuf" in the same
            directory.
        update (bool): Whether to update the manuf file automatically. Defaults to False.

    Raises:
        IOError: If manuf file could not be found.

    """
    MANUF_URL = "https://gitlab.com/wireshark/wireshark/-/raw/master/manuf"
    WFA_URL = "https://gitlab.com/wireshark/wireshark/-/raw/master/wka"

    def  __init__(self, manuf_name=None, update=False):
        self._manuf_name = manuf_name or self.get_packaged_manuf_file_path()
        if update:
            self.update()
        else:
            self.refresh()

    def refresh(self, manuf_name=None):
        """Refresh/reload manuf database. Call this when manuf file is updated.

        Args:
            manuf_name (str): Location of the manuf data base file. Defaults to "manuf" in the
                same directory.

        Raises:
            IOError: If manuf file could not be found.

        """
        if not manuf_name:
            manuf_name = self._manuf_name
        with io.open(manuf_name, "r", encoding="utf-8") as read_file:
            manuf_file = StringIO(read_file.read())
        self._masks = {}

        # Build mask -> result dict
        for line in manuf_file:
            try:
                line = line.strip()
                if not line or line[0] == "#":
                    continue
                line = line.replace("\t\t", "\t")
                fields = [field.strip() for field in line.split("\t")]

                parts = fields[0].split("/")
                mac_str = self._strip_mac(parts[0])
                mac_int = self._get_mac_int(mac_str)
                mask = self._bits_left(mac_str)

                # Specification includes mask
                if len(parts) > 1:
                    mask_spec = 48 - int(parts[1])
                    if mask_spec > mask:
                        mask = mask_spec

                comment = fields[3].strip("#").strip() if len(fields) > 3 else None
                long_name = fields[2] if len(fields) > 2 else None

                self._masks[(mask, mac_int >> mask)] = Vendor(manuf=fields[1], manuf_long=long_name, comment=comment)
            except:
                print( "Couldn't parse line", line)
                raise


        manuf_file.close()

    def update(self, manuf_url=None, wfa_url=None, manuf_name=None, refresh=True):
        """Update the Wireshark OUI database to the latest version.

        Args:
            manuf_url (str): URL pointing to OUI database. Defaults to database located at
                code.wireshark.org.
            manuf_name (str): Location to store the new OUI database. Defaults to "manuf" in the
                same directory.
            refresh (bool): Refresh the database once updated. Defaults to True. Uses database
                stored at manuf_name.

        Raises:
            URLError: If the download fails

        """
        if not manuf_url:
            manuf_url = self.MANUF_URL
        if not manuf_name:
            manuf_name = self._manuf_name

        # Retrieve the new database
        try:
            response = urlopen(manuf_url)
        except URLError:
            raise URLError("Failed downloading OUI database")

        # Parse the response
        if response.code == 200:
            with open(manuf_name, "wb") as write_file:
                write_file.write(response.read())
            if refresh:
                self.refresh(manuf_name)
        else:
            err = "{0} {1}".format(response.code, response.msg)
            raise URLError("Failed downloading database: {0}".format(err))

        response.close()
        if not wfa_url:
            wfa_url = self.WFA_URL

        # Append WFA to new database
        try:
            response = urlopen(wfa_url)
        except URLError:
            raise URLError("Failed downloading WFA database")

        # Parse the response
        if response.code == 200:
            with open(manuf_name, "ab") as write_file:
                write_file.write(response.read())
            if refresh:
                self.refresh(manuf_name)
        else:
            err = "{0} {1}".format(response.code, response.msg)
            raise URLError("Failed downloading database: {0}".format(err))

        response.close()

    def search(self, mac, maximum=1):
        """Search for multiple Vendor tuples possibly matching a MAC address.

        Args:
            mac (str): MAC address in standard format.
            maximum (int): Maximum results to return. Defaults to 1.

        Returns:
            List of Vendor namedtuples containing (manuf, comment), with closest result first. May
            be empty if no results found.

        Raises:
            ValueError: If the MAC could not be parsed.

        """
        vendors = []
        if maximum <= 0 or not mac:
            return vendors
        mac_str = self._strip_mac(mac)
        mac_int = self._get_mac_int(mac_str)

        # If the user only gave us X bits, check X bits. No partial matching!
        for mask in range(self._bits_left(mac_str), 48):
            result = self._masks.get((mask, mac_int >> mask))
            if result:
                vendors.append(result)
                if len(vendors) >= maximum:
                    break
        return vendors

    def get_all(self, mac):
        """Get a Vendor tuple containing (manuf, comment) from a MAC address.

        Args:
            mac (str): MAC address in standard format.

        Returns:
            Vendor: Vendor namedtuple containing (manuf, comment). Either or both may be None if
            not found.

        Raises:
            ValueError: If the MAC could not be parsed.

        """
        vendors = self.search(mac)
        if len(vendors) == 0:
            return Vendor(manuf=None, manuf_long=None, comment=None)
        return vendors[0]

    def get_manuf(self, mac):
        """Returns manufacturer from a MAC address.

        Args:
            mac (str): MAC address in standard format.

        Returns:
            string: String containing manufacturer, or None if not found.

        Raises:
            ValueError: If the MAC could not be parsed.

        """
        return self.get_all(mac).manuf

    def get_manuf_long(self, mac):
        """Returns manufacturer long name from a MAC address.

        Args:
            mac (str): MAC address in standard format.

        Returns:
            string: String containing manufacturer, or None if not found.

        Raises:
            ValueError: If the MAC could not be parsed.

        """
        return self.get_all(mac).manuf_long

    def get_comment(self, mac):
        """Returns comment from a MAC address.

        Args:
            mac (str): MAC address in standard format.

        Returns:
            string: String containing comment, or None if not found.

        Raises:
            ValueError: If the MAC could not be parsed.

        """
        return self.get_all(mac).comment

    # Gets the integer representation of a stripped mac string
    def _get_mac_int(self, mac_str):
        try:
            # Fill in missing bits with zeroes
            return int(mac_str, 16) << self._bits_left(mac_str)
        except ValueError:
            raise ValueError("Could not parse MAC: {0}".format(mac_str))

    # Regular expression that matches '-', ':', and '.' characters
    _pattern = re.compile(r"[-:\.]")

    # Strips the MAC address of '-', ':', and '.' characters
    def _strip_mac(self, mac):
        return self._pattern.sub("", mac)

    # Gets the number of bits left in a mac string
    @staticmethod
    def _bits_left(mac_str):
        return 48 - 4 * len(mac_str)

    @staticmethod
    def get_packaged_manuf_file_path():
        """
        returns the path to manuf file bundled with the package.
        :return:
        """
        if __package__ is None or __package__ == "":
            package_init_path = __file__
        else:
            package_init_path = importlib.import_module(__package__).__file__
        package_path = os.path.abspath(os.path.join(package_init_path, os.pardir))
        manuf_file_path = os.path.join(package_path, 'manuf')
        return manuf_file_path


def main(*input_args):
    """Simple command line wrapping for MacParser."""
    argparser = argparse.ArgumentParser(description="Parser utility for Wireshark's OUI database.")
    argparser.add_argument('-m', "--manuf",
                           help="manuf file path. Defaults to manuf file packaged with manuf.py installation",
                           action="store",
                           default=None)

    argparser.add_argument("-u", "--update",
                           help="update manuf file from the internet",
                           action="store_true")
    argparser.add_argument("mac_address", nargs='?', help="MAC address to check")

    input_args = input_args or None  # if main is called with explicit args parse these - else use sysargs
    args = argparser.parse_args(args=input_args)
    parser = MacParser(manuf_name=args.manuf, update=args.update)

    if args.mac_address:
        print(parser.get_all(args.mac_address))

    sys.exit(0)

if __name__ == "__main__":
    main()
