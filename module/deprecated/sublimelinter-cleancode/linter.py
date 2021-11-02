import os
import sys
import imp

from SublimeLinter.lint import PythonLinter


_thisdir = os.path.dirname(__file__)
if _thisdir not in sys.path[0]:
    sys.path.insert(0, _thisdir)
import cleancode
imp.reload(cleancode)


class Clean8(PythonLinter):

    syntax = ('python', 'python3')
    cmd = ('python',)

    # The following regex marks these pyflakes and pep8 codes as errors.
    # All other codes are marked as warnings.
    #
    # Pyflake Errors:
    #  - F402 import module from line N shadowed by loop variable
    #  - F404 future import(s) name after other statements
    #  - F812 list comprehension redefines name from line N
    #  - F823 local variable name ... referenced before assignment
    #  - F831 duplicate argument name in function definition
    #  - F821 undefined name name
    #  - F822 undefined name name in __all__
    #
    # Pep8 Errors:
    #  - E112 expected an indented block
    #  - E113 unexpected indentation
    #  - E901 SyntaxError or IndentationError
    #  - E902 IOError
    #
    # CleanCode Errors:
    #  - U201 unittest failed
    #  - U202 unittest assertion
    #  - U203 doctest assertion

    regex = (
        r'^.+?:(?P<line>\d+):(?P<col>\d+): '
        r'(?:(?P<error>(?:F(?:40[24]|8(?:12|2[123]|31))|E(?:11[23]|90[12])|U20[123]))|'
        r'(?P<warning>\w\d+)) '
        r'(?P<message>\'(.*\.)?(?P<near>.+)\' imported but unused|.*)'
    )
    regex = (
        r'^.+?:(?P<line>\d+):(?P<col>\d+):'
        r'(?:(?P<error> (?=F(?:40[24]|8(?:12|2[123]|31))|E(?:11[23]|90[12])|U20[123]))|'
        r'(?P<warning> (?=\w\d+)))'
        r'(?P<message>\'(.*\.)?(?P<near>.+)\' imported but unused|.*)'
    )
    multiline = True
    module = 'cleancode'

    def check(self, code, filename):
        return list(cleancode.runIter(filename))
