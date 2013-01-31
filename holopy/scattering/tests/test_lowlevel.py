# Copyright 2011-2013, Vinothan N. Manoharan, Thomas G. Dimiduk,
# Rebecca W. Perry, Jerome Fung, and Ryan McGorty, Anna Wang
#
# This file is part of HoloPy.
#
# HoloPy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# HoloPy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with HoloPy.  If not, see <http://www.gnu.org/licenses/>.
'''
Test low-level physics and mathematical primitives that are part of 
scattering calculations.  

Most of these tests will check Fortran extensions.

These tests are intended to evaluate well-established low-level 
quantities (such as scattering coefficients or matrices calculated 
by independent codebases) or mathematical identities (such as 
coordinate transformations).  While the tests of physically 
measurable quantities (such as holograms) in test_mie.py and
test_multisphere.py are important, it is hoped that should any
of those fail, failures in these low-level tests will help pin
down the problem.


.. moduleauthor:: Jerome Fung <fung@physics.harvard.edu>
'''

from __future__ import division

import os
import yaml
from nose.tools import assert_raises
from numpy.testing import assert_allclose
import numpy as np
from numpy import sqrt, dot, pi, conj, real, imag
from nose.tools import with_setup
from nose.plugins.attrib import attr

from ..theory.mie_f import mieangfuncs, miescatlib, multilayer_sphere_lib

# basic defs
kr = 10.
kr_asym = 1.9e4
theta = pi/4.
phi = -pi/4.

@attr('fast')
def test_spherical_vector_to_cartesian():
    '''
    Test conversions between complex vectors in spherical components
    and cartesian.

    Tests mieangfuncs.fieldstocart and mieangfuncs.radial_vect_to_cart.
    '''
    # acts on a column spherical vector from left
    conversion_mat = np.array([[1/2., 1/2., 1./sqrt(2)],
                               [-1/2., -1/2., 1./sqrt(2)],
                               [1./sqrt(2), -1./sqrt(2), 0.]])

    # test conversion of a vector with r, theta, and phi components
    test_vect = np.array([0.2, 1. + 1.j, -1.])
    fortran_conversion = mieangfuncs.radial_vect_to_cart(test_vect[0],
                                                         theta, phi)
    fortran_conversion += mieangfuncs.fieldstocart(test_vect[1:], 
                                                   theta, phi)

    assert_allclose(fortran_conversion, dot(conversion_mat, test_vect))


@attr('fast')
def test_polarization_to_scatt_coords():
    '''
    Test conversion of an incident polarization (specified as a
    Cartesian vector in the lab frame) to an incident field
    in scattering spherical coordinates.

    For convention, see Bohren & Huffman ([Bohren1983]_) pp. 61-62. 
    '''

    conversion_mat = 1./sqrt(2) * np.array([[1., -1.],
                                            [-1., -1.]])
    
    test_vect = np.array([-1., 3.])
    fortran_result = mieangfuncs.incfield(test_vect[0], test_vect[1], phi)
    assert_allclose(fortran_result, dot(conversion_mat, test_vect))


@attr('fast')
def test_mie_amplitude_scattering_matrices():
    '''
    Test calculation of Mie amplitude scattering matrix elements.
    We will check the following:
        far-field matrix elements (direct comparison with [Bohren1983]_)
        near-field matrix for kr ~ 10 differs from far-field result
        near-field matrix for kr ~ 10^4 is close to far-field result

    While radiometric quantities (such as cross sections) implicitly test
    the Mie scattering coefficients, they do not involve any angular 
    quantities.
    '''

    # scattering units
    m = 1.55
    x = 2. * pi * 0.525 / 0.6328
    
    asbs = miescatlib.scatcoeffs(x, m, miescatlib.nstop(x))
    amp_scat_mat = mieangfuncs.asm_mie_far(asbs, theta)
    amp_scat_mat_asym = mieangfuncs.asm_mie_fullradial(asbs, np.array([kr_asym,
                                                                       theta,
                                                                       phi]))
    amp_scat_mat_near = mieangfuncs.asm_mie_fullradial(asbs, np.array([kr, 
                                                                      theta,
                                                                      phi]))

    # gold results directly from B/H p.482.
    location = os.path.split(os.path.abspath(__file__))[0]
    gold_name = os.path.join(location, 'gold',
                             'gold_mie_scat_matrix')
    gold_dict = yaml.load(file(gold_name + '.yaml'))
    gold = np.array([gold_dict['S11'], gold_dict['pol'], 
                     gold_dict['S33'], gold_dict['S34']])


    # B/H gives real scattering matrix elements, which are related
    # to the amplitude scatering elements.  See p. 65.
    def massage_into_bh_form(asm):
        S2, S3, S4, S1 = np.ravel(asm)
        S11 = 0.5 * (abs(asm)**2).sum()
        S12 = 0.5 * (abs(S2)**2 - abs(S1)**2)
        S33 = real(S1 * conj(S2)) 
        S34 = imag(S2 * conj(S1))
        deg_of_pol = -S12/S11
        # normalization factors: see comment lines 40-44 on p. 479
        asm_fwd = mieangfuncs.asm_mie_far(asbs, 0.)
        S11_fwd = 0.5 * (abs(asm_fwd)**2).sum()
        results = np.array([S11/S11_fwd, deg_of_pol, S33 / S11, S34 / S11])
        return results

    # off-diagonal elements should be zero
    assert_allclose(np.ravel(amp_scat_mat)[1:3], np.zeros(2))

    # check far-field computation
    assert_allclose(massage_into_bh_form(amp_scat_mat), gold, 
                    rtol = 1e-5)
 
    # check asymptotic behavior of near field matrix
    asym = massage_into_bh_form(amp_scat_mat_asym)
    assert_allclose(asym, gold, rtol = 1e-4, atol = 5e-5)
 
    # check that the near field is different
    try:
        assert_allclose(amp_scat_mat, amp_scat_mat_near)
    except AssertionError:
        pass
    else:
        raise AssertionError("Near-field amplitude scattering matrix " +
                             "suspiciously close to far-field result.")

# TODO: another check on the near-field result: calculate the scattered
# power by 4pi integration of E_scat^2 over 4pi. The result should be
# independent of kr and close to the analytical result.

# TODO: check on matrix multiplication in mieangfuncs.calc_scat_field
