# -*- coding: utf-8 -*-
"""
Tests for subclasses of DbImporter, DbSearchResults and DbEntry
"""
from django.utils import unittest

from aiida.djsite.db.testbase import AiidaTestCase
        
__copyright__ = u"Copyright (c), 2015, ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE (Theory and Simulation of Materials (THEOS) and National Centre for Computational Design and Discovery of Novel Materials (NCCR MARVEL)), Switzerland and ROBERT BOSCH LLC, USA. All rights reserved."
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.4.1"
__contributors__ = "Andrea Cepellotti, Andrius Merkys, Giovanni Pizzi"

class TestCodDbImporter(AiidaTestCase):
    """
    Test the CodDbImporter class.
    """    
    from aiida.orm.data.cif import has_pycifrw
    
    def test_query_construction_1(self):
        from aiida.tools.dbimporters.plugins.cod import CodDbImporter

        codi = CodDbImporter()
        q = codi.query_sql( id = [ "1000000", 3000000 ],
                            element = [ "C", "H", "Cl" ],
                            number_of_elements = 5,
                            chemical_name = [ "caffeine", "serotonine" ],
                            formula = [ "C6 H6" ],
                            volume = [ 100, 120.005 ],
                            spacegroup = "P -1",
                            a = [ 10.0 / 3, 1 ],
                            alpha = [ 10.0 / 6, 0 ],
                            measurement_temp = [ 0, 10.5 ],
                            measurement_pressure = [ 1000, 1001 ] )
        self.assertEquals(q, \
                          "SELECT file, svnrevision FROM data WHERE "
                          "(status IS NULL OR status != 'retracted') AND "
                          "(file IN (1000000, 3000000)) AND "
                          "(chemname LIKE '%caffeine%' OR "
                          "chemname LIKE '%serotonine%') AND "
                          "(formula IN ('- C6 H6 -')) AND "
                          "(a BETWEEN 3.33233333333 AND 3.33433333333 OR "
                          "a BETWEEN 0.999 AND 1.001) AND "
                          "(celltemp BETWEEN -0.001 AND 0.001 OR "
                          "celltemp BETWEEN 10.499 AND 10.501) AND "
                          "(vol BETWEEN 99.999 AND 100.001 OR "
                          "vol BETWEEN 120.004 AND 120.006) AND "
                          "(alpha BETWEEN 1.66566666667 AND 1.66766666667 OR "
                          "alpha BETWEEN -0.001 AND 0.001) AND "
                          "(cellpressure BETWEEN 999 AND 1001 OR "
                          "cellpressure BETWEEN 1000 AND 1002) AND "
                          "(formula REGEXP ' C[0-9 ]' AND "
                          "formula REGEXP ' H[0-9 ]' AND "
                          "formula REGEXP ' Cl[0-9 ]') AND "
                          "(nel IN (5)) AND (sg IN ('P -1'))")

    def test_datatype_checks(self):
        """
        Rather complicated, but wide-coverage test for data types, accepted
        and rejected by CodDbImporter._*_clause methods.
        """
        from aiida.tools.dbimporters.plugins.cod import CodDbImporter

        codi = CodDbImporter()
        messages = [ "",
                     "incorrect value for keyword 'test' -- " + \
                     "only integers and strings are accepted",
                     "incorrect value for keyword 'test' -- " + \
                     "only strings are accepted",
                     "incorrect value for keyword 'test' -- " + \
                     "only integers and floats are accepted",
                     "invalid literal for int() with base 10: 'text'" ]
        values = [ 10, 'text', u'text', '10', 1.0 / 3, [ 1, 2, 3 ] ]
        methods = [ codi._int_clause,
                    codi._str_exact_clause,
                    codi._formula_clause,
                    codi._str_fuzzy_clause,
                    codi._composition_clause,
                    codi._volume_clause ]
        results = [ [ 0, 4, 4, 0, 1, 1 ],
                    [ 0, 0, 0, 0, 1, 1 ],
                    [ 2, 0, 2, 0, 2, 2 ],
                    [ 0, 0, 0, 0, 1, 1 ],
                    [ 2, 0, 0, 0, 2, 2 ],
                    [ 0, 3, 3, 3, 0, 3 ] ]

        for i in range( 0, len( methods ) ):
            for j in range( 0, len( values ) ):
                message = messages[0]
                try:
                    methods[i]( "test", "test", [ values[j] ] )
                except ValueError as e:
                    message = e.message
                self.assertEquals(message, messages[results[i][j]])

    def test_dbentry_creation(self):
        """
        Tests the creation of CodEntry from CodSearchResults.
        """
        from aiida.tools.dbimporters.plugins.cod \
            import CodEntry, CodSearchResults

        results = CodSearchResults( [ { 'id': '1000000', 'svnrevision': None },
                                      { 'id': '1000001', 'svnrevision': '1234' },
                                      { 'id': '2000000', 'svnrevision': '1234' } ] )
        self.assertEquals(len(results),3)
        self.assertEquals(str(results.at(1)),
                          'CodEntry(db_version="1234",db_id="1000001",'
                          'url="http://www.crystallography.net/cod/1000001.cif@1234",'
                          'db_url="http://www.crystallography.net",extras={},'
                          'db_source="Crystallography Open Database",'
                          'source_md5=None)')
        self.assertEquals(results.at(1).source['url'], \
                          "http://www.crystallography.net/cod/1000001.cif@1234")
        self.assertEquals([x.source['url'] for x in results],
                          ["http://www.crystallography.net/cod/1000000.cif",
                           "http://www.crystallography.net/cod/1000001.cif@1234",
                           "http://www.crystallography.net/cod/2000000.cif@1234"])

    @unittest.skipIf(not has_pycifrw(),"Unable to import PyCifRW")
    def test_dbentry_to_cif_node(self):
        """
        Tests the creation of CifData node from CodEntry.
        """
        from aiida.tools.dbimporters.plugins.cod import CodEntry
        from aiida.orm.data.cif import CifData

        entry = CodEntry("http://www.crystallography.net/cod/1000000.cif")
        entry._cif = "data_test _publ_section_title 'Test structure'"

        cif = entry.get_cif_node()
        self.assertEquals(isinstance(cif,CifData),True)
        self.assertEquals(cif.get_attr('md5'),
                          '070711e8e99108aade31d20cd5c94c48')
        self.assertEquals(cif.source,{
            'db_source' : 'Crystallography Open Database',
            'db_url'    : 'http://www.crystallography.net',
            'db_id'     : None,
            'db_version': None,
            'extras'    : {},
            'source_md5': '070711e8e99108aade31d20cd5c94c48',
            'url'       : 'http://www.crystallography.net/cod/1000000.cif'
        })

class TestTcodDbImporter(AiidaTestCase):
    """
    Test the TcodDbImporter class.
    """
    def test_dbentry_creation(self):
        """
        Tests the creation of TcodEntry from TcodSearchResults.
        """
        from aiida.tools.dbimporters.plugins.tcod import TcodSearchResults

        results = TcodSearchResults( [ { 'id': '10000000', 'svnrevision': None },
                                       { 'id': '10000001', 'svnrevision': '1234' },
                                       { 'id': '20000000', 'svnrevision': '1234' } ] )
        self.assertEquals(len(results),3)
        self.assertEquals(str(results.at(1)),
                          'TcodEntry(db_version="1234",db_id="10000001",'
                          'url="http://www.crystallography.net/tcod/10000001.cif@1234",'
                          'db_url="http://www.crystallography.net/tcod",extras={},'
                          'db_source="Theoretical Crystallography Open Database",'
                          'source_md5=None)')
        self.assertEquals(results.at(1).source['url'], \
                          "http://www.crystallography.net/tcod/10000001.cif@1234")
        self.assertEquals([x.source['url'] for x in results],
                          ["http://www.crystallography.net/tcod/10000000.cif",
                           "http://www.crystallography.net/tcod/10000001.cif@1234",
                           "http://www.crystallography.net/tcod/20000000.cif@1234"])

class TestPcodDbImporter(AiidaTestCase):
    """
    Test the PcodDbImporter class.
    """
    def test_dbentry_creation(self):
        """
        Tests the creation of PcodEntry from PcodSearchResults.
        """
        from aiida.tools.dbimporters.plugins.pcod import PcodSearchResults

        results = PcodSearchResults( [ { 'id': '12345678' } ] )
        self.assertEquals(len(results),1)
        self.assertEquals(str(results.at(0)),
                          'PcodEntry(db_version=None,db_id="12345678",'
                          'url="http://www.crystallography.net/pcod/cif/1/123/12345678.cif",'
                          'db_url="http://www.crystallography.net/pcod",extras={},'
                          'db_source="Predicted Crystallography Open Database",'
                          'source_md5=None)')
        self.assertEquals([x.source['url'] for x in results],
                          ["http://www.crystallography.net/pcod/cif/1/123/12345678.cif"])

class TestMpodDbImporter(AiidaTestCase):
    """
    Test the MpodDbImporter class.
    """
    def test_dbentry_creation(self):
        """
        Tests the creation of MpodEntry from MpodSearchResults.
        """
        from aiida.tools.dbimporters.plugins.mpod import MpodSearchResults

        results = MpodSearchResults( [ { 'id': '1234567' } ] )
        self.assertEquals(len(results),1)
        self.assertEquals(str(results.at(0)),
                          'MpodEntry(db_version=None,db_id="1234567",'
                          'url="http://mpod.cimav.edu.mx/datafiles/1234567.mpod",'
                          'db_url="http://mpod.cimav.edu.mx",extras={},'
                          'db_source="Material Properties Open Database",'
                          'source_md5=None)')
        self.assertEquals([x.source['url'] for x in results],
                          ["http://mpod.cimav.edu.mx/datafiles/1234567.mpod"])