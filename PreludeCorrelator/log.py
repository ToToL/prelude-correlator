# Copyright (C) 2009-2012 CS-SI. All Rights Reserved.
# Author: Yoann Vandoorselaere <yoann.v@prelude-ids.com>
#
# This file is part of the Prelude-Correlator program.
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
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import PreludeEasy
import logging, logging.config, logging.handlers, sys, os


debug_level = 0

def _debug(self, msg, *args, **kwargs):
        level = kwargs.pop("level", 0)

        if debug_level and level <= debug_level:
                self.log(logging.DEBUG, msg, *args, **kwargs)


logging.Logger.debug = _debug


def __C_log_callback(self, level, log):
        log = log.rstrip('\n')

        if level == PreludeEasy.PreludeLog.DEBUG:
                self.debug(log)

        elif level == PreludeEasy.PreludeLog.INFO:
                self.info(log)

        elif level == PreludeEasy.PreludeLog.WARNING:
                self.warning(log)

        elif level == PreludeEasy.PreludeLog.ERROR:
                self.error(log)

        elif level == PreludeEasy.PreludeLog.CRITICAL:
                self.critical(log)

        else:
                self.warning(("[unknown:%d] " % level) + log)


def initLogger(options):
        global debug_level

        debug_level = options.debug

        try:
                PreludeEasy.PreludeLog.SetCallback(__C_log_callback)
        except:
                # PreludeLog is available in recent libprelude version, we do not want to fail if it's not.
                pass

        try:
                logging.config.fileConfig(options.config)
        except Exception, e:
                DATEFMT = "%d %b %H:%M:%S"
                FORMAT="%(asctime)s %(name)s (pid:%(process)d) %(levelname)s: %(message)s"
                logging.basicConfig(level=logging.DEBUG, format=FORMAT, datefmt=DATEFMT, stream=sys.stderr)

        if options.daemon is True:
                hdlr = logging.handlers.SysLogHandler('/dev/log')
                hdlr.setFormatter(logging.Formatter('%(name)s: %(levelname)s: %(message)s'))
                logging.getLogger().addHandler(hdlr)


def getLogger(name=__name__):
        return logging.getLogger(name)
