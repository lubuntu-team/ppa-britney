#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright (C) 2011, 2012  Canonical Ltd.
# Author: Stéphane Graber <stgraber@ubuntu.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
# USA

try:
    import xmlrpc.client as xmlrpclib
except ImportError:
    import xmlrpclib

import base64
from datetime import datetime

# Taken from qatracker/qatracker.modules (PHP code)
# cat qatracker.module | grep " = array" | sed -e 's/^\$//g' \
#   -e 's/array(/[/g' -e 's/);/]/g' -e "s/t('/\"/g" -e "s/')/\"/g"
### AUTO-GENERATED ->
qatracker_build_milestone_status = ["Active", "Re-building", "Disabled",
                                    "Superseded", "Ready"]
qatracker_milestone_notify = ["No", "Yes"]
qatracker_milestone_autofill = ["No", "Yes"]
qatracker_milestone_status = ["Testing", "Released", "Archived"]
qatracker_milestone_series_status = ["Active", "Disabled"]
qatracker_milestone_series_manifest_status = ["Active", "Disabled"]
qatracker_product_status = ["Active", "Disabled"]
qatracker_product_type = ["iso", "package", "hardware"]
qatracker_product_download_type = ["HTTP", "RSYNC", "ZSYNC",
                                   "GPG signature", "MD5 checksum", "Comment",
                                   "Torrent"]
qatracker_testsuite_testcase_status = ["Mandatory", "Disabled", "Run-once",
                                       "Optional"]
qatracker_result_result = ["Failed", "Passed", "In progress"]
qatracker_result_status = ["Active", "Disabled"]
qatracker_rebuild_status = ["Requested", "Queued", "Building", "Built",
                            "Published", "Canceled"]
### <- AUTO-GENERATED


class QATrackerRPCObject():
    """Base class for objects received over XML-RPC"""

    CONVERT_BOOL = []
    CONVERT_DATE = []
    CONVERT_INT = []

    def __init__(self, tracker, rpc_dict):
        # Convert the dict we get from the API into an object

        for key in rpc_dict:
            if key in self.CONVERT_INT:
                try:
                    setattr(self, key, int(rpc_dict[key]))
                except ValueError:
                    setattr(self, key, None)
            elif key in self.CONVERT_BOOL:
                setattr(self, key, rpc_dict[key] == "true")
            elif key in self.CONVERT_DATE:
                try:
                    setattr(self, key, datetime.strptime(rpc_dict[key],
                                                         '%Y-%m-%d %H:%M:%S'))
                except ValueError:
                    setattr(self, key, None)
            else:
                setattr(self, key, str(rpc_dict[key]))

        self.tracker = tracker

    def __repr__(self):
        return "%s: %s" % (self.__class__.__name__, self.title)


class QATrackerBug(QATrackerRPCObject):
    """A bug entry"""

    CONVERT_INT = ['bugnumber', 'count']
    CONVERT_DATE = ['earliest_report', 'latest_report']

    def __repr__(self):
        return "%s: %s" % (self.__class__.__name__, self.bugnumber)


class QATrackerBuild(QATrackerRPCObject):
    """A build entry"""

    CONVERT_INT = ['id', 'productid', 'userid', 'status']
    CONVERT_DATE = ['date']

    def __repr__(self):
        return "%s: %s" % (self.__class__.__name__, self.id)

    def add_result(self, testcase, result, comment='', hardware='', bugs={}):
        """Add a result to the build"""

        if (self.tracker.access not in ("user", "admin") and
                self.tracker.access is not None):
            raise Exception("Access denied, you need 'user' but are '%s'" %
                            self.tracker.access)

        build_testcase = None

        # FIXME: Supporting 'str' containing the testcase name would be nice
        if isinstance(testcase, QATrackerTestcase):
            build_testcase = testcase.id
        elif isinstance(testcase, int):
            build_testcase = testcase

        if not build_testcase:
            raise IndexError("Couldn't find testcase: %s" % (testcase,))

        if isinstance(result, list):
            raise TypeError("result must be a string or an integer")

        build_result = self.tracker._get_valid_id_list(qatracker_result_result,
                                                       result)

        if not isinstance(bugs, dict):
            raise TypeError("bugs must be a dict")

        for bug in bugs:
            if not isinstance(bug, int) or bug <= 0:
                raise ValueError("A bugnumber must be a number >= 0")

            if not isinstance(bugs[bug], int) or bugs[bug] not in (0, 1):
                raise ValueError("A bugimportance must be in (0,1)")

        resultid = int(self.tracker.tracker.results.add(self.id,
                                                        build_testcase,
                                                        build_result[0],
                                                        str(comment),
                                                        str(hardware),
                                                        bugs))
        if resultid == -1:
            raise Exception("Couldn't post your result.")

        new_result = None
        for entry in self.get_results(build_testcase, 0):
            if entry.id == resultid:
                new_result = entry
                break

        return new_result

    def get_results(self, testcase, status=qatracker_result_status):
        """Get a list of results for the given build and testcase"""

        build_testcase = None

        # FIXME: Supporting 'str' containing the testcase name would be nice
        if isinstance(testcase, QATrackerTestcase):
            build_testcase = testcase.id
        elif isinstance(testcase, int):
            build_testcase = testcase

        if not build_testcase:
            raise IndexError("Couldn't find testcase: %s" % (testcase,))

        record_filter = self.tracker._get_valid_id_list(
            qatracker_result_status,
            status)

        if len(record_filter) == 0:
            return []

        results = []
        for entry in self.tracker.tracker.results.get_list(
                self.id, build_testcase, list(record_filter)):
            results.append(QATrackerResult(self.tracker, entry))

        return results


class QATrackerMilestone(QATrackerRPCObject):
    """A milestone entry"""

    CONVERT_INT = ['id', 'status', 'series']
    CONVERT_BOOL = ['notify']

    def get_bugs(self):
        """Returns a list of all bugs linked to this milestone"""

        bugs = []
        for entry in self.tracker.tracker.bugs.get_list(self.id):
            bugs.append(QATrackerBug(self.tracker, entry))

        return bugs

    def add_build(self, product, version, note="", notify=True):
        """Add a build to the milestone"""

        if self.status != 0:
            raise TypeError("Only active milestones are accepted")

        if self.tracker.access != "admin" and self.tracker.access is not None:
            raise Exception("Access denied, you need 'admin' but are '%s'" %
                            self.tracker.access)

        if not isinstance(notify, bool):
            raise TypeError("notify must be a boolean")

        build_product = None

        if isinstance(product, QATrackerProduct):
            build_product = product
        else:
            valid_products = self.tracker.get_products(0)

            for entry in valid_products:
                if (entry.title.lower() == str(product).lower() or
                        entry.id == product):
                    build_product = entry
                    break

        if not build_product:
            raise IndexError("Couldn't find product: %s" % product)

        if build_product.status != 0:
            raise TypeError("Only active products are accepted")

        self.tracker.tracker.builds.add(build_product.id, self.id,
                                        str(version), str(note), notify)

        new_build = None
        for entry in self.get_builds(0):
            if (entry.productid == build_product.id
                    and entry.version == str(version)):
                new_build = entry
                break

        return new_build

    def get_builds(self, status=qatracker_build_milestone_status):
        """Get a list of builds for the milestone"""

        record_filter = self.tracker._get_valid_id_list(
            qatracker_build_milestone_status, status)

        if len(record_filter) == 0:
            return []

        builds = []
        for entry in self.tracker.tracker.builds.get_list(self.id,
                                                          list(record_filter)):
            builds.append(QATrackerBuild(self.tracker, entry))

        return builds


class QATrackerProduct(QATrackerRPCObject):
    CONVERT_INT = ['id', 'type', 'status']

    def get_testcases(self, series,
                      status=qatracker_testsuite_testcase_status):
        """Get a list of testcases associated with the product"""

        record_filter = self.tracker._get_valid_id_list(
            qatracker_testsuite_testcase_status, status)

        if len(record_filter) == 0:
            return []

        if isinstance(series, QATrackerMilestone):
            seriesid = series.series
        elif isinstance(series, int):
            seriesid = series
        else:
            raise TypeError("series needs to be a valid QATrackerMilestone"
                            " instance or an integer")

        testcases = []
        for entry in self.tracker.tracker.testcases.get_list(
                self.id, seriesid, list(record_filter)):
            testcases.append(QATrackerTestcase(self.tracker, entry))

        return testcases


class QATrackerRebuild(QATrackerRPCObject):
    CONVERT_INT = ['id', 'seriesid', 'productid', 'milestoneid', 'requestedby',
                   'changedby', 'status']
    CONVERT_DATE = ['requestedat', 'changedat']

    def __repr__(self):
        return "%s: %s" % (self.__class__.__name__, self.id)

    def save(self):
        """Save any change that happened on this entry.
           NOTE: At the moment only supports the status field."""

        if (self.tracker.access != "admin" and
                self.tracker.access is not None):
            raise Exception("Access denied, you need 'admin' but are '%s'" %
                            self.tracker.access)

        retval = self.tracker.tracker.rebuilds.update_status(self.id,
                                                             self.status)
        if retval is not True:
            raise Exception("Failed to update rebuild")

        return retval


class QATrackerResult(QATrackerRPCObject):
    CONVERT_INT = ['id', 'reporterid', 'revisionid', 'result', 'changedby',
                   'status']
    CONVERT_DATE = ['date', 'lastchange']
    __deleted = False

    def __repr__(self):
        return "%s: %s" % (self.__class__.__name__, self.id)

    def delete(self):
        """Remove the result from the tracker"""

        if (self.tracker.access not in ("user", "admin") and
                self.tracker.access is not None):
            raise Exception("Access denied, you need 'user' but are '%s'" %
                            self.tracker.access)

        if self.__deleted:
            raise IndexError("Result has already been removed")

        retval = self.tracker.tracker.results.delete(self.id)
        if retval is not True:
            raise Exception("Failed to remove result")

        self.status = 1
        self.__deleted = True

    def save(self):
        """Save any change that happened on this entry"""

        if (self.tracker.access not in ("user", "admin") and
                self.tracker.access is not None):
            raise Exception("Access denied, you need 'user' but are '%s'" %
                            self.tracker.access)

        if self.__deleted:
            raise IndexError("Result no longer exists")

        retval = self.tracker.tracker.results.update(self.id, self.result,
                                                     self.comment,
                                                     self.hardware,
                                                     self.bugs)
        if retval is not True:
            raise Exception("Failed to update result")

        return retval


class QATrackerSeries(QATrackerRPCObject):
    CONVERT_INT = ['id', 'status']

    def get_manifest(self, status=qatracker_milestone_series_manifest_status):
        """Get a list of products in the series' manifest"""

        record_filter = self.tracker._get_valid_id_list(
            qatracker_milestone_series_manifest_status, status)

        if len(record_filter) == 0:
            return []

        manifest_entries = []
        for entry in self.tracker.tracker.series.get_manifest(
                self.id, list(record_filter)):
            manifest_entries.append(QATrackerSeriesManifest(
                                    self.tracker, entry))

        return manifest_entries


class QATrackerSeriesManifest(QATrackerRPCObject):
    CONVERT_INT = ['id', 'productid', 'status']

    def __repr__(self):
        return "%s: %s" % (self.__class__.__name__, self.product_title)


class QATrackerTestcase(QATrackerRPCObject):
    CONVERT_INT = ['id', 'status', 'weight', 'suite']


class QATracker():
    def __init__(self, url, username=None, password=None):
        class AuthTransport(xmlrpclib.Transport):
            def set_auth(self, auth):
                self.auth = auth

            def get_host_info(self, host):
                host, extra_headers, x509 = \
                    xmlrpclib.Transport.get_host_info(self, host)
                if extra_headers is None:
                    extra_headers = []
                extra_headers.append(('Authorization', 'Basic %s' % auth))
                return host, extra_headers, x509

        if username and password:
            try:
                auth = str(base64.b64encode(
                           bytes('%s:%s' % (username, password), 'utf-8')),
                           'utf-8')
            except TypeError:
                auth = base64.b64encode('%s:%s' % (username, password))

            transport = AuthTransport()
            transport.set_auth(auth)
            drupal = xmlrpclib.ServerProxy(url, transport=transport)
        else:
            drupal = xmlrpclib.ServerProxy(url)

        # Call listMethods() so if something is wrong we know it immediately
        drupal.system.listMethods()

        # Get our current access
        self.access = drupal.qatracker.get_access()

        self.tracker = drupal.qatracker

    def _get_valid_id_list(self, status_list, status):
        """ Get a list of valid keys and a list or just a single
            entry of input to check against the list of valid keys.
            The function looks for valid indexes and content, doing
            case insensitive checking for strings and returns a list
            of indexes for the list of valid keys. """

        def process(status_list, status):
            valid_status = [entry.lower() for entry in status_list]

            if isinstance(status, int):
                if status < 0 or status >= len(valid_status):
                    raise IndexError("Invalid status: %s" % status)
                return int(status)

            if isinstance(status, str):
                status = status.lower()
                if status not in valid_status:
                    raise IndexError("Invalid status: %s" % status)
                return valid_status.index(status)

            raise TypeError("Invalid status type: %s (expected str or int)" %
                            type(status))

        record_filter = set()

        if isinstance(status, list):
            for entry in status:
                record_filter.add(process(status_list, entry))
        else:
            record_filter.add(process(status_list, status))

        return list(record_filter)

    def get_bugs(self):
        """Get a list of all bugs reported on the site"""

        bugs = []
        for entry in self.tracker.bugs.get_list(0):
            bugs.append(QATrackerBug(self, entry))

        return bugs

    def get_milestones(self, status=qatracker_milestone_status):
        """Get a list of all milestones"""

        record_filter = self._get_valid_id_list(qatracker_milestone_status,
                                                status)

        if len(record_filter) == 0:
            return []

        milestones = []
        for entry in self.tracker.milestones.get_list(list(record_filter)):
            milestones.append(QATrackerMilestone(self, entry))

        return milestones

    def get_products(self, status=qatracker_product_status):
        """Get a list of all products"""

        record_filter = self._get_valid_id_list(qatracker_product_status,
                                                status)

        if len(record_filter) == 0:
            return []

        products = []
        for entry in self.tracker.products.get_list(list(record_filter)):
            products.append(QATrackerProduct(self, entry))

        return products

    def get_rebuilds(self, status=qatracker_rebuild_status):
        """Get a list of all rebuilds"""

        record_filter = self._get_valid_id_list(
            qatracker_rebuild_status, status)

        if len(record_filter) == 0:
            return []

        rebuilds = []
        for entry in self.tracker.rebuilds.get_list(list(record_filter)):
            rebuilds.append(QATrackerRebuild(self, entry))

        return rebuilds

    def get_series(self, status=qatracker_milestone_series_status):
        """Get a list of all series"""

        record_filter = self._get_valid_id_list(
            qatracker_milestone_series_status, status)

        if len(record_filter) == 0:
            return []

        series = []
        for entry in self.tracker.series.get_list(list(record_filter)):
            series.append(QATrackerSeries(self, entry))

        return series
