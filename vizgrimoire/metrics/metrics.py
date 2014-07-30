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


from GrimoireUtils import completePeriodIds, GetDates, GetPercentageDiff
from metrics_filter import MetricFilters

class Metrics(object):

    default_period = "month"
    default_start = "'2010-01-01'"
    default_end = "'2014-01-01'"
    default_npeople = 10
    id = None
    name = None
    desc = None
    data_source = None
    domains_limit = 30

    def __init__(self, dbcon = None, filters = None):
        """db connection and filter to be used"""
        self.db = dbcon
        self.filters = filters
        if filters == None:
            people_out = None
            companies_out = None
            npeople = None
            type_analysis = None
            self.filters = MetricFilters(Metrics.default_period,
                                         Metrics.default_start, Metrics.default_end,
                                         type_analysis, 
                                         npeople, people_out, companies_out)

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

    def _get_sql(self, evolutionary):
        """ Returns specific sql for the provided filters """
        raise NotImplementedError

    def _get_sql_filter_all (self, evolutionary):
        """ Returns specific sql for the provided filters """
        raise NotImplementedError

    def get_data_source(self):
        return self.data_source

    def get_ts (self):
        """ Returns a time series of values """
        query = self._get_sql(True)
        ts = self.db.ExecuteQuery(query)
        return completePeriodIds(ts, self.filters.period, 
                                 self.filters.startdate, self.filters.enddate)
    def get_filter_all_ts (self):
        """ Returns a time series of values for all items in a filter """
        query = self._get_sql_filter_all(True)
        ts = self.db.ExecuteQuery(query)
        return completePeriodIds(ts, self.filters.period, 
                                 self.filters.startdate, self.filters.enddate)

    def get_agg(self):
        """ Returns an aggregated value """
        query = self._get_sql(False)
        return self.db.ExecuteQuery(query)

    def get_filter_all_agg(self):
        """ Returns an aggregated value for all items in a filter  """
        query = self._get_sql_filter_all(False)
        return self.db.ExecuteQuery(query)


    def get_trends(self, date, days):
        """ Returns the trend metrics between now and now-days values """

        if self.filters.type_analysis and self.filters.type_analysis[1] is None:
            return self.get_trends_all_items(date, days)

        # Keeping state of origin filters
        filters = self.filters

        chardates = GetDates(date, days)
        self.filters = MetricFilters(filters.period,
                                     chardates[1], chardates[0], filters.type_analysis)
        last = self.get_agg()
        last = int(last[self.id])
        self.filters = MetricFilters(filters.period,
                                     chardates[2], chardates[1], filters.type_analysis)
        prev = self.get_agg()
        prev = int(prev[self.id])

        data = {}
        data['diff_net'+self.id+'_'+str(days)] = last - prev
        data['percentage_'+self.id+'_'+str(days)] = GetPercentageDiff(prev, last)
        data[self.id+'_'+str(days)] = last

        # Returning filters to their original value
        self.filters = filters
        return (data)

    def get_trends_all_items(self, date, days):
        """ Returns the trend metrics between now and now-days values """
        from GrimoireUtils import check_array_values
        from query_builder import DSQuery
        # Keeping state of origin filters
        filters = self.filters

        chardates = GetDates(date, days)
        self.filters = MetricFilters(filters.period,
                                     chardates[1], chardates[0], filters.type_analysis)
        last = check_array_values(self.get_agg())

        # last = int(last[self.id])
        self.filters = MetricFilters(filters.period,
                                     chardates[2], chardates[1], filters.type_analysis)
        prev = check_array_values(self.get_agg())

        group_field = DSQuery.get_group_field(self.filters.type_analysis[0])
        group_field = group_field.split('.')[1] # remove table name
        field = prev.keys()[0]
        if field == group_field: field = prev.keys()[1] 

        # We need to build a new dict with trends
        # First, we need to find all possible keys
        items = list(set(prev[group_field] + last[group_field]))
        # Complete prev and last adding missing (0) values
        for item in items:
            if item not in prev[group_field]:
                prev[field].append(0)
                prev[group_field].append(item)
            if item not in last[group_field]:
                last[field].append(0)
                last[group_field].append(item)
        # Recreate last so the items are in the same order than prev
        last_ordered = {}
        last_ordered[field] = []
        last_ordered[group_field] = []
        for item in prev[group_field]:
            last_ordered[group_field].append(item)
            pos = last[group_field].index(item)
            last_ordered[field].append(last[field][pos])

        # Create the dict with trend metrics
        data = {}
        data[group_field] = prev[group_field]
        data[self.id+'_'+str(days)] = last[field]
        data['diff_net'+self.id+'_'+str(days)] = \
            [last_ordered[field][i] - prev[field][i] for i in range(0, len(prev[field]))]
        data['percentage_'+self.id+'_'+str(days)] = \
            [GetPercentageDiff(prev[field][i],last_ordered[field][i]) for i in range(0, len(prev[field]))]

        # Returning filters to their original value
        self.filters = filters
        return (data)

    def _get_top_supported_filters(self):
        return []

    def _get_top_global(self, days = 0, metric_filters = None):
        return {}

    def _get_top(self, metric_filters = None, days = 0):
        if metric_filters.type_analysis and metric_filters.type_analysis is not None:
            if metric_filters.type_analysis[0] not in self._get_top_supported_filters():
                 return
            if metric_filters.type_analysis[0] == "repository":
                alist = self._get_top_repository(metric_filters, days)
            if metric_filters.type_analysis[0] == "company":
                alist = self._get_top_company(metric_filters, days)
            if metric_filters.type_analysis[0] == "country":
                alist = self._get_top_country(metric_filters, days)
            if metric_filters.type_analysis[0] == "domain":
                alist = self._get_top_domain(metric_filters, days)
            if metric_filters.type_analysis[0] == "project":
                alist = self._get_top_project(metric_filters, days)
        else:
            alist = self._get_top_global(days, metric_filters)
        return alist

    def get_list(self, metric_filters = None, days = 0):
        """ Returns a list of items. Mainly used for tops. """
        mlist = {}

        if metric_filters is not None:
            metric_filters_orig = self.filters
            self.filters = metric_filters

        mlist = self._get_top(self.filters, days)

        if metric_filters is not None: self.filters = metric_filters_orig

        return mlist

    def get_items_out_filter_sql (self, filter_, metric_filters = None):
        # The items_out *must* come in metric_filters
        filter_items = ''
        if metric_filters is None:
            metric_filters = self.filters

        if filter_ == "company":
            items_out = metric_filters.companies_out
            if items_out is not None:
                for item in items_out:
                    filter_items += " c.name<>'"+item+"' AND "

        if filter_items != '': filter_items = filter_items[:-4]
        return filter_items

    # TODO: Join with get_items_out_filter_sql once People is a filter
    def get_bots_filter_sql (self, metric_filters = None):
        bots = self.data_source.get_bots()
        if metric_filters is not None:
            if metric_filters.people_out is not None:
                bots = metric_filters.people_out
        filter_bots = ''
        for bot in bots:
            filter_bots = filter_bots + " u.identifier<>'"+bot+"' AND "
        if filter_bots != '': filter_bots = filter_bots[:-4]
        return filter_bots
