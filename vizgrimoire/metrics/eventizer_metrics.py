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
##


import logging
import MySQLdb

import re, sys

from vizgrimoire.metrics.metrics import Metrics

from vizgrimoire.metrics.metrics_filter import MetricFilters

from vizgrimoire.metrics.query_builder import EventizerQuery

from vizgrimoire.EventsDS import EventsDS

from sets import Set


class Events(Metrics):
    """ An event is a meeting of several people related to specific topics of interest

        This class filters by time of planification. There may be other options
        such as the time when the event was created or updated.
    """

    id = "events"
    name = "Events"
    desc = "Meetup events"
    data_source = EventsDS

    def _get_sql(self, evolutionary):
        fields = Set([])
        tables = Set([])
        filters = Set([])

        fields.add("count(distinct(eve.id)) as events")

        tables.add("events eve")
        tables.union_update(self.db.GetSQLReportFrom(self.filters))

        filters.union_update(self.db.GetSQLReportWhere(self.filters))

        query = self.db.BuildQuery(self.filters.period, self.filters.startdate,
                                   self.filters.enddate, " eve.time ", fields,
                                   tables, filters, evolutionary, self.filters.type_analysis)
        return query


class Members(Metrics):
    """ Members of a group are people that subscribed at some point to this

        This set of people contains all of them, confirmed attendees, confirmed
        not attendees and the unknown ones.
    """

    id = "members"
    name = "Members"
    desc = "Meetup members"
    data_source = EventsDS

    def _get_sql (self, evolutionary):
        fields = Set([])
        tables = Set([])
        filters = Set([])

        fields.add("count(distinct(p.id)) as members")

        tables.add("events eve")
        tables.add("groups gro")
        tables.add("members_groups mg")
        tables.add("people p")
        tables.union_update(self.db.GetSQLReportFrom(self.filters))

        filters.add("eve.group_id = gro.id")
        filters.add("gro.id = mg.group_id")
        filters.add("mg.member_id = p.id")
        filters.union_update(self.db.GetSQLReportWhere(self.filters))

        # Using the field "p.joined" to calculate timeseries, we're assuming
        # that when the user joined Meetup, the user directly joined to the
        # several groups. This is initially false and we would need to build
        # another algorithm. This would trace all of the rsvps and check the first
        # time the user decided to attend or not a group.
        query = self.db.BuildQuery(self.filters.period, self.filters.startdate,
                                   self.filters.enddate, " p.joined ", fields,
                                   tables, filters, evolutionary, self.filters.type_analysis)
        return query


class Attendees(Metrics):
    """ Attendees are members that confirmed their assistance to the event

        However, it is not possible to confirm that all of the confirmed people
        attended the event.
    """

    id = "attendees"
    name = "Attendees"
    desc = "Number of people that confirmed their assistance"
    data_source = EventsDS

    def _get_sql(self, evolutionary, islist = False):
        fields = Set([])
        tables = Set([])
        filters = Set([])

        if islist:
            fields.add("p.name")
            fields.add("count(distinct(eve.id))")
        else:
            fields.add("count(distinct(p.id)) as attendees")

        tables.add("events eve")
        tables.add("rsvps")
        tables.add("people p")
        tables.union_update(self.db.GetSQLReportFrom(self.filters))

        filters.add("eve.id = rsvps.event_id")
        filters.add("rsvps.response = 'yes'")
        filters.add("rsvps.member_id = p.id")
        filters.union_update(self.db.GetSQLReportWhere(self.filters))

        query = self.db.BuildQuery(self.filters.period, self.filters.startdate,
                                   self.filters.enddate, " eve.time ", fields,
                                   tables, filters, evolutionary, self.filters.type_analysis)

        if islist:
            query = query + " group by p.name "
            query = query + " order by count(distinct(eve.id)) desc "
            query = query + " limit %d " % self.filters.npeople

        return query

    def get_list(self):
        query = self._get_sql(None, True) # evolutionary value is not used
        data = self.db.ExecuteQuery(query)
        return data
        

class Cities(Metrics):
    """ Cities that are part of each event
    """

    id = "cities"
    name = "Cities"
    desc = "Cities where events are celebrated"
    data_source = EventsDS

    def _get_sql(self, evolutionary):
        fields = Set([])
        tables = Set([])
        filters = Set([])

        fields.add("count(distinct(cit.id)) as cities")

        tables.add("events eve")
        tables.add("cities cit")
        tables.union_update(self.db.GetSQLReportFrom(self.filters))

        filters.add("eve.city_id = cit.id")
        filters.union_update(self.db.GetSQLReportWhere(self.filters))

        query = self.db.BuildQuery(self.filters.period, self.filters.startdate,
                                  self.filters.enddate, " eve.time ", fields,
                                  tables, filters, evolutionary, self.filters.type_analysis)

        return query


if __name__ == '__main__':
    filters = MetricFilters("month", "'2014-04-01'", "'2015-01-01'")
    dbcon = EventizerQuery("root", "", "test_eventizer", "test_eventizer")

    cities = Cities(dbcon, filters)
    print cities.get_agg()
    print cities.get_ts()

    attendees = Attendees(dbcon, filters)
    print attendees.get_agg()
    print attendees.get_ts()
    print attendees.get_list()


