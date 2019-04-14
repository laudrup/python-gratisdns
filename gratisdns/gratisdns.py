# -*- encoding: utf-8 -*-
"""
Copyright (c) 2007 Mads Sülau Jørgensen <mads@sulau.dk>

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

from urllib.parse import parse_qs, urlparse

import requests
from requests_html import HTML, HTMLSession

__version__ = '$Id$'
__license__ = 'MIT'
__copyright__ = 'Mads Sülau Jørgensen <mads@sulau.dk>'


class GratisDNSError(Exception):
    pass


class Record(object):
    def __eq__(self, other):
        if not isinstance(other, Record):
            return NotImplemented
        return vars(self) == vars(other)

    def __repr__(self):
        return f'{type(self).__name__}: {vars(self)}'

    @property
    def record_type(self):
        return type(self).__name__.split("Record")[0]


class ARecord(Record):
    def __init__(self, user_domain, name, ip, id=None, ttl='43200'):
        self.user_domain = user_domain
        self.name = name
        self.ip = ip
        self.id = id
        self.ttl = ttl


class AAAARecord(Record):
    def __init__(self, user_domain, name, ip, id=None, ttl='43200'):
        self.user_domain = user_domain
        self.name = name
        self.ip = ip
        self.id = id
        self.ttl = ttl


class CNAMERecord(Record):
    pass


class MXRecord(Record):
    def __init__(self, user_domain, name, exchanger, preference=None, id=None, ttl='43200'):
        self.user_domain = user_domain
        self.name = name
        self.exchanger = exchanger
        self.preference = preference
        self.id = id
        self.ttl = ttl


class TXTRecord(Record):
    def __init__(self, user_domain, name, txtdata, id=None, ttl='43200'):
        self.user_domain = user_domain
        self.name = name
        self.txtdata = txtdata
        self.id = id
        self.ttl = ttl


class SRVRecord(Record):
    pass


class GratisDNS(object):
    BACKEND_URL = 'https://admin.gratisdns.com/'
    SUPPORTED_RECORDS = ('A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV')

    def __init__(self, username: str, password: str):
        self.__session = HTMLSession()

        payload = {
            'action': 'logmein',
            'login': username,
            'password': password
        }
        response = self.__session.post(GratisDNS.BACKEND_URL, data=payload, allow_redirects=False)

        if response.status_code != requests.codes.found:
            # Unfortunately, GratisDNS doesn't user proper HTTP status
            # codes, but does use a redirect on successfull login, so
            # assume anything else is an error.
            raise GratisDNSError('Login response was not redirect. Possibly invalid username/password')

    def __get_domains(self, action: str, table_id: str) -> list:
        domains = []
        response = self.__session.get(GratisDNS.BACKEND_URL, params={'action': action})
        table = response.html.find(table_id, first=True)
        for domain in table.find('tr'):
            domain_change_link = domain.find('a', containing='Ændre', first=True)
            if domain_change_link:
                href = domain_change_link.attrs['href']
                query = parse_qs(urlparse(href).query)
                domains.append(query['user_domain'][0])
        return domains

    def __record_from_dict(self, record_type: str, record_entries: dict) -> Record:
        if record_type == 'A':
            return ARecord(record_entries.get('user_domain'),
                           record_entries['Hostname'],
                           record_entries['IPv4'],
                           id=record_entries.get('id'),
                           ttl=record_entries['TTL'])

        elif record_type == 'AAAA':
            return AAAARecord(record_entries.get('user_domain'),
                              record_entries['Hostname'],
                              record_entries['IPv6'],
                              id=record_entries.get('id'),
                              ttl=record_entries['TTL'])

        elif record_type == 'CNAME':
            raise NotImplementedError()

        elif record_type == 'MX':
            return MXRecord(record_entries.get('user_domain'),
                            record_entries['Hostname'],
                            record_entries['Exchanger'],
                            record_entries['Preference'],
                            id=record_entries.get('id'),
                            ttl=record_entries['TTL'])

        elif record_type == 'TXT':
            return TXTRecord(record_entries.get('user_domain'),
                             record_entries['Hostname'],
                             record_entries['Text'],
                             id=record_entries.get('id'),
                             ttl=record_entries['TTL'])

        elif record_type == 'SRV':
            raise NotImplementedError()

        raise NotImplementedError()

    def __record_change_query_from_column(self, column) -> dict:
        record_change_link = column.find('a', containing='Ændre', first=True)
        if record_change_link:
            href = record_change_link.attrs['href']
            query = parse_qs(urlparse(href).query)
            return {k: v[0] for k, v in query.items()}
        return {}

    def __get_records(self, html: HTML) -> dict:
        records = {}
        for entry in html.find('.dns-records'):
            record_type = entry.find('h2', first=True).element.text.strip()
            if record_type not in self.SUPPORTED_RECORDS:
                continue
            table = entry.find('table', first=True)
            headers = [h.text for h in table.find('thead', first=True).find('tr', first=True).find('th')]
            record_entries = []
            for row in table.find('tbody', first=True).find('tr'):
                cols = row.find('td')
                entry = {}
                for i, h in enumerate(headers):
                    column = cols[i]
                    if h:
                        entry[h] = column.text
                    else:
                        record_change_link_query = self.__record_change_query_from_column(column)
                        if record_change_link_query:
                            entry['id'] = record_change_link_query['id']
                            entry['user_domain'] = record_change_link_query['user_domain']
                if entry:
                    record_entries.append(self.__record_from_dict(record_type, entry))
            if record_entries:
                records[record_type] = record_entries
        return records

    def create_record(self, domain, host, type, data, preference=None, weight=None, port=None):
        raise NotImplementedError()

    def update_record(self, record: Record):
        if record.record_type not in self.SUPPORTED_RECORDS:
            raise NotImplementedError()

        form_data = vars(record)
        form_data['action'] = f'dns_primary_record_update_{record.record_type.lower()}'
        self.__session.post(GratisDNS.BACKEND_URL,
                            data=form_data)

    def delete_record(self, domain, host, type=None, preference=None):
        raise NotImplementedError()

    def get_primary_domains(self):
        return self.__get_domains('dns_primarydns', '#primarydnslist')

    def get_secondary_domains(self):
        return self.__get_domains('dns_secondarydns', '#secondarydnslist')

    def get_primary_domain_details(self, domain: str):
        response = self.__session.get(GratisDNS.BACKEND_URL, params={'action': 'dns_primary_changeDNSsetup',
                                                                     'user_domain': domain})
        return self.__get_records(response.html)

    def create_primary_domain(self, domain):
        raise NotImplementedError()

    def create_secondary_domain(self, domain, master, slave='xxx.xxx.xxx.xxx'):
        raise NotImplementedError()

    def delete_primary_domain(self, domain):
        raise NotImplementedError()

    def delete_secondary_domain(self, domain):
        raise NotImplementedError()

    def import_from_axfr(self, domain, slave='127.0.0.1'):
        raise NotImplementedError()
