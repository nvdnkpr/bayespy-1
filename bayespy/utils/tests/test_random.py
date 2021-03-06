######################################################################
# Copyright (C) 2014 Jaakko Luttinen
#
# This file is licensed under Version 3.0 of the GNU General Public
# License. See LICENSE for a text of the license.
######################################################################

######################################################################
# This file is part of BayesPy.
#
# BayesPy is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# BayesPy is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BayesPy.  If not, see <http://www.gnu.org/licenses/>.
######################################################################

"""
Unit tests for bayespy.utils.random module.
"""

import numpy as np

from .. import utils
from .. import random

class TestCeilDiv(utils.TestCase):

    def test_categorical(self):

        # Test dummy one category
        y = random.categorical([1])
        self.assertEqual(y, 0)

        # Test multiple categories
        y = random.categorical([1,0,0])
        self.assertEqual(y, 0)
        y = random.categorical([0,1,0])
        self.assertEqual(y, 1)
        y = random.categorical([0,0,1])
        self.assertEqual(y, 2)

        # Test un-normalized probabilities
        y = random.categorical([0,0.1234])
        self.assertEqual(y, 1)

        # Test multiple distributions
        y = random.categorical([ [1,0,0], [0,0,1], [0,1,0] ])
        self.assertArrayEqual(y, [0,2,1])

        # Test multiple samples
        y = random.categorical([0,1,0], size=(4,))
        self.assertArrayEqual(y, [1,1,1,1])

        #
        # ERRORS
        #
        
        # Negative probablities
        self.assertRaises(ValueError, 
                          random.categorical,
                          [0, -1])

        # Requested size and probability array size mismatch
        self.assertRaises(ValueError, 
                          random.categorical,
                          [[1,0],[0,1]], 
                          size=(3,))

        pass
        


class TestDirichlet(utils.TestCase):
    """
    Unit tests for the Dirichlet random sampling
    """

    def test(self):
        """
        Test random sampling from the Dirichlet distribution.
        """

        # Test computations
        p = random.dirichlet([1e-10, 1e-10, 1e10, 1e-10])
        self.assertAllClose(p,
                            [0, 0, 1, 0],
                            atol=1e-5)
        p = random.dirichlet([1e20, 1e20, 1e20, 5*1e20])
        self.assertAllClose(p,
                            [0.125, 0.125, 0.125, 0.625])

        # Test array
        p = random.dirichlet([ [1e20, 1e-20], [3*1e20, 1e20] ])
        self.assertAllClose(p,
                            [[1.0, 0.0], [0.75, 0.25]])

        # Test size argument
        p = random.dirichlet([ [1e20, 1e-20] ], size=3)
        self.assertAllClose(p,
                            [[1, 0], [1, 0], [1, 0]])
        p = random.dirichlet([ [3*1e20, 1e20] ], size=(2,3))
        self.assertAllClose(p,
                            [ [[0.75, 0.25], [0.75, 0.25], [0.75, 0.25]],
                              [[0.75, 0.25], [0.75, 0.25], [0.75, 0.25]] ])
        
        pass


class TestAlphaBetaRecursion(utils.TestCase):
    
    def test(self):
        """
        Test the results of alpha-beta recursion for Markov chains
        """

        np.seterr(divide='ignore')

        # Deterministic oscillator
        p0 = np.array([1.0, 0.0])
        P = np.array(3*[[[0.0, 1.0],
                         [1.0, 0.0]]])
        (z0, zz, g) = random.alpha_beta_recursion(np.log(p0),
                                                  np.log(P))
        self.assertAllClose(z0,
                            [1.0, 0])
        self.assertAllClose(zz,
                            [ [[0.0, 1.0],
                               [0.0, 0.0]],
                              [[0.0, 0.0],
                               [1.0, 0.0]],
                              [[0.0, 1.0],
                               [0.0, 0.0]] ])
        self.assertAllClose(g,
                            -np.log(np.einsum('a,ab,bc,cd->',
                                              p0, P[0], P[1], P[2])),
                            msg="Cumulant generating function incorrect")

        # Maximum randomness
        p0 = np.array([0.5, 0.5])
        P = np.array(3*[[[0.5, 0.5],
                         [0.5, 0.5]]])
        (z0, zz, g) = random.alpha_beta_recursion(np.log(p0),
                                                  np.log(P))
        self.assertAllClose(z0,
                            [0.5, 0.5])
        self.assertAllClose(zz,
                            [ [[0.25, 0.25],
                               [0.25, 0.25]],
                              [[0.25, 0.25],
                               [0.25, 0.25]],
                              [[0.25, 0.25],
                               [0.25, 0.25]] ])
        self.assertAllClose(g,
                            -np.log(np.einsum('a,ab,bc,cd->',
                                              p0, P[0], P[1], P[2])),
                            msg="Cumulant generating function incorrect")

        # Unnormalized probabilities
        p0 = np.array([2, 2])
        P = np.array([ [[4, 4],
                        [4, 4]],
                       [[8, 8],
                        [8, 8]],
                       [[20, 20],
                        [20, 20]] ])
        (z0, zz, g) = random.alpha_beta_recursion(np.log(p0),
                                                  np.log(P))
        self.assertAllClose(z0,
                            [0.5, 0.5])
        self.assertAllClose(zz,
                            [ [[0.25, 0.25],
                               [0.25, 0.25]],
                              [[0.25, 0.25],
                               [0.25, 0.25]],
                              [[0.25, 0.25],
                               [0.25, 0.25]] ])
        self.assertAllClose(g,
                            -np.log(np.einsum('a,ab,bc,cd->',
                                              p0, P[0], P[1], P[2])),
                            msg="Cumulant generating function incorrect")
        p0 = np.array([2, 6])
        P = np.array([ [[0, 3],
                        [4, 1]],
                       [[3, 5],
                        [6, 4]],
                       [[9, 2],
                        [8, 1]] ])
        (z0, zz, g) = random.alpha_beta_recursion(np.log(p0),
                                                  np.log(P))
        y0 = np.einsum('a,ab,bc,cd->a', p0, P[0], P[1], P[2])
        y1 = np.einsum('a,ab,bc,cd->ab', p0, P[0], P[1], P[2])
        y2 = np.einsum('a,ab,bc,cd->bc', p0, P[0], P[1], P[2])
        y3 = np.einsum('a,ab,bc,cd->cd', p0, P[0], P[1], P[2])
        self.assertAllClose(z0,
                            y0 / np.sum(y0))
        self.assertAllClose(zz,
                            [ y1 / np.sum(y1),
                              y2 / np.sum(y2),
                              y3 / np.sum(y3) ])
        self.assertAllClose(g,
                            -np.log(np.einsum('a,ab,bc,cd->',
                                              p0, P[0], P[1], P[2])),
                            msg="Cumulant generating function incorrect")

        # Test plates
        p0 = np.array([ [1.0, 0.0],
                        [0.5, 0.5] ])
        P = np.array([ [ [[0.0, 1.0],
                          [1.0, 0.0]] ],
                       [ [[0.5, 0.5],
                          [0.5, 0.5]] ] ])
        (z0, zz, g) = random.alpha_beta_recursion(np.log(p0),
                                                  np.log(P))
        self.assertAllClose(z0,
                            [[1.0, 0.0],
                             [0.5, 0.5]])
        self.assertAllClose(zz,
                            [ [ [[0.0, 1.0],
                                 [0.0, 0.0]] ],
                              [ [[0.25, 0.25],
                                 [0.25, 0.25]] ] ])
        self.assertAllClose(g,
                            -np.log(np.einsum('...a,...ab->...',
                                              p0, P[...,0,:,:])),
                            msg="Cumulant generating function incorrect")

        # Test overflow
        logp0 = np.array([1e5, -np.inf])
        logP = np.array([[[-np.inf, 1e5],
                          [-np.inf, 1e5]]])
        (z0, zz, g) = random.alpha_beta_recursion(logp0,
                                                  logP)
        self.assertAllClose(z0,
                            [1.0, 0])
        self.assertAllClose(zz,
                            [ [[0.0, 1.0],
                               [0.0, 0.0]] ])
        ## self.assertAllClose(g,
        ##                     -np.log(np.einsum('a,ab,bc,cd->',
        ##                                       p0, P[0], P[1], P[2])))

        # Test underflow
        logp0 = np.array([-1e5, -np.inf])
        logP = np.array([[[-np.inf, -1e5],
                          [-np.inf, -1e5]]])
        (z0, zz, g) = random.alpha_beta_recursion(logp0,
                                                  logP)
        self.assertAllClose(z0,
                            [1.0, 0])
        self.assertAllClose(zz,
                            [ [[0.0, 1.0],
                               [0.0, 0.0]] ])
        ## self.assertAllClose(g,
        ##                     -np.log(np.einsum('a,ab,bc,cd->',
        ##                                       p0, P[0], P[1], P[2])))

        # Test stability of the algorithm
        logp0 = np.array([-1e5, -np.inf])
        logP = np.array(10*[[[-np.inf, 1e5],
                             [1e0, -np.inf]]])
        (z0, zz, g) = random.alpha_beta_recursion(logp0,
                                                  logP)
        self.assertTrue(np.all(~np.isnan(z0)),
                        msg="Nans in results, algorithm not stable")
        self.assertTrue(np.all(~np.isnan(zz)),
                        msg="Nans in results, algorithm not stable")
        self.assertTrue(np.all(~np.isnan(g)),
                        msg="Nans in results, algorithm not stable")

        pass
