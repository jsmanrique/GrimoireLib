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
##   Alvaro del Castillo <acs@bitergia.com>

import logging
import MySQLdb
import re
import sys

class DSQuery(object):
    """ Generic methods to control access to db """

    db_conn_pool = {} # one connection per database

    def __init__(self, user, password, database, identities_db = None, host="127.0.0.1", port=3306, group=None):
        self.identities_db = identities_db
        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = port
        self.group = group
        if database in DSQuery.db_conn_pool:
            db = DSQuery.db_conn_pool[database]
        else:
            db = self.__SetDBChannel__(user, password, database, host, port, group)
            DSQuery.db_conn_pool[database] = db
        self.cursor = db.cursor()
        self.cursor.execute("SET NAMES 'utf8'")

        db = self.__SetDBChannel__(user, password, database, host, port, group)

        self.create_indexes()

    def create_indexes(self):
        """ Basic indexes used in each data source """
        pass

    def GetSQLGlobal(self, date, fields, tables, filters, start, end):
        sql = 'SELECT '+ fields
        sql += ' FROM '+ tables
        sql += ' WHERE '+date+'>='+start+' AND '+date+'<'+end
        reg_and = re.compile("^[ ]*and", re.IGNORECASE)
        if (filters != ""):
            if (reg_and.match (filters.lower())) is not None: sql += " " + filters
            else: sql += ' AND '+filters
        return(sql)

    def GetSQLPeriod(self, period, date, fields, tables, filters, start, end):
        # kind = ['year','month','week','day']
        iso_8601_mode = 3
        if (period == 'day'):
            # Remove time so unix timestamp is start of day    
            sql = 'SELECT UNIX_TIMESTAMP(DATE('+date+')) AS unixtime, '
        elif (period == 'week'):
            sql = 'SELECT YEARWEEK('+date+','+str(iso_8601_mode)+') AS week, '
        elif (period == 'month'):
            sql = 'SELECT YEAR('+date+')*12+MONTH('+date+') AS month, '
        elif (period == 'year'):
            sql = 'SELECT YEAR('+date+')*12 AS year, '
        else:
            logging.error("PERIOD: "+period+" not supported")
            sys.exit(1)
        # sql = paste(sql, 'DATE_FORMAT (',date,', \'%d %b %Y\') AS date, ')
        sql += fields
        sql += ' FROM ' + tables
        sql = sql + ' WHERE '+date+'>='+start+' AND '+date+'<'+end
        reg_and = re.compile("^[ ]*and", re.IGNORECASE)

        if (filters != ""):
            if (reg_and.match (filters.lower())) is not None: sql += " " + filters
            else: sql += ' AND ' + filters

        if (period == 'year'):
            sql += ' GROUP BY YEAR('+date+')'
            sql += ' ORDER BY YEAR('+date+')'
        elif (period == 'month'):
            sql += ' GROUP BY YEAR('+date+'),MONTH('+date+')'
            sql += ' ORDER BY YEAR('+date+'),MONTH('+date+')'
        elif (period == 'week'):
            sql += ' GROUP BY YEARWEEK('+date+','+str(iso_8601_mode)+')'
            sql += ' ORDER BY YEARWEEK('+date+','+str(iso_8601_mode)+')'
        elif (period == 'day'):
            sql += ' GROUP BY YEAR('+date+'),DAYOFYEAR('+date+')'
            sql += ' ORDER BY YEAR('+date+'),DAYOFYEAR('+date+')'
        else:
            logging.error("PERIOD: "+period+" not supported")
            sys.exit(1)
        return(sql)


    def BuildQuery (self, period, startdate, enddate, date_field, fields, tables, filters, evolutionary):
        # Select the way to evolutionary or aggregated dataset
        q = ""

        if (evolutionary):
            q = self.GetSQLPeriod(period, date_field, fields, tables, filters,
                              startdate, enddate)
        else:
            q = self.GetSQLGlobal(date_field, fields, tables, filters,
                              startdate, enddate)

        return(q)

    def __SetDBChannel__ (self, user=None, password=None, database=None,
                      host="127.0.0.1", port=3306, group=None):
        if (group == None):
            db = MySQLdb.connect(user=user, passwd=password,
                                 db=database, host=host, port=port)
        else:
            db = MySQLdb.connect(read_default_group=group, db=database)

        return db

    def ExecuteQuery (self, sql):
        if sql is None: return {}
        result = {}
        self.cursor.execute(sql)
        rows = self.cursor.rowcount
        columns = self.cursor.description

        if columns is None: return result

        for column in columns:
            result[column[0]] = []
        if rows > 1:
            for value in self.cursor.fetchall():
                for (index,column) in enumerate(value):
                    result[columns[index][0]].append(column)
        elif rows == 1:
            value = self.cursor.fetchone()
            for i in range (0, len(columns)):
                result[columns[i][0]] = value[i]
        return result

    def ExecuteViewQuery(self, sql):
        self.cursor.execute(sql)

    def get_subprojects(self, project):
        """ Return all subprojects ids for a project in a string join by comma """

        q = "SELECT project_id from %s.projects WHERE id='%s'" % (self.identities_db, project)
        project_id = self.ExecuteQuery(q)['project_id']

        q = """
            SELECT subproject_id from %s.project_children pc where pc.project_id = '%s'
        """ % (self.identities_db, project_id)

        subprojects = self.ExecuteQuery(q)

        if not isinstance(subprojects['subproject_id'], list):
            subprojects['subproject_id'] = [subprojects['subproject_id']]

        project_with_children = subprojects['subproject_id'] + [project_id]
        project_with_children_str = ','.join(str(x) for x in project_with_children)

        return  project_with_children_str

class SCMQuery(DSQuery):
    """ Specific query builders for source code management system data source """

    def GetSQLRepositoriesFrom (self):
        #tables necessaries for repositories
        return (" , repositories r")

    def GetSQLRepositoriesWhere (self, repository):
        #fields necessaries to match info among tables
        return (" and r.name ="+ repository + \
                " and r.id = s.repository_id")

    def GetSQLProjectFrom (self):
        #tables necessaries for repositories
        return (" , repositories r")

    def GetSQLProjectWhere (self, project):
        # include all repositories for a project and its subprojects
        # Remove '' from project name
        if (project[0] == "'" and project[-1] == "'"):
            project = project[1:-1]

        repos = """and r.uri IN (
               SELECT repository_name
               FROM   %s.projects p, %s.project_repositories pr
               WHERE  p.project_id = pr.project_id AND p.project_id IN (%s)
                     AND pr.data_source='scm'
               )""" % (self.identities_db, self.identities_db, self.get_subprojects(project))

        return (repos   + " and r.id = s.repository_id")

    def GetSQLCompaniesFrom (self, identities_db):
        #tables necessaries for companies
        return (" , "+identities_db+".people_upeople pup,"+\
                      identities_db+".upeople_companies upc,"+\
                      identities_db+".companies c")

    def GetSQLCompaniesWhere (self, company, role):
         #fields necessaries to match info among tables
         return ("and s."+role+"_id = pup.people_id "+\
                 "  and pup.upeople_id = upc.upeople_id "+\
                 "  and s.date >= upc.init "+\
                 "  and s.date < upc.end "+\
                 "  and upc.company_id = c.id "+\
                 "  and c.name =" + company)

    def GetSQLCountriesFrom (self, identities_db):
        #tables necessaries for companies
        return (" , "+identities_db+".people_upeople pup, "+\
                      identities_db+".upeople_countries upc, "+\
                      identities_db+".countries c")

    def GetSQLCountriesWhere (self, country, role):
         #fields necessaries to match info among tables
        return ("and s."+role+"_id = pup.people_id "+\
                      "and pup.upeople_id = upc.upeople_id "+\
                      "and upc.country_id = c.id "+\
                      "and c.name ="+ country)

    def GetSQLDomainsFrom (self, identities_db) :
        #tables necessaries for domains
        return (" , "+identities_db+".people_upeople pup, "+\
                    identities_db+".upeople_domains upd, "+\
                    identities_db+".domains d")

    def GetSQLDomainsWhere (self, domain, role) :
        #fields necessaries to match info among tables
        return ("and s."+role+"_id = pup.people_id "+\
                "and pup.upeople_id = upd.upeople_id "+\
                "and upd.domain_id = d.id "+\
                "and d.name ="+ domain)

    def GetSQLReportFrom (self, type_analysis):
        #generic function to generate 'from' clauses
        #"type" is a list of two values: type of analysis and value of 
        #such analysis

        From = ""

        if (type_analysis is None or len(type_analysis) != 2): return From

        analysis = type_analysis[0]
        # value = type_analysis[1]

        if analysis == 'repository': From = self.GetSQLRepositoriesFrom()
        elif analysis == 'company': From = self.GetSQLCompaniesFrom(self.identities_db)
        elif analysis == 'country': From = self.GetSQLCountriesFrom(self.identities_db)
        elif analysis == 'domain': From = self.GetSQLDomainsFrom(self.identities_db)
        elif analysis == 'project': From = self.GetSQLProjectFrom()

        return (From)

    def GetSQLReportWhere (self, type_analysis, role):
        #generic function to generate 'where' clauses

        #"type" is a list of two values: type of analysis and value of 
        #such analysis

        where = ""

        if (type_analysis is None or len(type_analysis) != 2): return where

        analysis = type_analysis[0]
        value = type_analysis[1]

        if analysis == 'repository': where = self.GetSQLRepositoriesWhere(value)
        elif analysis == 'company': where = self.GetSQLCompaniesWhere(value, role)
        elif analysis == 'country': where = self.GetSQLCountriesWhere(value, role)
        elif analysis == 'domain': where = self.GetSQLDomainsWhere(value, role)
        elif analysis == 'project': where = self.GetSQLProjectWhere(value)

        return (where)

    # To be used in the future for apply a generic filter to all queries
    def GetCommitsFiltered(self):
        filters = ""
        return filters

    def GetPeopleQuerySCM (self, developer_id, period, startdate, enddate, evol) :
        fields ='COUNT(s.id) AS commits'
        tables = "scmlog s, people_upeople pup "
        filters = "pup.people_id = s.author_id "
        filters +=" AND pup.upeople_id="+str(developer_id)
        if (evol) :
            q = self.GetSQLPeriod(period,'s.date', fields, tables, filters,
                    startdate, enddate)
        else :
            fields += ",DATE_FORMAT (min(s.date),'%Y-%m-%d') as first_date, "+\
                      "DATE_FORMAT (max(s.date),'%Y-%m-%d') as last_date"
            q = self.GetSQLGlobal('s.date', fields, tables, filters, 
                    startdate, enddate)

        return (q)

    def GetEvolPeopleSCM (self, developer_id, period, startdate, enddate) :
        q = self.GetPeopleQuerySCM (developer_id, period, startdate, enddate, True)

        data = self.ExecuteQuery(q)
        return (data)

    def GetStaticPeopleSCM (self, developer_id, startdate, enddate) :
        q = self.GetPeopleQuerySCM (developer_id, None, startdate, enddate, False)

        data = self.ExecuteQuery(q)
        return (data)

    def GetPeopleIntake(self, min, max):
        filters = self.GetCommitsFiltered()
        if (filters != ""): filters  = " WHERE " + filters
        filters = ""

        q_people_num_commits_evol = """
            SELECT COUNT(*) AS total, author_id,
                YEAR(date) as year, MONTH(date) as monthid
            FROM scmlog
            %s
            GROUP BY author_id, year, monthid
            HAVING total > %i AND total <= %i
            ORDER BY date DESC
            """ % (filters, min, max)

        q_people_num_evol = """
            SELECT COUNT(*) as people, year*12+monthid AS month
            FROM (%s) t
            GROUP BY year, monthid
            """ % (q_people_num_commits_evol)

        return self.ExecuteQuery(q_people_num_evol)

class ITSQuery(DSQuery):
    """ Specific query builders for issue tracking system data source """
    def GetSQLRepositoriesFrom (self):
        # tables necessary for repositories 
        return (", trackers t")

    def GetSQLRepositoriesWhere (self, repository):
        # fields necessary to match info among tables
        return (" i.tracker_id = t.id and t.url = "+repository+" ")

    def GetSQLProjectsFrom (self):
        # tables necessary for repositories
        return (", trackers t")

    def GetSQLProjectsWhere (self, project, identities_db):
        # include all repositories for a project and its subprojects
        # Remove '' from project name
        if len(project) > 1 :
            if (project[0] == "'" and project[-1] == "'"):
                project = project[1:-1]

        subprojects = self.get_subprojects(project)

        repos = """ t.url IN (
               SELECT repository_name
               FROM   %s.projects p, %s.project_repositories pr
               WHERE  p.project_id = pr.project_id AND pr.data_source='its'
        """ % (identities_db, identities_db)

        if subprojects != "[]":
            repos += " AND p.project_id IN (%s) " % subprojects

        return (repos   + ") and t.id = i.tracker_id")

    def GetSQLCompaniesFrom (self, i_db):
        # fields necessary for the companies analysis

        return(" , people_upeople pup, "+\
               i_db+".companies c, "+\
               i_db+".upeople_companies upc")

    def GetSQLCompaniesWhere (self, name):
        # filters for the companies analysis
        return(" i.submitted_by = pup.people_id and "+\
               "pup.upeople_id = upc.upeople_id and "+\
               "upc.company_id = c.id and "+\
               "i.submitted_on >= upc.init and "+\
               "i.submitted_on < upc.end and "+\
               "c.name = "+name)

    def GetSQLCountriesFrom (self, i_db):
        # fields necessary for the countries analysis

        return(" , people_upeople pup, "+\
               i_db+".countries c, "+\
               i_db+".upeople_countries upc")

    def GetSQLCountriesWhere (self, name):
        # filters for the countries analysis
        return(" i.submitted_by = pup.people_id and "+\
               "pup.upeople_id = upc.upeople_id and "+\
               "upc.country_id = c.id and "+\
               "c.name = "+name)


    def GetSQLDomainsFrom (self, i_db):
        # fields necessary for the domains analysis

        return(" , people_upeople pup, "+\
               i_db+".domains d, "+\
               i_db+".upeople_domains upd")


    def GetSQLDomainsWhere (self, name):
        # filters for the domains analysis
        return(" i.submitted_by = pup.people_id and "+\
               "pup.upeople_id = upd.upeople_id and "+\
               "upd.domain_id = d.id and "+\
               "d.name = "+name)

    def GetSQLReportFrom (self, identities_db, type_analysis):
        #generic function to generate 'from' clauses
        #"type" is a list of two values: type of analysis and value of 
        #such analysis

        From = ""

        if (type_analysis is None or len(type_analysis) != 2): return From

        analysis = type_analysis[0]
        value = type_analysis[1]

        if analysis == 'repository': From = self.GetSQLRepositoriesFrom()
        elif analysis == 'company': From = self.GetSQLCompaniesFrom(identities_db)
        elif analysis == 'country': From = self.GetSQLCountriesFrom(identities_db)
        elif analysis == 'domain': From = self.GetSQLDomainsFrom(identities_db)
        elif analysis == 'project': From = self.GetSQLProjectsFrom()

        return (From)

    def GetSQLReportWhere (self, type_analysis, identities_db = None):
        #generic function to generate 'where' clauses

        #"type" is a list of two values: type of analysis and value of 
        #such analysis
        where = ""

        if (type_analysis is None or len(type_analysis) != 2): return where

        analysis = type_analysis[0]
        value = type_analysis[1]

        if analysis == 'repository': where = self.GetSQLRepositoriesWhere(value)
        elif analysis == 'company': where = self.GetSQLCompaniesWhere(value)
        elif analysis == 'country': where = self.GetSQLCountriesWhere(value)
        elif analysis == 'domain': where = self.GetSQLDomainsWhere(value)
        elif analysis == 'project': where = self.GetSQLProjectsWhere(value, identities_db)

        return (where)

    def GetSQLIssuesStudies (self, period, startdate, enddate, identities_db, type_analysis, evolutionary, study):
        # Generic function that counts evolution/agg number of specific studies with similar
        # database schema such as domains, companies and countries
        fields = ' count(distinct(name)) as ' + study
        tables = " issues i " + self.GetSQLReportFrom(identities_db, type_analysis)
        filters = self.GetSQLReportWhere(type_analysis, identities_db)

        #Filtering last part of the query, not used in this case
        #filters = gsub("and\n( )+(d|c|cou|com).name =.*$", "", filters)

        q = self.BuildQuery(period, startdate, enddate, " i.submitted_on ", fields, tables, filters, evolutionary)
        q = re.sub(r'and (d|c|cou|com).name.*=', "", q)

        return (q)

class MLSQuery(DSQuery):
    """ Specific query builders for mailing lists data source """
    def GetSQLRepositoriesFrom (self):
        # tables necessary for repositories
        #return (" messages m ") 
        return (" ")

    def GetSQLRepositoriesWhere (self, repository):
        # fields necessary to match info among tables
        return (" m.mailing_list_url = "+repository+" ")

    def GetSQLCompaniesFrom (self, i_db):
        # fields necessary for the companies analysis
        return(" , messages_people mp, "+\
                       "people_upeople pup, "+\
                       i_db+".companies c, "+\
                       i_db+".upeople_companies upc")

    def GetSQLCompaniesWhere (self, name):
        # filters for the companies analysis
        return(" m.message_ID = mp.message_id and "+\
                   "mp.email_address = pup.people_id and "+\
                   "mp.type_of_recipient=\'From\' and "+\
                   "pup.upeople_id = upc.upeople_id and "+\
                   "upc.company_id = c.id and "+\
                   "m.first_date >= upc.init and "+\
                   "m.first_date < upc.end and "+\
                   "c.name = "+name)

    def GetSQLCountriesFrom (self, i_db):
        # fields necessary for the countries analysis
        return(" , messages_people mp, "+\
                   "people_upeople pup, "+\
                   i_db+".countries c, "+\
                   i_db+".upeople_countries upc ")

    def GetSQLCountriesWhere (self, name):
        # filters necessary for the countries analysis

        return(" m.message_ID = mp.message_id and "+\
                   "mp.email_address = pup.people_id and "+\
                   "mp.type_of_recipient=\'From\' and "+\
                   "pup.upeople_id = upc.upeople_id and "+\
                   "upc.country_id = c.id and "+\
                   "c.name="+name)

    def GetSQLDomainsFrom (self, i_db) :
        return (" , messages_people mp, "+\
                   "people_upeople pup, "+\
                  i_db+".domains d, "+\
                  i_db+".upeople_domains upd")

    def GetSQLDomainsWhere (self, name) :
        return (" m.message_ID = mp.message_id and "+\
                    "mp.email_address = pup.people_id and "+\
                    "mp.type_of_recipient=\'From\' and "+\
                    "pup.upeople_id = upd.upeople_id AND "+\
                    "upd.domain_id = d.id AND "+\
                    "m.first_date >= upd.init AND "+\
                    "m.first_date < upd.end and "+\
                    "d.name="+ name)

    def GetSQLProjectsFrom(self):
        return (" , mailing_lists ml")

    def GetSQLProjectsWhere(self, project, identities_db):
        # include all repositories for a project and its subprojects
        p = project.replace("'", "") # FIXME: why is "'" needed in the name?

        repos = """and ml.mailing_list_url IN (
               SELECT repository_name
               FROM   %s.projects p, %s.project_repositories pr
               WHERE  p.project_id = pr.project_id AND p.project_id IN (%s)
                   AND pr.data_source='mls'
        )""" % (identities_db, identities_db, self.get_subprojects(p))

        return (repos  + " and ml.mailing_list_url = m.mailing_list_url")

    # Using senders only here!
    def GetFiltersOwnUniqueIds  (self) :
        return ('m.message_ID = mp.message_id AND '+\
                ' mp.email_address = pup.people_id AND '+\
                ' mp.type_of_recipient=\'From\'')

    ##########
    #Generic functions to obtain FROM and WHERE clauses per type of report
    ##########

    def GetSQLReportFrom (self, type_analysis):
        #generic function to generate 'from' clauses
        #"type" is a list of two values: type of analysis and value of 
        #such analysis

        From = ""

        if (type_analysis is None or len(type_analysis) != 2): return From

        analysis = type_analysis[0]

        if analysis == 'repository': From = self.GetSQLRepositoriesFrom()
        elif analysis == 'company': From = self.GetSQLCompaniesFrom(self.identities_db)
        elif analysis == 'country': From = self.GetSQLCountriesFrom(self.identities_db)
        elif analysis == 'domain': From = self.GetSQLDomainsFrom(self.identities_db)
        elif analysis == 'project': From = self.GetSQLProjectsFrom()

        return (From)


    def GetSQLReportWhere (self, type_analysis):
        #generic function to generate 'where' clauses
        #"type" is a list of two values: type of analysis and value of 
        #such analysisd

        where = ""

        if (type_analysis is None or len(type_analysis) != 2): return where

        analysis = type_analysis[0]
        value = type_analysis[1]

        if analysis == 'repository': where = self.GetSQLRepositoriesWhere(value)
        elif analysis == 'company': where = self.GetSQLCompaniesWhere(value)
        elif analysis == 'country': where = self.GetSQLCountriesWhere(value)
        elif analysis == 'domain': where = self.GetSQLDomainsWhere(value)
        elif analysis == 'project':
            if (self.identities_db is None):
                logging.error("project filter not supported without identities_db")
                sys.exit(0)
            else:
                where = self.GetSQLProjectsWhere(value, self.identities_db)

        return (where)

    def GetStudies (self, period, startdate, enddate, type_analysis, evolutionary, study):
        # Generic function that counts evolution/agg number of specific studies with similar
        # database schema such as domains, companies and countries

        fields = ' count(distinct(name)) as ' + study
        tables = " messages m " + self.GetSQLReportFrom(type_analysis)
        filters = self.GetSQLReportWhere(type_analysis) + " and m.is_response_of is null "

        #Filtering last part of the query, not used in this case
        #filters = gsub("and\n( )+(d|c|cou|com).name =.*$", "", filters)

        q = self.BuildQuery(period, startdate, enddate, " m.first_date ", fields, tables, filters, evolutionary)
        q = re.sub(r'(d|c|cou|com).name.*and', "", q)

        return q


class SCRQuery(DSQuery):
    """ Specific query builders for source code review source"""

    def GetSQLRepositoriesFrom (self):
        #tables necessaries for repositories
        return (" , trackers t")

    def GetSQLRepositoriesWhere (self, repository):
        #fields necessaries to match info among tables
        return (" and t.url ='"+ repository+ "' and t.id = i.tracker_id")

    def GetTablesOwnUniqueIds (self, table=''):
        tables = 'changes c, people_upeople pup'
        if (table == "issues"): tables = 'issues i, people_upeople pup'
        return (tables)


    def GetFiltersOwnUniqueIds  (self, table=''):
        filters = 'pup.people_id = c.changed_by'
        if (table == "issues"): filters = 'pup.people_id = i.submitted_by'
        return (filters)

    def GetSQLProjectFrom (self):
        # projects are mapped to repositories
        return (" , trackers t")

    def GetSQLProjectWhere (self, project, identities_db):
        # include all repositories for a project and its subprojects

        repos = """and t.url IN (
               SELECT repository_name
               FROM   %s.projects p, %s.project_repositories pr
               WHERE  p.project_id = pr.project_id AND p.project_id IN (%s)
                   AND pr.data_source='scr'
        )""" % (identities_db, identities_db, self.get_subprojects(project))

        return (repos   + " and t.id = i.tracker_id")

    def GetSQLCompaniesFrom (self, identities_db):
        #tables necessaries for companies
        return (" , people_upeople pup,"+\
                identities_db+".upeople_companies upc,"+\
                identities_db+".companies c")

    def GetSQLCompaniesWhere (self, company):
        #fields necessaries to match info among tables
        return ("and i.submitted_by = pup.people_id "+\
                  "and pup.upeople_id = upc.upeople_id "+\
                  "and i.submitted_on >= upc.init "+\
                  "and i.submitted_on < upc.end "+\
                  "and upc.company_id = c.id "+\
                  "and c.name ='"+ company+"'")

    def GetSQLCountriesFrom (self, identities_db):
        #tables necessaries for companies
        return (" , people_upeople pup, "+\
                  identities_db+".upeople_countries upc, "+\
                  identities_db+".countries c ")

    def GetSQLCountriesWhere (self, country):
        #fields necessaries to match info among tables
        return ("and i.submitted_by = pup.people_id "+\
                  "and pup.upeople_id = upc.upeople_id "+\
                  "and upc.country_id = c.id "+\
                  "and c.name ='"+country+"'")

    ##########
    #Generic functions to obtain FROM and WHERE clauses per type of report
    ##########
    def GetSQLReportFrom (self, identities_db, type_analysis):
        #generic function to generate 'from' clauses
        #"type" is a list of two values: type of analysis and value of
        #such analysis

        From = ""

        if (type_analysis is None or len(type_analysis) != 2): return From

        analysis = type_analysis[0]

        if (analysis):
            if analysis == 'repository': From = self.GetSQLRepositoriesFrom()
            elif analysis == 'company': From = self.GetSQLCompaniesFrom(identities_db)
            elif analysis == 'country': From = self.GetSQLCountriesFrom(identities_db)
            elif analysis == 'project': From = self.GetSQLProjectFrom()

        return (From)

    def GetSQLReportWhere (self, type_analysis, identities_db = None):
        #generic function to generate 'where' clauses

        #"type" is a list of two values: type of analysis and value of
        #such analysis

        where = ""
        if (type_analysis is None or len(type_analysis) != 2): return where

        analysis = type_analysis[0]
        value = type_analysis[1]

        if (analysis):
            if analysis == 'repository': where = self.GetSQLRepositoriesWhere(value)
            elif analysis == 'company': where = self.GetSQLCompaniesWhere(value)
            elif analysis == 'country': where = self.GetSQLCountriesWhere(value)
            elif analysis == 'project':
                if (identities_db is None):
                    logging.error("project filter not supported without identities_db")
                    sys.exit(0)
                else:
                    where = self.GetSQLProjectWhere(value, identities_db)
        return (where)

    def GetReviewsSQL (self, period, startdate, enddate, type_, type_analysis, evolutionary, identities_db):
        #Building the query
        fields = " count(distinct(i.issue)) as " + type_
        tables = "issues i" +  self.GetSQLReportFrom(identities_db, type_analysis)
        if type_ == "submitted": filters = ""
        elif type_ == "opened": filters = " (i.status = 'NEW' or i.status = 'WORKINPROGRESS') "
        elif type_ == "new": filters = " i.status = 'NEW' "
        elif type_ == "inprogress": filters = " i.status = 'WORKINGPROGRESS' "
        elif type_ == "closed": filters = " (i.status = 'MERGED' or i.status = 'ABANDONED') "
        elif type_ == "merged": filters = " i.status = 'MERGED' "
        elif type_ == "abandoned": filters = " i.status = 'ABANDONED' "
        filters += self.GetSQLReportWhere(type_analysis, identities_db)

        if (self.GetIssuesFiltered() != ""): filters += " AND " + self.GetIssuesFiltered()

        q = self.BuildQuery (period, startdate, enddate, "i.submitted_on", fields, tables, filters, evolutionary)

        return q

    # Reviews status using changes table
    def GetReviewsChangesSQL (self, period, startdate, enddate, type_, type_analysis, evolutionary, identities_db):
        fields = "count(issue_id) as "+ type_+ "_changes"
        tables = "changes c, issues i"
        tables += self.GetSQLReportFrom(identities_db, type_analysis)
        filters = "c.issue_id = i.id AND new_value='"+type_+"'"
        filters += self.GetSQLReportWhere(type_analysis, identities_db)

        q = self.BuildQuery (period, startdate, enddate, "changed_on", fields, tables, filters, evolutionary)

        if (self.GetChangesFiltered() != ""): filters += " AND " + self.GetChangesFiltered()

        return q

    def GetEvaluationsSQL (self, period, startdate, enddate, type_, type_analysis, evolutionary, identities_db = None):
        # verified - VRIF
        # approved - APRV
        # code review - CRVW
        # submitted - SUBM

        #Building the query
        fields = " count(distinct(c.id)) as " + type_
        tables = " changes c, issues i " + self.GetSQLReportFrom(identities_db, type_analysis)
        if type_ == "verified": filters =  " (c.field = 'VRIF' OR c.field = 'Verified') "
        elif type_ == "approved": filters =  " c.field = 'APRV'  "
        elif type_ == "codereview": filters =  "   (c.field = 'CRVW' OR c.field = 'Code-Review') "
        elif type_ == "sent": filters =  " c.field = 'SUBM'  "
        filters = filters + " and i.id = c.issue_id "
        filters = filters + self.GetSQLReportWhere(type_analysis, identities_db)

        q = self.BuildQuery (period, startdate, enddate, "c.changed_on",
                             fields, tables, filters, evolutionary)
        return q

    def GetWaiting4ReviewerSQL (self, period, startdate, enddate, identities_db, type_analysis, evolutionary):
        fields = " count(distinct(c.id)) as WaitingForReviewer "
        tables = " changes c, "+\
                 "  issues i, "+\
                 "        (select c.issue_id as issue_id, "+\
                 "                c.old_value as old_value, "+\
                 "                max(c.id) as id "+\
                 "         from changes c, "+\
                 "              issues i "+\
                 "         where c.issue_id = i.id and "+\
                 "               i.status='NEW' "+\
                 "         group by c.issue_id, c.old_value) t1 "
        tables = tables + self.GetSQLReportFrom(identities_db, type_analysis)
        filters =  " i.id = c.issue_id  "+\
                   "  and t1.id = c.id "+\
                   "  and (c.field='CRVW' or c.field='Code-Review' or c.field='Verified' or c.field='VRIF') "+\
                   "  and (c.new_value=1 or c.new_value=2) "
        filters = filters + self.GetSQLReportWhere(type_analysis, identities_db)

        q = self.BuildQuery (period, startdate, enddate, "c.changed_on",
                             fields, tables, filters, evolutionary)
        return q

    def GetWaiting4SubmitterSQL (self, period, startdate, enddate, identities_db, type_analysis, evolutionary):
        fields = "count(distinct(c.id)) as WaitingForSubmitter "
        tables = "  changes c, "+\
                 "   issues i, "+\
                 "        (select c.issue_id as issue_id, "+\
                 "                c.old_value as old_value, "+\
                 "                max(c.id) as id "+\
                 "         from changes c, "+\
                 "              issues i "+\
                 "         where c.issue_id = i.id and "+\
                 "               i.status='NEW' "+\
                 "         group by c.issue_id, c.old_value) t1 "
        tables = tables + self.GetSQLReportFrom(identities_db, type_analysis)
        filters = " i.id = c.issue_id "+\
                  "  and t1.id = c.id "+\
                  "  and (c.field='CRVW' or c.field='Code-Review' or c.field='Verified' or c.field='VRIF') "+\
                  "  and (c.new_value=-1 or c.new_value=-2) "
        filters = filters + self.GetSQLReportWhere(type_analysis, identities_db)

        q = self.BuildQuery (period, startdate, enddate, "c.changed_on",
                             fields, tables, filters, evolutionary)
        return q

    # Real reviews spend >1h, are not autoreviews, and bots are filtered out.
    def GetTimeToReviewQuerySQL (self, startdate, enddate, identities_db = None, type_analysis = [], bots = []):
        filter_bots = ''
        for bot in bots:
            filter_bots = filter_bots + " people.name<>'"+bot+"' and "

        # Subquery to get the time to review for all reviews
        fields = "TIMESTAMPDIFF(SECOND, submitted_on, changed_on)/(24*3600) AS revtime, changed_on "
        tables = "issues i, changes, people "
        tables = tables + self.GetSQLReportFrom(identities_db, type_analysis)
        filters = filter_bots + " i.id = changes.issue_id "
        filters += " AND people.id = changes.changed_by "
        filters += self.GetSQLReportWhere(type_analysis, identities_db)
        filters += " AND field='status' AND new_value='MERGED' "
        # remove autoreviews
        filters += " AND i.submitted_by<>changes.changed_by "
        filters += " ORDER BY changed_on "
        q = self.GetSQLGlobal('changed_on', fields, tables, filters,
                        startdate, enddate)
        # min_days_for_review = 0.042 # one hour
        # q = "SELECT revtime, changed_on FROM ("+q+") qrevs WHERE revtime>"+str(min_days_for_review)
        return (q)

    # Time to review accumulated for pending submissions using submit date or update date
    def GetTimeToReviewPendingQuerySQL (self, startdate, enddate, identities_db = None,
                                        type_analysis = [], bots = [], updated = False, reviewers = False):

        filter_bots = ''
        for bot in bots:
            filter_bots = filter_bots + " people.name<>'"+bot+"' AND "

        fields = "TIMESTAMPDIFF(SECOND, submitted_on, NOW())/(24*3600) AS revtime, submitted_on "
        if (updated):
            fields = "TIMESTAMPDIFF(SECOND, mod_date, NOW())/(24*3600) AS revtime, submitted_on "
        tables = "issues i, people, issues_ext_gerrit ie "
        if reviewers:
                q_last_change = self.get_sql_last_change_for_issues_new()
                tables += ", changes ch, (%s) t1" % q_last_change
        tables += self.GetSQLReportFrom(identities_db, type_analysis)
        filters = filter_bots + " people.id = i.submitted_by "
        filters += self.GetSQLReportWhere(type_analysis,identities_db)
        filters += " AND status<>'MERGED' AND status<>'ABANDONED' "
        filters += " AND ie.issue_id  = i.id "
        if reviewers:
                filters += """
                    AND i.id = ch.issue_id  AND t1.id = ch.id
                    AND (ch.field='CRVW' or ch.field='Code-Review' or ch.field='Verified' or ch.field='VRIF')
                    AND (ch.new_value=1 or ch.new_value=2)
                """

        if (self.GetIssuesFiltered() != ""): filters += " AND " + self.GetIssuesFiltered()

        filters += " ORDER BY  submitted_on"
        q = self.GetSQLGlobal('submitted_on', fields, tables, filters,
                              startdate, enddate)
        return(q)

    def get_sql_last_change_for_issues_new(self):
        # last changes for reviews. Removed added change status = NEW that is "artificial"
        q_last_change = """
            SELECT c.issue_id as issue_id,  max(c.id) as id
            FROM changes c, issues i
            WHERE c.issue_id = i.id and i.status='NEW' and field<>'status'
            GROUP BY c.issue_id
        """
        return q_last_change

    def GetPeopleQuerySubmissions (self, developer_id, period, startdate, enddate, evol):
        fields = "COUNT(i.id) AS submissions"
        tables = self.GetTablesOwnUniqueIds('issues')
        filters = self.GetFiltersOwnUniqueIds('issues')+ " AND pup.upeople_id = "+ str(developer_id)

        if (evol):
            q = self.GetSQLPeriod(period,'submitted_on', fields, tables, filters,
                    startdate, enddate)
        else:
            fields = fields + \
                    ",DATE_FORMAT (min(submitted_on),'%Y-%m-%d') as first_date, "+\
                    "  DATE_FORMAT (max(submitted_on),'%Y-%m-%d') as last_date"
            q = self.GetSQLGlobal('submitted_on', fields, tables, filters,
                    startdate, enddate)
        return (q)

    def GetPeopleEvolSubmissionsSCR (self, developer_id, period, startdate, enddate):
        q = self.GetPeopleQuerySubmissions(developer_id, period, startdate, enddate, True)
        return(self.ExecuteQuery(q))

    def GetPeopleStaticSubmissionsSCR (self, developer_id, startdate, enddate):
        q = self.GetPeopleQuerySubmissions(developer_id, None, startdate, enddate, False)
        return(self.ExecuteQuery(q))

    def GetPeopleIntake(self, min, max):
        filters = self.GetIssuesFiltered()
        if (filters != ""): filters  = " WHERE " + filters
        filters = ""

        q_people_num_submissions_evol = """
            SELECT COUNT(*) AS total, submitted_by,
                YEAR(submitted_on) as year, MONTH(submitted_on) as monthid
            FROM issues
            %s
            GROUP BY submitted_by, year, monthid
            HAVING total > %i AND total <= %i
            ORDER BY submitted_on DESC
            """ % (filters, min, max)

        q_people_num_evol = """
            SELECT COUNT(*) as people, year*12+monthid AS month
            FROM (%s) t
            GROUP BY year, monthid
            """ % (q_people_num_submissions_evol)

        return self.ExecuteQuery(q_people_num_evol)

    # No use of generic query because changes table is not used
    def GetCompaniesQuarters (self, year, quarter, identities_db, limit = 25):
        filters = self.GetIssuesFiltered()
        if (filters != ""): filters  += " AND "
        filters = ""
        q = """
            SELECT COUNT(i.id) AS total, c.name, c.id, QUARTER(submitted_on) as quarter, YEAR(submitted_on) year
            FROM issues i, people p , people_upeople pup, %s.upeople_companies upc,%s.companies c
            WHERE %s i.submitted_by=p.id AND pup.people_id=p.id
                AND pup.upeople_id = upc.upeople_id AND upc.company_id = c.id
                AND status='merged'
                AND QUARTER(submitted_on) = %s AND YEAR(submitted_on) = %s
              GROUP BY year, quarter, c.id
              ORDER BY year, quarter, total DESC, c.name
              LIMIT %s
            """ % (identities_db, identities_db, filters,  quarter, year, limit)

        return (self.ExecuteQuery(q))


    # PEOPLE
    def GetPeopleQuarters (self, year, quarter, identities_db, limit = 25, bots = []) :
        filter_bots = ''
        for bot in bots:
            filter_bots = filter_bots + " up.identifier<>'"+bot+"' AND "

        filters = self.GetIssuesFiltered()
        if (filters != ""): filters  = filter_bots + filters + " AND "
        else: filters = filter_bots

        filters = filter_bots

        q = """
            SELECT COUNT(i.id) AS total, p.name, pup.upeople_id as id,
                QUARTER(submitted_on) as quarter, YEAR(submitted_on) year
            FROM issues i, people p , people_upeople pup, %s.upeople up
            WHERE %s i.submitted_by=p.id AND pup.people_id=p.id AND pup.upeople_id = up.id
                AND status='merged'
                AND QUARTER(submitted_on) = %s AND YEAR(submitted_on) = %s
           GROUP BY year, quarter, pup.upeople_id
           ORDER BY year, quarter, total DESC, id
           LIMIT %s
           """ % (identities_db, filters, quarter, year, limit)
        return (self.ExecuteQuery(q))

    def GetPeopleList (self, startdate, enddate, bots):

        filter_bots = ""
        for bot in bots:
            filter_bots += " name<>'"+bot+"' and "

        fields = "DISTINCT(pup.upeople_id) as id, count(i.id) as total, name"
        tables = self.GetTablesOwnUniqueIds('issues') + ", people"
        filters = filter_bots
        filters += self.GetFiltersOwnUniqueIds('issues')+ " and people.id = pup.people_id"
        filters += " GROUP BY id ORDER BY total desc"
        q = self.GetSQLGlobal('submitted_on', fields, tables, filters, startdate, enddate)
        return(self.ExecuteQuery(q))

    def GetCompaniesName  (self,startdate, enddate, identities_db, limit = 0):
        limit_sql=""
        if (limit > 0): limit_sql = " LIMIT " + str(limit)

        q = "SELECT c.id as id, c.name as name, COUNT(DISTINCT(i.id)) AS total "+\
                   "FROM  "+identities_db+".companies c, "+\
                           identities_db+".upeople_companies upc, "+\
                    "     people_upeople pup, "+\
                    "     issues i "+\
                   "WHERE i.submitted_by = pup.people_id AND "+\
                   "  upc.upeople_id = pup.upeople_id AND "+\
                   "  c.id = upc.company_id AND "+\
                   "  i.status = 'merged' AND "+\
                   "  i.submitted_on >="+  startdate+ " AND "+\
                   "  i.submitted_on < "+ enddate+ " "+\
                   "GROUP BY c.name "+\
                   "ORDER BY total DESC " + limit_sql
        return(self.ExecuteQuery(q))

    # Global filter to remove all results from Wikimedia KPIs from SCR
    def __init__(self, user, password, database, identities_db = None, host="127.0.0.1", port=3306, group=None):
        super(SCRQuery, self).__init__(user, password, database, identities_db, host, port, group)
        # _filter_submitter_id as a static global var to avoid SQL re-execute
        people_userid = 'l10n-bot'
        q = "SELECT id FROM people WHERE user_id = '%s'" % (people_userid)
        self._filter_submitter_id = self.ExecuteQuery(q)['id']
        self._filter_submitter_id = None # don't filter in general

    # To be used for issues table
    def GetIssuesFiltered(self):
        filters = ""
        if self._filter_submitter_id is not None:
            filters = " submitted_by <> %s" % (self._filter_submitter_id)
        return filters

    # To be used for changes table
    def GetChangesFiltered(self):
        filters = ""
        if self._filter_submitter_id is not None:
            filters = " changed_by <> %s" % (self._filter_submitter_id)
        return filters

class IRCQuery(DSQuery):

    def GetSQLRepositoriesFrom (self):
        # tables necessary for repositories
        return (", channels c")

    def GetSQLRepositoriesWhere(self, repository):
        # filters necessaries for repositories
        return (" i.channel_id = c.id and c.name=" + repository)

    def GetSQLCompaniesFrom(self):
        # tables necessary to companies analysis
        return(" , people_upeople pup, " +\
               self.identities_db + "companies c, " +\
               self.identities_db + ".upeople_companies upc")

    def GetSQLCompaniesWhere(self, name):
        # filters necessary to companies analysis
        return(" i.nick = pup.people_id and "+\
               "pup.upeople_id = upc.upeople_id and "+\
               "upc.company_id = c.id and "+\
               "i.submitted_on >= upc.init and "+\
               "i.submitted_on < upc.end and "+\
               "c.name = " + name)

    def GetSQLCountriesFrom(self):
        # tables necessary to countries analysis
        return(" , people_upeople pup, " +\
               self.identities_db + ".countries c, " +\
               self.identities_db + ".upeople_countries upc")

    def GetSQLCountriesWhere(self, name):
        # filters necessary to countries analysis
        return(" i.nick = pup.people_id and "+\
               "pup.upeople_id = upc.upeople_id and "+\
               "upc.country_id = c.id and "+\
               "c.name = " + name)

    def GetSQLDomainsFrom(self):
        # tables necessary to domains analysis
        return(" , people_upeople pup, " +\
               self.identities_db + ".domains d, " +\
               self.identities_db + ".upeople_domains upd")

    def GetSQLDomainsWhere(self, name):
        # filters necessary to domains analysis
        return(" i.nick = pup.people_id and "+\
               "pup.upeople_id = upd.upeople_id and "+\
               "upd.domain_id = d.id and "+\
               "d.name = " + name)

    def GetTablesOwnUniqueIds (self) :
        tables = 'irclog, people_upeople pup'
        return (tables)

    def GetFiltersOwnUniqueIds (self) :
        filters = 'pup.people_id = irclog.nick'
        return (filters) 

    def GetSQLReportFrom(self, type_analysis):
        #generic function to generate 'from' clauses
        #"type" is a list of two values: type of analysis and value of 
        #such analysis

        From = ""

        if (type_analysis is None or len(type_analysis) != 2): return From

        analysis = type_analysis[0]

        if analysis == 'repository': From = self.GetSQLRepositoriesFrom()
        elif analysis == 'company': From = self.GetSQLCompaniesFrom(self.identities_db)
        elif analysis == 'country': From = self.GetSQLCountriesFrom(self.identities_db)
        elif analysis == 'domain': From = self.GetSQLDomainsFrom(self.identities_db)

        return (From)

    def GetSQLReportWhere (self, type_analysis):
        #generic function to generate 'where' clauses
        #"type" is a list of two values: type of analysis and value of 
        #such analysis

        where = ""

        if (type_analysis is None or len(type_analysis) != 2): return where

        analysis = type_analysis[0]
        value = type_analysis[1]

        if analysis == 'repository': where = self.GetSQLRepositoriesWhere(value)
        elif analysis == 'company': where = self.GetSQLCompaniesWhere(value)
        elif analysis == 'country': where = self.GetSQLCountriesWhere(value)
        elif analysis == 'domain': where = self.GetSQLDomainsWhere(value)

        return (where)

class MediawikiQuery(DSQuery):

    def GetTablesOwnUniqueIds () :
        tables = 'wiki_pages_revs, people_upeople pup'
        return (tables)

    def GetFiltersOwnUniqueIds () :
        filters = 'pup.people_id = wiki_pages_revs.user'
        return (filters) 

    def GetSQLReportFrom (self, type_analysis):
        return ""

    def GetSQLReportWhere (self, type_analysis):
        return ""


class QAForumsQuery(DSQuery):
    """ Specific query builders for question and answer platforms """

    def create_indexes(self):
        try:
            q = "create index q_id_a_idx on answers (question_identifier)"
            self.ExecuteQuery(q)
        except Exception:
            pass
            # logging.info("Indexes for QAForums already created")
            # import traceback
            # traceback.print_exc(file=sys.stdout)
        try:
            q = "create index q_id_qt_idx on questionstags (question_identifier)"
            self.ExecuteQuery(q)
        except:
            pass
        try:
            q = "create index tag_id_qt_idx on questionstags (question_identifier)"
            self.ExecuteQuery(q)
        except:
            pass
        try:
            q = "create index tag_idx_t on tags (tag)"
            self.ExecuteQuery(q)
        except:
            pass

    def GetSQLReportFrom(self, type_analysis):
        # generic function to generate "from" clauses
        # type_analysis contains two values: type of analysis (company, country...)
        # and the value itself

        #WARNING: if needed, identities_db is accessed as self.identities_db
        tables = ""
        report = ""
        value = ""

        if type_analysis is not None and len(type_analysis) == 2:
            report = type_analysis[0]
            value = type_analysis[1]

        #TODO: repository needs to be change to tag, once this is accepted as new
        #      data source in VizGrimoireJS-lib
        if report == "repository":
            tables = ", tags t, questionstags qt "

        #rest of reports to be implemented

        return tables

    def GetSQLReportWhere(self, type_analysis, table):
        # generic function to generate "where" clauses
        # type_analysis contains two values: type of analysis (company, country...)
        # and the value itself

        shorttable = str(table[0])

        #WARNING: if needed, identities_db is accessed as self.identities_db
        where = ""
        report = ""
        value = ""

        if type_analysis is not None and len(type_analysis) == 2:
            report = type_analysis[0]
            value = type_analysis[1]

        #TODO: repository needs to be change to tag, once this is accepted as new
        #      data source in VizGrimoireJS-lib
        if report == "repository":
            where = shorttable + ".question_identifier = qt.question_identifier and " +\
                    " qt.tag_id = t.id and t.tag = " + value

        return where

    def __get_date_field(self, table_name):
        # the tables of the Sibyl tool are not coherent among them
        #so we have different fields for the date of the different posts
        if (table_name == "questions"):
            return "added_at"
        elif (table_name == "answers"):
            return "submitted_on"
        elif (table_name == "comments"):
            return "submitted_on"
        # FIXME add exceptions here

    def __get_author_field(self, table_name):
        # the tables of the Sibyl tool are not coherent among them
        #so we have different fields for the author ids of the different posts
        if (table_name == "questions"):
            return "author_identifier"
        elif (table_name == "answers"):
            return "user_identifier"
        elif (table_name == "comments"):
            return "user_identifier"
        # FIXME add exceptions here

    def __get_metric_name(self, type_post, suffix):
        metric_str = ""
        if (type_post == "questions"):
            metric_str = "q"
        elif (type_post == "answers"):
            metric_str = "a"
        elif (type_post == "comments"):
            metric_str = "c"
        metric_str += suffix
        #else: raise UnexpectedParameter
        return metric_str

    def get_sent(self, period, startdate, enddate, type_analysis, evolutionary,
                 type_post = "questions"):
        # type_post has to be "comment", "question", "answer"

        date_field = self.__get_date_field(type_post)
        date_field = " " + date_field + " "

        if ( type_post == "questions"):
            fields = " count(distinct(q.id)) as qsent "
            tables = " questions q " + self.GetSQLReportFrom(type_analysis)
            filters = self.GetSQLReportWhere(type_analysis, "questions")
        elif ( type_post == "answers"):
            fields = " count(distinct(a.id)) as asent "
            tables = " answers a " + self.GetSQLReportFrom(type_analysis)
            filters = self.GetSQLReportWhere(type_analysis, "answers")
        else:
            fields = " count(distinct(c.id)) as csent "
            tables = " comments c " + self.GetSQLReportFrom(type_analysis)
            filters = self.GetSQLReportWhere(type_analysis, "comments")

        q = self.BuildQuery(period, startdate, enddate, date_field, fields, tables, filters, evolutionary)

        return q

    def get_senders(self, period, startdate, enddate, type_analysis, evolutionary,
                    type_post = "questions"):
        table_name = type_post
        date_field = self.__get_date_field(table_name)
        author_field = self.__get_author_field(table_name)


        if ( type_post == "questions"):
            fields = " count(distinct(q.%s)) as qsenders " % (author_field)
            tables = " questions q " + self.GetSQLReportFrom(type_analysis)
            filters = self.GetSQLReportWhere(type_analysis, "questions")
        elif ( type_post == "answers"):
            fields = " count(distinct(a.%s)) as asenders " % (author_field)
            tables = " answers a " + self.GetSQLReportFrom(type_analysis)
            filters = self.GetSQLReportWhere(type_analysis, "answers")
        else:
            fields = " count(distinct(c.%s)) as csenders " % (author_field)
            tables = " comments c " + self.GetSQLReportFrom(type_analysis)
            filters = self.GetSQLReportWhere(type_analysis, "comments")


        q = self.BuildQuery(period, startdate, enddate, date_field, fields, tables, filters, evolutionary)

        return q



    def static_num_sent(self, period, startdate, enddate, type_analysis=[],
                        type_post = "questions"):
        table_name = type_post #type_post matches the name of the table
        date_field = self.__get_date_field(table_name)
        prefix_table = table_name[0]

        if type_post == "questions":
            metric_name = "qsent"
        if type_post == "answers":
            metric_name = "asent"
        if type_post == "comments":
            metric_name = "csent"

        fields = "SELECT count(distinct("+prefix_table+".id)) as "+metric_name+", \
        DATE_FORMAT (min(" + prefix_table + "." + date_field + "), '%Y-%m-%d') as first_date, \
        DATE_FORMAT (max(" + prefix_table + "." + date_field + "), '%Y-%m-%d') as last_date "

        tables = " FROM %s %s " % (table_name, prefix_table)
        tables = tables + self.GetSQLReportFrom(type_analysis)

        filters = "WHERE %s.%s >= %s AND %s.%s < %s " % (prefix_table, date_field, startdate, prefix_table, date_field, enddate)
        extra_filters = self.GetSQLReportWhere(type_analysis, type_post)
        if extra_filters <> "":
            filters = filters + " and " + extra_filters

        q = fields + tables + filters

        return q

    def static_num_senders(self, period, startdate, enddate, type_analysis=[],
                           type_post = "questions"):
        table_name = type_post #type_post matches the name of the table
        date_field = self.__get_date_field(table_name)
        author_field = self.__get_author_field(table_name)
        prefix_table = table_name[0]

        if type_post == "questions":
            metric_name = "qsenders"
        if type_post == "answers":
            metric_name = "asenders"
        if type_post == "comments":
            metric_name = "csenders"

        fields = "SELECT count(distinct(%s.%s)) as %s" % (prefix_table, author_field, metric_name)
        tables = " FROM %s %s " % (table_name, prefix_table)
        tables = tables + self.GetSQLReportFrom(type_analysis)
        filters = "WHERE %s.%s >= %s AND %s.%s < %s " % (prefix_table, date_field, startdate, prefix_table, date_field, enddate)
        extra_filters = self.GetSQLReportWhere(type_analysis, type_post)
        if extra_filters <> "":
            filters = filters + " and " + extra_filters
        q = fields + tables + filters

        return q


class DownloadsDSQuery(DSQuery):
    """ Specific query builders for downloads """

    pass

class ReleasesDSQuery(DSQuery):
    """ Specific query builders for downloads """
    pass
