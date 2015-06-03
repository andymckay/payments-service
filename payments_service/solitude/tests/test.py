from urllib import urlencode

from nose.tools import eq_, raises
from slumber.exceptions import HttpClientError, HttpServerError

from payments_service.base.tests import (AuthenticatedTestCase,
                                         WithDynamicEndpoints)

from .. import SolitudeBodyguard


class TestSolitudeBodyguard(AuthenticatedTestCase, WithDynamicEndpoints):

    def setUp(self):
        super(TestSolitudeBodyguard, self).setUp()

        class DefaultEndpoint(SolitudeBodyguard):
            methods = ['get', 'post']
            # Hook up a random (and unrealistic) Solitude endpoint.
            resource = 'services.status'

        self.endpoint(DefaultEndpoint)

        # Set some default return values. These will most likely get overidden.
        self.solitude.services.status.get.return_value = {}
        self.solitude.services.status.post.return_value = {}

    def get(self, **kw):
        return self._request('get', **kw)

    def post(self, params={}, **kw):
        return self._request('post', params, **kw)

    def _request(self, method, *args, **kw):
        url = '/dynamic-endpoint'
        query_params = kw.pop('query_params', None)
        if query_params:
            url = '{url}?{query}'.format(url=url,
                                         query=urlencode(query_params))
        res = getattr(self.client, method)(url, *args, **kw)
        return self.json(res)

    def test_disallow_post(self):

        class GetOnly(SolitudeBodyguard):
            methods = ['get']
            resource = 'services.status'

        self.endpoint(GetOnly)

        self.solitude.services.status.post.side_effect = RuntimeError(
            'post should not be called')
        res, data = self.post()
        eq_(res.status_code, 405, res)
        eq_(data['error_message'], 'Method Not Allowed')

    def test_disallow_get(self):

        class PostOnly(SolitudeBodyguard):
            methods = ['post']
            resource = 'services.status'

        self.endpoint(PostOnly)

        self.solitude.services.status.get.side_effect = RuntimeError(
            'get should not be called')
        res, data = self.get()
        eq_(res.status_code, 405, res)
        eq_(data['error_message'], 'Method Not Allowed')

    def test_pass_post_params_to_solitude(self):
        params = {'foo': '1', 'bar': 'baz'}
        self.post(params)
        call_args = self.solitude.services.status.post.call_args
        eq_(call_args[0][0]['foo'], params['foo'])
        eq_(call_args[0][0]['bar'], params['bar'])

    def test_pass_get_params_to_solitude(self):
        params = {'foo': '1', 'bar': 'baz'}
        self.get(query_params=params)
        call_args = self.solitude.services.status.get.call_args
        eq_(call_args[1]['foo'], params['foo'])
        eq_(call_args[1]['bar'], params['bar'])

    def test_replace_call_args(self):
        new_args = ('one', 'two')
        new_kw = {'other': 'something'}

        class Replacer(SolitudeBodyguard):
            methods = ['get']
            resource = 'services.status'

            def replace_call_args(self, django_request, args, kw):
                return new_args, new_kw

        self.endpoint(Replacer)

        self.get(query_params={'foo': 1})
        call_args = self.solitude.services.status.get.call_args
        eq_(call_args, [new_args, new_kw])

    def test_proxy_solitude_response(self):
        self.solitude.services.status.get.return_value = {
            'item': 'value'
        }
        res, data = self.get()
        eq_(data['item'], 'value')

    @raises(HttpServerError)
    def test_500_in_solitude_raises_exception(self):
        exc = HttpServerError('500')
        self.solitude.services.status.get.side_effect = exc
        self.get()

    def test_bad_request_without_content(self):
        exc = HttpClientError('400')
        self.solitude.services.status.post.side_effect = exc
        res, data = self.post()
        eq_(res.status_code, 400, res)
        eq_(data['error_message'], 'Bad Request')
        eq_(data['error_response'], {})

    def test_bad_request_with_content(self):
        exc = HttpClientError('400')
        # Simulate a form error.
        exc.content = {'field-name': ['was invalid']}

        self.solitude.services.status.post.side_effect = exc
        res, data = self.post()
        eq_(data['error_message'], 'Bad Request')
        eq_(data['error_response'], exc.content)
        eq_(res.status_code, 400)
