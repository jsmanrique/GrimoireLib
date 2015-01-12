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
##   Alvaro del Castillo <acs@bitergia.com>

""" Metrics for the source code review system based in the pullpo data model """

import logging
import MySQLdb
import numpy

from GrimoireUtils import completePeriodIds, checkListArray, medianAndAvgByPeriod, check_array_values
from query_builder import DSQuery

from metrics import Metrics

from metrics_filter import MetricFilters

from query_builder import SCRQuery

from query_builder import ITSQuery

from SCR import SCR

from sets import Set

class SCRPullQuery(DSQuery):

    def GetSQLReportFrom (self, type_analysis):
        #generic function to generate 'from' clauses
        #"type" is a list of two values: type of analysis and value of
        #such analysis

        From = Set([])

        return From

        if (type_analysis is None or len(type_analysis) != 2): return From

        analysis = type_analysis[0]

        if (analysis):
            if analysis == 'repository': From.union_update(self.GetSQLRepositoriesFrom())
            elif analysis == 'company': From.union_update(self.GetSQLCompaniesFrom())
            elif analysis == 'country': From.union_update(self.GetSQLCountriesFrom())
            elif analysis == 'project': From.union_update(self.GetSQLProjectFrom())

        return From

    def GetSQLReportWhere (self, type_analysis):
        #generic function to generate 'where' clauses

        #"type" is a list of two values: type of analysis and value of
        #such analysis

        where = Set([])
        return where
        if (type_analysis is None or len(type_analysis) != 2): return where

        analysis = type_analysis[0]
        value = type_analysis[1]

        if (analysis):
            if analysis == 'repository': where.union_update(self.GetSQLRepositoriesWhere(value))
            elif analysis == 'company': where.union_update(self.GetSQLCompaniesWhere(value))
            elif analysis == 'country': where.union_update(self.GetSQLCountriesWhere(value))
            elif analysis == 'project':
                if (self.identities_db is None):
                    logging.error("project filter not supported without identities_db")
                    sys.exit(0)
                else:
                    where.union_update(self.GetSQLProjectWhere(value))
        return where

    def GetReviewsSQL (self, period, startdate, enddate, type_, type_analysis, evolutionary):
        #Building the query
        fields = Set([])
        tables = Set([])
        filters = Set([])

        fields.add("count(distinct(pr.github_id)) as " + type_)

        tables.add("pull_requests pr")
        tables.union_update(self.GetSQLReportFrom(type_analysis))

        if type_ == "submitted": filters = Set([])
        elif type_ == "new": filters.add("pr.state = 'open'")
        elif type_ == "closed": filters.add("pr.state = 'closed'")
        elif type_ == "merged": filters.add("pr.state = 'closed' and merged_at is not NULL")
        elif type_ == "abandoned": filters.add("pr.state = 'closed' and merged_at is NULL")
        filters.union_update(self.GetSQLReportWhere(type_analysis))

        date_field = "pr.created_at"
        if type_ in ["closed", "merged", "abandoned"]: date_field = "pr.updated_at"
        # Not include reviews before startdate no matter mod_date is after startdate
        filters.add("pr.created_at >= " + startdate)

        q = self.BuildQuery (period, startdate, enddate, date_field, fields, tables,
                             filters, evolutionary, type_analysis)
        return q
    pass


class Submitted(Metrics):
    id = "submitted"
    name = "Submitted reviews"
    desc = "Number of submitted code review processes"
    data_source = SCR

    def _get_sql(self, evolutionary):
        q = self.db.GetReviewsSQL(self.filters.period, self.filters.startdate,
                                  self.filters.enddate, "submitted",
                                  self.filters.type_analysis, evolutionary)


        print(q)

        return q

class Merged(Metrics):
    id = "merged"
    name = "Merged changes"
    desc = "Number of changes merged into the source code"
    data_source = SCR

    def _get_sql(self, evolutionary):
        q = self.db.GetReviewsSQL(self.filters.period, self.filters.startdate,
                                  self.filters.enddate, "merged",
                                  self.filters.type_analysis, evolutionary)
        return q

class Mergers(Metrics):
    id = "mergers"
    name = "Successful submitters"
    desc = "Number of persons submitting changes that got accepted"
    data_source = SCR

    def _get_sql(self, evolutionary):
        pass

class Abandoned(Metrics):
    id = "abandoned"
    name = "Abandoned reviews"
    desc = "Number of abandoned review processes"
    data_source = SCR

    def _get_sql(self, evolutionary):
        q = self.db.GetReviewsSQL(self.filters.period, self.filters.startdate,
                                  self.filters.enddate, "abandoned",
                                  self.filters.type_analysis, evolutionary)
        return q

class BMISCR(Metrics):
    """This class calculates the efficiency closing reviews

    This class is based on the Backlog Management Index that in issues, it is
    calculated as the number of closed issues out of the total number of opened
    ones in a period. (The other way around also provides an interesting view). 
    
    In terms of the code review system, this values is measured as the number
    of merged+abandoned reviews out of the total number of submitted ones.
    """

    id = "bmiscr"
    name = "BMI SCR"
    desc = "Efficiency reviewing: (merged+abandoned reviews)/(submitted reviews)"
    data_source = SCR

    def get_ts(self):
        abandoned_reviews = Abandoned(self.db, self.filters)
        merged_reviews = Merged(self.db, self.filters)
        submitted_reviews = Submitted(self.db, self.filters)

        abandoned = abandoned_reviews.get_ts()
        abandoned = completePeriodIds(abandoned, self.filters.period, self.filters.startdate,
                                      self.filters.enddate)
        # casting the type of the variable in order to use numpy
        # faster way to deal with datasets...
        abandoned_array = numpy.array(abandoned["abandoned"])

        merged = merged_reviews.get_ts()
        merged = completePeriodIds(merged, self.filters.period, self.filters.startdate,
                                      self.filters.enddate)
        merged_array = numpy.array(merged["merged"])

        submitted = submitted_reviews.get_ts()
        submitted = completePeriodIds(submitted, self.filters.period, self.filters.startdate,
                                      self.filters.enddate)
        submitted_array = numpy.array(submitted["submitted"])

        bmi_array = (abandoned_array.astype(float) + merged_array.astype(float)) / submitted_array.astype(float)

        bmi = abandoned
        bmi.pop("abandoned")
        bmi["bmiscr"] = list(bmi_array)

        return bmi

    def get_agg(self):
        abandoned_reviews = Abandoned(self.db, self.filters)
        merged_reviews = Merged(self.db, self.filters)
        submitted_reviews = Submitted(self.db, self.filters)

        abandoned = abandoned_reviews.get_agg()
        abandoned_data = abandoned["abandoned"]
        merged = merged_reviews.get_agg()
        merged_data = merged["merged"]
        submitted = submitted_reviews.get_agg()
        submitted_data = submitted["submitted"]

        if submitted_data == 0:
            # We should probably add a NaN value.
            bmi_data= 0
        else:
            bmi_data = float(merged_data + abandoned_data) / float(submitted_data)
        bmi = {"bmiscr":bmi_data}

        return bmi



class Pending(Metrics):
    id = "pending"
    name = "Pending reviews"
    desc = "Number of pending review processes"
    data_source = SCR

    def _get_metrics_for_pending(self):
        # We need to fix the same filter for all metrics
        metrics_for_pendig = {}

        metric = SCR.get_metrics("submitted", SCR)
        if metric is None:
            metric = Submitted(self.db, self.filters)
        metric.filters = self.filters
        metrics_for_pendig['submitted'] = metric

        metric = SCR.get_metrics("merged", SCR)
        if metric is None:
            metric = Merged(self.db, self.filters)
        metric.filters = self.filters
        metrics_for_pendig['merged'] = metric

        metric = SCR.get_metrics("abandoned", SCR)
        if metric is None:
            metric = Abandoned(self.db, self.filters)
        metric.filters = self.filters
        metrics_for_pendig['abandoned'] = metric

        return metrics_for_pendig

    def _get_metrics_for_pending_all(self, evol):
        """ Return the metric for all items normalized """
        metrics = self._get_metrics_for_pending()
        if evol is True:
            submitted = metrics['submitted'].get_ts()
            merged = metrics['merged'].get_ts()
            abandoned = metrics['abandoned'].get_ts()
        else:
            submitted = metrics['submitted'].get_agg()
            merged = metrics['merged'].get_agg()
            abandoned = metrics['abandoned'].get_agg()

        from report import Report
        filter = Report.get_filter(self.filters.type_analysis[0])
        items = SCR.get_filter_items(filter, self.filters.startdate,
                                     self.filters.enddate, self.db.identities_db)
        items = items.pop('name')

        from GrimoireUtils import fill_and_order_items
        id_field = DSQuery.get_group_field(self.filters.type_analysis[0])
        id_field = id_field.split('.')[1] # remove table name
        submitted = check_array_values(submitted)
        merged = check_array_values(merged)
        abandoned = check_array_values(abandoned)

        submitted = fill_and_order_items(items, submitted, id_field,
                                         evol, self.filters.period,
                                         self.filters.startdate, self.filters.enddate)
        merged = fill_and_order_items(items, merged, id_field,
                                         evol, self.filters.period,
                                         self.filters.startdate, self.filters.enddate)
        abandoned = fill_and_order_items(items, abandoned, id_field,
                                         evol, self.filters.period,
                                         self.filters.startdate, self.filters.enddate)
        metrics_for_pendig_all = {
          id_field: submitted[id_field],
          "submitted": submitted["submitted"],
          "merged": merged["merged"],
          "abandoned": abandoned["abandoned"]
        }
        if evol:
            metrics_for_pendig_all[self.filters.period] = submitted[self.filters.period]

        return metrics_for_pendig_all

    def get_agg_all(self):
        evol = False
        metrics = self._get_metrics_for_pending_all(evol)
        id_field = DSQuery.get_group_field(self.filters.type_analysis[0])
        id_field = id_field.split('.')[1] # remove table name
        data= \
            [metrics['submitted'][i]-metrics['merged'][i]-metrics['abandoned'][i] \
             for i in range(0, len(metrics['submitted']))]
        return {id_field:metrics[id_field], "pending":data}

    def get_ts_all(self):
        evol = True
        metrics = self._get_metrics_for_pending_all(evol)
        id_field = DSQuery.get_group_field(self.filters.type_analysis[0])
        id_field = id_field.split('.')[1] # remove table name
        pending = {"pending":[]}
        for i in range(0, len(metrics['submitted'])):
            pending["pending"].append([])
            for j in range(0, len(metrics['submitted'][i])):
                pending_val = metrics["submitted"][i][j] - metrics["merged"][i][j] - metrics["abandoned"][i][j]
                pending["pending"][i].append(pending_val)
        pending[self.filters.period] = metrics[self.filters.period]
        pending[id_field] = metrics[id_field]
        return pending

    def get_agg(self):
        metrics = self._get_metrics_for_pending()
        submitted = metrics['submitted'].get_agg()
        merged = metrics['merged'].get_agg()
        abandoned = metrics['abandoned'].get_agg()

        # GROUP BY queries
        if self.filters.type_analysis is not None and self.filters.type_analysis[1] is None:
            pending = self.get_agg_all()
        else:
            pending = submitted['submitted']-merged['merged']-abandoned['abandoned']
            pending = {"pending":pending}
        return pending

    def get_ts(self):
        metrics = self._get_metrics_for_pending()
        submitted = metrics["submitted"].get_ts()
        merged = metrics["merged"].get_ts()
        abandoned = metrics["abandoned"].get_ts()
        evol = dict(submitted.items() + merged.items() + abandoned.items())
        pending = {"pending":[]}
            # GROUP BY queries
        if self.filters.type_analysis is not None and self.filters.type_analysis[1] is None:
            pending = self.get_ts_all()
        else:
            for i in range(0, len(evol['submitted'])):
                pending_val = evol["submitted"][i] - evol["merged"][i] - evol["abandoned"][i]
                pending["pending"].append(pending_val)
            pending[self.filters.period] = evol[self.filters.period]
        return pending

class Closed(Metrics):
    id = "closed"
    name = "Closed reviews"
    desc = "Number of closed review processes (merged or abandoned)"
    data_source = SCR

    def _get_sql(self, evolutionary):
        q = self.db.GetReviewsSQL(self.filters.period, self.filters.startdate,
                                  self.filters.enddate, "closed",
                                  self.filters.type_analysis, evolutionary)
        return q

class New(Metrics):
    id = "new"
    name = "New reviews"
    desc = "Number of new review processes"
    data_source = SCR

    def _get_sql(self, evolutionary):
        q = self.db.GetReviewsSQL(self.filters.period, self.filters.startdate,
                                  self.filters.enddate, "new",
                                  self.filters.type_analysis, evolutionary)
        return q

    def _get_sqlchanges (self, evolutionary):
        q = self.db.GetReviewsChangesSQL(self.filters.period, self.filters.startdate,
                                         self.filters.enddate, "new",
                                         self.filters.type_analysis, evolutionary)
        return q

    def get_ts_changes(self):
        query = self._get_sqlchanges(True)
        ts = self.db.ExecuteQuery(query)
        return completePeriodIds(ts, self.filters.period,
                                 self.filters.startdate, self.filters.enddate)


class Companies(Metrics):
    id = "companies"
    name = "Organizations"
    desc = "Number of organizations (companies, etc.) with persons active in code review"
    data_source = SCR

    def _get_sql(self, evolutionary):
        fields = Set([])
        tables = Set([])
        filters = Set([])

        #TODO: warning -> not using GetSQLReportFrom/Where to build queries
        fields.add("count(distinct(upc.company_id)) as companies")
        tables.add("pull_requests pr")
        tables.add("people_upeople pup")
        tables.add(self.db.identities_db + ".upeople_companies upc")
        filters.add("pr.submitted_by = pup.people_id")
        filters.add("pup.upeople_id = upc.upeople_id")

        q = self.db.BuildQuery (self.filters.period, self.filters.startdate,
                                self.filters.enddate, " pr.created_at",
                                fields, tables, filters, evolutionary, self.filters.type_analysis)
        return q

    def get_list (self):
        q = "SELECT c.id as id, c.name as name, COUNT(DISTINCT(pr.id)) AS total "+\
                   "FROM  "+self.db.identities_db+".companies c, "+\
                           self.db.identities_db+".upeople_companies upc, "+\
                    "     people_upeople pup, "+\
                    "     pull_requests pr "+\
                   "WHERE pr.submitted_by = pup.people_id AND "+\
                   "  upc.upeople_id = pup.upeople_id AND "+\
                   "  c.id = upc.company_id AND "+\
                   "  pr.state = 'merged' AND "+\
                   "  pr.created_at >="+  self.filters.startdate+ " AND "+\
                   "  pr.created_at < "+ self.filters.enddate+ " "+\
                   "GROUP BY c.name "+\
                   "ORDER BY total DESC, c.name "
        return(self.db.ExecuteQuery(q))

class Countries(Metrics):
    id = "countries"
    name = "Countries"
    desc = "Number of countries with persons active in code review"
    data_source = SCR

    def _get_sql(self, evolutionary):
        fields = Set([])
        tables = Set([])
        filters = Set([])

        #TODO: warning -> not using GetSQLReportFrom/Where to build queries
        fields.add("count(distinct(upc.country_id)) as countries")
        tables.add("pull_requests pr")
        tables.add("people_upeople pup")
        tables.add(self.db.identities_db + ".upeople_countries upc")
        filters.add("pr.submitted_by = pup.people_id")
        filters.add("pup.upeople_id = upc.upeople_id")

        q = self.db.BuildQuery (self.filters.period, self.filters.startdate,
                                self.filters.enddate, " pr.created_at",
                                fields, tables, filters, evolutionary, self.filters.type_analysis)
        return q

    def get_list  (self):
        q = "SELECT c.name as name, COUNT(DISTINCT(pr.id)) AS issues "+\
               "FROM  "+self.db.identities_db+".countries c, "+\
                       self.db.identities_db+".upeople_countries upc, "+\
                "    people_upeople pup, "+\
                "    pull_requests pr "+\
               "WHERE pr.submitted_by = pup.people_id AND "+\
               "  upc.upeople_id = pup.upeople_id AND "+\
               "  c.id = upc.country_id AND "+\
               "  pr.state = 'merged' AND "+\
               "  pr.created_at >="+  self.filters.startdate+ " AND "+\
               "  pr.created_at < "+ self.filters.enddate+ " "+\
               "GROUP BY c.name "+\
               "ORDER BY issues DESC "
        return(self.db.ExecuteQuery(q))

class Domains(Metrics):
    id = "domains"
    name = "Domains"
    desc = "Number of domains with persons active in code review"
    data_source = SCR

    def _get_sql(self, evolutionary):
        pass

class Projects(Metrics):
    id = "projects"
    name = "Projects"
    desc = "Number of projects in code review"
    data_source = SCR

    def _get_sql(self, evolutionary):
        pass

    def get_list (self):
        # Projects activity needs to include subprojects also
        logging.info ("Getting projects list for SCR")

        # Get all projects list
        q = "SELECT p.id AS name FROM  %s.projects p" % (self.db.identities_db)
        projects = self.db.ExecuteQuery(q)
        data = []

        # Loop all projects getting reviews
        for project in projects['name']:
            type_analysis = ['project', project]

            metric = SCR.get_metrics("submitted", SCR)
            type_analysis_orig = metric.filters.type_analysis
            metric.filters.type_analysis = type_analysis
            reviews = metric.get_agg()
            metric.filters.type_analysis = type_analysis_orig

            reviews = reviews['submitted']
            if (reviews > 0):
                data.append([reviews,project])

        # Order the list using reviews: https://wiki.python.org/moin/HowTo/Sorting
        from operator import itemgetter
        data_sort = sorted(data, key=itemgetter(0),reverse=True)
        names = [name[1] for name in data_sort]

        return({"name":names})

class Repositories(Metrics):
    id = "repositories"
    name = "Repositories"
    desc = "Number of repositories with persons active in code review"
    data_source = SCR

    def _get_sql(self, evolutionary):
        fields = Set([])
        tables = Set([])
        filters = Set([])

        fields.add("count(distinct(t.id)) as repositories")
        tables.add("pull_requests pr")
        tables.add("trackers t")
        tables.union_update(self.db.GetSQLReportFrom(self.filters.type_analysis))
        filters.add("pr.tracker_id = t.id")
        filters.union_update(self.db.GetSQLReportWhere(self.filters.type_analysis))
        q = self.db.BuildQuery (self.filters.period, self.filters.startdate,
                                self.filters.enddate, " pr.created_at",
                                fields, tables, filters, evolutionary, self.filters.type_analysis)
        return q

    def get_list  (self):
        #TODO: warning -> not using GetSQLReportFrom/Where
        q = "SELECT t.url as name, COUNT(DISTINCT(pr.id)) AS issues "+\
               " FROM  pull_requests pr, trackers t "+\
               " WHERE pr.tracker_id = t.id AND "+\
               "  pr.created_at >="+  self.filters.startdate+ " AND "+\
               "  pr.created_at < "+ self.filters.enddate +\
               " GROUP BY t.url "+\
               " ORDER BY issues DESC "
        names = self.db.ExecuteQuery(q)
        if not isinstance(names['name'], (list)): names['name'] = [names['name']]
        return(names)


class People(Metrics):
    id = "people2"
    name = "People"
    desc = "Number of people active in code review activities"
    data_source = SCR

    def _get_sql(self, evolutionary):
        pass

    def _get_top_global (self, days = 0, metric_filters = None):
        """ Implemented using Submitters """
        top = None
        submitters = SCR.get_metrics("submitters", SCR)
        if submitters is None:
            #TODO: absolutely wrong: EmailsSenders???
            submitters = EmailsSenders(self.db, self.filters)
            top = submitters._get_top_global(days, metric_filters)
        else:
            afilters = submitters.filters
            submitters.filters = self.filters
            top = submitters._get_top_global(days, metric_filters)
            submitters.filters = afilters

        top['name'] = top.pop('openers')
        return top

class Reviewers(Metrics):
    id = "reviewers"
    name = "Reviewers"
    desc = "Number of persons reviewing code review activities"
    data_source = SCR
    action = "reviews"

    # Not sure if this top is right
    def _get_top_global (self, days = 0, metric_filters = None):
        if metric_filters == None:
            metric_filters = self.filters

        startdate = metric_filters.startdate
        enddate = metric_filters.enddate
        limit = metric_filters.npeople
        filter_bots = self.db.get_bots_filter_sql(self.data_source, metric_filters)
        if filter_bots != "": filter_bots += " AND "
        date_limit = ""

        #TODO: warning -> not using GetSQLReportFrom/Where
        if (days != 0 ):
            q = "SELECT @maxdate:=max(changed_on) from changes limit 1"
            self.db.ExecuteQuery(q)
            date_limit = " AND DATEDIFF(@maxdate, changed_on)<" + str(days)

        q = "SELECT up.id as id, up.identifier as reviewers, "+\
            "               count(distinct(c.id)) as reviewed "+\
            "        FROM people_upeople pup, changes c, "+ self.db.identities_db+".upeople up "+\
            "        WHERE "+ filter_bots+ " "+\
            "            c.changed_by = pup.people_id and "+\
            "            pup.upeople_id = up.id and "+\
            "            c.changed_on >= "+ startdate + " and "+\
            "            c.changed_on < "+ enddate + " "+\
            "            "+ date_limit + " "+\
            "        GROUP BY up.identifier "+\
            "        ORDER BY reviewed desc, reviewers "+\
            "        LIMIT " + str(limit)

        return(self.db.ExecuteQuery(q))



    def _get_sql(self, evolutionary):
        fields = Set([])
        tables = Set([])
        filters = Set([])

        fields.add("count(distinct(changed_by)) as reviewers")
        tables.add("changes ch")
        tables.add("pull_requests pr")
        tables.union_update(self.db.GetSQLReportFrom(self.filters.type_analysis))
        filters.add("ch.issue_id = pr.id")
        filters.union_update(self.db.GetSQLReportWhere(self.filters.type_analysis))

        #Specific case for the basic option where people_upeople table is needed
        #and not taken into account in the initial part of the query
        tables.add("people_upeople pup")
        filters.add("ch.changed_by  = pup.people_id")

        q = self.db.BuildQuery (self.filters.period, self.filters.startdate,
                                self.filters.enddate, " ch.changed_on",
                                fields, tables, filters, evolutionary, self.filters.type_analysis)
        return q


class Closers(Metrics):
    id = "closers"
    name = "Closers"
    desc = "Number of persons closing code review activities"
    data_source = SCR
    action = "closed"

    def _get_top_global (self, days = 0, metric_filters = None):

        if metric_filters == None:
            metric_filters = self.filters

        startdate = metric_filters.startdate
        enddate = metric_filters.enddate
        limit = metric_filters.npeople
        filter_bots = self.db.get_bots_filter_sql(self.data_source, metric_filters)
        if filter_bots != "": filter_bots += " AND "
        date_limit = ""

        if (days != 0 ):
            q = "SELECT @maxdate:=max(created_at) from issues limit 1"
            self.db.ExecuteQuery(q)
            date_limit = " AND DATEDIFF(@maxdate, created_at)<"+str(days)

        # TODO: warning-> not using GetSQLReportFrom/Where
        merged_sql = " AND status='MERGED' "
        rol = "mergers"
        action = "merged"

        q = "SELECT up.id as id, up.identifier as "+rol+", "+\
            "            count(distinct(pr.id)) as "+action+" "+\
            "        FROM people_upeople pup, pull_requests pr, "+self.db.identities_db+".upeople up "+\
            "        WHERE "+ filter_bots+ " "+\
            "            pr.submitted_by = pup.people_id and "+\
            "            pup.upeople_id = up.id and "+\
            "            pr.created_at >= "+ startdate+ " and "+\
            "            pr.created_at < "+ enddate+ " "+\
            "            "+date_limit+ merged_sql+ " "+\
            "        GROUP BY up.identifier "+\
            "        ORDER BY "+action+" desc, id "+\
            "        LIMIT "+ str(limit)
        return(self.db.ExecuteQuery(q))


    def _get_sql(self, evolutionary):
        pass

# Pretty similar to ITS openers
class Submitters(Metrics):
    id = "submitters"
    name = "Submitters"
    desc = "Number of persons submitting code review processes"
    data_source = SCR
    action = "submitted"

    def __get_sql_trk_prj__(self, evolutionary):
        """ First we get the submitters then join with unique identities """

        tpeople_sql  = "SELECT  distinct(submitted_by) as submitted_by, created_at  "
        tpeople_sql += " FROM pull_requests pr, " + self.db._get_tables_query(self.db.GetSQLReportFrom(self.filters.type_analysis))
        filters_ext = self.db._get_filters_query(self.db.GetSQLReportWhere(self.filters.type_analysis))
        if (filters_ext != ""):
            tpeople_sql += " WHERE " + filters_ext

        fields = Set([])
        tables = Set([])
        filters = Set([])

        fields.add("count(distinct(upeople_id)) as submitters")
        tables.add("people_upeople pup")
        tables.add("(%s) tpeople" % (tpeople_sql))
        filters.add("tpeople.submitted_by = pup.people_id")

        q = self.db.BuildQuery(self.filters.period, self.filters.startdate,
                               self.filters.enddate, " tpeople.created_at ",
                               fields, tables, filters, evolutionary, self.filters.type_analysis)
        return q


    def __get_sql_default__(self, evolutionary):
        """ This function returns the evolution or agg number of people opening issues """
        fields = Set([])
        tables = Set([])
        filters = Set([])

        fields.add("count(distinct(pup.upeople_id)) as submitters")
        tables.add("pull_requests pr")
        tables.union_update(self.db.GetSQLReportFrom(self.filters.type_analysis))
        filters.union_update(self.db.GetSQLReportWhere(self.filters.type_analysis))

        #Specific case for the basic option where people_upeople table is needed
        #and not taken into account in the initial part of the query
        tables.add("people_upeople pup")
        filters.add("pr.submitted_by = pup.people_id")

        q = self.db.BuildQuery(self.filters.period, self.filters.startdate,
                               self.filters.enddate, " created_at ",
                               fields, tables, filters, evolutionary, self.filters.type_analysis)
        return q

    def _get_sql(self, evolutionary):
        if (self.filters.type_analysis is not None and (self.filters.type_analysis[0] in  ["repository","project"])):
            return self.__get_sql_trk_prj__(evolutionary)
        else:
            return self.__get_sql_default__(evolutionary)

    def _get_top_global (self, days = 0, metric_filters = None):
        if metric_filters == None:
            metric_filters = self.filters
        startdate = metric_filters.startdate
        enddate = metric_filters.enddate
        limit = metric_filters.npeople
        filter_bots = self.db.get_bots_filter_sql(self.data_source, metric_filters)
        if filter_bots != "": filter_bots += " AND "

        date_limit = ""
        rol = "openers"
        action = "opened"

        #TODO: warning -> not using GetSQLReportFrom/Where
        if (days != 0 ):
            q = "SELECT @maxdate:=max(created_at) from issues limit 1"
            self.db.ExecuteQuery(q)
            date_limit = " AND DATEDIFF(@maxdate, created_at)<"+str(days)

        q = "SELECT up.id as id, up.identifier as "+rol+", "+\
            "            count(distinct(pr.id)) as "+action+" "+\
            "        FROM people_upeople pup, pull_requests pr, "+self.db.identities_db+".upeople up "+\
            "        WHERE "+ filter_bots+ " "+\
            "            pr.submitted_by = pup.people_id and "+\
            "            pup.upeople_id = up.id and "+\
            "            pr.created_at >= "+ startdate+ " and "+\
            "            pr.created_at < "+ enddate+ " "+\
            "            "+date_limit +  " "+\
            "        GROUP BY up.identifier "+\
            "        ORDER BY "+action+" desc, id "+\
            "        LIMIT "+ str(limit)
        return(self.db.ExecuteQuery(q))

class TimeToReview(Metrics):
    id = "review_time"
    name = "Review Time"
    desc = "Time to review"
    data_source = SCR

    def _get_sql(self):
        if self.filters.period != "month": return None
        bots = []
        q = self.db.GetTimeToReviewQuerySQL (self.filters.startdate, self.filters.enddate,
                                             self.filters.type_analysis, bots)
        return q

    def get_agg(self):
        from numpy import median, average
        from GrimoireUtils import removeDecimals

        q = self._get_sql()
        if q is None: return {}
        data = self.db.ExecuteQuery(q)
        data = data['revtime']
        if (isinstance(data, list) == False): data = [data]
        # ttr_median = sorted(data)[len(data)//2]
        if (len(data) == 0):
            ttr_median = float("nan")
            ttr_avg = float("nan")
        else:
            ttr_median = float(median(removeDecimals(data)))
            ttr_avg = float(average(removeDecimals(data)))
        return {"review_time_days_median":ttr_median, "review_time_days_avg":ttr_avg}

    def get_ts(self):
        q = self._get_sql()
        if q is None: return {}
        review_list = self.db.ExecuteQuery(q)
        checkListArray(review_list)
        metrics_list = {}


        med_avg_list = medianAndAvgByPeriod(self.filters.period, review_list['changed_on'], review_list['revtime'])
        if (med_avg_list != None):
            metrics_list['review_time_days_median'] = med_avg_list['median']
            metrics_list['review_time_days_avg'] = med_avg_list['avg']
            metrics_list['month'] = med_avg_list['month']
        else:
            metrics_list['review_time_days_median'] = []
            metrics_list['review_time_days_avg'] = []
            metrics_list['month'] = []

        metrics_list = completePeriodIds(metrics_list, self.filters.period,
                          self.filters.startdate, self.filters.enddate)

        return metrics_list