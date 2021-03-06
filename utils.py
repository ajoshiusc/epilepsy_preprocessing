# -*- coding: utf-8 -*-
"""
Created on Tue Apr 18 22:07:18 2017

@author: chenym

some utility functions... need some organization
"""

import numpy as np
from nipy.core.api import Image
import os.path
import re

class BrainImageFileNotFoundError(Exception):
    pass

def build_input_path(name_in, folder):
    return build_image_path(name_in, folder, check_exist=True)

def build_output_path(name_in, name_out, folder, name_ext='out', name_conv='replace'):
    name_in = re.sub('\_+\Z','',name_in)
    name_ext = re.sub('\A\_+','',name_ext)
    
    if not name_out:
        if name_conv == 'replace':
            name_in = name_in.split('_')[0] # remove extras, then accumulate
        elif name_conv != 'accumulate':
            raise ValueError("expect one of the two naming convensions: ['replace','accumulate'], received: %s"%name_conv)
        name_out = name_in + '_' + name_ext
    out_file = build_image_path(name_out, folder)
    return name_out, out_file
        

def build_image_path(filename, filedir, fileext = '.nii.gz', check_exist=False):
    
    path = os.path.join(filedir, filename + fileext)
    if not check_exist or os.path.isfile(path):
        return path
    else:
        raise BrainImageFileNotFoundError('path: '+path)

#def get_extra_kwargs(func, kwargs):
#    if func.func_name not in kwargs.keys():
#        return {})
#    return kwargs[func.func_name]

class AllFeatures:
    
    def __init__(self, func, param_dict):
        self.func = func
        self.func_name = func.__name__
        if self.func_name in param_dict and type(param_dict[self.func_name]) is dict:
            self.param = param_dict[self.func_name]
        else:
            self.param = {}
    
    def run(self, *args, **kwargs):
        if not self.param:
            print 'no extra parameter selected for %s' % self.func_name
        else:
            print 'extra parameter selected for %s' % self.func_name
        _kwargs = dict(kwargs) # shallow copy
        for key in self.param: # update param
            _kwargs[key] = self.param[key]
        print 'run: %s(%s **%s)'%(
        self.func_name, self._trimstr(str(args)[1:-1]), self._trimstr(_kwargs))
        return self.func(*args, **_kwargs)
    
    def _trimstr(self, obj):
        obj_str = str(obj)
        if len(obj_str) > 50:
            return obj_str[:50] + ' ...'
        return obj_str

def flip_x_axis(img_obj, cmap=None, meta=None):
    """
    flip the x-axis of image data    
    
    background:
    Two orientations have been used in brain imaging volume data: s-form and
    q-form. S-form is the default orientation (and the only output option) of
    brainsuite, which is "left to right (x), then posterior to anterior (y), 
    then inferior to superior (z)." Q-form is the used by FSL (and thus) 
    fcon_1000 and C-PAC. The orientation of q-form is "Right-to-Left 
    Posterior-to-Anterior Inferior-to-Superior". 
    
    As a result, voxel data is flipped along x-axis between q-form and s-form. 
    Now, this normally won't be an issue, since by having different mappers, 
    i.e. different affine transformations, data in voxel space, whether using
    s- and q-form, will eventually have the same orientation once they are 
    mapped into the world's (millimeter) coordinate system. But since we are 
    trying to compare the results between Brainsuite and fcon_1000, it will be 
    convinient to convert s-form to q-form (and maybe vice versa). 
    
    inputs:
        img_obj: nipy Image object. Note: this img_obj is not preserved
        cmap: a given coordmap that can be used to construct a new image.
    
    return:
        new Image object
    
    """
    data = img_obj.get_data()
    data = np.flipud(data)
    
    if cmap is None:
        cmap = img_obj.coordmap
        cmap.affine[0,:] = -cmap.affine[0,:] # need to double check the math...
    
    return Image(data,cmap,meta) # have not tested meta!=None yet