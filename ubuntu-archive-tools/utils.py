#!/usr/bin/python2.7

# Copyright (C) 2019 Canonical Ltd.
# Author: Brian Murray <brian.murray@canonical.com>

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

"""Portions of archive related code that is re-used by various tools."""

import gzip
import os
import tempfile

import apt_pkg


def read_tag_file(path, pkg=None):
    tmp = tempfile.NamedTemporaryFile(prefix='checkrdepends.', delete=False)
    try:
        compressed = gzip.open(path)
        try:
            tmp.write(compressed.read())
        finally:
            compressed.close()
        tmp.close()
        with open(tmp.name) as uncompressed:
            tag_file = apt_pkg.TagFile(uncompressed)
            prev_name = None
            prev_stanza = None
            for stanza in tag_file:
                try:
                    name = stanza['package']
                except KeyError:
                    continue
                if pkg:
                    if name != pkg:
                        continue
                if name != prev_name and prev_stanza is not None:
                    yield prev_stanza
                prev_name = name
                prev_stanza = stanza
            if prev_stanza is not None:
                yield prev_stanza
    finally:
        os.unlink(tmp.name)
