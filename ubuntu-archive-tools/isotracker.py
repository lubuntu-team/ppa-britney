# -*- coding: utf-8 -*-

# Copyright (C) 2011, 2012  Canonical Ltd.
# Author: Stéphane Graber <stgraber@ubuntu.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# To use this module, you need a ini configuration file at ~/.isotracker.conf
# example:
#  [general]
#  url=http://iso.qa.ubuntu.com/xmlrpc.php
#  username=stgraber
#  password=blablabla
#  default_milestone=Precise Daily
#
#  [localized]
#  url=http://localized-iso.qa.ubuntu.com/xmlrpc.php
#  password=differentpassword

from __future__ import print_function
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

from qatracker import QATracker, QATrackerMilestone, QATrackerProduct
import os

class NoConfigurationError(Exception):
    pass


class ISOTracker:
    def __init__(self, target=None):
        # Store the alternative target (configuration section)
        self.target = target

        # Read configuration
        configfile = os.path.expanduser('~/.isotracker.conf')
        if not os.path.exists(configfile):
            raise NoConfigurationError(
                "Missing configuration file at: %s" % configfile)

        # Load the config
        self.config = configparser.ConfigParser()
        self.config.read([configfile])

        # Connect to the tracker
        url = self.config.get('general', 'url')
        username = self.config.get('general', 'username')
        password = self.config.get('general', 'password')

        # Override with custom URL and credentials for the target
        if self.target:
            if self.config.has_section(self.target):
                if self.config.has_option(self.target, 'url'):
                    url = self.config.get(self.target, 'url')
                if self.config.has_option(self.target, 'username'):
                    username = self.config.get(self.target, 'username')
                if self.config.has_option(self.target, 'password'):
                    password = self.config.get(self.target, 'password')
            else:
                print("Couldn't find a '%s' target, using the default." %
                      self.target)

        self.qatracker = QATracker(url, username, password)

        # Get the required list of products and milestones
        self.tracker_products = self.qatracker.get_products()
        self.tracker_milestones = self.qatracker.get_milestones()

    def default_milestone(self):
        """
            Get the default milestone from the configuration file.
        """

        milestone_name = None

        if self.target:
            # Series-specific default milestone
            try:
                milestone_name = self.config.get(self.target,
                                                 'default_milestone')
            except (KeyError, configparser.NoSectionError,
                    configparser.NoOptionError):
                pass

        if not milestone_name:
            # Generic default milestone
            try:
                milestone_name = self.config.get('general',
                                                 'default_milestone')
            except (KeyError, configparser.NoSectionError,
                    configparser.NoOptionError):
                pass

        if not milestone_name:
            raise KeyError("No default milestone selected")
        else:
            return self.get_milestone_by_name(milestone_name)

    def get_product_by_name(self, product):
        """
            Get a QATrackerProduct from the product's name.
        """

        for entry in self.tracker_products:
            if entry.title.lower() == product.lower():
                return entry
        else:
            raise KeyError("Product '%s' not found" % product)

    def get_milestone_by_name(self, milestone):
        """
            Get a QATrackerMilestone from the milestone's name.
        """

        for entry in self.tracker_milestones:
            if entry.title.lower() == milestone.lower():
                return entry
        else:
            raise KeyError("Milestone '%s' not found" % milestone)

    def get_builds(self, milestone=None,
                   status=['Active', 'Re-building', 'Ready']):
        """
            Get a list of QATrackerBuild for the given milestone and status.
        """

        if not milestone:
            milestone = self.default_milestone()
        elif not isinstance(milestone, QATrackerMilestone):
            milestone = self.get_milestone_by_name(milestone)

        return milestone.get_builds(status)

    def post_build(self, product, version, milestone=None, note="",
                   notify=True):
        """
            Post a new build to the given milestone.
        """

        if not isinstance(product, QATrackerProduct):
            product = self.get_product_by_name(product)

        notefile = os.path.expanduser('~/.isotracker.note')
        if note == "" and os.path.exists(notefile):
            with open(notefile, 'r') as notefd:
                note = notefd.read()

        if not milestone:
            milestone = self.default_milestone()
        elif not isinstance(milestone, QATrackerMilestone):
            milestone = self.get_milestone_by_name(milestone)

        if milestone.add_build(product, version, note, notify):
            print("Build successfully added to the tracker")
        else:
            print("Failed to add build to the tracker")
