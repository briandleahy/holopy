# Copyright 2011, Vinothan N. Manoharan, Thomas G. Dimiduk, Rebecca
# W. Perry, Jerome Fung, and Ryan McGorty
#
# This file is part of Holopy.
#
# Holopy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Holopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Holopy.  If not, see <http://www.gnu.org/licenses/>.

import os
from collections import OrderedDict

import numpy as np

import holopy as hp

from nose.tools import with_setup
from nose.plugins.attrib import attr
from numpy.testing import assert_allclose, assert_equal
from scatterpy.theory import Mie
from scatterpy.scatterer import Sphere

from holopy.analyze.fit_new import Parameter, Model, fit, Minimizer

def setup_optics():
    # set up optics class for use in several test functions
    global optics
    wavelen = 658e-9
    polarization = [0., 1.0]
    divergence = 0
    pixel_scale = [.1151e-6, .1151e-6]
    index = 1.33
    
    optics = hp.optics.Optics(wavelen=wavelen, index=index,
                              pixel_scale=pixel_scale,
                              polarization=polarization,
                                  divergence=divergence)
    
def teardown_optics():
    global optics
    del optics

gold_single = OrderedDict((('center.x', 5.534e-6),
               ('center.y', 5.792e-6),
               ('center.z', 1.415e-5),
               ('n.imag', 1e-4),
               ('n.real', 1.582),
               ('r', 6.484e-7)))
gold_alpha = .6497

@attr('medium')
@with_setup(setup=setup_optics, teardown=teardown_optics)
def test_fit_mie_single():
    return True
    path = os.path.abspath(hp.__file__)
    path = os.path.join(os.path.split(path)[0],'tests', 'exampledata')
    holo = hp.process.normalize(hp.load(os.path.join(path, 'image0001.npy'),
                                        optics=optics))

    parameters = [Parameter(name='x', guess=.567e-5, limit = [0.0, 1e-5]),
                  Parameter(name='y', guess=.576e-5, limit = [0, 1e-5]),
                  Parameter(name='z', guess=15e-6, limit = [1e-5, 2e-5]),
                  Parameter(name='r', guess=8.5e-7, limit = [1e-8, 1e-5]),
                  Parameter(name='alpha', guess=.6, limit = [.1, 1])]

    
    def make_scatterer(x, y, z, r):
        return Sphere(n=1.59+1e-4j, r = r, center = (x, y, z))

    model = Model(parameters, Multisphere, make_scatterer=make_scatterer)

    result = fit(model, holo)
    
@attr('fast')
def test_parameter():
    par = Parameter(name='x', guess=.567e-5, limit = [0.0, 1e-5])
    assert_equal(1e-6, par.unscale(par.scale(1e-6)))


@attr('fast')
def test_model():
    parameters = [Parameter(name='x', guess=.567e-5, limit = [0.0, 1e-5]),
                  Parameter(name='y', guess=.576e-5, limit = [0, 1e-5]),
                  Parameter(name='z', guess=15e-6, limit = [1e-5, 2e-5]),
                  Parameter(name='r', guess=8.5e-7, limit = [1e-8, 1e-5]),
                  Parameter(name='alpha', guess=.6, limit = [.1, 1])]

    def make_scatterer(x, y, z, r):
        return Sphere(n=1.59+1e-4j, r = r, center = (x, y, z))

    model = Model(parameters, Mie, make_scatterer=make_scatterer)

@attr('fast')
def test_minimizer():
    x = np.arange(-10, 10, .1)
    a = 5.3
    b = -1.8
    c = 3.4
    y = a*x**2 + b*x + c

    def cost_func(par_values):
        a, b, c = par_values
        return a*x**2 + b*x + c - y

    parameters = [Parameter(name='a', guess = 5),
                 Parameter(name='b', guess = -2),
                 Parameter(name='c', guess = 3)]

    minimizer = Minimizer()

    result = minimizer.minimize(parameters, cost_func)

    assert_allclose([a, b, c], result)
    