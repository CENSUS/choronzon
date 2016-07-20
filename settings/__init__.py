import platform
if platform.system() == 'Linux':
    from system import *
elif platform.system() == 'Windows':
    from winsystem import *
