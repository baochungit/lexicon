from base import Provider as BaseProvider
import requests
import json

class Provider(BaseProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)
        self.domain_id = None
        self.api_endpoint = provider_options.get('api_endpoint') or 'https://api.dnspark.com/v2'

    def authenticate(self):

        payload = self._get('/dns/{0}'.format(self.options['domain']))

        if not payload['additional']['domain_id']:
            raise StandardError('No domain found')

        self.domain_id = payload['additional']['domain_id']


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        record = {
            'rname': self._relative_name(name),
            'rtype': type,
            'rdata': content
        }
        payload = {}
        try:
            payload = self._post('/dns/{0}'.format(self.domain_id), record)
        except requests.exceptions.HTTPError, e:
            if e.response.status_code == 400:
                payload = {}
            raise e
                # http 400 is ok here, because the record probably already exists
        print 'create_record: {0}'.format(True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}

        payload = self._get('/dns/{0}'.format(self.domain_id))
        records = []
        for record in payload['records']:
            processed_record = {
                'type': record['rtype'],
                'name': record['rname'],
                'ttl': record['ttl'],
                'content': record['rdata'],
                'id': record['record_id']
            }
            records.append(processed_record)

        if type:
            records = [record for record in records if record['type'] == type]
        if name:
            records = [record for record in records if record['name'] == self._full_name(name)]
        if content:
            records = [record for record in records if record['content'] == content]

        print 'list_records: {0}'.format(records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {
            'ttl': 300
        }
        if type:
            data['rtype'] = type
        if name:
            data['rname'] = self._relative_name(name)
        if content:
            data['rdata'] = content

        payload = self._put('/dns/{0}'.format(identifier), data)

        print 'update_record: {0}'.format(True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if not identifier:
            records = self.list_records(type, name, content)
            print records
            if len(records) == 1:
                identifier = records[0]['id']
            else:
                raise StandardError('Record identifier could not be found.')
        payload = self._delete('/dns/{0}'.format(identifier))

        # is always True at this point, if a non 200 response is returned an error is raised.
        print 'delete_record: {0}'.format(True)
        return True


    # Helpers


    def _full_name(self, record_name):
        record_name = record_name.rstrip('.') # strip trailing period from fqdn if present
        #check if the record_name is fully specified
        if not record_name.endswith(self.options['domain']):
            record_name = "{0}.{1}".format(record_name, self.options['domain'])
        return record_name

    def _relative_name(self, record_name):
        record_name = record_name.rstrip('.') # strip trailing period from fqdn if present
        #check if the record_name is fully specified
        if record_name.endswith(self.options['domain']):
            record_name = record_name[:-len(self.options['domain'])]
            record_name = record_name.rstrip('.')
        return record_name

    def _get(self, url='/', query_params={}):
        return self._request('GET', url, query_params=query_params)

    def _post(self, url='/', data={}, query_params={}):
        return self._request('POST', url, data=data, query_params=query_params)

    def _put(self, url='/', data={}, query_params={}):
        return self._request('PUT', url, data=data, query_params=query_params)

    def _delete(self, url='/', query_params={}):
        return self._request('DELETE', url, query_params=query_params)

    def _request(self, action='GET',  url='/', data={}, query_params={}):

        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        default_auth = (self.options['auth_username'], self.options.get('auth_password') or self.options.get('auth_token'))

        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers,
                             auth=default_auth)
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()
