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
## Authors:
##   Daniel Izquierdo <dizquierdo@bitergia.com>
##   Alvaro del Castillo <acso@bitergia.com>

#############
# TODO: missing functions wrt 
#       evolution and agg values of countries and organizations
#############

import logging
import os
import re
import sys
import datetime

from vizgrimoire.GrimoireSQL import GetSQLGlobal, GetSQLPeriod
from vizgrimoire.GrimoireSQL import ExecuteQuery, BuildQuery
from vizgrimoire.GrimoireUtils import GetPercentageDiff, GetDates, completePeriodIds, getPeriod, createJSON, get_subprojects
from vizgrimoire.metrics.metrics_filter import MetricFilters
from vizgrimoire.analysis.threads import Threads
from vizgrimoire.data_source import DataSource
from vizgrimoire.filter import Filter


class MLS(DataSource):
    _metrics_set = []

    @staticmethod
    def get_repo_field():
        return "mailing_list_url"

    @staticmethod
    def get_db_name():
        return "db_mlstats"

    @staticmethod
    def get_name(): return "mls"

    @staticmethod
    def get_evolutionary_data (period, startdate, enddate, identities_db, filter_ = None):
        # rfield = MLS.get_repo_field()
        evolutionary = True
        evol = {}

        metrics = MLS.get_metrics_data(period, startdate, enddate, identities_db, filter_, evolutionary)
        if filter_ is not None: studies = {}
        else:
            studies = DataSource.get_studies_data(MLS, period, startdate, enddate, evolutionary)
        evol = dict(metrics.items()+studies.items())

        return evol

    @staticmethod
    def create_evolutionary_report (period, startdate, enddate, destdir, i_db, type_analysis = None):
        data =  MLS.get_evolutionary_data (period, startdate, enddate, i_db, type_analysis)
        filename = MLS().get_evolutionary_filename()
        createJSON (data, os.path.join(destdir, filename))

    @staticmethod
    def get_agg_data (period, startdate, enddate, identities_db, filter_ = None):
        rfield = MLS.get_repo_field()
        evolutionary = False

        metrics = MLS.get_metrics_data(period, startdate, enddate, identities_db, filter_, evolutionary)
        if filter_ is not None: studies = {}
        else:
            studies = DataSource.get_studies_data(MLS, period, startdate, enddate, evolutionary)
        agg = dict(metrics.items()+studies.items())

        return agg

    @staticmethod
    def create_agg_report (period, startdate, enddate, destdir, i_db, filter_ = None):
        data = MLS.get_agg_data (period, startdate, enddate, i_db, filter_)
        filename = MLS().get_agg_filename()
        createJSON (data, os.path.join(destdir, filename))

    @staticmethod
    def getLongestThreads(startdate, enddate, identities_db, npeople):
        # This function builds a coherent data structure according
        # to other simila structures. The Class Threads only returns
        # the head of the threads (the first message) and the message_id
        # of each of its children.

        main_topics = Threads(startdate, enddate, identities_db)

        longest_threads = main_topics.topLongestThread(npeople)
        l_threads = {}
        l_threads['message_id'] = []
        l_threads['length'] = []
        l_threads['subject'] = []
        l_threads['date'] = []
        l_threads['initiator_name'] = []
        l_threads['initiator_id'] = []
        l_threads['url'] = []
        for email in longest_threads:
            l_threads['message_id'].append(email.message_id)
            l_threads['length'].append(main_topics.lenThread(email.message_id))
            l_threads['subject'].append(email.subject)
            if not isinstance(email.date, list):
                #not expected result: an empty list.
                l_threads['date'].append(email.date.strftime("%Y-%m-%d"))
            l_threads['initiator_name'].append(email.initiator_name)
            l_threads['initiator_id'].append(email.initiator_id)
            l_threads['url'].append(email.url)

        return l_threads


    @staticmethod
    def get_top_metrics ():
        return ["senders"]

    @staticmethod
    def get_top_data (startdate, enddate, identities_db, filter_, npeople, threads_top = True):
        msenders = DataSource.get_metrics("senders", MLS)
        period = None
        type_analysis = None
        if filter_ is not None:
            type_analysis = filter_.get_type_analysis()
        mfilter = MetricFilters(period, startdate, enddate, type_analysis, npeople)
        top = {}

        if filter_ is None:

            top['senders.'] = msenders.get_list(mfilter, 0)
            top['senders.last month'] = msenders.get_list(mfilter, 31)
            top['senders.last year'] = msenders.get_list(mfilter, 365)

            if threads_top:
	    	top['threads.'] = MLS.getLongestThreads(startdate, enddate, identities_db, npeople)
            	startdate = datetime.date.today() - datetime.timedelta(days=365)
            	startdate =  "'" + str(startdate) + "'"
            	top['threads.last year'] = MLS.getLongestThreads(startdate, enddate, identities_db, npeople)
            	startdate = datetime.date.today() - datetime.timedelta(days=30)
            	startdate =  "'" + str(startdate) + "'"
            	top['threads.last month'] = MLS.getLongestThreads(startdate, enddate, identities_db, npeople) 

        else:
            filter_name = filter_.get_name()
            item = filter_.get_item()

            if filter_name in ["company","domain","repository","domain","country"]:
                if filter_name in ["company","domain","repository","domain","country"]:
                    top['senders.'] = msenders.get_list(mfilter, 0)
                    top['senders.last month'] = msenders.get_list(mfilter, 31)
                    top['senders.last year'] = msenders.get_list(mfilter, 365)
                else:
                    # Remove filters above if there are performance issues
                    top = msenders.get_list(mfilter)
            else:
                top = None

        return top

    @staticmethod
    def create_top_report (startdate, enddate, destdir, npeople, i_db):
        data = MLS.get_top_data (startdate, enddate, i_db, None, npeople)
        top_file = destdir+"/"+MLS().get_top_filename()
        createJSON (data, top_file)

    @staticmethod
    def get_filter_items(filter_, startdate, enddate, identities_db):
        items = None
        filter_name = filter_.get_name()

        if (filter_name == "repository"):
            metric = DataSource.get_metrics("repositories", MLS)
        elif (filter_name == "company"):
            metric = DataSource.get_metrics("organizations", MLS)
        elif (filter_name == "country"):
            metric = DataSource.get_metrics("countries", MLS)
        elif (filter_name == "domain"):
            metric = DataSource.get_metrics("domains", MLS)
        elif (filter_name == "project"):
            metric = DataSource.get_metrics("projects", MLS)
        elif (filter_name == "people2"):
            metric = DataSource.get_metrics("people2", MLS)
        else:
            logging.error(filter_name + " not supported")
            return items

        items = metric.get_list()

        return {"name":items}

    @staticmethod
    def get_filter_summary(filter_, period, startdate, enddate, identities_db, limit, projects_db):
        summary = None
        filter_name = filter_.get_name()

        if (filter_name == "company"):
            summary =  GetSentSummaryCompanies(period, startdate, enddate, identities_db, limit, projects_db)
        return summary

    @staticmethod
    def create_filter_report(filter_, period, startdate, enddate, destdir, npeople, identities_db):
        from vizgrimoire.report import Report
        items = Report.get_items()
        if items is None:
            items = MLS.get_filter_items(filter_, startdate, enddate, identities_db)
            if (items == None): return
            items = items['name']

        filter_name = filter_.get_name()

        if not isinstance(items, (list)):
            items = [items]

        items_files = [item.replace('/', '_').replace("<","__").replace(">","___")
            for item in items]

        fn = os.path.join(destdir, filter_.get_filename(MLS()))
        createJSON(items_files, fn)

        if filter_name in ("domain", "company", "repository"):
            items_list = {'name' : [], 'sent_365' : [], 'senders_365' : []}
        else:
            items_list = items

        for item in items :
            item_name = "'"+ item+ "'"
            logging.info (item_name)
            filter_item = Filter(filter_.get_name(), item)

            evol_data = MLS.get_evolutionary_data(period, startdate, enddate, 
                                                  identities_db, filter_item)
            fn = os.path.join(destdir, filter_item.get_evolutionary_filename(MLS()))
            createJSON(evol_data, fn)

            agg = MLS.get_agg_data(period, startdate, enddate, identities_db, filter_item)
            fn = os.path.join(destdir, filter_item.get_static_filename(MLS()))
            createJSON(agg, fn)

            if filter_name in ("domain", "company", "repository"):
                items_list['name'].append(item.replace('/', '_').replace("<","__").replace(">","___"))
                items_list['sent_365'].append(agg['sent_365'])
                items_list['senders_365'].append(agg['senders_365'])

            top_senders = MLS.get_top_data(startdate, enddate, identities_db, filter_item, npeople, False)
            createJSON(top_senders, destdir+"/"+filter_item.get_top_filename(MLS()))

        fn = os.path.join(destdir, filter_.get_filename(MLS()))
        createJSON(items_list, fn)

        if (filter_name == "company"):
            ds = MLS
            if False:
                summary = MLS.get_filter_summary(
                    filter_, period, startdate, enddate,
                    identities_db, 10, self.db.projects_db
                    )
                createJSON (summary,
                            destdir + "/" + filter_.get_summary_filename(MLS))
            # Perform ages study, if it is specified in Report
            MLS.ages_study_com (items, period, startdate, enddate, destdir)

    @staticmethod
    def _check_report_all_data(data, filter_, startdate, enddate, idb,
                               evol = False, period = None):
        pass

    @staticmethod
    def create_filter_report_all(filter_, period, startdate, enddate, destdir, npeople, identities_db):
        check = False # activate to debug issues
        filter_name = filter_.get_name()
        if filter_name in ["people2","company","repository","country","domain"] :
            filter_all = Filter(filter_name, None)
            agg_all = MLS.get_agg_data(period, startdate, enddate,
                                       identities_db, filter_all)
            fn = os.path.join(destdir, filter_.get_static_filename_all(MLS()))
            createJSON(agg_all, fn)
            MLS.convert_all_to_single(agg_all, filter_, destdir, False, period)

            evol_all = MLS.get_evolutionary_data(period, startdate, enddate,
                                                 identities_db, filter_all)
            fn = os.path.join(destdir, filter_.get_evolutionary_filename_all(MLS()))
            createJSON(evol_all, fn)
            MLS.convert_all_to_single(evol_all, filter_, destdir, True, period)

            if check:
                MLS._check_report_all_data(evol_all, filter_, startdate, enddate,
                                           identities_db, True, period)
                MLS._check_report_all_data(agg_all, filter_, startdate, enddate,
                                           identities_db, False, period)
        else:
            logging.error(filter_name +" does not support yet group by items sql queries")

    @staticmethod
    def get_top_people(startdate, enddate, identities_db, npeople):
        top_data = MLS.get_top_data (startdate, enddate, identities_db, None, npeople, False)

        top = top_data['senders.']["id"]
        top += top_data['senders.last year']["id"]
        top += top_data['senders.last month']["id"]
        # remove duplicates
        people = list(set(top))
        return people

    @staticmethod
    def get_person_evol(uuid, period, startdate, enddate, identities_db, type_analysis):
        evol = GetEvolPeopleMLS(uuid, period, startdate, enddate)
        evol = completePeriodIds(evol, period, startdate, enddate)
        return evol

    @staticmethod
    def get_person_agg(uuid, startdate, enddate, identities_db, type_analysis):
        return GetStaticPeopleMLS(uuid, startdate, enddate)

    @staticmethod
    def create_r_reports(vizr, enddate, destdir):
        unique_ids = True
        # Demographics - created now with age study in Python
        # vizr.ReportDemographicsAgingMLS(enddate, destdir, unique_ids)
        # vizr.ReportDemographicsBirthMLS(enddate, destdir, unique_ids)

        ## Which quantiles we're interested in
        # quantiles_spec = [0.99,0.95,0.5,0.25]

        ## Yearly quantiles of time to attention (minutes)
        ## Monthly quantiles of time to attention (hours)
        ## JSON files generated from VizR
        vizr.ReportTimeToAttendMLS(destdir)

    @staticmethod
    def get_query_builder():
        from vizgrimoire.metrics.query_builder import MLSQuery
        return MLSQuery

    @staticmethod
    def get_metrics_core_agg():
        m  = ['sent','senders','threads','sent_response','senders_response','senders_init','repositories']
        return m


    @staticmethod
    def get_metrics_core_ts():
        m  = ['sent','senders','threads','sent_response','senders_response','senders_init','repositories']
        return m

    @staticmethod
    def get_metrics_core_trends():
        return ['sent','senders']

##############
# Specific FROM and WHERE clauses per type of report
##############

def GetMLSSQLRepositoriesFrom ():
    # tables necessary for repositories
    #return (" messages m ") 
    return (" ")


def GetMLSSQLRepositoriesWhere (repository):
    # fields necessary to match info among tables
    return (" m.mailing_list_url = "+repository+" ")



def GetMLSSQLCompaniesFrom (i_db):
    # fields necessary for the organizations analysis

    return(" , messages_people mp, "+\
                   "people_uidentities pup, "+\
                   i_db+".organizations org, "+\
                   i_db+".enrollments enr")


def GetMLSSQLCompaniesWhere (name):
    # filters for the organizations analysis
    return(" m.message_ID = mp.message_id and "+\
               "mp.email_address = pup.people_id and "+\
               "mp.type_of_recipient=\'From\' and "+\
               "pup.uuid = enr.uuid and "+\
               "enr.organization_id = org.id and "+\
               "m.first_date >= enr.start and "+\
               "m.first_date < enr.end and "+\
               "org.name = "+name)


def GetMLSSQLCountriesFrom (i_db):
    # fields necessary for the countries analysis
    return(" , messages_people mp, "+\
               "people_uidentities pup, "+\
               i_db+".countries c, "+\
               i_db+".profiles pro ")


def GetMLSSQLCountriesWhere (name):
    # filters necessary for the countries analysis

    return(" m.message_ID = mp.message_id and "+\
               "mp.email_address = pup.people_id and "+\
               "mp.type_of_recipient=\'From\' and "+\
               "pup.uuid = pro.uuid and "+\
               "pro.country_code = c.id and "+\
               "c.name="+name)

def GetMLSSQLDomainsFrom (i_db) :
    return (" , messages_people mp, "+\
               "people_uidentities pup, "+\
              i_db+".domains d, "+\
              i_db+".uidentities_domains upd")


def GetMLSSQLDomainsWhere (name) :
    return (" m.message_ID = mp.message_id and "+\
                "mp.email_address = pup.people_id and "+\
                "mp.type_of_recipient=\'From\' and "+\
                "pup.uuid = upd.uuid AND "+\
                "upd.domain_id = d.id AND "+\
                "m.first_date >= upd.init AND "+\
                "m.first_date < upd.end and "+\
                "d.name="+ name)


def GetSQLProjectsFromMLS():
    return (" , mailing_lists ml")


def GetSQLProjectsWhereMLS(project, projects_db):
    # include all repositories for a project and its subprojects
    p = project.replace("'", "") # FIXME: why is "'" needed in the name?

    repos = """and ml.mailing_list_url IN (
           SELECT repository_name
           FROM   %s.projects p, %s.project_repositories pr
           WHERE  p.project_id = pr.project_id AND p.project_id IN (%s)
               AND pr.data_source='mls'
    )""" % (projects_db, projects_db, get_subprojects(p, identities_db))

    return (repos  + " and ml.mailing_list_url = m.mailing_list_url")

# Using senders only here!
def GetMLSFiltersOwnUniqueIdsMLS  () :
    return ('m.message_ID = mp.message_id AND '+\
            ' mp.email_address = pup.people_id AND '+\
            ' mp.type_of_recipient=\'From\'')

##########
#Generic functions to obtain FROM and WHERE clauses per type of report
##########

def GetMLSSQLReportFrom (identities_db, type_analysis):
    #generic function to generate 'from' clauses
    #"type" is a list of two values: type of analysis and value of 
    #such analysis

    From = ""

    if (type_analysis is None or len(type_analysis) != 2): return From

    analysis = type_analysis[0]

    if analysis == 'repository': From = GetMLSSQLRepositoriesFrom()
    elif analysis == 'company': From = GetMLSSQLCompaniesFrom(identities_db)
    elif analysis == 'country': From = GetMLSSQLCountriesFrom(identities_db)
    elif analysis == 'domain': From = GetMLSSQLDomainsFrom(identities_db)
    elif analysis == 'project': From = GetSQLProjectsFromMLS()

    return (From)


def GetMLSSQLReportWhere (type_analysis, projects_db):
    #generic function to generate 'where' clauses
    #"type" is a list of two values: type of analysis and value of 
    #such analysis

    where = ""

    if (type_analysis is None or len(type_analysis) != 2): return where

    analysis = type_analysis[0]
    value = type_analysis[1]

    if analysis == 'repository': where = GetMLSSQLRepositoriesWhere(value)
    elif analysis == 'company': where = GetMLSSQLCompaniesWhere(value)
    elif analysis == 'country': where = GetMLSSQLCountriesWhere(value)
    elif analysis == 'domain': where = GetMLSSQLDomainsWhere(value)
    elif analysis == 'project':
        if (identities_db is None):
            logging.error("project filter not supported without identities_db")
            sys.exit(0)
        else:
            where = GetSQLProjectsWhereMLS(value, projects_db)

    return (where)


#########
# Other generic functions
#########

def reposField () :
    # Depending on the mailing list, the field to be
    # used is mailing_list or mailing_list_url
    rfield = 'mailing_list'
    sql = "select count(distinct(mailing_list)) from messages"
    mailing_lists = ExecuteQuery(sql)
    if (len(mailing_lists) == 0) :
        rfield = "mailing_list_url"

    return (rfield);


def GetMLSFiltersResponse () :
    filters = GetMLSFiltersOwnUniqueIdsMLS()
    filters_response = filters + " AND m.is_response_of IS NOT NULL"
    return filters_response

##########
# Meta functions that aggregate all evolutionary or static data in one call
##########

def GetEmailsSent (period, startdate, enddate, identities_db, type_analysis, evolutionary, projects_db):
    # Generic function that counts emails sent

    if (evolutionary):
        fields = " count(distinct(m.message_ID)) as sent "
    else:
        fields = " count(distinct(m.message_ID)) as sent, "+\
                  " DATE_FORMAT (min(m.first_date), '%Y-%m-%d') as first_date, "+\
                  " DATE_FORMAT (max(m.first_date), '%Y-%m-%d') as last_date "

    tables = " messages m " + GetMLSSQLReportFrom(identities_db, type_analysis)
    filters = GetMLSSQLReportWhere(type_analysis, projects_db)

    q = BuildQuery(period, startdate, enddate, " m.first_date ", fields, tables, filters, evolutionary)
    return(ExecuteQuery(q))

def EvolEmailsSent (period, startdate, enddate, identities_db, type_analysis = [], projects_db = None):
    # Evolution of emails sent
    return(GetEmailsSent(period, startdate, enddate, identities_db, type_analysis , True, projects_db))

########################
# People functions as in the old version, still to be refactored!
########################

def GetTablesOwnUniqueIdsMLS () :
    return ('messages m, messages_people mp, people_uidentities pup')


# Using senders only here!
def GetFiltersOwnUniqueIdsMLS  () :
    return ('m.message_ID = mp.message_id AND '+\
             "mp.email_address = pup.people_id AND "+\
             'mp.type_of_recipient=\'From\'')


def GetFiltersInit () :
    filters = GetFiltersOwnUniqueIdsMLS()
    filters_init = filters + " AND m.is_response_of IS NULL"
    return filters_init

def GetFiltersResponse () :
    filters = GetFiltersOwnUniqueIdsMLS()
    filters_response = filters + " AND m.is_response_of IS NOT NULL"
    return filters_response

def GetListPeopleMLS (startdate, enddate) :
    fields = "DISTINCT(pup.uuid) as id, count(m.message_ID) total"
    tables = GetTablesOwnUniqueIdsMLS()
    filters = GetFiltersOwnUniqueIdsMLS()
    filters += " GROUP BY id ORDER BY total desc"
    q = GetSQLGlobal('first_date',fields,tables, filters, startdate, enddate)

    data = ExecuteQuery(q)
    return (data)

def GetQueryPeopleMLS (developer_id, period, startdate, enddate, evol) :
    fields = "COUNT(m.message_ID) AS sent"
    tables = GetTablesOwnUniqueIdsMLS()
    filters = GetFiltersOwnUniqueIdsMLS() + "AND pup.uuid = '" + str(developer_id) + "'"

    if (evol) :
        q = GetSQLPeriod(period,'first_date', fields, tables, filters,
                startdate, enddate)
    else:
        fields = fields +\
                ",DATE_FORMAT (min(first_date),'%Y-%m-%d') as first_date, "+\
                "DATE_FORMAT (max(first_date),'%Y-%m-%d') as last_date"
        q = GetSQLGlobal('first_date', fields, tables, filters,
                startdate, enddate)
    return (q)


def GetEvolPeopleMLS (developer_id, period, startdate, enddate) :
    q = GetQueryPeopleMLS(developer_id, period, startdate, enddate, True)

    data = ExecuteQuery(q)
    return (data)


def GetStaticPeopleMLS (developer_id, startdate, enddate) :
    q = GetQueryPeopleMLS(developer_id, None, startdate, enddate, False)

    data = ExecuteQuery(q)
    return (data)


def GetSentSummaryCompanies (period, startdate, enddate, identities_db, num_organizations, projects_db):
    count = 1
    first_organizations = {}

    metric = DataSource.get_metrics("organizations", MLS)
    organizations = metric.get_list()

    for company in organizations:
        type_analysis = ["company", "'"+company+"'"]
        sent = EvolEmailsSent(period, startdate, enddate, identities_db, type_analysis, projects_db)
        sent = completePeriodIds(sent, period, startdate, enddate)
        # Rename field sent to company name
        sent[company] = sent["sent"]
        del sent['sent']

        if (count <= num_organizations):
            #Case of organizations with entity in the dataset
            first_organizations = dict(first_organizations.items() + sent.items())
        else :
            #Case of organizations that are aggregated in the field Others
            if 'Others' not in first_organizations:
                first_organizations['Others'] = sent[company]
            else:
                first_organizations['Others'] = [a+b for a, b in zip(first_organizations['Others'],sent[company])]
        count = count + 1

    first_organizations = completePeriodIds(first_organizations, period, startdate, enddate)

    return(first_organizations)
