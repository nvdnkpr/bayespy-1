######################################################################
# Copyright (C) 2013,2014 Jaakko Luttinen
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

import functools

import numpy as np

from bayespy.utils import utils

from .node import Node, Moments

class Deterministic(Node):
    """
    Base class for nodes that are deterministic.

    Sub-classes must implement:
    1. For implementing the deterministic function:
       _compute_moments(self, *u)
    2. One of the following options:
       a) Simple methods:
          _compute_message_to_parent(self, index, m, *u)
          not? _compute_mask_to_parent(self, index, mask)
       b) More control with:
          _compute_message_and_mask_to_parent(self, index, m, *u)

    Sub-classes may need to re-implement:
    1. If they manipulate plates:
       _compute_mask_to_parent(index, mask)
       _plates_to_parent(self, index)
       _plates_from_parent(self, index)
    
    
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, plates=None, notify_parents=False, **kwargs)

    def get_moments(self):
        u_parents = self._message_from_parents()
        return self._compute_moments(*u_parents)

    def _compute_message_and_mask_to_parent(self, index, m_children, *u_parents):
        # The following methods should be implemented by sub-classes.
        m = self._compute_message_to_parent(index, m_children, *u_parents)
        mask = self._compute_mask_to_parent(index, self.mask)
        return (m, mask)

    def _get_message_and_mask_to_parent(self, index):
        u_parents = self._message_from_parents(exclude=index)
        m_children = self._message_from_children()
        return self._compute_message_and_mask_to_parent(index,
                                                        m_children,
                                                        *u_parents)
        
    
    def _compute_moments(self, *u_parents):
        # Sub-classes should implement this
        raise NotImplementedError()

    def _add_child(self, child, index):
        """
        Add a child node.

        Only child nodes that are stochastic (or have stochastic children
        recursively) are counted as children because deterministic nodes without
        stochastic children do not have any messages to send so the parents do
        not need to know about the deterministic node.

        A deterministic node does not notify its parents when created, but if it
        gets a stochastic child node, then notify parents. This method is called
        only if a stochastic child (recursively) node is added, thus there is at
        least one stochastic node below this deterministic node.

        Parameters
        ----------
        child : node
        index : int
           The parent index of this node for the child node.  
           The child node recognizes its parents by their index 
           number.
        """
        super()._add_child(child, index)
        # Now that this deterministic node has non-deterministic children,
        # notify parents
        for (ind,parent) in enumerate(self.parents):
            parent._add_child(self, ind)

    def _remove_child(self, child, index):
        """
        Remove a child node.

        Only child nodes that are stochastic (or have stochastic children
        recursively) are counted as children because deterministic nodes without
        stochastic children do not have any messages to send so the parents do
        not need to know about the deterministic node.

        So, if the deterministic node does not have any stochastic children left
        after removal, remove it from its parents.
        """
        super()._remove_child(child, index)
        # Check whether there are any children left. If not, remove from parents
        if len(self.children) == 0:
            for (ind, parent) in enumerate(self.parents):
                parent._remove_child(self, ind)

    def lower_bound_contribution(self, gradient=False):
        # Deterministic functions are delta distributions so the lower bound
        # contribuion is zero.
        return 0

def tile(X, tiles):
    """
    Tile the plates of the input node.

    x = [a,b,c]
    y = tile(x, 2) = [a,b,c,a,b,c]

    There should be no need to tile plates that have unit length because they
    are handled properly by the broadcasting rules already.

    Parameters:
    -----------
    X : Node
        Input node to be tiled.
    tiles : int, tuple
        Tiling of the plates (broadcasting rules for plates apply).

    See also:
    ---------
    numpy.tile
    """
    
    # Make sure `tiles` is tuple (even if an integer is given)
    tiles = tuple(np.ravel(tiles))

    
    class _Tile(Deterministic):

        _parent_moments = (Moments(),)
        
        def __init__(self, X, **kwargs):
            self._moments = X._moments
            super().__init__(X, dims=X.dims, **kwargs)
    
        def _plates_to_parent(self, index):
            plates = list(self.plates)
            for i in range(-len(tiles), 0):
                plates[i] = plates[i] // tiles[i]
            return tuple(plates)

        def _plates_from_parent(self, index):
            return tuple(utils.multiply_shapes(self.parents[index].plates,
                                               tiles))

        def _compute_mask_to_parent(self, index, mask):
            # Idea: Reshape the message array such that every other axis
            # will be summed and every other kept.

            # Make plates equal length
            plates = self._plates_to_parent(index)
            shape_m = np.shape(mask)
            (plates, tiles_m, shape_m) = utils.make_equal_length(plates, 
                                                                 tiles,
                                                                 shape_m)
            
            # Handle broadcasting rules for axes that have unit length in
            # the message (although the plate may be non-unit length). Also,
            # compute the corresponding plate_multiplier.
            plates = list(plates)
            tiles_m = list(tiles_m)
            for j in range(len(plates)):
                if shape_m[j] == 1:
                    plates[j] = 1
                    tiles_m[j] = 1
                    
            # Combine the tuples by picking every other from tiles_ind and
            # every other from shape
            shape = functools.reduce(lambda x,y: x+y,
                                     zip(tiles_m, plates))
            # ..and reshape the array, that is, every other axis corresponds
            # to tiles and every other to plates/dimensions in parents
            mask = np.reshape(mask, shape)

            # Sum over every other axis
            axes = tuple(range(0,len(shape),2))
            mask = np.any(mask, axis=axes)

            # Remove extra leading axes
            ndim_parent = len(self.parents[index].plates)
            mask = utils.squeeze_to_dim(mask, ndim_parent)

            return mask


        def _compute_message_to_parent(self, index, m, u_X):
            m = list(m)
            for ind in range(len(m)):

                # Idea: Reshape the message array such that every other axis
                # will be summed and every other kept.
                
                shape_ind = self._plates_to_parent(index) + self.dims[ind]
                # Add variable dimensions to tiles
                tiles_ind = tiles + (1,)*len(self.dims[ind])

                # Make shape tuples equal length
                shape_m = np.shape(m[ind])
                (tiles_ind, shape, shape_m) = utils.make_equal_length(tiles_ind,
                                                                      shape_ind,
                                                                      shape_m)

                # Handle broadcasting rules for axes that have unit length in
                # the message (although the plate may be non-unit length). Also,
                # compute the corresponding plate_multiplier.
                r = 1
                shape = list(shape)
                tiles_ind = list(tiles_ind)
                for j in range(len(shape)):
                    if shape_m[j] == 1:
                        r *= tiles_ind[j]
                        shape[j] = 1
                        tiles_ind[j] = 1

                # Combine the tuples by picking every other from tiles_ind and
                # every other from shape
                shape = functools.reduce(lambda x,y: x+y,
                                         zip(tiles_ind, shape))
                # ..and reshape the array, that is, every other axis corresponds
                # to tiles and every other to plates/dimensions in parents
                m[ind] = np.reshape(m[ind], shape)

                # Sum over every other axis
                axes = tuple(range(0,len(shape),2))
                m[ind] = r * np.sum(m[ind], axis=axes)

                # Remove extra leading axes
                ndim_parent = len(self.parents[index].get_shape(ind))
                m[ind] = utils.squeeze_to_dim(m[ind], ndim_parent)
            
            return m

        def _compute_moments(self, u_X):
            """
            Tile the plates of the parent's moments.
            """
            # Utilize broadcasting: If a tiled axis is unit length in u_X, there
            # is no need to tile it.
            u = list()
            for ind in range(len(u_X)):
                ui = u_X[ind]
                shape_u = np.shape(ui)
                if np.ndim(ui) > 0:
                    # Add variable dimensions
                    tiles_ind = tiles + (1,)*len(self.dims[ind])
                    # Utilize broadcasting: Do not tile leading empty axes
                    nd = min(len(tiles_ind), np.ndim(ui))
                    tiles_ind = tiles_ind[(-nd):]
                    # For simplicity, make tiles and shape equal length
                    (tiles_ind, shape_u) = utils.make_equal_length(tiles_ind,
                                                                   shape_u)
                    # Utilize broadcasting: Use tiling only if the parent's
                    # moment has non-unit axis length.
                    tiles_ind = [tile if sh > 1 else 1
                                 for (tile, sh) in zip(tiles_ind, shape_u)]
                        
                    # Tile
                    ui = np.tile(ui, tiles_ind)
                u.append(ui)
            return u
            
    return _Tile(X, name="tile(%s, %s)" % (X.name, tiles))
