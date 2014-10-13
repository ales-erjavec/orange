
import errno

from collections import namedtuple
from xml.etree import ElementTree

import pkg_resources

from PyQt4.QtGui import (
    QDialog, QVBoxLayout, QLabel, QTreeView, QHeaderView, QDialogButtonBox,
    QStandardItemModel, QStandardItem
)

from PyQt4.QtCore import Qt, QObject, QThread, QCoreApplication, QEvent
from PyQt4.QtCore import pyqtSignal as Signal

from ..gui.utils import message_critical

requirement = namedtuple(
    "requirement",
    ["name", "spec", "link"]
)


def scheme_requires(scheme_text):
    """
    Return a list of requirements for loading a scheme.
    """
    scheme = ElementTree.fromstring(scheme_text)
    requires = []
    for package in scheme.findall("requires/package"):
        requires.append(
            requirement(
                package.attrib.get("name"),
                package.attrib.get("spec", None),
                package.attrib.get("link", None),
            )
        )
    names = [r.name for r in requires]
    for node in scheme.findall("nodes/node"):
        project = node.attrib.get("project_name", "")
        if project not in names:
            requires.append(requirement(project, None, None))
            names.append(project)

    return [req for req in requires if not is_req_satisfied(req)]


def is_req_satisfied(req):
    """
    Is a requirement satisfied (installed).
    """
    if req.spec:
        req_string = "{} {}".format(req.name, req.spec)
    else:
        req_string = req.name

    reqs = list(pkg_resources.parse_requirements(req_string))
    assert len(reqs) == 1
    return is_requirement_available(reqs[0])


def is_requirement_available(requirement):
    """
    Is `requirement` (`pkg_resources.Requirement`) available on sys.path.
    """
    try:
        pkg_resources.get_distribution(requirement)
    except pkg_resources.DistributionNotFound:
        return False
    except pkg_resources.VersionConflict:
        # ???
        return False
    else:
        return True


class InstallPackagesDialog(QDialog):
    def __init__(self, parent=None):
        super(InstallPackagesDialog, self).__init__(parent)

        layout = QVBoxLayout()
        self.__text = QLabel(
            self.tr("The following packages need to be installed")
        )

        self.__text.setWordWrap(True)
        layout.addWidget(self.__text)

        self.__informativeText = QLabel()
        self.__informativeText.setWordWrap(True)
        layout.addWidget(self.__informativeText)

        self.__view = QTreeView(
            selectionMode=QTreeView.NoSelection,
            alternatingRowColors=True,
            rootIsDecorated=False,
            editTriggers=QTreeView.NoEditTriggers
        )
        self.__view.header().setResizeMode(0, QHeaderView.Stretch)
        self.__view.header().setResizeMode(1, QHeaderView.ResizeToContents)

        layout.addWidget(self.__view)
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.__accepted)
        bbox.rejected.connect(self.reject)

        layout.addWidget(bbox)

        self.setLayout(layout)
        self.setMinimumWidth(400)

    def setPackages(self, requires):
        self.__packages = requires
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels([self.tr("Name"), self.tr("Version")])
        for req in requires:
            item = QStandardItem(req.name)
            item.setFlags(Qt.ItemIsEnabled)
            item.setData(req, Qt.UserRole)
            item.distribution = req

            model.appendRow([item, QStandardItem("...")])

        self.__view.setModel(model)
        self.__view.resizeColumnToContents(1)

    def setText(self, text):
        self.__text.setText(text)

    def __accepted(self):
        self.setDisabled(True)
        self.__thread = thread = QThread(self)
        thread.start()
        installer = Installer(packages=self.__packages)
        installer.moveToThread(thread)
        installer.finished.connect(self.__on_installerFinished)
        installer.error.connect(self.__on_installerError)
        installer.start()
        self.__installer = installer

    def __on_installerFinished(self):
        self.accept()
        self.__thread.quit()

    def __on_installerError(self, returncode, program, output):
        message_critical(
            "{!r} exited with error code {}".format(str(program), returncode),
            title="Error",
            details=output,
            parent=self
        )
        self.reject()
        self.__thread.quit()


class Installer(QObject):
    statusChanged = Signal(unicode)
    started = Signal()
    finished = Signal()
    stdout = Signal(unicode)
    error = Signal(int, str, str)

    def __init__(self, parent=None, packages=[]):
        QObject.__init__(self, parent)
        self.__packages = packages
        self.__interupt = False

    def start(self):
        QCoreApplication.postEvent(self, QEvent(QEvent.User))

    def interupt(self):
        self.__interupt = True

    def customEvent(self, event):
        self.run()

    def run(self):
        self.started.emit()
        for pkg in self.__packages:
            self.statusChanged.emit("Installing {0}".format(pkg.name))
            if pkg.link is None:
                process = easy_install_process([pkg.name])
            else:
                process = easy_install_process(
                    ["--find-links", pkg.link, pkg.name]
                )

            returncode, output = self.__subprocessrun(process)

            if returncode != 0:
                self.error.emit(returncode, 'easy_install', output)
                return

        self.finished.emit()

    def __subprocessrun(self, process):
        output = []
        while process.poll() is None:
            try:
                line = process.stdout.readline()
            except IOError as ex:
                if ex.errno != errno.EINTR:
                    raise
            else:
                self.stdout.emit(line)
                output.append(line)
                print line,

        # Read remaining output if any
        line = process.stdout.read()
        if line:
            self.stdout.emit(line)
            output.append(line)
            print line
        return process.returncode, "".join(output)

import sys
import os
import pipes
import subprocess
import textwrap


def easy_install_process(args, bufsize=-1):
    from setuptools.command import easy_install
    # Check if easy_install supports '--user' switch
    options = [opt[0] for opt in easy_install.easy_install.user_options]
    has_user_site = "user" in options

    if has_user_site and not hasattr(sys, "real_prefix"):
        # we're not in a virtualenv
        # (why are we assuming we have write permissions in the
        # virtualenv's site dir?)
        args = ["--user"] + args

    # properly quote arguments if necessary
    args = map(pipes.quote, args)

    script = textwrap.dedent("""
        import sys
        from setuptools.command.easy_install import main
        sys.exit(main({args!r}))
    """)
    script = script.format(args=args)

    return python_process(["-c", script], bufsize=bufsize)


def pip_process(args, ):
    script = textwrap.dedent("""
        import sys
        from pip import main
        sys.exit(main({args!r}))
    """)
    args = map(pipes.quote, args)
    return python_process(["-c", script], bufsize=-1)


def python_process(args, script_name=None, cwd=None, env=None, **kwargs):
    """
    Run a `sys.executable` in a subprocess with `args`.
    """
    executable = sys.executable
    if os.name == "nt" and os.path.basename(executable) == "pythonw.exe":
        # Don't run the script with a 'gui' (detached) process.
        dirname = os.path.dirname(executable)
        executable = os.path.join(dirname, "python.exe")
        # by default a new console window would show up when executing the
        # script
        startupinfo = subprocess.STARTUPINFO()
        if hasattr(subprocess, "STARTF_USESHOWWINDOW"):
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            # This flag was missing in inital releases of 2.7
            startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW

        kwargs["startupinfo"] = startupinfo

    if script_name is not None:
        script = script_name
    else:
        script = executable

    process = subprocess.Popen(
        [script] + args,
        executable=executable,
        cwd=cwd,
        env=env,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        **kwargs
    )

    return process
