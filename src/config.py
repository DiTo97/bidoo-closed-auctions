import os
import re


#
# Paths
#

PATH_D_root = os.path.join(
    '/',
    'content',
    'drive',
    'MyDrive',
    'Colab Notebooks',
    'bidoobot'
)

PATH_D_data = os.path.join(PATH_D_root, 'data')
PATH_D_logs = os.path.join(PATH_D_root, 'logs')

PATH_D_data_raw = os.path.join(PATH_D_data, 'raw')
PATH_D_data_processed = os.path.join(PATH_D_data, 'processed')

#
# Metadata
#

TZ = 'CET'

#
# Regular expressions
#

RE_F_access = re.compile('access_\d{4}\d{2}\d{2}.log')
RE_F_error  = re.compile('error_\d{4}\d{2}\d{2}.log')

#
# Strings
#

STR_MKT_open = 'Opening auction market...'
STR_MKT_close = 'Closing auction market...'
