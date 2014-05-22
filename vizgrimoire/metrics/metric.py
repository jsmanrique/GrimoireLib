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


class MetricDomain(object):

    def __init__(self, dbcon = None, filters = None):
        """db connection and filter to be used"""
        self.id = None
        self.name = None
        self.desc = None
        self.data_source = None
        self.db = dbcon
        self.filters = filters

    def get_definition(self):
        def_ = {
               "id":self.id,
               "name":self.name,
               "desc":self.desc
        }
        return def_

    def get_data_source(self):
        """ Returns the family of the instance """
        return self.data_source

    def get_sql(self):
        """ Returns specific sql for the provided filters """
        raise NotImplementedError

    def get_agg(self):
        """ Returns an aggregated value """
        raise NotImplementedError

    def get_ts(self):
        """ Returns a time serie of values """
        raise NotImplementedError

    def get_list(self):
        """ Returns a list of items """
        raise NotImplementedError
