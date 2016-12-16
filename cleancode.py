# noqa: cov, E501
import os
import sys
import unittest
import warnings
import traceback
import doctest

import re

debug = print


class TestLoader(unittest.TestLoader):
    def loadTestsFromModule(self, module, use_load_tests=True):
        self.module = module
        return super().loadTestsFromModule(module, use_load_tests)


def loadTarget(target):
    """
    """
    debug("Attempting to load target '{}'".format(target))

    if (target is None) or (not os.path.isfile(target)):
        assert(False)
    need_cleanup = False
    target = os.path.abspath(target)
    target_parent = os.path.dirname(target)
    cwd = os.getcwd()
    if target_parent != cwd:
        os.chdir(target_parent)
        cwd = target_parent
    if cwd != sys.path[0]:
        need_cleanup = True
        sys.path.insert(0, cwd)
    dotted_path = os.path.basename(target).replace('.py', '').replace(os.sep, '.')
    debug("dotted_path is '{}'".format(dotted_path))

    loader = TestLoader()
    tests = loader.loadTestsFromName(dotted_path)
    try:
        doctests = doctest.DocTestSuite(loader.module)
    except ValueError:
        doctests = None

    # unload module after get it's tests
    for name, mod in list(sys.modules.items()):
        if mod is loader.module:
            del sys.modules[name]

    if need_cleanup:
        sys.path.remove(cwd)
    return tests, doctests


class TestResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.unsuccess_list = []

    def addError(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().
        """
        super().addError(test, err)
        self.unsuccess_list.append((test, err))

    def addFailure(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info()."""
        super().addFailure(test, err)
        self.unsuccess_list.append((test, err))

    def addSubTest(self, test, subtest, err):
        """Called at the end of a subtest.
        'err' is None if the subtest ended successfully, otherwise it's a
        tuple of values as returned by sys.exc_info().
        """
        super().addSubTest(test, subtest, err)
        self.unsuccess_list.append((test, err))

    def addUnexpectedSuccess(self, test):
        """Called when a test was expected to fail, but succeed."""
        super().addUnexpectedSuccess(test)
        self.unsuccess_list.append((test, (None, None, None)))


def getTestCaseLine(case):
    if hasattr(case, '_dt_test'):
        # doctest DocTestCase
        return (case._dt_test.filename,
                case._dt_test.lineno,
                case._dt_test.name,
                True)

    if case._testMethodName != 'runTest':
        # unittest class case
        testfunc = getattr(case, case._testMethodName)
    else:
        # unittest function case
        testfunc = case._testFunc
    case_info = (testfunc.__code__.co_filename,
                 testfunc.__code__.co_firstlineno,
                 testfunc.__name__,
                 False)
    return case_info


def matchFileInTraceback(filename, tb):
    if not isinstance(tb, list):
        tb = traceback.extract_tb(tb)
    filename = os.path.abspath(filename)
    for tb_filename, lineno, funcname, line in tb[::-1]:
        tb_filename = os.path.abspath(tb_filename)
        if tb_filename == filename:
            return tb_filename, lineno, funcname, line

    return tb[-1]


def runFlake8(target):
    import pep8
    import flake8.main as flake8

    # suppress dafault stdout errors from pep8.StandardReport
    class Pep8Report(pep8.StandardReport):
        def get_file_results(self):
            return self.file_errors

    flake8_style = flake8.get_style_guide(paths=[target], verbose=1, reporter=Pep8Report)
    report = flake8_style.check_files()
    errors = []

    # the actual errors is store in `_deferred_print`
    for line_number, offset, code, text, doc in report._deferred_print:
        errors.append({
            'path': report.filename,
            'row': report.line_offset + line_number,
            'col': offset + 1,
            'code': code,
            'text': text,
        })
    return errors


def runUnitTest(target, run_doctest=True):
    from coverage import coverage as Coverage
    warns_list = []
    testerrors = []
    result = TestResult()
    cov = Coverage()
    cov.start()
    with warnings.catch_warnings():
        # suppress dafault stdout warning from python builtin
        def warn_record_traceback(message, category, filename, lineno,
                                  file=None, line=None):
            exc_type, exc_value, exc_tb = sys.exc_info()
            warns_list.append((message, traceback.extract_stack()))

        warnings.showwarning = warn_record_traceback
        try:
            test, doctests = loadTarget(target)
            result.startTestRun()
            test.run(result)
            if doctests and run_doctest:
                doctests.run(result)
            result.stopTestRun()
        except:
            error_type, error_value, error_traceback = sys.exc_info()
            filename, lineno, funcname, line = matchFileInTraceback(target, error_traceback)
            testerrors.append({'path': filename,
                               'row': int(lineno),
                               'col': 1,
                               'code': 'U202',
                               'text': repr(error_value)})

    cov.stop()

    warns = []
    for message, warn_traceback in warns_list:
        filename, lineno, funcname, line = matchFileInTraceback(target, warn_traceback)
        warns.append({'path': filename,
                      'row': lineno,
                      'col': 1,
                      'code': 'U101',
                      'text': message})

    
    for test, (error_type, error_value, error_traceback) \
            in result.unsuccess_list:
        casefile, caselineno, casename, is_doctest = getTestCaseLine(test)
        if error_type is not None:
            # when result is not UnexpectedSuccess
            if is_doctest:
                filename, lineno, funcname, excepted, got = \
                    doctest_regex(error_value.args[0]).groups()
                testerrors.append({'path': filename,
                                   'row': int(lineno),
                                   'col': 1,
                                   'code': 'U203',
                                   'text': 'Excepted: {}; Got: {}'.format(excepted, got)})
            else:
                filename, lineno, funcname, line = matchFileInTraceback(casefile, error_traceback)
                testerrors.append({'path': filename,
                                   'row': lineno,
                                   'col': 1,
                                   'code': 'U202',
                                   'text': repr(error_value)})

        testerrors.append({'path': casefile,
                           'row': caselineno,
                           'col': 1,
                           'code': 'U201',
                           'text': '{} failed'.format('doctest' if is_doctest else 'unittest')})

    missing_linenos = cov.analysis(target)[2]
    missings = []
    for lineno in missing_linenos:
        missings.append({'path': target,
                         'row': lineno,
                         'col': 0,
                         'code': 'V100',
                         'text': 'never executed'})

    return warns, testerrors, missings


pep8_format = '%(path)s:%(row)d:%(col)d: %(code)s %(text)s'
noqa = re.compile(r'\s*# noqa[:=]\s*([ ,a-zA-Z0-9]*)', re.I).search
doctest_regex = re.compile(r'File "(.*?)", line (\d+), in (.*?)\n'
                           r'Failed example:\n\s+.*?\n'
                           r'Expected:\n\s+(.*?)\n'
                           r'Got:\n\s+(.*)'
                           ).search


def formatAndFilterErrors(noqas, errors):
    cwd = os.getcwd()
    for error in errors:
        if all(not error['code'].startswith(noqa) for noqa in noqas):
            error = error.copy()
            error['path'] = os.path.relpath(error['path'], cwd)
            yield pep8_format % error


def runIter(target):
    with open(target, encoding='utf-8') as fp:
        matches = [noqa(line).group(1).split(',') for line in fp if noqa(line)]
        noqas = [word.strip() for match in matches for word in match]
    
    if 'pep8' not in noqas and 'flake8' not in noqas:
        errors = runFlake8(target)
        if errors:
            yield from formatAndFilterErrors(noqas, errors)

    warns, testerrors, missings = runUnitTest(target, run_doctest='doctest' not in noqas)
    if 'test' not in noqas and (warns or testerrors):
        yield from formatAndFilterErrors(noqas, warns + testerrors)
    elif 'cov' not in noqas:
        yield from formatAndFilterErrors(noqas, missings)


def runAndPrint(target):
    for line in runIter(target):
        print(line)


if __name__ == '__main__':
    runAndPrint(sys.argv[1])
