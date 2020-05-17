#!/usr/bin/python3

# Copyright (C) 2016  Canonical Ltd.
# Author: Steve Langasek <steve.langasek@canonical.com>

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


import re
import sys
import subprocess


class KernelWorkflowError(Exception):
    """An exception occurred with the state of the workflow bug"""


def get_name_and_version_from_bug(bug):
    title_re = re.compile(
        r'^([a-z]+\/)?(?P<package>[a-z0-9.-]+): '
        + '(?P<version>[0-9.-]+[0-9a-z.~-]*)'
        + ' -proposed tracker$')
    match = title_re.search(bug.title)
    if not match:
        print("Ignoring bug %s, not a kernel SRU tracking bug" % bug.id)
        return (None, None)
    package = match.group('package')
    version = match.group('version')
    # FIXME: check that the package version is correct for the suite
    return (package, version)


def process_sru_bug(lp, bugnum, task_callback, source_callback, context=None):
    """Process the indicated bug and call the provided helper functions
    as needed
    """
    package_re = re.compile(
        (r'^%subuntu/(?P<release>[0-9a-z.-]+)/'
         + '\+source/(?P<package>[a-z0-9.-]+)$') % str(lp._root_uri))
    workflow_re = re.compile(
        r'^%skernel-sru-workflow/(?P<subtask>.*)' % str(lp._root_uri))
    prep_re = re.compile(r'prepare-package(?P<subpackage>.*)')

    packages = []
    source_name = None
    proposed_task = None
    updates_task = None
    security_task = None
    bug = lp.bugs[int(bugnum)]
    package, version = get_name_and_version_from_bug(bug)
    if not package or not version:
        return

    task_results = {}
    for task in bug.bug_tasks:
        # If a task is set to invalid, we do not care about it
        if task.status == 'Invalid':
            continue

        # FIXME: ok not exactly what we want, we probably want a hash?
        task_results.update(task_callback(lp, bugnum, task, context))
        task_match = workflow_re.search(str(task.target))
        if task_match:
            subtask = task_match.group('subtask')
            # FIXME: consolidate subtask / prep_match here
            prep_match = prep_re.search(subtask)
            if prep_match:
                packages.append(prep_match.group('subpackage'))

        pkg_match = package_re.search(str(task.target))
        if pkg_match:
            if source_name:
                print("Too many source packages, %s and %s, ignoring bug %s"
                      % (source_name, pkg_match.group('package'), bugnum))
                continue
            source_name = pkg_match.group('package')
            release = pkg_match.group('release')
            continue

    if not source_name:
        print("No source package to act on, skipping bug %s" % bugnum)
        return

    if source_name != package:
        print("Cannot determine base package for %s, %s vs. %s"
              % (bugnum, source_name, package))
        if context['skipnamecheck']:
            return

    if not packages:
        print("No packages in the prepare list, don't know what to do")
        return

    if not '' in packages:
        print("No kernel package in prepare list, only meta packages.  "
              "Continue? [yN] ", end="")
        sys.stdout.flush()
        response = sys.stdin.readline()
        if not response.strip().lower().startswith('y'):
            return

    full_packages = []
    for pkg in packages:
        if pkg == '-lbm':
            pkg = '-backports-modules-3.2.0'
        elif pkg == '-lrm':
            pkg = '-restricted-modules'

        real_package = re.sub(r'^linux', 'linux' + pkg, package)
        full_packages.append(real_package)

    source_callback(lp, bugnum, task_results, full_packages, release, context)
