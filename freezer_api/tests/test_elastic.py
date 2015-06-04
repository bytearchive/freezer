"""Freezer swift.py related tests

Copyright 2014 Hewlett-Packard

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This product includes cryptographic software written by Eric Young
(eay@cryptsoft.com). This product includes software written by Tim
Hudson (tjh@cryptsoft.com).
========================================================================
"""

import unittest
from mock import Mock, patch

from elasticsearch import TransportError

from freezer_api.storage import elastic
from common import *
from freezer_api.common.exceptions import *


class TypeManager(unittest.TestCase):

    def setUp(self):
        self.mock_es = Mock()
        self.type_manager = elastic.TypeManager(self.mock_es, 'base_doc_type', 'freezer')

    def test_get_base_search_filter(self):
        my_search = {'match': [{'some_field': 'some text'},
                               {'description': 'some other text'}]}
        q = self.type_manager.get_base_search_filter('my_user_id', search=my_search)
        expected_q = [{'term': {'user_id': 'my_user_id'}},
                      {'query':
                           {'bool':
                                {'must':
                                     [{'match': {'some_field': 'some text'}},
                                      {'match': {'description': 'some other text'}}
                                     ]}}}]
        self.assertEqual(q, expected_q)

    def test_get_ok(self):
        self.mock_es.get.return_value = fake_action_0_elasticsearch_found
        res = self.type_manager.get(user_id=fake_action_0_user_id,
                                    doc_id=fake_action_0_action_id)
        self.assertEqual(res, fake_action_0_doc)

    def test_get_raise_DocumentNotFound_when_doc_not_found(self):
        self.mock_es.get.side_effect = TransportError('regular test failure')
        self.assertRaises(DocumentNotFound, self.type_manager.get,
                          user_id=fake_action_0_user_id,
                          doc_id=fake_action_0_action_id)

    def test_get_raise_StorageEngineError_when_db_raises(self):
        self.mock_es.get.side_effect = Exception('regular test failure')
        self.assertRaises(StorageEngineError, self.type_manager.get,
                          user_id=fake_action_0_user_id,
                          doc_id=fake_action_0_action_id)

    def test_get_raises_DocumentNotFound_when_user_id_not_match(self):
        self.mock_es.get.return_value = fake_action_0_elasticsearch_found
        self.assertRaises(DocumentNotFound, self.type_manager.get,
                          user_id='obluraschi',
                          doc_id=fake_action_0_action_id)

    def test_search_ok(self):
        self.mock_es.search.return_value = fake_data_0_elasticsearch_hit
        expected_q = {'query': {'filtered': {'filter':
                          {'bool':
                               {'must':
                                    [{'term': {'user_id': 'my_user_id'}},
                                     {'query':
                                          {'bool':
                                               {'must':
                                                    [{'match': {'some_field': 'some text'}},
                                                     {'match': {'description': 'some other text'}}]}}}
                                    ]}}}}}
        my_search = {'match': [{'some_field': 'some text'},
                               {'description': 'some other text'}]}
        res = self.type_manager.search(user_id='my_user_id', doc_id='mydocid', search=my_search, offset=7, limit=19)
        self.mock_es.search.assert_called_with(index='freezer', doc_type='base_doc_type', size=19, from_=7, body=expected_q)
        self.assertEqual(res, [fake_data_0_backup_metadata])

    def test_search_raise_StorageEngineError_when_search_raises(self):
        self.mock_es.search.side_effect = Exception('regular test failure')
        self.assertRaises(StorageEngineError, self.type_manager.search, user_id='my_user_id', doc_id='mydocid')

    def test_insert_ok(self):
        self.mock_es.index.return_value = {'created': True}
        test_doc = {'test_key_412': 'test_value_412'}
        res = self.type_manager.insert(doc=test_doc)
        self.assertEqual(res, True)
        self.mock_es.index.assert_called_with(index='freezer', doc_type='base_doc_type', body=test_doc, id=None)

    def test_insert_fails(self):
        self.mock_es.index.side_effect = Exception('regular test failure')
        test_doc = {'test_key_412': 'test_value_412'}
        self.assertRaises(StorageEngineError, self.type_manager.insert, doc=test_doc)
        self.mock_es.index.assert_called_with(index='freezer', doc_type='base_doc_type', body=test_doc, id=None)

    def test_delete(self):
        doc_id='mydocid345'
        res = self.type_manager.delete(user_id='my_user_id', doc_id=doc_id)
        self.assertEqual(res, doc_id)

    def test_delete_fails(self):
        self.mock_es.delete_by_query.side_effect = Exception('regular test failure')
        doc_id='mydocid345'
        self.assertRaises(StorageEngineError, self.type_manager.delete, user_id='my_user_id', doc_id=doc_id)


class TestBackupManager(unittest.TestCase):

    def setUp(self):
        self.mock_es = Mock()
        self.backup_manager = elastic.BackupTypeManager(self.mock_es, 'backups')

    def test_get_search_query(self):
        my_search = {'match': [{'backup_name': 'my_backup'} , {'mode': 'fs'}],
                     "time_before": 1428510506,
                     "time_after": 1428510506
                     }
        q = self.backup_manager.get_search_query('my_user_id', 'my_doc_id', search=my_search)
        expected_q = {'query': {'filtered': {'filter':
                          {'bool':
                               {'must':
                                    [{'term': {'user_id': 'my_user_id'}},
                                     {'query': {'bool': {'must': [{'match': {'backup_name': 'my_backup'}},
                                                                  {'match': {'mode': 'fs'}}]}}},
                                     {'term': {'backup_id': 'my_doc_id'}},
                                     {'range': {'timestamp': {'gte': 1428510506}}},
                                     {'range': {'timestamp': {'lte': 1428510506}}}
                                    ]}}}}}

        self.assertEqual(q, expected_q)


class ClientTypeManager(unittest.TestCase):

    def setUp(self):
        self.mock_es = Mock()
        self.client_manager = elastic.ClientTypeManager(self.mock_es, 'clients')

    def test_get_search_query(self):
        my_search = {'match': [{'some_field': 'some text'},
                               {'description': 'some other text'}]}
        q = self.client_manager.get_search_query('my_user_id', 'my_doc_id', search=my_search)
        expected_q = {'query': {'filtered': {'filter':
                          {'bool':
                               {'must':
                                    [{'term': {'user_id': 'my_user_id'}},
                                     {'query':
                                          {'bool':
                                               {'must':
                                                    [{'match': {'some_field': 'some text'}},
                                                     {'match': {'description': 'some other text'}}]}}},
                                     {'term': {'client_id': 'my_doc_id'}}
                                    ]}}}}}
        self.assertEqual(q, expected_q)


class ActionTypeManager(unittest.TestCase):

    def setUp(self):
        self.mock_es = Mock()
        self.action_manager = elastic.ActionTypeManager(self.mock_es, 'clients')

    def test_get_search_query(self):
        my_search = {'match': [{'some_field': 'some text'},
                               {'description': 'some other text'}]}
        q = self.action_manager.get_search_query('my_user_id', 'my_doc_id', search=my_search)
        expected_q = {'query': {'filtered': {'filter':
                                                 {'bool':
                                                      {'must':
                                                           [{'term': {'user_id': 'my_user_id'}},
                                                            {'query':
                                                                 {'bool':
                                                                      {'must':
                                                                           [{'match': {'some_field': 'some text'}},
                                                                            {'match': {'description': 'some other text'}}]}}},
                                                            {'term': {'action_id': 'my_doc_id'}}
                                                           ]}}}}}
        self.assertEqual(q, expected_q)

    def test_update_ok(self):
        self.mock_es.update.return_value = {
            u'_id': u'd6c1e00d-b9c1-4eb3-8219-1e83c02af101',
            u'_index': u'freezer',
            u'_type': u'actions',
            u'_version': 3
        }
        res = self.action_manager.update(action_id=fake_action_0_action_id,
                                         action_update_doc={'status': 'sleepy'})
        self.assertEqual(res, 3)
        self.mock_es.update.assert_called_with(index=self.action_manager.index,
                                               doc_type=self.action_manager.doc_type,
                                               id=fake_action_0_action_id,
                                               body={"doc": {'status': 'sleepy'}})

    def test_update_raise_DocumentNotFound_when_not_found(self):
        self.mock_es.update.side_effect = TransportError('regular test failure')
        self.assertRaises(DocumentNotFound, self.action_manager.update,
                          action_id=fake_action_0_action_id,
                          action_update_doc={'status': 'sleepy'})

    def test_update_raise_StorageEngineError_when_db_raises(self):
        self.mock_es.update.side_effect = Exception('regular test failure')
        self.assertRaises(StorageEngineError, self.action_manager.update,
                          action_id=fake_action_0_action_id,
                          action_update_doc={'status': 'sleepy'})



class TestElasticSearchEngine_backup(unittest.TestCase):

    @patch('freezer_api.storage.elastic.logging')
    @patch('freezer_api.storage.elastic.elasticsearch')
    def setUp(self, mock_logging, mock_elasticsearch):
        mock_elasticsearch.Elasticsearch.return_value = Mock()
        self.eng = elastic.ElasticSearchEngine('http://elasticservaddr:1997')
        self.eng.backup_manager = Mock()

    def test_get_backup_userid_and_backup_id_return_ok(self):
        self.eng.backup_manager.search.return_value = [fake_data_0_wrapped_backup_metadata]
        my_search = {'match': [{'some_field': 'some text'},
                               {'description': 'some other text'}]}
        res = self.eng.get_backup(user_id=fake_data_0_user_id,
                                  backup_id=fake_data_0_backup_id,
                                  offset=3, limit=7,
                                  search=my_search)
        self.assertEqual(res, [fake_data_0_wrapped_backup_metadata])
        self.eng.backup_manager.search.assert_called_with(
            fake_data_0_wrapped_backup_metadata['user_id'],
            fake_data_0_wrapped_backup_metadata['backup_id'],
            search=my_search,
            limit=7, offset=3)

    def test_get_backup_list_with_userid_and_search_return_list(self):
        self.eng.backup_manager.search.return_value = [fake_data_0_wrapped_backup_metadata,
                                                       fake_data_1_wrapped_backup_metadata]
        my_search = {'match': [{'some_field': 'some text'},
                               {'description': 'some other text'}]}
        res = self.eng.get_backup(user_id=fake_data_0_user_id,
                                  offset=3, limit=7,
                                  search=my_search)
        self.assertEqual(res, [fake_data_0_wrapped_backup_metadata,
                               fake_data_1_wrapped_backup_metadata])
        self.eng.backup_manager.search.assert_called_with(
            fake_data_0_wrapped_backup_metadata['user_id'],
            None,
            search=my_search,
            limit=7, offset=3)

    def test_get_backup_list_with_userid_and_search_return_empty(self):
        self.eng.backup_manager.search.return_value = []
        my_search = {'match': [{'some_field': 'some text'},
                               {'description': 'some other text'}]}
        res = self.eng.get_backup(user_id=fake_data_0_user_id,
                                  offset=3, limit=7,
                                  search=my_search)
        self.assertEqual(res, [])
        self.eng.backup_manager.search.assert_called_with(
            fake_data_0_wrapped_backup_metadata['user_id'],
            None,
            search=my_search,
            limit=7, offset=3)

    def test_get_backup_userid_and_backup_id_not_found_returns_empty(self):
        self.eng.backup_manager.search.return_value = []
        my_search = {'match': [{'some_field': 'some text'},
                               {'description': 'some other text'}]}
        res = self.eng.get_backup(user_id=fake_data_0_user_id,
                                  backup_id=fake_data_0_backup_id,
                                  offset=3, limit=7,
                                  search=my_search)
        self.assertEqual(res, [])
        self.eng.backup_manager.search.assert_called_with(
            fake_data_0_wrapped_backup_metadata['user_id'],
            fake_data_0_wrapped_backup_metadata['backup_id'],
            search=my_search,
            limit=7, offset=3)

    def test_add_backup_raises_when_data_is_malformed(self):
        self.assertRaises(BadDataFormat, self.eng.add_backup,
                          user_id=fake_data_0_user_id,
                          user_name=fake_data_0_user_name,
                          doc=fake_malformed_data_0_backup_metadata)

    def test_add_backup_ok(self):
        self.eng.backup_manager.search.return_value = []
        res = self.eng.add_backup(fake_data_0_user_id,
                                  user_name=fake_data_0_user_name,
                                  doc=fake_data_0_backup_metadata)
        self.assertEqual(res, fake_data_0_wrapped_backup_metadata['backup_id'])

    def test_add_backup_raises_when_doc_exists(self):
        self.eng.backup_manager.search.return_value = [fake_data_0_wrapped_backup_metadata]
        self.assertRaises(DocumentExists, self.eng.add_backup,
                          user_id=fake_data_0_user_id,
                          user_name=fake_data_0_user_name,
                          doc=fake_data_0_backup_metadata)

    def test_add_backup_raises_when_manager_insert_raises(self):
        self.eng.backup_manager.search.return_value = []
        self.eng.backup_manager.insert.side_effect = StorageEngineError('regular test failure')
        self.assertRaises(StorageEngineError, self.eng.add_backup,
                          user_id=fake_data_0_user_id,
                          user_name=fake_data_0_user_name,
                          doc=fake_data_0_backup_metadata)

    def test_add_backup_raises_when_manager_insert_fails(self):
        self.eng.backup_manager.search.return_value = []
        self.eng.backup_manager.insert.return_value = False
        self.assertRaises(StorageEngineError, self.eng.add_backup,
                          user_id=fake_data_0_user_id,
                          user_name=fake_data_0_user_name,
                          doc=fake_data_0_backup_metadata)

    def test_delete_backup_ok(self):
        self.eng.backup_manager.delete.return_value = fake_data_0_backup_id
        res = self.eng.delete_backup(user_id=fake_data_0_user_id,
                                     backup_id=fake_data_0_backup_id)
        self.assertEqual(res, fake_data_0_backup_id)

    def test_delete_backup_raises_when_es_delete_raises(self):
        self.eng.backup_manager.delete.side_effect = StorageEngineError()
        self.assertRaises(StorageEngineError, self.eng.delete_backup,
                          user_id=fake_data_0_user_id,
                          backup_id=fake_data_0_backup_id)


class TestElasticSearchEngine_client(unittest.TestCase):

    @patch('freezer_api.storage.elastic.logging')
    @patch('freezer_api.storage.elastic.elasticsearch')
    def setUp(self, mock_logging, mock_elasticsearch):
        mock_elasticsearch.Elasticsearch.return_value = Mock()
        self.eng = elastic.ElasticSearchEngine('http://elasticservaddr:1997')
        self.eng.client_manager = Mock()

    def test_get_client_userid_and_client_id_return_1elem_list_(self):
        self.eng.client_manager.search.return_value = [fake_client_entry_0]
        my_search = {'match': [{'some_field': 'some text'},
                               {'description': 'some other text'}]}
        res = self.eng.get_client(user_id=fake_client_entry_0['user_id'],
                                  client_id=fake_client_info_0['client_id'],
                                  offset=6, limit=15,
                                  search=my_search)
        self.assertEqual(res, [fake_client_entry_0])
        self.eng.client_manager.search.assert_called_with(
            fake_client_entry_0['user_id'],
            fake_client_info_0['client_id'],
            search=my_search,
            limit=15, offset=6)

    def test_get_client_list_with_userid_and_search_return_list(self):
        self.eng.client_manager.search.return_value = [fake_client_entry_0, fake_client_entry_1]
        my_search = {'match': [{'some_field': 'some text'},
                               {'description': 'some other text'}]}
        res = self.eng.get_client(user_id=fake_client_entry_0['user_id'],
                                  offset=6, limit=15,
                                  search=my_search)
        self.assertEqual(res, [fake_client_entry_0, fake_client_entry_1])
        self.eng.client_manager.search.assert_called_with(
            fake_client_entry_0['user_id'],
            None,
            search=my_search,
            limit=15, offset=6)

    def test_get_client_list_with_userid_and_search_return_empty_list(self):
        self.eng.client_manager.search.return_value = []
        my_search = {'match': [{'some_field': 'some text'},
                               {'description': 'some other text'}]}
        res = self.eng.get_client(user_id=fake_client_entry_0['user_id'],
                                  offset=6, limit=15,
                                  search=my_search)
        self.assertEqual(res, [])
        self.eng.client_manager.search.assert_called_with(
            fake_client_entry_0['user_id'],
            None,
            search=my_search,
            limit=15, offset=6)

    def test_add_client_raises_when_data_is_malformed(self):
        doc = fake_client_info_0.copy()
        doc.pop('client_id')
        self.assertRaises(BadDataFormat, self.eng.add_client,
                          user_id=fake_data_0_user_name,
                          doc=doc)

    def test_add_client_raises_when_doc_exists(self):
        self.eng.client_manager.search.return_value = [fake_client_entry_0]
        self.assertRaises(DocumentExists, self.eng.add_client,
                          user_id=fake_data_0_user_id,
                          doc=fake_client_info_0)

    def test_add_client_ok(self):
        self.eng.client_manager.search.return_value = []
        res = self.eng.add_client(user_id=fake_data_0_user_id,
                                  doc=fake_client_info_0)
        self.assertEqual(res, fake_client_info_0['client_id'])
        self.eng.client_manager.search.assert_called_with(
            fake_data_0_user_id,
            fake_client_info_0['client_id'])

    def test_add_client_raises_when_manager_insert_raises(self):
        self.eng.client_manager.search.return_value = []
        self.eng.client_manager.insert.side_effect = StorageEngineError('regular test failure')
        self.assertRaises(StorageEngineError, self.eng.add_client,
                          user_id=fake_data_0_user_id,
                          doc=fake_client_info_0)

    def test_add_client_raises_when_manager_insert_fails_without_raise(self):
        self.eng.client_manager.search.return_value = []
        self.eng.client_manager.insert.return_value = False
        self.assertRaises(StorageEngineError, self.eng.add_client,
                          user_id=fake_data_0_user_id,
                          doc=fake_client_info_0)

    def test_delete_client_ok(self):
        self.eng.client_manager.delete.return_value = fake_client_info_0['client_id']
        res = self.eng.delete_client(user_id=fake_data_0_user_id,
                                     client_id=fake_client_info_0['client_id'])
        self.assertEqual(res, fake_client_info_0['client_id'])

    def test_delete_client_raises_when_es_delete_raises(self):
        self.eng.client_manager.delete.side_effect = StorageEngineError()
        self.assertRaises(StorageEngineError, self.eng.delete_client,
                          user_id=fake_data_0_user_id,
                          client_id=fake_client_info_0['client_id'])

class TestElasticSearchEngine_action(unittest.TestCase):

    @patch('freezer_api.storage.elastic.logging')
    @patch('freezer_api.storage.elastic.elasticsearch')
    def setUp(self, mock_elasticsearch, mock_logging):
        mock_elasticsearch.Elasticsearch.return_value = Mock()
        self.eng = elastic.ElasticSearchEngine('http://elasticservaddr:1997')
        self.eng.action_manager = Mock()

    def test_get_action_userid_and_action_id_return_doc(self):
        self.eng.action_manager.get.return_value = fake_action_0_doc
        res = self.eng.get_action(user_id=fake_client_entry_0['user_id'],
                                  action_id=fake_client_info_0['client_id'])
        self.assertEqual(res, fake_action_0_doc)
        self.eng.action_manager.get.assert_called_with(
            fake_client_entry_0['user_id'],
            fake_client_info_0['client_id'])

    def test_get_action_userid_and_action_id_return_none(self):
        self.eng.action_manager.get.return_value = None
        res = self.eng.get_action(user_id=fake_client_entry_0['user_id'],
                                  action_id=fake_client_info_0['client_id'])
        self.assertEqual(res, None)
        self.eng.action_manager.get.assert_called_with(
            fake_client_entry_0['user_id'],
            fake_client_info_0['client_id'])

    def test_get_action_with_userid_and_search_return_list(self):
        self.eng.action_manager.search.return_value = \
            [fake_action_0_doc, fake_action_0_doc]
        my_search = {'match': [{'some_field': 'some text'},
                               {'description': 'some other text'}]}
        res = self.eng.search_action(user_id=fake_action_0_doc['user_id'],
                                     offset=6, limit=15,
                                     search=my_search)
        self.assertEqual(res, [fake_action_0_doc, fake_action_0_doc])
        self.eng.action_manager.search.assert_called_with(
            fake_action_0_doc['user_id'],
            search=my_search,
            limit=15, offset=6)

    def test_get_action_with_userid_and_search_return_empty_list(self):
        self.eng.action_manager.search.return_value = []
        my_search = {'match': [{'some_field': 'some text'},
                               {'description': 'some other text'}]}
        res = self.eng.search_action(user_id=fake_action_0_doc['user_id'],
                                     offset=6, limit=15,
                                     search=my_search)
        self.assertEqual(res, [])
        self.eng.action_manager.search.assert_called_with(
            fake_action_0_doc['user_id'],
            search=my_search,
            limit=15, offset=6)

    def test_add_action_raises_BadDataFormat_when_data_is_malformed(self):
        doc = fake_action_0.copy()
        doc.pop('action_id')
        self.assertRaises(BadDataFormat, self.eng.add_action,
                          user_id=fake_action_0_doc['user_id'],
                          doc=doc)

    def test_add_action_ok(self):
        self.eng.action_manager.insert.return_value = fake_action_0_action_id
        res = self.eng.add_action(user_id=fake_action_0_user_id,
                                  doc=fake_action_0)
        self.assertEqual(res, fake_action_0_action_id)
        self.eng.action_manager.insert.assert_called_with(
            {'action': fake_action_0,
             'user_id': fake_action_0_user_id},
            fake_action_0_action_id)

    def test_add_action_raises_StorageEngineError_when_manager_insert_raises(self):
        self.eng.action_manager.get.return_value = None
        self.eng.action_manager.insert.side_effect = StorageEngineError('regular test failure')
        self.assertRaises(StorageEngineError, self.eng.add_action,
                          user_id=fake_action_0_user_id,
                          doc=fake_action_0)

    def test_add_action_raises_StorageEngineError_when_manager_insert_fails_without_raise(self):
        self.eng.action_manager.get.return_value = None
        self.eng.action_manager.insert.return_value = False
        self.assertRaises(StorageEngineError, self.eng.add_action,
                          user_id=fake_action_0_user_id,
                          doc=fake_action_0)

    def test_delete_action_ok(self):
        self.eng.action_manager.delete.return_value = fake_action_0['action_id']
        res = self.eng.delete_action(user_id=fake_action_0_user_id,
                                     action_id=fake_action_0_action_id)
        self.assertEqual(res, fake_action_0_action_id)

    def test_delete_client_raises_StorageEngineError_when_es_delete_raises(self):
        self.eng.action_manager.delete.side_effect = StorageEngineError()
        self.assertRaises(StorageEngineError, self.eng.delete_action,
                          user_id=fake_action_0_user_id,
                          action_id=fake_action_0_action_id)

    def test_update_client_raises_BadDataFormat_when_update_has_action_id(self):
        self.eng.action_manager.get.return_value = fake_action_0_doc
        patch = {'action_id': 'butterfly_caught'}
        self.assertRaises(BadDataFormat, self.eng.update_action,
                          user_id=fake_action_0_user_id,
                          action_id=fake_action_0_action_id,
                          patch=patch)

    def test_update_action_raises_DocumentNotFound_when_doc_not_exists(self):
        self.eng.action_manager.get.side_effect = DocumentNotFound('regular test failure')
        patch = {'some_field': 'black_milk'}
        self.assertRaises(DocumentNotFound, self.eng.update_action,
                          user_id=fake_action_0_user_id,
                          action_id=fake_action_0_action_id,
                          patch=patch)

    def test_update_action_raises_DocumentNotFound_when_update_raises_DocumentNotFound(self):
        self.eng.action_manager.get.return_value = fake_action_0_doc
        patch = {'some_field': 'black_milk'}
        self.eng.action_manager.update.side_effect = DocumentNotFound('regular test failure')
        self.assertRaises(DocumentNotFound, self.eng.update_action,
                          user_id=fake_action_0_user_id,
                          action_id=fake_action_0_action_id,
                          patch=patch)

    def test_update_action_returns_new_doc_version(self):
        self.eng.action_manager.get.return_value = fake_action_0_doc
        patch = {'some_field': 'group_four'}
        self.eng.action_manager.update.return_value = 11
        res = self.eng.update_action(user_id=fake_action_0_user_id,
                                     action_id=fake_action_0_action_id,
                                     patch=patch)
        self.assertEqual(res, 11)