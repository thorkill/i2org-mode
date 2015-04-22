#!/usr/bin/env python
# 2015-04-22 Rafal Lesniak
# 03/21/2010 jcvernaleo (john@netpurgatory.com)
# $Id: read_ical.py,v 1.2 2010/03/31 01:29:27 john Exp $
# Copyright 2010 John C. Vernaleo
# read_ical v0.1
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# See the file gpl.txt in the same directory as this.
#
# This is a first pass at a python interface to ical files (specifically
# what Apple's iCal considers an ical file.  It only handle's todo items
# (VTODO) at the moment since that was all I wanted.
#
# The main purpose of it was to convert iCal todo's to a format I can use
# with emacs org-mode.  Thanks to this I was able to completely move my todo
# lists (and I really depend on todo lists) from iCal (which I never liked)
# to emacs (which I really like).
# I may try to improve this, but for now it does what I needed.

import argparse
import re
import sys

from pprint import pprint
from datetime import datetime, tzinfo, date
from icalendar import Calendar

class calendar:
      def __init__(self):
            self.timezone = None
            self.name = None
            self.version = None
            self.todo_list = []

      def get_orgmode_header(self):
            lines = []
            lines.append("# -*- mode:org -*-\n")
            lines.append("#+FILETAGS: :{}:\n".format(self.name))
            lines.append("#+TODO: TODO(t) STARTED(s) WAITING(w) | DONE(d) CANCELED(c)\n")
            return "".join(lines)

class todo:
      """A simple class to hold a single TODO element from ical
      along with some routines to work with it.  The goal is to get
      data out of ical and into emacs org-mode.
      """
      def __init__(self, timezone='UTC'):
            self.created=""
            self.UID=""
            self.summary=""
            self.completed=""
            self.location = ""
            self.due=""
            self.sched = ""
            self.description=""
            self.tz = tzinfo(timezone)
            return

      def get_item(self,line,item,name):
            if not item:
                  term=re.compile(name)
                  result=term.match(line)
                  if result:
                        return(term.split(line)[1])
                  else:
                        return
            else:
                  return(item)

      def read_ical_line(self,line):
            return

      def org_mode_date(self,date):
            """This is assuming that dates are always in the form
            YYYYMMDD followed by other stuff I don't care about.
            org mode allows for more precision for the completion dates
            but the extra info in the ical files doesn't look very helpful.
            """
            return date.strftime("%Y-%m-%d %H:%M")

      def get_orgmode_line(self, level=2, astodo=True):
            lines = []
            lines.append("*"*level)
            if astodo:
                  if not (self.completed):
                        lines.append(" TODO "+self.summary)
                  else:
                        lines.append(" DONE "+self.summary)
            else:
                  lines.append(" "+self.summary)

            if self.sched or self.due:
                  lines.append("\n   ")

            if self.sched:
                  lines.append("SCHEDULED: <{}>".format(self.org_mode_date(self.sched)))
                  if self.due:
                        lines.append(" ")

            if self.due:
                  lines.append("DEADLINE: <{}>".format(self.org_mode_date(self.due)))

            if self.completed:
                  if not self.due:
                        lines.append("  ")
                  lines.append(" CLOSED: ["+self.org_mode_date(self.completed)+"]")

            lines.append("\n")
            if self.UID:
                  lines.append(("   :PROPERTIES:\n   :ID: {}\n   :LOCATION: {}\n   :END:\n".format(self.UID,
                                                                                              self.location)))
            if self.description:
                  lines.append("   #+BEGIN_ASCII\n")
                  for a in self.description.splitlines():
                        lines.append("   {}\n".format(a))
                  lines.append("\n   #+END_ASCII\n")
            return "".join(lines)

def read_ical(fh, pastlimit=0):
      """This function reads a filename and put any VTODO items it finds
      in a list of TODO objects.
      """
      today = date.today()
      cal = Calendar.from_ical(fh.read())
      lcal = calendar()
      for line in cal.walk():

            if line.name == 'VCALENDAR':
                  lcal.name = line.get('X-WR-CALNAME')
                  lcal.version = line.get('VERSION')
            elif line.name == 'VEVENT':

                  t = todo()

                  t.UID = line.get('UID')
                  t.summary = line.get("SUMMARY", '')
                  try:
                        dt = line.decoded("created")
                        if dt:
                              t.created = dt
                  except KeyError as e:
                        pass

                  dt = line.decoded('dtstart')
                  if dt:
                        t.sched = dt

                  dt = line.decoded('dtend')
                  if dt:
                        t.due = dt

                  t.description = line.get('DESCRIPTION', '')
                  t.location = line.get('LOCATION', '')

                  if pastlimit == 0 or abs(datetime.today() - datetime(*(dt.timetuple()[:6]))).days <= pastlimit:
                        lcal.todo_list.append(t)

      return lcal

if __name__ == "__main__":

      parser = argparse.ArgumentParser()
      parser.add_argument("-o", "--outfile", default=sys.stdout, help="name of the output file")
      parser.add_argument("-i", "--infile", required=True, default=sys.stdin, help="name of the input file")
      parser.add_argument("-T", "--astodo", default=True, help="do not set events as TODO", action="store_true")
      parser.add_argument("-P", "--pastlimit", default=0, help="limit timeframe into the past (in days)", type=int)

      args = parser.parse_args()

      if args.infile != parser.get_default('infile'):
            fh = open(args.infile,'rb')

      if args.outfile != parser.get_default('outfile'):
            fh_w = open(args.outfile,'wb')

      lcal = read_ical(fh, pastlimit=args.pastlimit)

      fh_w.write(bytes(lcal.get_orgmode_header(), 'UTF-8'))
      for item in lcal.todo_list:
            fh_w.write(bytes(item.get_orgmode_line(astodo=args.astodo),'UTF-8'))
