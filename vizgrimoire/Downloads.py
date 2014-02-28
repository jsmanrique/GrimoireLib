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
## This file is a part of the vizGrimoire R package
##  (an R library for the MetricsGrimoire and vizGrimoire systems)
##
## Authors:
##   Daniel Izquierdo <dizquierdo@bitergia.com>


# All of the functions found in this file expect to find a database
# with the followin format:
# Table: downloads
#       Fields:
#       

from GrimoireSQL import GetSQLGlobal, GetSQLPeriod, ExecuteQuery, BuildQuery
from GrimoireUtils import GetPercentageDiff, GetDates, completePeriodIds

def GetDownloads(period, startdate, enddate, evolutionary):
    # Generic function to obtain number of downloads 
    fields = "count(*) as downloads"
    tables = "downloads"
    filters = ""
   
    query = BuildQuery(period, startdate, enddate, " date ", fields, tables, filters, evolutionary)
    return(ExecuteQuery(query))

def EvolDownloads(period, startdate, enddate):
    # Evolution of downloads
    return GetDownloads(period, startdate, enddate, True)

def AggDownloads(period, startdate, enddate):
    # Agg number of downloads
    return GetDownloads(period, startdate, enddate, False)

