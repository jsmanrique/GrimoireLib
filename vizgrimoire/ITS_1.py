## Copyright (C) 2012, 2015 Bitergia
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
## GNU General Public License for more details. 
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
##
## ITS.py
##
## Metrics for Issues Tracking System data source
##
## Authors:
##   Alvaro del Castillo <acs@bitergia.com>

from vizgrimoire.ITS import ITS, Backend

class ITS_1(ITS):
    _metrics_set = []
    _backend = None

    @staticmethod
    def get_db_name():
        return "db_bicho_1"

    @staticmethod
    def get_name(): return "its_1"

    @staticmethod
    def _get_backend():
        import vizgrimoire.report
        if ITS_1._backend == None:
            automator = vizgrimoire.report.Report.get_config()
            its_backend = automator['bicho_1']['backend']
            backend = Backend(its_backend)
        else:
            backend = ITS_1._backend
        return backend

    @staticmethod
    def get_metrics_core_agg():
        m = ['closed','closers','changed','changers',"opened",'openers','trackers']
        m += ['allhistory_participants','bmitickets']
        m += ['stories_opened','stories_openers','stories_closed','stories_pending']
        return m

    @staticmethod
    def get_metrics_core_ts():
        m = ['closed','closers','changed','changers',"opened",'openers','trackers']
        m += ['bmitickets']
        m += ['stories_opened','stories_openers','stories_closed','stories_pending']
        return m

    @staticmethod
    def get_metrics_core_trends():
        m = ['closed','closers','changed','changers',"opened",'openers']
        m += ['bmitickets']
        m += ['stories_opened','stories_openers','stories_closed','stories_pending']
        return m