# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida_core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
"""Module that contains the class definitions necessary to offer support for
queries to Materials Project."""

from __future__ import absolute_import
import os
import datetime
import requests

from pymatgen import MPRester
from aiida.tools.dbimporters.baseclasses import CifEntry, DbEntry, DbImporter, DbSearchResults


class MatProjImporter(DbImporter):
    """
    Database importer for the Materials Project.
    """

    _collection = 'structures'
    _supported_keywords = None

    def __init__(self, api_key=None):
        """
        Instantiate the MatProjImporter by setting up the Materials API (MAPI) connection details

        :param api_key: the API key to be used to access MAPI
        """
        self.setup_db(api_key=api_key)
        self._mpr = MPRester(self._api_key)

    def setup_db(self, **kwargs):
        """
        Setup the required parameters to the REST API

        :param api_key: the API key to be used to access MAPI
        """
        api_key = kwargs['api_key']
        if api_key is None:
            try:
                self._api_key = os.environ['PMG_MAPI_KEY']
            except KeyError:
                raise ValueError('API key not supplied and PMG_MAPI_KEY environment '
                                 'variable not set. Either pass it when initializing the class, '
                                 'or set the environment variable PMG_MAPI_KEY to your API key.')
        self._api_key = api_key
        self._verify_api_key()

    def _verify_api_key(self):
        """
        Verify the supplied API key by issuing a request to Materials Project.
        """
        response = requests.get(
            'https://www.materialsproject.org/rest/v1/api_check', headers={'X-API-KEY': self._api_key})
        response_content = response.json()  # a dict
        if 'error' in response_content:
            raise RuntimeError(response_content['error'])
        if not response_content['valid_response']:
            raise RuntimeError('Materials Project did not give a valid response for the API key check.')
        if not response_content['api_key_valid']:
            raise RuntimeError('Your API key for Materials Project is not valid.')

    @property
    def api_key(self):
        """
        Return the API key configured for the importer
        """
        return self._api_key

    @property
    def collection(self):
        """
        Return the collection that will be queried
        """
        return self._collection

    @property
    def pagesize(self):
        """
        Return the pagesize set for the importer
        """
        raise NotImplementedError('not implemented in the Materials Project importer')

    @property
    def structures(self):
        """
        Access the structures collection in the MPDS
        """
        raise NotImplementedError('not implemented in the Materials Project importer')

    @property
    def get_supported_keywords(self):
        """
        Returns the list of all supported query keywords

        :return: list of strings
        """
        return self._supported_keywords

    def query(self, **kwargs):
        """
        Query the database with a given dictionary of query parameters for a given collection

        :param query: a dictionary with the query parameters
        :param collection: the collection to query
        """
        try:
            query = kwargs['query']
        except AttributeError:
            raise AttributeError('Make sure the supplied dictionary has `query` as a key. This '
                                 'should containg a dictionary with the right query needed.')
        try:
            collection = kwargs['collection']
        except AttributeError:
            raise AttributeError('Make sure the supplied dictionary has `collection` as a key.')

        if not isinstance(query, dict):
            raise TypeError('The query argument should be a dictionary')

        if collection is None:
            collection = self._collection

        if collection == 'structure':
            results = []
            collection_list = ['structure', 'material_id', 'cif']
            for entry in self.find(query, collection_list):
                results.append(entry)
            search_results = MatProjSearchResults(results, return_class=MatProjCifEntry)
        else:
            raise ValueError('Unsupported collection: {}'.format(collection))

        return search_results

    def find(self, query, collection):
        """
        Query the database with a given dictionary of query parameters

        :param query: a dictionary with the query parameters
        """
        for entry in self._mpr.query(criteria=query, properties=collection):
            yield entry


class MatProjEntry(DbEntry):
    """
    Represents an Materials Project database entry
    """

    def __init__(self, **kwargs):
        """
        Set the class license from the source dictionary
        """
        lic = kwargs.pop('license', None)

        if lic is not None:
            self._license = lic

        super(MatProjEntry, self).__init__(**kwargs)


class MatProjCifEntry(CifEntry, MatProjEntry):  # pylint: disable=abstract-method
    """
    An extension of the MatProjEntry class with the CifEntry class, which will treat
    the contents property through the URI as a cif file
    """

    def __init__(self, url, **kwargs):
        """
        The DbSearchResults base class instantiates a new DbEntry by explicitly passing the url
        of the entry as an argument. In this case it is the same as the 'uri' value that is
        already contained in the source dictionary so we just copy it
        """
        cif = kwargs.pop('cif', None)
        kwargs['uri'] = url
        super(MatProjCifEntry, self).__init__(**kwargs)

        if cif is not None:
            self.cif = cif


class MatProjSearchResults(DbSearchResults):  # pylint: disable=abstract-method
    """
    A collection of MatProjEntry query result entries.
    """

    _db_name = 'Materials Project'
    _db_uri = 'https://materialsproject.org'
    _material_base_url = 'https://materialsproject.org/materials/'
    _license = 'Unknown'
    _version = 'Pulled from the Materials Project databse at: ' + str(datetime.datetime.now())
    _return_class = MatProjEntry

    def __init__(self, results, return_class=None):
        if return_class is not None:
            self._return_class = return_class
        super(MatProjSearchResults, self).__init__(results)

    def _get_source_dict(self, result_dict):
        """
        Return the source information dictionary of an Materials Project query result entry

        :param result_dict: query result entry dictionary
        """
        source_dict = {
            'db_name': self._db_name,
            'db_uri': self._db_uri,
            'id': result_dict['material_id'],
            'license': self._license,
            'uri': self._material_base_url + result_dict['material_id'],
            'version': self._version,
        }

        if 'cif' in result_dict:
            source_dict['cif'] = result_dict['cif']

        return source_dict

    def _get_url(self, result_dict):
        """
        Return the permanent URI of the result entry

        :param result_dict: query result entry dictionary
        """
        return self._material_base_url + result_dict['material_id'],
