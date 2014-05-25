## Copyright (C) 2014 Bitergia
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
## This file is a part of GrimoireLib
##  (an Python library for the MetricsGrimoire and vizGrimoire systems)
##
##
## Authors:
##   Daniel Izquierdo-Cortazar <dizquierdo@bitergia.com>


from metrics_filter import MetricFilters

class Metrics(object):

    default_period = "month"
    default_start = "'2010-01-01'"
    default_end = "'2014-01-01'"
    id = None
    name = None
    desc = None
    data_source = None

    def __init__(self, dbcon = None, filters = None):
        """db connection and filter to be used"""
        self.db = dbcon
        self.filters = filters
        if filters == None:
            self.filters = MetricFilters(Metrics.default_period, 
                                         Metrics.default_start, Metrics.default_end, 
                                         None)


    def get_definition(self):
        def_ = {
               "id":self.id,
               "name":self.name,
               "desc":self.desc
        }
        return def_

    def get_data_source(self):
        """ Returns the family of the instance """
        return Metrics.data_source

    def __get_sql__(self):
        """ Returns specific sql for the provided filters """
        raise NotImplementedError

    def get_data_source(self):
        return self.data_source

    def get_ts (self):
        """ Returns a time serie of values """
        query = self.__get_sql__(True)
        ts = self.db.ExecuteQuery(query)
        return completePeriodIds(ts, self.filters.period, 
                                 self.filters.startdate, self.filters.enddate)

    def get_agg(self):
        """ Returns an aggregated value """
        query = self.__get_sql__(False)
        return self.db.ExecuteQuery(query)

    def get_list(self):
        """ Returns a list of items """
        raise NotImplementedError