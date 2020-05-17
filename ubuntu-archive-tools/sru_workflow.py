#!/usr/bin/python3

# Copyright (C) 2017  Canonical Ltd.
# Author: Brian Murray <brian.murray@canonical.com>
# Author: Lukasz 'sil2100' Zemczak <lukasz.zemczak@canonical.com>

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

"""Portions of SRU-related code that is re-used by various SRU tools."""

import re


def process_bug(launchpad, sourcepkg, version, release, num):
    bug_target_re = re.compile(
        r'/ubuntu/(?:(?P<suite>[^/]+)/)?\+source/(?P<source>[^/]+)$')
    bug = launchpad.bugs[num]
    sourcepkg_match = False
    distroseries_match = False
    for task in bug.bug_tasks:
        # Ugly; we have to do URL-parsing to figure this out.
        # /ubuntu/+source/foo can be fed to launchpad.load() to get a
        # distribution_source_package, but /ubuntu/hardy/+source/foo can't.
        match = bug_target_re.search(task.target.self_link)
        if (not match or
            (sourcepkg and
             match.group('source') != sourcepkg)):
            print("Ignoring task %s in bug %s" % (task.web_link, num))
            continue
        sourcepkg_match = True
        if match.group('suite') == release:
            if task.status in ("Invalid", "Won't Fix", "Fix Released"):
                print("Matching task was set to %s before accepting the SRU, "
                      "please double-check if this bug is still liable for "
                      "fixing.  Switching to Fix Committed." % task.status)
            task.status = "Fix Committed"
            task.lp_save()
            print("Success: task %s in bug %s" % (task.web_link, num))
            distroseries_match = True

    if sourcepkg_match and not distroseries_match:
        # add a release task
        lp_url = launchpad._root_uri
        series_task_url = '%subuntu/%s/+source/%s' % \
                          (lp_url, release, sourcepkg)
        sourcepkg_target = launchpad.load(series_task_url)
        new_task = bug.addTask(target=sourcepkg_target)
        new_task.status = "Fix Committed"
        new_task.lp_save()
        print("LP: #%s added task for %s %s" % (num, sourcepkg, release))
    if not sourcepkg_match:
        # warn that the bug has no source package tasks
        print("LP: #%s has no %s tasks!" % (num, sourcepkg))

    # XXX: it might be useful if the package signer/sponsor was
    #   subscribed to the bug report
    bug.subscribe(person=launchpad.people['ubuntu-sru'])
    bug.subscribe(person=launchpad.people['sru-verification'])

    # there may be something else to sponsor so just warn
    subscribers = [sub.person for sub in bug.subscriptions]
    if launchpad.people['ubuntu-sponsors'] in subscribers:
        print('ubuntu-sponsors is still subscribed to LP: #%s. '
              'Is there anything left to sponsor?' % num)

    if not sourcepkg or 'linux' not in sourcepkg:
        block_proposed_series = 'block-proposed-%s' % release
        if block_proposed_series in bug.tags:
            print('The %s tag is still set on bug LP: #%s. '
                  'Should the package continue to be blocked in proposed? '
                  'Please investigate and adjust the tags accordingly.'
                  % (block_proposed_series, num))

        # this dance is needed due to
        # https://bugs.launchpad.net/launchpadlib/+bug/254901
        btags = bug.tags
        for t in ('verification-failed', 'verification-failed-%s' % release,
                  'verification-done', 'verification-done-%s' % release):
            if t in btags:
                tags = btags
                tags.remove(t)
                bug.tags = tags

        if 'verification-needed' not in btags:
            btags.append('verification-needed')
            bug.tags = btags

        needed_tag = 'verification-needed-%s' % release
        if needed_tag not in btags:
            btags.append(needed_tag)
            bug.tags = btags

        bug.lp_save()

    text = ('Hello %s, or anyone else affected,\n\n' %
            re.split(r'[,\s]', bug.owner.display_name)[0])

    if sourcepkg:
        text += 'Accepted %s into ' % sourcepkg
    else:
        text += 'Accepted into '
    if sourcepkg and release:
        text += ('%s-proposed. The package will build now and be available at '
                 'https://launchpad.net/ubuntu/+source/%s/%s in a few hours, '
                 'and then in the -proposed repository.\n\n' % (
                     release, sourcepkg, version))
    else:
        text += ('%s-proposed. The package will build now and be available in '
                 'a few hours in the -proposed repository.\n\n' % (
                     release))

    text += ('Please help us by testing this new package.  ')

    if sourcepkg == 'casper':
        text += ('To properly test it you will need to obtain and boot '
                 'a daily build of a Live CD for %s.' % (release))
    else:
        text += ('See https://wiki.ubuntu.com/Testing/EnableProposed for '
                 'documentation on how to enable and use -proposed.')

    text += ('  Your feedback will aid us getting this update out to other '
             'Ubuntu users.\n\nIf this package fixes the bug for you, '
             'please add a comment to this bug, mentioning the version of the '
             'package you tested, what testing has been performed on the '
             'package and change the tag from '
             'verification-needed-%s to verification-done-%s. '
             'If it does not fix the bug for you, please add a comment '
             'stating that, and change the tag to verification-failed-%s. '
             'In either case, without details of your testing we will not '
             'be able to proceed.\n\nFurther information regarding the '
             'verification process can be found at '
             'https://wiki.ubuntu.com/QATeam/PerformingSRUVerification .  '
             'Thank you in advance for helping!\n\n'
             'N.B. The updated package will be released to -updates after '
             'the bug(s) fixed by this package have been verified and '
             'the package has been in -proposed for a minimum of 7 days.' %
             (release, release, release))
    bug.newMessage(content=text, subject='Please test proposed package')
