# Copyright (C) 2009 PreludeIDS Technologies. All Rights Reserved.
# Author: Yoann Vandoorselaere <yoann.v@prelude-ids.com>
#
# This file is part of the Prewikka program.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.

import pkg_resources
import ConfigParser, sys, os, traceback
from PreludeCorrelator import siteconfig


config = ConfigParser.ConfigParser()
config.read(siteconfig.conf_dir + '/plugins.conf')

ENTRYPOINT = 'PreludeCorrelator.plugins'

class Plugin(object):
    enable = True

    def getConfigValue(self, key, replacement=None):
        if not config.has_section(self.__class__.__name__):
            return replacement

        try:
            return config.get(self.__class__.__name__, key)
        except ConfigParser.NoOptionError:
            return replacement

    def run(self, idmef):
        pass


class PluginManager:
    def __init__(self):
        self._count = 0
        self.__instances = []

        for entrypoint in pkg_resources.iter_entry_points(ENTRYPOINT):
            plugin_class = entrypoint.load()

            self.__instances.append(plugin_class())
            self._count += 1

    def getPluginCount(self):
        return self._count

    def run(self, idmef):
        for plugin in self.__instances:
            try:
                plugin.run(idmef)
            except Exception, e:
                traceback.print_exc()

