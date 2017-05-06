# -*- coding: utf-8 -*-
"""
Created on Fri May 05 03:09:54 2017

@author: chenym
"""

import warnings
from utils import build_input_path, build_image_path
import numpy as np
import nibabel as nib

REG_FUNC_OPTS = []

# nipy packages
try:
    from nipy import load_image, save_image
    from nipy.algorithms.registration import HistogramRegistration, resample, Affine
    REG_FUNC_OPTS.append('nipy')
except ImportError:
    warnings.warn("nipy modules are not available.")

# pypreprocess packages
try:
    from pypreprocess.coreg import Coregister
    from nilearn.image import resample_img
    from sklearn.externals.joblib import Memory # for caching!
    REG_FUNC_OPTS.append('pypreprocess')
except ImportError:
    warnings.warn("pypreprocess modules are not available.")

def registration(anat, func, mni, reg_dir = 'reg', 
                 registration_to_use = 'nipy', _nb = '2', **func_params):
    # choose which registration algorithm from which package to use    
    affine_registration = _choose_registration_function(registration_to_use)
    
    # construct paths to anat, func, mni file
    anat_path = build_input_path(anat, reg_dir)
    func_path = build_input_path(func, reg_dir)
    mni_path = build_input_path(mni, reg_dir)
    
    # construct paths to futher outputs
    op_1 = build_output_path(func, anat, reg_dir, _nb)
    op_2 = build_output_path(anat, mni, reg_dir, _nb)
    op_3 = build_output_path(func, mni, reg_dir, _nb)
    
    # first register from functional space to anatomical (highres) space
    T1 = affine_registration(func_path, anat_path, op_1[0], op_1[1], op_1[2], 
                             **func_params)
    
    # then register from anatomical (highres) space to mni (standard) space
    T2 = affine_registration(anat_path, mni_path, op_2[0], op_2[1], op_2[2], 
                             **func_params)
                             
    # then register from functional space to mni (standard) space by directly
    # applying a transformation matrix
    T3 = _concat_transforms(T1, T2, registration_to_use)
    T3 = affine_registration(func_path, mni_path, op_3[0], op_3[1], op_3[2], 
                             T = T3, **func_params)

def build_output_path(name_in, name_ref, reg_dir, name_conn):
    """
    build the paths to 3 output files for each registration process. 
    
    inputs:
        name_in, name_ref: name of files. str with no extention
        reg_dir: directory for load and save
        name_conn: string to bridge strings and show directions. e.g. 2, _to_
    return: a list of file paths, with orders like this:
            ['in2ref.nii.gz', 'in2ref.mat', 'ref2in.mat']
    """
    ls = []
    ls.append(build_image_path(name_in+name_conn+name_ref, reg_dir))
    ls.append(build_image_path(name_in+name_conn+name_ref, reg_dir, fileext='.mat'))
    ls.append(build_image_path(name_ref+name_conn+name_in, reg_dir, fileext='.mat'))
    
    return ls

def _choose_registration_function(registration_to_use):
    
    registration_options = {'nipy':affine_registration_nipy,
                            'pypreprocess':affine_registration_pypreprocess}

    if registration_to_use not in REG_FUNC_OPTS:
        err_msg = ("option %s is not valid. either it does not belong to"
        " the following list: %s, or there was an error during import. "
        ) % (registration_to_use, registration_options.keys())
        raise ValueError(err_msg)
    
    return registration_options[registration_to_use]

def _concat_transforms(T1, T2, registration_to_use):
    if registration_to_use == 'nipy':
        return T2.as_affine().dot(T1.as_affine())
    if registration_to_use == 'pypreprocess':
        print T1
        print T2
        return T1 + T2
    raise KeyError(registration_to_use)

def affine_registration_nipy(in_path, ref_path, out_path, 
                             in_ref_mat = '', ref_in_mat = '',
                             T = None, **func_params):
    """
    Affine registation and resampling. Uses Histogram registration from NIPY. 
    
    inputs:
        in_path: path to the source (input) image.
        ref_path: path to the target (reference) image.
        out_path: path to use to save the registered image. 
        in_ref_mat: if bool(in_ref_mat) is True, save the 4x4 transformation
                    matrix to a text file <in_ref_mat>. 
        ref_in_mat: if bool(ref_in_mat) is True, save the reverse of the 4x4
                    transformation matrix to a text file <ref_in_mat>. 
        T: affine transformation to use. if None, T will be estimated using 
           HistogramRegistration and optimizers; if type(T) is not Affine, 
           T = Affine(array=T)
        reg_kwargs: extra parameters to HistogramRegistration.__init__
        
    return T
    """

    source_image = load_image(in_path)
    target_image = load_image(ref_path)

    if T is None:
        print('assess the affine transformation using histogram registration. ')
        R = HistogramRegistration(source_image, target_image)
        T = R.optimize('affine', optimizer='powell')
    else:
        if type(T) is not Affine:
            T = Affine(array=T)
        print('using a predefined affine:\n%s\nwith a 4x4 matrix:\n%s\n' % (T, T.as_affine()))
    It = resample(source_image, T.inv(), reference=target_image)
    # the second argument of resample takes an transformation from ref to mov
    # so that's why we need T.inv() here
    save_image(It, out_path)
    if in_ref_mat:
        np.savetxt(in_ref_mat, T.as_affine())
    if ref_in_mat:
        np.savetxt(ref_in_mat, T.inv().as_affine())
    
    return T

def affine_registration_pypreprocess(in_path, ref_path, out_path, 
                                     in_ref_mat = '', ref_in_mat = '',
                                     T = None, resample = False, reg_kwargs = {}):
    """
    Affine registation and resampling. Uses Histogram registration from NIPY. 
    
    inputs:
        in_path: path to the source (input) image.
        ref_path: path to the target (reference) image.
        out_path: path to use to save the registered image. 
        in_ref_mat: if bool(in_ref_mat) is True, save the 4x4 transformation
                    matrix to a text file <in_ref_mat>. 
        ref_in_mat: if bool(ref_in_mat) is True, save the reverse of the 4x4
                    transformation matrix to a text file <ref_in_mat>. 
        T: affine transformation to use. if None, T will be estimated using 
           HistogramRegistration and optimizers; if type(T) is not Affine, 
           T = Affine(array=T)
        reg_kwargs: extra parameters to HistogramRegistration.__init__
        
    """
    source = nib.load(in_path)
    target = nib.load(ref_path)
    
    coreg = Coregister()
    
    if T is None:
        mem = Memory("affine_registration_pypreprocess_cache")
        coreg = mem.cache(coreg.fit)(target, source) # fit(target, source)
    else:
        T_ = np.array(T)
        if T_.size != 6 or T_.dtype != float:
            raise ValueError('T should either be None or ndarray with size 6 and dtype float')
        print('using predefined T = %s' % T)
        coreg.params_ = T_
    
    img = coreg.transform(source)[0]
    if resample:
        img = resample_img(img, target.affine, target.shape)
    nib.save(img, out_path)
    if in_ref_mat:
        np.savetxt(in_ref_mat,  coreg.params_)
    if ref_in_mat:
        np.savetxt(ref_in_mat, -coreg.params_)
    
    return coreg.params_
    
if __name__ == '__main__':
    registration('highres','example_func', 'standard', 'reg')
    registration('highres','example_func', 'standard', 'reg2',
                 registration_to_use='pypreprocess')
    from nilearn.plotting import plot_epi
    plot_epi('sample2/example_func2highres.nii.gz', cut_coords=(-12,14,22))
    plot_epi('sample2/highres2standard.nii.gz', cut_coords=(-12,14,22))
    plot_epi('sample2/example_func2standard.nii.gz', cut_coords=(-12,14,22))
    
    plot_epi('reg/example_func2highres.nii.gz', cut_coords=(-12,14,22))
    plot_epi('reg/highres2standard.nii.gz', cut_coords=(-12,14,22))
    plot_epi('reg/example_func2standard.nii.gz', cut_coords=(-12,14,22))
    
    plot_epi('reg2/example_func2highres.nii.gz', cut_coords=(-12,14,22))
    plot_epi('reg2/highres2standard.nii.gz', cut_coords=(-12,14,22))
    plot_epi('reg2/example_func2standard.nii.gz', cut_coords=(-12,14,22))