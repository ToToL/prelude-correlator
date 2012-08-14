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

import os, time, StringIO, pickle
from PreludeEasy import IDMEFTime
from PreludeCorrelator.idmef import IDMEF
from PreludeCorrelator import require

_TIMER_LIST = [ ]
_CONTEXT_TABLE = { }


class Timer:
        def __setstate__(self, dict):
                self.__dict__.update(dict)
                if self._timer_start:
                        _TIMER_LIST.append(self)

        def __init__(self, expire, cb_func=None):
                self._timer_start = None
                self._timer_expire = expire
                self._timer_cb = cb_func

        def _timerExpireCallback(self):
                self.stop()
                try:
                        self._timer_cb(self)
                except:
                        pass

        def hasExpired(self, now=time.time()):
                return self.elapsed(now) >= self._timer_expire

        def check(self, now=time.time()):
                if self.hasExpired(now):
                        self._timerExpireCallback()

        def elapsed(self, now=time.time()):
                return now - self._timer_start

        def running(self):
                return self._timer_start != None

        def setExpire(self, expire):
                self._timer_expire = expire

        def start(self):
                if not self._timer_start and self._timer_expire > 0:
                        self._timer_start = time.time()
                        _TIMER_LIST.append(self)

        def stop(self):
                if self._timer_start:
                        _TIMER_LIST.remove(self)
                        self._timer_start = None

        def reset(self):
                self.stop()
                self.start()


class Context(IDMEF, Timer):
        FORMAT_VERSION = 0.2

        def __setstate__(self, dict):
                Timer.__setstate__(self, dict)
                IDMEF.__setstate__(self, dict)

        def __init__(self, name, options={}, overwrite=True, update=False, idmef=None):
                already_initialized = (update or (overwrite is False)) and hasattr(self, "_name")
                if already_initialized is True:
                        return

                self._version = self.FORMAT_VERSION
                self._options = { "threshold": -1, "expire": 0, "alert_on_expire": False }
                IDMEF.__init__(self)
                Timer.__init__(self, 0)

                name = getName(name)
                self._name = name
                self._update_count = 0

                self._options.update(options)
                self.setOptions(self._options)

                if isinstance(idmef, IDMEF):
                        self.addAlertReference(idmef)

                t = self._getTime(idmef)
                self._time_min = t - self._options["expire"]

                if self._options["expire"] > 0:
                        self._time_max = t + self._options["expire"]
                else:
                        self._time_max = -1

                if not _CONTEXT_TABLE.has_key(name):
                        _CONTEXT_TABLE[name] = []

                _CONTEXT_TABLE[name].append(self)

                x = self._mergeIntersect(debug=False)
                if x > 0:
                        from PreludeCorrelator.main import env
                        env.logger.error("A context merge happened on initialization. This should NOT happen : please report this error.")

        def __new__(cls, name, options={}, overwrite=True, update=False, idmef=None):
                if update or (overwrite is False):
                        ctx = search(name, idmef, update=True)
                        if ctx:
                                if update:
                                        ctx.update(options, idmef)

                                        # If a context was updated, check intersection
                                        ctx._mergeIntersect()
                                        return ctx

                                if overwrite is False:
                                        return ctx
                else:
                        ctx = search(name, idmef, update=False)
                        if ctx:
                                ctx.destroy()

                return super(Context, cls).__new__(cls)

        def _getTime(self, idmef=None):
                if not idmef:
                        return time.time()

                if isinstance(idmef, IDMEFTime):
                    return long(idmef)

                return long(idmef.getTime())

        def _updateTime(self, itime):
                self._time_min = min(itime - self._options["expire"], self._time_min)
                if self._time_max != -1:
                        self._time_max = max(itime + self._options["expire"], self._time_max)

        def _intersect(self, idmef, debug=False):
                if isinstance(idmef, Context):
                        itmin = idmef._time_min
                        itmax = idmef._time_max
                else:
                        itime = self._getTime(idmef)
                        itmin = itime - self._options["expire"]
                        itmax = itime + self._options["expire"]

                if (itmin <= self._time_min and (self._time_max == -1 or itmax >= self._time_min)) or \
                   (itmin >= self._time_min and (self._time_max == -1 or itmin <= self._time_max)):
                        return min(itmin, self._time_min), max(itmax, self._time_max)

                return None

        def _mergeIntersect(self, debug=False):
            for ctx in _CONTEXT_TABLE[self._name]:
                if ctx == self:
                        continue

                if self._intersect(ctx, debug):
                        self.merge(ctx)
                        return True

            return False

        def merge(self, ctx):
                self._update_count += ctx._update_count
                self._time_min = min(self._time_min, ctx._time_min)
                self._time_max = max(self._time_max, ctx._time_max)

                self.Set("alert.source(>>)", ctx.Get("alert.source"))
                self.Set("alert.target(>>)", ctx.Get("alert.target"))
                self.Set("alert.correlation_alert.alertident(>>)", ctx.Get("alert.correlation_alert.alertident"))

                ctx.destroy()

        def checkTimeWindow(self, idmef, update=True):
                i = self._intersect(idmef)
                if not i:
                        return False

                if update:
                        self._time_min = i[0]
                        if self._time_max != -1:
                                self._time_max = i[1]

                return True

        def _timerExpireCallback(self):
                threshold = self._options["threshold"]
                alert_on_expire = self._options["alert_on_expire"]

                if alert_on_expire:
                    if threshold == -1 or (self._update_count + 1) >= threshold:
                        if callable(alert_on_expire):
                                alert_on_expire(self)
                                return
                        else:
                                self.alert()

                self.destroy()

        def isVersionCompatible(self):
                version = self.__dict__.get("_version", None)
                return self.FORMAT_VERSION == version

        def update(self, options={}, idmef=None):
                self._update_count += 1

                if idmef:
                        self.addAlertReference(idmef)

                if self.running():
                        self.reset()

                self._options.update(options)
                self.setOptions(self._options)

        def stats(self, log_func, now=time.time()):
                str = ""

                if self._options["threshold"] != -1:
                        str += " threshold=%d/%d" % (self._update_count + 1, self._options["threshold"])

                if self._timer_start:
                        str += " expire=%d/%d" % (self.elapsed(now), self._options["expire"])

                tmin = time.strftime("%c", time.localtime(self._time_min))
                if self._time_max == -1:
                    tmax = "<none>"
                else:
                    tmax = time.strftime("%c", time.localtime(self._time_max))

                log_func("[%s]: tmin=%s tmax=%s update=%d%s" % (self._name, tmin, tmax, self._update_count, str))

        def getOptions(self):
                return self._options

        def setOptions(self, options={}):
                self._options = options

                Timer.setExpire(self, self._options.get("expire", 0))
                Timer.start(self) # will only start the timer if not already running

        def getUpdateCount(self):
                return self._update_count

        def destroy(self):
                if isinstance(self, Timer):
                        self.stop()

                _CONTEXT_TABLE[self._name].remove(self)
                if not _CONTEXT_TABLE[self._name]:
                    _CONTEXT_TABLE.pop(self._name)

def getName(arg):
        def escape(s):
                return s.replace("_", "\\_")

        if type(arg) is str:
                return escape(arg)

        cnt = 0
        name = ""
        for i in arg:
            if cnt > 0:
                name += "_"
            name += escape(str(i))
            cnt += 1

        return name

def search(name, idmef=None, update=False):
    name = getName(name)
    for ctx in _CONTEXT_TABLE.get(name, ()):
        ctime = ctx.checkTimeWindow(idmef, update)
        if ctime:
            return ctx

    return None


_ctxt_filename = require.get_data_filename(None, "context.dat")

def save():
        fd = open(_ctxt_filename, "w")
        pickle.dump(_CONTEXT_TABLE, fd)
        fd.close()

def load():
        if os.path.exists(_ctxt_filename):
                global _TIMER_LIST
                global _CONTEXT_TABLE

                fd = open(_ctxt_filename, "r")
                try:
                        _CONTEXT_TABLE.update(pickle.load(fd))
                except EOFError:
                        return

                v = _CONTEXT_TABLE.values()
                if v and type(v[0]) is not list:
                        _TIMER_LIST = [ ]
                        _CONTEXT_TABLE = { }

                for ctxlist in _CONTEXT_TABLE.values():
                    for ctx in ctxlist:
                        if not ctx.isVersionCompatible():
                                ctx.destroy()

def wakeup(now):
        for timer in _TIMER_LIST:
                timer.check(now)

def stats(logger):
        now = time.time()

        with_threshold = []

        for ctxlist in _CONTEXT_TABLE.values():
            for ctx in ctxlist:
                if ctx._options["threshold"] == -1:
                        ctx.stats(logger.info, now)
                else:
                        with_threshold.append(ctx)

        with_threshold.sort(lambda x, y: x.getUpdateCount() - y.getUpdateCount())
        for ctx in with_threshold:
                ctx.stats(logger.info, now)
