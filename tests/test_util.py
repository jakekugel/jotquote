# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

from __future__ import unicode_literals

import os
import shutil


def init_quotefile(tempdir, data_filename):
    """Copy test quote file to the temp directory used for the test"""
    test_module_directory = os.path.dirname(__file__)
    test_data_source = os.path.join(test_module_directory, "testdata", data_filename)
    test_data_target = os.path.join(tempdir, data_filename)

    shutil.copyfile(test_data_source, test_data_target)
    return test_data_target
