#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
import sys
import os

# test neb restart:
# do first a neb calculation (e.g. ./test_neb.py --send neb_codname)
# then use a this one with the previous neb calculation as parent
# (no need to specify codename):
# ./test_neb_restart --send neb_parent_calc_pk

################################################################
UpfData = DataFactory('upf')
ParameterData = DataFactory('parameter')
StructureData = DataFactory('structure')
RemoteData = DataFactory('remote')

# Used to test the parent calculation
QENebCalc = CalculationFactory('quantumespresso.neb')

try:
    dontsend = sys.argv[1]
    if dontsend == "--dont-send":
        submit_test = True
    elif dontsend == "--send":
        submit_test = False
    else:
        raise IndexError
except IndexError:
    print >> sys.stderr, ("The first parameter can only be either "
                          "--send or --dont-send")
    sys.exit(1)

try:
    parent_id = sys.argv[2]
except IndexError:
    print >> sys.stderr, ("Must provide as second parameter the parent ID")
    sys.exit(1)


#####
# test parent

try:
    int(parent_id)
except ValueError:
    raise ValueError('Parent_id not an integer: {}'.format(parent_id))

parentcalc = Calculation.get_subclass_from_pk(parent_id)

queue = None

#####

if isinstance(parentcalc, QENebCalc):

    # do a restart neb calculation
    if ( (parentcalc.get_state() == 'FAILED') and
             ('Maximum CPU time exceeded' in parentcalc.res.warnings) ):

        calc = parentcalc.create_restart(force_restart=True)
        #calc.label = "Test QE neb.x restart"
        calc.description = "Test restart calculation with the Quantum ESPRESSO neb.x code"

    else:
        print >> sys.stderr, ("Parent calculation did not fail or did "
                              "not stop because of maximum CPU time limit.")
        sys.exit(1)


else:
    print >> sys.stderr, ("Parent calculation should be a neb.x "
                          "calculation.")
    sys.exit(1)

######

if submit_test:
    subfolder, script_filename = calc.submit_test()
    print "Test_submit for calculation (uuid='{}')".format(
        calc.uuid)
    print "Submit file in {}".format(os.path.join(
        os.path.relpath(subfolder.abspath),
        script_filename
    ))
else:
    calc.store_all()
    print "created calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid, calc.dbnode.pk)
    calc.submit()
    print "submitted calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid, calc.dbnode.pk)
