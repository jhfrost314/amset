# coding: utf-8

from __future__ import unicode_literals
import logging
import numpy as np
import os
import unittest

from amset import AMSET

test_dir = os.path.dirname(__file__)

class AmsetTest(unittest.TestCase):
    def setUp(self):
        self.model_params = {'bs_is_isotropic': True,
                             'elastic_scatterings': ['ACD', 'IMP', 'PIE'],
                             'inelastic_scatterings': ['POP']}
        self.performance_params = {'dE_min': 0.0001, 'nE_min': 2,
                                   'parallel': True, 'BTE_iters': 5}
    def tearDown(self):
        pass

    def test_GaAs(self):
        expected_mu = {'ACD': 68036.7, 'IMP': 1430457.6, 'PIE': 172180.7,
                       'POP': 10084.5, 'overall': 8057.9}
        cube_path = os.path.join(test_dir, '..', 'test_files', 'GaAs')
        coeff_file = os.path.join(cube_path, 'fort.123_GaAs_1099kp')
        material_params = {'epsilon_s': 12.9, 'epsilon_inf': 10.9,
                'W_POP': 8.73, 'C_el': 139.7, 'E_D': {'n': 8.6, 'p': 8.6},
                'P_PIE': 0.052, 'scissor': 0.5818}
        amset = AMSET(calc_dir=cube_path, material_params=material_params,
                      model_params=self.model_params,
                      performance_params=self.performance_params,
                      dopings=[-2e15], temperatures=[300], k_integration=True,
                      e_integration=True, fermi_type='e')
        amset.run(coeff_file, kgrid_tp='very coarse', loglevel=logging.ERROR)
        egrid = amset.egrid
        kgrid = amset.kgrid
        # check general characteristics of the grid
        print(kgrid['n']['velocity'][0].shape)
        self.assertEqual(kgrid['n']['velocity'][0].shape[0], 576)
        mean_v = np.mean(kgrid['n']['velocity'][0], axis=0)
        self.assertAlmostEqual(np.std(mean_v), 0.00, places=2) # isotropic BS
        self.assertAlmostEqual(mean_v[0], 4.30840999e7, places=1) # zeroth band

        # check mobility values
        for mu in expected_mu.keys():
            self.assertAlmostEqual(np.std( # test isotropic
                egrid['mobility'][mu][-2e15][300]['n']), 0.00, places=2)
            self.assertAlmostEqual(egrid['mobility'][mu][-2e15][300]['n'][0],
                    expected_mu[mu], places=1)

        # TODO-JF: similar tests for k-integration (e.g. isotropic mobility)

