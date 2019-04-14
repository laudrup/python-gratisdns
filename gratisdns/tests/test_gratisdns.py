import os
import unittest
from urllib.parse import parse_qs

import requests
import requests_mock

from gratisdns import AAAARecord, ARecord, GratisDNS, MXRecord, TXTRecord


def mocked_response(fname):
    path = os.path.sep.join((os.path.dirname(os.path.abspath(__file__)), fname))
    return open(path, 'r').read()


class FormMatcher(object):
    def __init__(self):
        self.query = {}

    def __call__(self, request):
        response = requests.Response()
        response.status_code = 200
        assert(request.headers['Content-Type'] == 'application/x-www-form-urlencoded')
        self.form_data = {k: v[0] for k, v in parse_qs(request.text).items()}
        return response


@requests_mock.Mocker()
class TestGratisDns(unittest.TestCase):
    def setUp(self):
        with requests_mock.Mocker() as mock_request:
            mock_request.post(GratisDNS.BACKEND_URL, status_code=requests.codes.found)
            self.gratisdns = GratisDNS('user', 'password')

    def test_get_primary_domains(self, mock_request):
        mock_request.get(GratisDNS.BACKEND_URL, text=mocked_response('primary_domains.html'))
        self.assertEqual(self.gratisdns.get_primary_domains(), ['mytest.dk', 'mytest2.dk'])

    def test_get_seconday_domains(self, mock_request):
        mock_request.get(GratisDNS.BACKEND_URL, text=mocked_response('secondary_domains.html'))
        self.assertEqual(self.gratisdns.get_secondary_domains(), [])

    def test_get_primary_domain_details(self, mock_request):
        mock_request.get(GratisDNS.BACKEND_URL, text=mocked_response('primary_domain_details.html'))
        records = self.gratisdns.get_primary_domain_details('mytest.dk')
        self.assertEqual(len(records), 4)

        for record in records['A']:
            self.assertIsInstance(record, ARecord)
        self.assertListEqual(records['A'], [
            ARecord('mytest.dk', '*.mytest.dk', '1.2.3.4', id='42'),
            ARecord('mytest.dk', 'mytest.dk', '1.2.3.4', id='17'),
            ARecord(None, 'localhost.mytest.dk', '127.0.0.1')
        ])

        for record in records['AAAA']:
            self.assertIsInstance(record, AAAARecord)
        self.assertEqual(records['AAAA'], [
            AAAARecord('mytest.dk', 'mytest.dk', '2001:db8:85a3:8d3:1319:8a2e:370:7348', id='1337')
        ])

        for record in records['MX']:
            self.assertIsInstance(record, MXRecord)
        self.assertEqual(records['MX'], [
            MXRecord('mytest.dk', 'mytest.dk', 'mytest.dk', '10', id='666')
        ])

        for record in records['TXT']:
            self.assertIsInstance(record, TXTRecord)
        self.assertEqual(records['TXT'], [
            TXTRecord('mytest.dk', 'mytest.dk', 'lumskebuks', id='1992')
        ])

    def test_update_a_record(self, mock_request):
        matcher = FormMatcher()
        mock_request.get(GratisDNS.BACKEND_URL, text=mocked_response('primary_domain_details.html'))
        mock_request.post(GratisDNS.BACKEND_URL, additional_matcher=matcher)

        record = self.gratisdns.get_primary_domain_details('mytest.dk')['A'][0]
        record.ip = '13.13.13.13'
        self.gratisdns.update_record(record)
        self.assertDictEqual(matcher.form_data,
                             {'user_domain': 'mytest.dk',
                              'name': '*.mytest.dk',
                              'ip': '13.13.13.13',
                              'id': '42',
                              'ttl': '43200',
                              'action': 'dns_primary_record_update_a'})

    def test_update_aaaa_record(self, mock_request):
        matcher = FormMatcher()
        mock_request.get(GratisDNS.BACKEND_URL, text=mocked_response('primary_domain_details.html'))
        mock_request.post(GratisDNS.BACKEND_URL, additional_matcher=matcher)

        record = self.gratisdns.get_primary_domain_details('mytest.dk')['AAAA'][0]
        record.ip = '1234:5678:90ab:cdef:1234:5678:90ab:cdef'
        self.gratisdns.update_record(record)
        self.assertDictEqual(matcher.form_data,
                             {'user_domain': 'mytest.dk',
                              'name': 'mytest.dk',
                              'ip': '1234:5678:90ab:cdef:1234:5678:90ab:cdef',
                              'id': '1337',
                              'ttl': '43200',
                              'action': 'dns_primary_record_update_aaaa'})

    def test_update_mx_record(self, mock_request):
        matcher = FormMatcher()
        mock_request.get(GratisDNS.BACKEND_URL, text=mocked_response('primary_domain_details.html'))
        mock_request.post(GratisDNS.BACKEND_URL, additional_matcher=matcher)

        record = self.gratisdns.get_primary_domain_details('mytest.dk')['MX'][0]
        record.exchanger = 'testpost.dk'
        self.gratisdns.update_record(record)
        self.assertDictEqual(matcher.form_data,
                             {'user_domain': 'mytest.dk',
                              'name': 'mytest.dk',
                              'exchanger': 'testpost.dk',
                              'id': '666',
                              'preference': '10',
                              'ttl': '43200',
                              'action': 'dns_primary_record_update_mx'})

    def test_update_txt_record(self, mock_request):
        matcher = FormMatcher()
        mock_request.get(GratisDNS.BACKEND_URL, text=mocked_response('primary_domain_details.html'))
        mock_request.post(GratisDNS.BACKEND_URL, additional_matcher=matcher)

        record = self.gratisdns.get_primary_domain_details('mytest.dk')['TXT'][0]
        record.txtdata = 'fjollerik'
        self.gratisdns.update_record(record)
        self.assertDictEqual(matcher.form_data,
                             {'user_domain': 'mytest.dk',
                              'name': 'mytest.dk',
                              'txtdata': 'fjollerik',
                              'id': '1992',
                              'ttl': '43200',
                              'action': 'dns_primary_record_update_txt'})
